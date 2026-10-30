#!/usr/bin/env python3
"""Segunda pasada del corte: saca el AIRE que quedó (pausas) y las MULETILLAS, sobre el corte ya armado y verificado.
uso: python3 -I aire.py <workdir> [--report]      (lo llama edl.py después de align.py; necesita cut.wav, edl.json, words.json, tight.json)
Por qué: tighten.py corta sobre la energía del crudo con un umbral fijo y pausas ≥ 0,25 s; las respiraciones y los «eh…/mmm» tienen
energía (no son silencio) y Whisper no los transcribe, así que quedaban adentro del corte (GUION3 30/10/2026: una muletilla de 2 s
después de «un montón de cosas» y 8–19 pausas de 0,3–0,7 s por video). Acá se trabaja sobre el CORTE con las palabras que Whisper
oyó clip por clip (tiempos fiables a ±0,1 s, align.py):
  · PAUSA: tramo por debajo del nivel de habla (relativo: p70 − 14 dB) de ≥ config.pause_max (0,30 s) → se achica a ~0,2 s
  · MULETILLA: tramo con voz (> p70 − 12 dB) donde Whisper no oyó NINGUNA palabra, ≥ config.filler_min (0,22 s), lejos de una palabra
    del guion que falte (si falta una palabra al lado, puede ser esa palabra mal oída: no se toca)
  · PALABRA FUERA DEL GUION: lo que Whisper oyó y no está en el subtítulo (eh, este, bueno, una palabra repetida), aislado de sus
    vecinas ≥ 0,15 s (o un «eh/mmm/este» conocido) y sin palabras del guion faltando cerca
Cada hueco se pasa a tiempos del crudo y se aplica en tight.json (se parte o recorta la frase; el texto se reparte por las palabras oídas);
después edl.py vuelve a armar el corte y lo verifica. Con --report no cambia nada: informa el aire que queda (⚠️ si supera los umbrales).
Sale con 3 si cambió tight.json (edl.py hace la segunda pasada), 0 si no había nada que sacar. config: "aire": false lo desactiva.
"""
import os as _o,sys as _s,subprocess as _sp
if _o.name=='nt' and __name__=='__main__' and not _s.flags.utf8_mode: _s.exit(_sp.run([_s.executable,'-X','utf8','-I',_o.path.abspath(__file__),*_s.argv[1:]]).returncode)  # Windows: acentos en UTF-8
import json,os,sys,wave,struct,math,re,unicodedata
W=sys.argv[1];REPORT='--report' in sys.argv
cfg=json.load(open(os.path.join(W,'config.json')));FPS=cfg.get('fps',30)
import atexit,time;sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)));import timing;_t0=time.time();atexit.register(lambda:timing.log(W,'Aire y muletillas',time.time()-_t0))
E=json.load(open(os.path.join(W,'edl.json')));P=json.load(open(os.path.join(W,'tight.json')))
WORDS=json.load(open(os.path.join(W,'words.json')))
try: QA=json.load(open(os.path.join(W,'qa_words.json')))
except Exception: QA=[]
PAUSE_MAX=cfg.get('pause_max',0.30);FILL_MIN=cfg.get('filler_min',0.22)
PRE=0.04;POST=cfg.get('post_pad',0.08);POST_END=cfg.get('post_pad_end',0.14);TAIL=cfg.get('tail',1.2)
PAD_PRE=cfg.get('aire_pre',0.02);PAD_POST=cfg.get('aire_post',0.04)   # márgenes de los empalmes que aire.py apretó (queda ≈ 0,1–0,15 s de aire con el redondeo a frames)
norm=lambda s:re.sub(r'[^a-z0-9ñ]','',unicodedata.normalize('NFD',s.lower().replace('ñ','\0')).encode('ascii','ignore').decode().replace('\0','ñ'))
FILLERS={'eh','ehh','ehhh','ehm','em','emm','emmm','mm','mmm','mmmm','hmm','hm','ah','ahh','ahhh','este','esteee','bueno','osea','digamos','viste','tipo','aver','a','e','o','y'}
# --- energía del corte (dB RMS, ventana 20 ms cada 10 ms) ---
w=wave.open(os.path.join(W,'cut.wav'));SR=w.getframerate();raw=w.readframes(w.getnframes());S=struct.unpack('<%dh'%(len(raw)//2),raw)
HOP=0.01;N=int(SR*HOP)
def db(i):
    seg=S[i*N:i*N+2*N]
    return 20*math.log10(max(1,math.sqrt(sum(x*x for x in seg)/len(seg)))/32768) if seg else -99
ENV=[db(i) for i in range(len(S)//N)];SRT=sorted(ENV);n=len(ENV)
SP=SRT[int(n*.7)];FL=SRT[int(n*.05)]
TH_LOW=max(FL+6,SP-14);TH_VOICE=SP-12
DUR=n*HOP
def runs(pred,minD,lo=0,hi=None):
    hi=n if hi is None else min(n,hi);st=None;out=[]
    for i in range(lo,hi+1):
        q=pred(i) if i<hi else False
        if q and st is None: st=i
        if not q and st is not None:
            if (i-st)*HOP>=minD: out.append([st*HOP,i*HOP])
            st=None
    return out
# --- palabras oídas (todas) y del guion (emparejadas) ---
heard=[x for x in WORDS if x.get('e',0)>x.get('s',0)]
matched=[x for x in heard if not x.get('x')]
cov=[False]*n   # cubierto por CUALQUIER palabra oída (las que sobran se tratan aparte)
for x in heard:
    for i in range(max(0,int(x['s']/HOP)),min(n,int(math.ceil(x['e']/HOP)))): cov[i]=True
last_voice=max([x['e'] for x in matched] or [DUR]);tail_from=min(DUR,last_voice+POST_END+0.05)   # la cola final (config.tail) se deja a propósito
falta=[x['t'] for x in QA if x.get('tipo')=='falta']
near_falta=lambda a,b:any(a-0.45<=t<=b+0.45 for t in falta)
clip_at=lambda t:next((c for c in E['clips'] if c['tl_in']/FPS<=t<c['tl_out']/FPS),E['clips'][-1] if E['clips'] else None)
def ctx(a,b):
    pv=[x['w'] for x in heard if x['e']<=a+0.05][-2:];nx=[x['w'] for x in heard if x['s']>=b-0.05][:2]
    return f"…{' '.join(pv)} | {' '.join(nx)}…"
holes=[]   # [a, b, tipo, detalle]  en segundos de la línea de tiempo
# 1 · pausas largas → dejar KEEP de aire en el medio (más los márgenes que agrega edl.py: ≈ 0,2 s en total)
pauses=runs(lambda i:ENV[i]<=TH_LOW,PAUSE_MAX,0,int(tail_from/HOP))
for a,b in pauses: holes.append([a+0.02,b-0.02,'pausa',f'{b-a:.2f} s'])   # edl.py vuelve a poner sus márgenes (≈ 0,12 s) al rearmar: queda ≈ 0,2 s de aire
# 2 · voz sin ninguna palabra (muletilla, risa, chasquido, respiración fuerte)
for a,b in runs(lambda i:ENV[i]>TH_LOW and not cov[i],FILL_MIN):   # tramo sin palabra por encima del nivel de pausa (incluye la zona gris entre dos «eh»)
    pk=max(ENV[int(a/HOP):int(b/HOP)] or [-99])
    if pk<=TH_VOICE or near_falta(a,b): continue   # sin pico de voz = cola/ruido (lo trata la regla de pausas); con una palabra del guion faltando al lado, no se toca
    i0=int(a/HOP);i1=int(b/HOP)   # extender hacia el silencio vecino no cubierto (hasta 60 ms), sin pisar palabras
    while i0>0 and not cov[i0-1] and (a-i0*HOP)<0.06: i0-=1
    while i1<n and not cov[i1] and (i1*HOP-b)<0.06: i1+=1
    h0,h1=i0*HOP,i1*HOP
    if i0>0 and cov[i0-1]:   # pega a una palabra sin pausa en el medio (los tiempos de Whisper son ±0,1 s): cortar en el punto más callado de los
        j=min(range(i0+2,min(i1,i0+16)),key=lambda k:ENV[k],default=i0+5);h0=j*HOP   # 150 ms siguientes (la transición «s → eh» suele tener un bache)
    if i1<n and cov[i1]:
        j=min(range(max(i0,i1-16),i1-2),key=lambda k:ENV[k],default=i1-5);h1=j*HOP
    if h1-h0>=0.1: holes.append([h0,h1,'muletilla',f'voz sin palabra {b-a:.2f} s · pico {pk:.0f} dB'])
# 3 · palabras oídas que no están en el guion (eh, este, bueno, repetidas) → grupos consecutivos del mismo clip
k=0
while k<len(heard):
    if not heard[k].get('x'): k+=1;continue
    g=[heard[k]];k+=1
    while k<len(heard) and heard[k].get('x') and heard[k]['clip']==g[0]['clip'] and heard[k]['s']-g[-1]['e']<0.3: g.append(heard[k]);k+=1
    a,b=g[0]['s'],g[-1]['e'];c=g[0]['clip']
    if near_falta(a,b) or b-a<0.1: continue
    pv=[x for x in matched if x['clip']==c and x['e']<=a+0.02];nx=[x for x in matched if x['clip']==c and x['s']>=b-0.02]
    gp=a-pv[-1]['e'] if pv else None;gn=nx[0]['s']-b if nx else None
    thr=0.05 if all(norm(x['w']) in FILLERS for x in g) else 0.15   # «eh/este/bueno» conocidos: alcanza con no pisar a las vecinas; lo demás, bien aislado
    if (gp is not None and gp<thr) or (gn is not None and gn<thr): continue
    lo=pv[-1]['e'] if pv else a-0.03;hi=nx[0]['s'] if nx else b+0.03
    holes.append([max(lo,a-0.03),min(hi,b+0.03),'fuera de guion','«'+' '.join(x['w'] for x in g)+'»'])
holes=[h for h in holes if h[1]-h[0]>=0.06];holes.sort()
merged=[]
for h in holes:
    if merged and h[0]<=merged[-1][1]+0.02: merged[-1][1]=max(merged[-1][1],h[1]);merged[-1][2]=merged[-1][2] if merged[-1][2]==h[2] else merged[-1][2]+'+'+h[2]
    else: merged.append(list(h))
holes=merged
# --- informe ---
tot=sum(h[1]-h[0] for h in holes)
md=['# Aire y muletillas',f'nivel de habla (p70) {SP:.0f} dB · pausa ≤ {TH_LOW:.0f} dB · voz > {TH_VOICE:.0f} dB · pausas de ≥ {PAUSE_MAX:.2f} s: {len(pauses)} · huecos: {len(holes)} ({tot:.2f} s)','']
if REPORT:
    rest_p=[(a,b) for a,b in pauses];rest_f=[h for h in holes if h[2]!='pausa']
    md+=['## Lo que queda después de la segunda pasada']+[f'- ⚠️ pausa de {b-a:.2f} s en {a:.2f}s {ctx(a,b)}' for a,b in rest_p]+[f'- ⚠️ {h[2]} en {h[0]:.2f}s ({h[3]}) {ctx(h[0],h[1])}' for h in rest_f]
    if not rest_p and not rest_f: md.append('- sin pausas de ≥ %.2f s ni muletillas detectables ✓'%PAUSE_MAX)
    prev=open(os.path.join(W,'aire.md')).read() if os.path.exists(os.path.join(W,'aire.md')) and '## Lo que queda' not in open(os.path.join(W,'aire.md')).read() else ''
    open(os.path.join(W,'aire.md'),'w').write(prev+('\n' if prev else '')+'\n'.join(md[2:] if prev else md)+'\n')   # la tabla de huecos de la primera pasada + lo que queda
    print(f'aire restante: {len(rest_p)} pausa(s) de ≥ {PAUSE_MAX:.2f} s · {len(rest_f)} muletilla(s)/fuera de guion (umbral habla {SP:.0f} dB)')
    for a,b in rest_p: print(f'  ⚠️  pausa de {b-a:.2f} s en {a:.2f}s {ctx(a,b)} → check.py en el crudo y, si es real, bajar pause_max o tocar segs.json')
    for h in rest_f: print(f'  ⚠️  {h[2]} en {h[0]:.2f}s ({h[3]}) {ctx(h[0],h[1])} → confirmar con check.py')
    sys.exit(0)
md+=['| en el corte | dur | tipo | detalle | contexto | en el crudo |','|---|---|---|---|---|---|']
# --- aplicar en tight.json: hueco de la línea de tiempo → tramo del crudo → recortar / partir la frase ---
def to_src(t,c): return c['src_in']/FPS+(t-c['tl_in']/FPS)
caps_pi={}
for cp in E['caps']:
    for wd in cp['words']: caps_pi.setdefault(cp.get('pi'),[]).append(wd)
pieces=[dict(p,_k=i) for i,p in enumerate(P)]   # _k = índice original (para el texto)
def split_text(p,s0,s1,c):
    """Reparte el texto de la frase p: palabras que (según Whisper en el corte) suenan antes del hueco → izquierda."""
    wds=caps_pi.get(p['_k'],[]);words=p['t'].split()
    if len(wds)!=len(words) or not wds: return None
    left=[wd for wd,x in zip(words,wds) if to_src(x['s']/FPS,c)<(s0+s1)/2]
    return ' '.join(left),' '.join(words[len(left):])
changed=0
for h0,h1,tipo,det in holes:
    for c in E['clips']:
        ca,cb=c['tl_in']/FPS,c['tl_out']/FPS
        a,b=max(h0,ca),min(h1,cb)
        if b-a<0.04: continue
        s0,s1=to_src(a,c),to_src(b,c)
        md.append(f'| {h0:.2f}s | {h1-h0:.2f} | {tipo} | {det} | {ctx(h0,h1)} | {s0:.2f}–{s1:.2f}s |')
        for pi in c.get('pieces',[]):
            p=next((q for q in pieces if q['_k']==pi and not q.get('_drop')),None)
            if p is None: continue
            pa,pb=p['a'],p['b']
            if tipo.startswith('pausa'):   # el aire de un empalme vive en los márgenes que agrega edl.py (0,04 antes / 0,08–0,14 después) + redondeo:
                if pb-0.01<=s0<=pb+POST_END+0.08 and s1>=pb:
                    if p.get('post',9)>PAD_POST: p['post']=PAD_POST;changed+=1
                    continue    # la pausa arranca en la cola de esta frase → margen mínimo
                if pa-PRE-0.08<=s1<=pa+0.01 and s0<=pa:
                    if p.get('pre',9)>PAD_PRE: p['pre']=PAD_PRE;changed+=1
                    continue           # la pausa termina en el arranque de esta frase
            if s1<=pa+0.01 or s0>=pb-0.01: continue
            if s0<=pa+0.01 and s1>=pb-0.01:   # el hueco tapa la frase entera: solo si no tiene palabras del guion oídas adentro
                if not any(to_src(x['s']/FPS,c)>=pa-0.05 and to_src(x['s']/FPS,c)<=pb+0.05 for x in matched if x['clip']==c['i']): p['_drop']=True;changed+=1
                continue
            if s0<=pa+0.01: p['a']=round(s1,3);p['pre']=PAD_PRE;changed+=1;continue    # recorta el arranque
            if s1>=pb-0.01: p['b']=round(s0,3);p['post']=PAD_POST;changed+=1;continue    # recorta la cola
            st=split_text(p,s0,s1,c)
            if st is None: continue
            l,r=st
            if l and r:
                new=dict(p,a=round(s1,3),t=r,_k=p['_k'],pre=PAD_PRE);new.pop('post',None);p['b']=round(s0,3);p['t']=l;p['post']=PAD_POST
                pieces.insert(pieces.index(p)+1,new);changed+=1
            elif l: p['b']=round(s0,3);p['post']=PAD_POST;changed+=1    # lo que sigue al hueco no tiene palabras del guion → se va
            elif r: p['a']=round(s1,3);p['pre']=PAD_PRE;changed+=1
def _heard_src(p):   # tiempos en el crudo donde se oyeron las palabras del guion de la frase p
    wds=caps_pi.get(p['_k'],[]);c=next((c for c in E['clips'] if p['_k'] in c.get('pieces',[])),None)
    return [to_src(x['s']/FPS,c) for x in wds if x.get('real')] if c else []
live=[p for p in pieces if not p.get('_drop') and p['b']-p['a']>=0.08]
for p in list(live):
    hs=_heard_src(p)
    if not hs or any(p['a']-0.08<=t<=p['b']+0.08 for t in hs): continue   # alguna de sus palabras suena adentro: está bien
    q=next((q for q in live if q is not p and q['seg']==p['seg'] and sum(q['a']-0.08<=t<=q['b']+0.08 for t in hs)>=len(hs)/2),None)
    if q is None: continue
    if q['a']<p['a']: q['t']=(q['t']+' '+p['t']).strip()
    else: q['t']=(p['t']+' '+q['t']).strip()
    p['_drop']=True;changed+=1;md.append(f'| — | {p["b"]-p["a"]:.2f} | texto huérfano | «{p["t"]}» se oye en otra frase: pasa allí y la región sale | | {p["a"]:.2f}–{p["b"]:.2f}s |')
out=[]
for p in pieces:
    if p.get('_drop') or p['b']-p['a']<0.08: continue
    out.append(dict(seg=p['seg'],a=p['a'],b=p['b'],t=p['t'],**{k:p[k] for k in('pre','post') if k in p}))
open(os.path.join(W,'aire.md'),'w').write('\n'.join(md)+'\n')
if not changed:
    print(f'aire: nada que sacar (pausas de ≥ {PAUSE_MAX:.2f} s: 0 · muletillas: 0 · umbral habla {SP:.0f} dB)');sys.exit(0)
import shutil;shutil.copy(os.path.join(W,'tight.json'),os.path.join(W,'tight_pre_aire.json'))
json.dump(out,open(os.path.join(W,'tight.json'),'w'),ensure_ascii=False,indent=1)
print(f'aire: {len(holes)} hueco(s), {tot:.2f} s sacados ('+' · '.join(f'{t}: {sum(1 for h in holes if h[2]==t)}' for t in dict.fromkeys(h[2] for h in holes))+f') → tight.json ({len(P)} → {len(out)} frases); el corte se vuelve a armar')
for h0,h1,tipo,det in holes: print(f'  − {h0:7.2f}s {h1-h0:.2f}s {tipo:14s} {det}  {ctx(h0,h1)}')
sys.exit(3)
