#!/usr/bin/env python3
"""Paso 2: corte AJUSTADO. Lee <workdir>/segs.json y recorta cada frase sobre la energía real de la voz,
partiendo en pausas internas >= 0.20s (config.gap; lecturas, miradas al costado, respiraciones). Las regiones cortas y muy por debajo
del nivel de habla (respiraciones, roces) no entran. La segunda pasada (aire.py, la corre edl.py) saca lo que esto no ve: pausas que
quedan en el corte y muletillas con energía que Whisper no transcribe.
segs.json = lista de SEGMENTOS lógicos; cada segmento = lista de [a, b, "texto corregido para subtítulos"].
  Un segmento agrupa frases que comparten un gráfico (los MG se sincronizan por índice de segmento).
uso: python3 -I tighten.py <workdir>      → <workdir>/tight.json
Umbrales automáticos según el piso de ruido de la grabación.
"""
import os as _o,sys as _s,subprocess as _sp
if _o.name=='nt' and __name__=='__main__' and not _s.flags.utf8_mode: _s.exit(_sp.run([_s.executable,'-X','utf8','-I',_o.path.abspath(__file__),*_s.argv[1:]]).returncode)  # Windows: acentos en UTF-8
import wave,struct,math,json,subprocess,os,sys,difflib
MODEL=os.path.expanduser('~/.cache/whisper-cpp/ggml-large-v3-turbo.bin')
WHISPER=os.environ.get('WHISPER_CLI') or __import__('shutil').which('whisper-cli') or os.path.join(os.environ.get('LOCALAPPDATA',''),'whisper-cpp','whisper-cli.exe')
W=sys.argv[1];A=os.path.join(W,'audio16k.wav')
import atexit,time;sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)));import timing;_t0=time.time();atexit.register(lambda:timing.log(W,'Corte ajustado',time.time()-_t0))
import whisperlib as WL;LIV=WL.liviano(W);WD=WL.words(W,A) if LIV else None   # perfil liviano (8 GB): modelo q5 + whisper-server cargado una vez; el potente (Mac) no cambia
w=wave.open(A);SR=w.getframerate();raw=w.readframes(w.getnframes());S=struct.unpack('<%dh'%(len(raw)//2),raw)
HOP=0.01;N=int(SR*HOP)
def db(i):
    seg=S[i*N:i*N+2*N]
    if not seg: return -99
    return 20*math.log10(max(1,math.sqrt(sum(x*x for x in seg)/len(seg)))/32768)
ENV=[db(i) for i in range(len(S)//N)]
FLOOR=sorted(ENV)[len(ENV)//10]
_cfg={}
try: _cfg=json.load(open(os.path.join(W,'config.json')))
except Exception: pass
TH=-32; GAP=_cfg.get('gap',0.20); ATT=max(FLOOR+10,-46); DEC=max(FLOOR+8,-46)   # cola: seguir hasta que la voz se apaga del todo (s, n, vocales finales)
SPEECH=sorted(ENV)[int(len(ENV)*0.7)]   # nivel de habla (p70): una región corta y muy por debajo es respiración/ruido, no una palabra
print(f'piso de ruido {FLOOR:.0f} dB · habla {SPEECH:.0f} dB · umbral voz {TH} · ataque {ATT:.0f} · cola {DEC:.0f} · pausa mínima {GAP:.2f} s')
BREATHS=0;MULET=[]
SEG=json.load(open(os.path.join(W,'segs.json')))
def regions(a,b,lo=0):
    i0=max(0,int((max(a-0.15,lo))/HOP));i1=min(len(ENV)-1,int((b+0.15)/HOP))
    regs=[];st=None
    for k in range(i0,i1+1):
        v=ENV[k]>TH;t=k*HOP
        if v and st is None: st=t
        if not v and st is not None: regs.append([st,t]);st=None
    if st is not None: regs.append([st,(i1+1)*HOP])
    regs=[r for r in regs if r[1]-r[0]>=0.04]
    merged=[]
    for r in regs:
        if merged and r[0]-merged[-1][1]<GAP: merged[-1][1]=r[1]
        else: merged.append(r)
    merged=[r for r in merged if r[1]-r[0]>=0.12]
    def _breath(r):   # región corta (< 0,35 s) que nunca llega a 12 dB del nivel de habla = respiración / roce, no una palabra ("a", "y" son vocales: suenan fuerte)
        return r[1]-r[0]<0.35 and max(ENV[int(r[0]/HOP):int(r[1]/HOP)+1] or [-99])<SPEECH-12
    global BREATHS
    br=[r for r in merged if _breath(r)];BREATHS+=len(br);merged=[r for r in merged if r not in br]
    for r in merged:
        i=int(r[0]/HOP);first=i;k=0   # arranque suave ("En", "Es" a −34 dB): hacia atrás con histéresis (60 ms de silencio real cortan), hasta 300 ms
        while k<30 and i>0:
            if ENV[i-1]>ATT: first=i-1
            elif first-(i-1)>=6: break
            i-=1;k+=1
        r[0]=first*HOP
        j=int(r[1]/HOP);k=0;last=j   # histéresis: la cola sigue hasta 80 ms de silencio REAL (un bache dentro de la palabra no la corta)
        while k<45 and j<len(ENV):
            if ENV[j]>DEC: last=j+1
            elif j-last>=8: break
            j+=1;k+=1
        r[1]=last*HOP
    return merged
def heard(a,b,prompt):
    f=os.path.join(W,'t.wav');subprocess.run(['ffmpeg','-v','error','-y','-ss',str(max(0,a-0.05)),'-to',str(b+0.05),'-i',A,f])
    if LIV: return WL.text(f,W)
    return subprocess.run([WHISPER,'-m',MODEL,'-f',f,'-l','es','-np','-nt'],capture_output=True,text=True).stdout.strip().replace('\n',' ')   # sin prompt: el texto esperado haría que Whisper "complete" lo que no se dijo
out=[];prev_b=None
for si,seg in enumerate(SEG):
    for (a,b,txt) in seg:
        rs=regions(a,b,prev_b if prev_b is not None and prev_b<=a else 0);words=txt.split();prev_b=b
        if not rs: print('!! sin voz detectada en',a,b,txt);continue
        if len(rs)==1: out.append(dict(seg=si,a=round(rs[0][0],3),b=round(rs[0][1],3),t=txt));continue
        if WD is not None:   # liviano: el guion se reparte por los tiempos de la pasada única (sin Whisper por región)
            ts=WL.assign(WD,rs,txt)
            if all(t and len(t.split())<=6*(r[1]-r[0])+1 for r,t in zip(rs,ts)):   # dudoso (región con voz y sin palabras, o más de ~6 palabras/s) → Whisper por región, como siempre
                for r,t in zip(rs,ts): out.append(dict(seg=si,a=round(r[0],3),b=round(r[1],3),t=t))
                continue
        hs=[heard(r[0],r[1],txt) for r in rs]
        # reparto del guion entre regiones EMPAREJANDO palabras (no por cantidad): una región donde Whisper oyó solo «eh», «¿qué?», una
        # risa o nada que se parezca al guion es una MULETILLA y queda fuera (antes se llevaba la última palabra del guion y entraba
        # al corte con subtítulo: GUION3 30/10/2026, «cosas.» sobre un «eh» de 1 s)
        ws=[dict(t=t,a=r[0]+0.001) for r,h in zip(rs,hs) for t in h.split()]
        ts=WL.assign(ws,rs,txt) if ws else ['']*len(rs)
        nm=WL._nm;sw=[nm(x) for x in words]
        def _mulet(h):   # ≤ 2 palabras oídas y ninguna se parece a una palabra del guion de esta frase
            hw=[nm(x) for x in h.split() if nm(x)]
            return len(hw)<=2 and not any(difflib.SequenceMatcher(None,a,b).ratio()>=0.6 and len(b)>=2 for a in hw for b in sw)
        keep=[]
        for j,r in enumerate(rs):
            if not ts[j].strip() and _mulet(hs[j]): MULET.append((r[0],r[1],hs[j] or '(sin texto)'));continue
            keep.append(j)
        if any(not ts[j].strip() for j in keep):   # región con voz real pero sin palabras emparejadas → reparto proporcional de antes
            cnt=[len(hs[j].split()) for j in keep];tot=sum(cnt) or 1;k=0
            for n_,j in enumerate(keep):
                n=len(words)-k if n_==len(keep)-1 else min(len(words)-k,max(0,round(len(words)*cnt[n_]/tot)))
                ts[j]=' '.join(words[k:k+n]);k+=n
        for j in keep: out.append(dict(seg=si,a=round(rs[j][0],3),b=round(rs[j][1],3),t=ts[j]))
for p in out: print(f"{p['seg']:02d} {p['a']:7.2f}-{p['b']:7.2f} ({p['b']-p['a']:.2f}) {p['t']}")
if BREATHS: print(f'{BREATHS} respiración(es)/ruido corto fuera del corte (regiones < 0,35 s a más de 12 dB bajo el habla)')
for a,b,h in MULET: print(f'muletilla fuera del corte: {a:.2f}-{b:.2f} ({b-a:.2f} s) se oye «{h}»')
json.dump(out,open(os.path.join(W,'tight.json'),'w'),ensure_ascii=False,indent=1)
