#!/usr/bin/env python3
"""Paso 3: arma la línea de tiempo (un clip por región de voz) y VERIFICA el corte (align.py: Whisper con tiempos por palabra).
uso: python3 -I edl.py <workdir> [--no-verify] [--no-aire]   → <workdir>/edl.json (+ cut.wav, words.json, qa_words.json, aire.md)
Después de verificar corre aire.py (segunda pasada): saca las pausas que quedaron en el corte y las muletillas que Whisper no transcribe
(voz sin palabra, «eh/este/bueno» fuera del guion); si encontró algo, reescribe tight.json y vuelve a armar y verificar el corte.
Lee config.json (fps, tail = segundos extra al final; post_pad 0.08 / post_pad_end 0.14 = aire después de la voz).
Garantías del corte (no se negocian):
  · entradas redondeadas hacia ATRÁS y salidas hacia ADELANTE (nunca se come el inicio ni la última letra por redondeo a frames)
  · si la voz sigue sonando justo en el punto de corte, el corte se corre (hasta 3 frames) a donde ya hay silencio
  · dos clips nunca repiten audio: si sus márgenes se pisan, el corte pasa al frame más silencioso de la zona común
  · clips contiguos en el origen (sin corte real) se funden en uno solo → no hay salto de encuadre ni fade en el medio
"""
import os as _o,sys as _s,subprocess as _sp
if _o.name=='nt' and __name__=='__main__' and not _s.flags.utf8_mode: _s.exit(_sp.run([_s.executable,'-X','utf8','-I',_o.path.abspath(__file__),*_s.argv[1:]]).returncode)  # Windows: acentos en UTF-8
import json,os,sys,subprocess,wave,struct,math
W=sys.argv[1];cfg=json.load(open(os.path.join(W,'config.json')))
import atexit,time;sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)));import timing;_t0=time.time();atexit.register(lambda:timing.log(W,'Línea de tiempo + verificación',time.time()-_t0))
FPS=cfg.get('fps',30);PRE=0.04;TAIL=cfg.get('tail',1.2)
POST=cfg.get('post_pad',0.08);POST_END=cfg.get('post_pad_end',0.14)
P=json.load(open(os.path.join(W,'tight.json')))
# energía por frame (dB) del audio que se transcribió: es la MISMA línea de tiempo que el crudo conformado (conform.py)
w=wave.open(os.path.join(W,'audio16k.wav'));SR=w.getframerate();raw=w.readframes(w.getnframes());S=struct.unpack('<%dh'%(len(raw)//2),raw);NFR=int(len(S)/SR*FPS)
N=SR/FPS
def edb(k):
    seg=S[int(k*N):int((k+1)*N)]
    return 20*math.log10(max(1,math.sqrt(sum(x*x for x in seg)/len(seg)))/32768) if seg else -99
ENV=[edb(k) for k in range(NFR)]
FLOOR=sorted(ENV)[len(ENV)//10];QUIET=max(min(max(FLOOR+20,-46),-34),FLOOR+8)   # por debajo de QUIET el frame ya es silencio/ruido de fondo. En una sala ruidosa (piso −38) el ruido fluctúa hasta −33: con −34 fijo la pausa
# contaba como «voz» y los huecos de ≤ 3 frames se cerraban dejando la pausa entera (GUION3 30/10/2026) → nunca menos de piso + 8 (la «cola» de tighten.py)
e_=lambda k:ENV[k] if 0<=k<NFR else -99
# 1 · márgenes y redondeo hacia afuera
iv=[]
for ci,p in enumerate(P):
    nx=P[ci+1] if ci+1<len(P) else None;end=(not nx) or nx['seg']!=p['seg'] or p['t'].rstrip().endswith(('.',',',':',';','?','!','…'))
    post=p.get('post',POST_END if end else POST)   # aire.py achica los márgenes de los empalmes donde quedaba una pausa
    a=p['a']-p.get('pre',PRE);b=p['b']+post+(TAIL if ci==len(P)-1 else 0)
    iv.append([max(0,math.floor(a*FPS+1e-6)),min(NFR,math.ceil(b*FPS-1e-6))])
if cfg.get('start_zero') and iv: iv[0][0]=0   # gancho visual: el video arranca en el segundo 0 del master (silencio inicial a propósito); los subtítulos siguen a la voz
# 2 · si la voz sigue sonando en el punto de corte, correr el corte hasta donde ya hay silencio (sin invadir al vecino)
snap=0
for i,v in enumerate(iv):
    lim_o=NFR if i==len(iv)-1 or iv[i+1][0]<v[0] else iv[i+1][0]   # vecino siguiente en orden cronológico
    k=0
    while k<3 and v[1]<lim_o and e_(v[1]-1)>QUIET: v[1]+=1;k+=1;snap+=1
    lim_i=0 if i==0 or iv[i-1][1]>v[1] else iv[i-1][1]
    k=0
    while k<2 and v[0]>lim_i and e_(v[0])>QUIET: v[0]-=1;k+=1;snap+=1
# 3 · nada de audio repetido: si dos clips consecutivos (en orden cronológico) se pisan, el corte pasa al frame más callado de la zona común
ovl=0
for i in range(len(iv)-1):
    a,b=iv[i],iv[i+1]
    if a[0]<=b[0]<a[1]:
        m=min(range(b[0],a[1]+1),key=lambda k:(e_(k-1)+e_(k))/2)   # corte = límite entre los frames k-1 y k
        a[1]=m;b[0]=m;ovl+=1
# 3b · hueco de ≤3 frames con voz sonando en el empalme = no había pausa real: se cierra (queda continuo, sin corte ni fade)
gap=0
for i in range(len(iv)-1):
    a,b=iv[i],iv[i+1]
    if 0<b[0]-a[1]<=3 and (e_(a[1]-1)>QUIET or e_(b[0])>QUIET): a[1]=b[0];gap+=1
# 4 · clips + subtítulos. Piezas contiguas en el origen (mismo segmento) = un solo clip (no hay corte real)
clips=[];caps=[];t=0;pieces=[]
for ci,p in enumerate(P):
    sin,sout=iv[ci];d=sout-sin
    if d<=0: continue
    if clips and clips[-1]['src_out']==sin and clips[-1]['seg']==p['seg']:
        c=clips[-1];c['src_out']=sout;c['tl_out']+=d;c['text']+=' '+p['t']
    else: clips.append(dict(i=len(clips),seg=p['seg'],src_in=sin,src_out=sout,tl_in=t,tl_out=t+d,text=p['t'],pieces=[]))
    clips[-1]['pieces'].append(ci);t+=d;pieces.append((len(clips)-1,p,ci))
for k,c in enumerate(clips):   # fade de 1 frame (dentro del margen de silencio) solo donde hay un corte real
    c['fade_in']=k==0 or clips[k-1]['src_out']!=c['src_in']
    c['fade_out']=k==len(clips)-1 or clips[k+1]['src_in']!=c['src_out']
for ci,p,pi in pieces:
    c=clips[ci];words=p['t'].split();groups=[];cur=[]
    for wd in words:
        cur.append(wd)
        if len(' '.join(cur))>=14 or wd.endswith((',',':','?','...','!')): groups.append(cur);cur=[]
    if cur:
        if groups and len(' '.join(cur))<6: groups[-1]+=cur
        else: groups.append(cur)
    pa,pb=p['a'],p['b'];tot=sum(len(' '.join(g)) for g in groups) or 1;s=pa
    TL=lambda x:int(round((x*FPS-c['src_in'])+c['tl_in']))   # tiempo del origen → fotograma de la línea de tiempo
    for g in groups:
        d=(pb-pa)*len(' '.join(g))/tot;wl=[];ws=s;gl=sum(len(wd) for wd in g)
        for wd in g:
            wdur=d*len(wd)/gl;wl.append(dict(w=wd,s=TL(ws),e=TL(ws+wdur)));ws+=wdur
        caps.append(dict(clip=ci,seg=p['seg'],pi=pi,tl_in=TL(s),tl_out=TL(s+d),text=' '.join(g),words=wl));s+=d
for k in range(len(caps)-1):
    if caps[k+1]['tl_in']-caps[k]['tl_out']<12: caps[k]['tl_out']=caps[k+1]['tl_in']
json.dump(dict(fps=FPS,total=t,clips=clips,caps=caps,src_frames=NFR),open(os.path.join(W,'edl.json'),'w'),ensure_ascii=False,indent=1)
segs={}
for c in clips: segs.setdefault(c['seg'],[c['tl_in'],c['tl_out']]);segs[c['seg']][1]=c['tl_out']
print('total %.2fs · %d clips'%(t/FPS,len(clips)));print(' '.join('%d:%.1f-%.1f'%(k,v[0]/FPS,v[1]/FPS) for k,v in segs.items()))
print(f'corte: {snap} ajustes a silencio · {ovl} solapes resueltos · {gap} huecos con voz cerrados · umbral de silencio {QUIET:.0f} dB (piso {FLOOR:.0f})')
if '--no-verify' not in sys.argv:
    fc=';'.join('[0:a]atrim=start=%.4f:end=%.4f,asetpts=PTS-STARTPTS[a%d]'%(c['src_in']/FPS,c['src_out']/FPS,i) for i,c in enumerate(clips))
    fc+=';'+''.join('[a%d]'%i for i in range(len(clips)))+'concat=n=%d:v=0:a=1[out]'%len(clips)
    open(os.path.join(W,'fc_cut.txt'),'w').write(fc)
    cut=os.path.join(W,'cut.wav')
    subprocess.run(['ffmpeg','-v','error','-y','-i',os.path.join(W,'audio16k.wav'),'-/filter_complex',os.path.join(W,'fc_cut.txt'),'-map','[out]',cut],check=True)
    print('\n--- verificación del corte (Whisper SIN prompt, tiempos por palabra, clip por clip) ---',flush=True)
    SD=os.path.dirname(os.path.abspath(__file__))
    if subprocess.run([sys.executable,'-X','utf8','-I',os.path.join(SD,'align.py'),W]).returncode: sys.exit(1)
    if cfg.get('aire',True) and '--no-aire' not in sys.argv:
        if '--pass2' in sys.argv:   # ya es la segunda pasada: solo informar el aire que queda
            print('\n--- aire restante (segunda pasada) ---',flush=True);subprocess.run([sys.executable,'-X','utf8','-I',os.path.join(SD,'aire.py'),W,'--report'])
        else:
            print('\n--- aire y muletillas (pausas que quedaron, voz sin palabra, palabras fuera del guion) ---',flush=True)
            rc=subprocess.run([sys.executable,'-X','utf8','-I',os.path.join(SD,'aire.py'),W]).returncode
            if rc==3:   # tight.json cambió: volver a armar el corte y verificarlo (una sola vez)
                print('\n=== segunda pasada: corte sin ese aire ===',flush=True)
                sys.exit(subprocess.run([sys.executable,'-X','utf8','-I',os.path.abspath(__file__),W,'--pass2']+[a for a in sys.argv[2:] if a not in('--pass2',)]).returncode)
            elif rc not in(0,3): print('⚠️  aire.py falló: el corte queda sin la segunda pasada (revisar arriba)')
