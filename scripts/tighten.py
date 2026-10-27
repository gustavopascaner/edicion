#!/usr/bin/env python3
"""Paso 2: corte AJUSTADO. Lee <workdir>/segs.json y recorta cada frase sobre la energía real de la voz,
partiendo en pausas internas >= 0.25s (lecturas, miradas al costado, respiraciones).
segs.json = lista de SEGMENTOS lógicos; cada segmento = lista de [a, b, "texto corregido para subtítulos"].
  Un segmento agrupa frases que comparten un gráfico (los MG se sincronizan por índice de segmento).
uso: python3 -I tighten.py <workdir>      → <workdir>/tight.json
Umbrales automáticos según el piso de ruido de la grabación.
"""
import os as _o,sys as _s,subprocess as _sp
if _o.name=='nt' and __name__=='__main__' and not _s.flags.utf8_mode: _s.exit(_sp.run([_s.executable,'-X','utf8','-I',_o.path.abspath(__file__),*_s.argv[1:]]).returncode)  # Windows: acentos en UTF-8
import wave,struct,math,json,subprocess,os,sys
MODEL=os.path.expanduser('~/.cache/whisper-cpp/ggml-large-v3-turbo.bin')
WHISPER=os.environ.get('WHISPER_CLI') or __import__('shutil').which('whisper-cli') or os.path.join(os.environ.get('LOCALAPPDATA',''),'whisper-cpp','whisper-cli.exe')
W=sys.argv[1];A=os.path.join(W,'audio16k.wav')
import atexit,time;sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)));import timing;_t0=time.time();atexit.register(lambda:timing.log(W,'Corte ajustado',time.time()-_t0))
import whisperlib as WL;LIV=WL.liviano(W)   # perfil liviano (8 GB): modelo q5 + whisper-server cargado una vez; el potente (Mac) no cambia
w=wave.open(A);SR=w.getframerate();raw=w.readframes(w.getnframes());S=struct.unpack('<%dh'%(len(raw)//2),raw)
HOP=0.01;N=int(SR*HOP)
def db(i):
    seg=S[i*N:i*N+2*N]
    if not seg: return -99
    return 20*math.log10(max(1,math.sqrt(sum(x*x for x in seg)/len(seg)))/32768)
ENV=[db(i) for i in range(len(S)//N)]
FLOOR=sorted(ENV)[len(ENV)//10]
TH=-32; GAP=0.25; ATT=max(FLOOR+10,-46); DEC=max(FLOOR+8,-46)   # cola: seguir hasta que la voz se apaga del todo (s, n, vocales finales)
print(f'piso de ruido {FLOOR:.0f} dB · umbral voz {TH} · ataque {ATT:.0f} · cola {DEC:.0f}')
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
        hs=[heard(r[0],r[1],txt) for r in rs];cnt=[len(x.split()) for x in hs];tot=sum(cnt) or 1;k=0
        for j,r in enumerate(rs):
            n=len(words)-k if j==len(rs)-1 else min(len(words)-k,max(0,round(len(words)*cnt[j]/tot)))
            out.append(dict(seg=si,a=round(r[0],3),b=round(r[1],3),t=' '.join(words[k:k+n])));k+=n
for p in out: print(f"{p['seg']:02d} {p['a']:7.2f}-{p['b']:7.2f} ({p['b']-p['a']:.2f}) {p['t']}")
json.dump(out,open(os.path.join(W,'tight.json'),'w'),ensure_ascii=False,indent=1)
