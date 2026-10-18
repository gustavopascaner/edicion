#!/usr/bin/env python3
"""QA de los empalmes del corte (rápido, sin Whisper). uso: python3 -I qa_cut.py <workdir>   → <workdir>/qa_cut.md
Por cada corte real entre clips mide, sobre el audio del master:
  · voz en el punto de corte (energía a ambos lados > umbral de silencio) → riesgo de letra comida o de clic
  · audio DUPLICADO: la cola del clip que sale se parece (correlación) al arranque del que entra → «pedacito repetido»
  · margen de silencio disponible a cada lado (los fades de 1 fotograma tienen que caer dentro)
Sale con código 1 si hay audio duplicado. Lo de Whisper (palabras que faltan o sobran) lo hace align.py y se muestra al final.
"""
import os as _o,sys as _s,subprocess as _sp
if _o.name=='nt' and __name__=='__main__' and not _s.flags.utf8_mode: _s.exit(_sp.run([_s.executable,'-X','utf8','-I',_o.path.abspath(__file__),*_s.argv[1:]]).returncode)  # Windows: acentos en UTF-8
import json,os,sys,wave,struct,math
W=sys.argv[1];E=json.load(open(os.path.join(W,'edl.json')));FPS=E['fps']
w=wave.open(os.path.join(W,'audio16k.wav'));SR=w.getframerate();raw=w.readframes(w.getnframes());S=struct.unpack('<%dh'%(len(raw)//2),raw)
def rms(a,b):
    seg=S[max(0,int(a*SR)):int(b*SR)] or [0]
    return 20*math.log10(max(1,math.sqrt(sum(x*x for x in seg)/len(seg)))/32768)
N=int(SR/FPS);ENV=[rms(k/FPS,(k+1)/FPS) for k in range(len(S)//N)];FLOOR=sorted(ENV)[len(ENV)//10];QUIET=min(max(FLOOR+20,-46),-34)
D=4   # decimado para la correlación (16 kHz → 4 kHz)
def seg(a,b):
    x=S[max(0,int(a*SR)):int(b*SR)];return [sum(x[i:i+D])/D for i in range(0,len(x)-D+1,D)]
def ncc(x,y):
    n=min(len(x),len(y))
    if n<20: return 0
    x,y=x[:n],y[:n];mx,my=sum(x)/n,sum(y)/n;x=[v-mx for v in x];y=[v-my for v in y]
    d=math.sqrt(sum(v*v for v in x)*sum(v*v for v in y));return sum(a*b for a,b in zip(x,y))/d if d else 0
rows=[];dup=0;voiced=0;cuts=0
for k in range(len(E['clips'])-1):
    a,b=E['clips'][k],E['clips'][k+1]
    if not (a['fade_out'] and b['fade_in']): continue            # empalme sin corte real
    cuts+=1;to,ti=a['src_out']/FPS,b['src_in']/FPS
    e_out,e_in=rms(to-0.03,to),rms(ti,ti+0.03)
    m_out=sum(1 for f in range(a['src_out']-1,a['src_out']-6,-1) if ENV[min(len(ENV)-1,max(0,f))]<=QUIET)   # frames de silencio antes del corte (máx 5)
    m_in=sum(1 for f in range(b['src_in'],b['src_in']+5) if ENV[min(len(ENV)-1,max(0,f))]<=QUIET)
    tail=seg(to-0.12,to);head=seg(ti,ti+0.12)
    best=max(ncc(tail,head[o:]) if o>=0 else ncc(tail[-o:],head) for o in range(-40,41))   # ±10 ms a 4 kHz
    flags=[]
    if best>0.9 and max(e_out,e_in)>QUIET: flags.append('DUPLICADO');dup+=1
    if e_out>QUIET or e_in>QUIET: flags.append('voz en el corte');voiced+=1
    rows.append((k,to,e_out,e_in,m_out,m_in,best,flags))
md=['# QA de empalmes','',f'{cuts} cortes reales · umbral de silencio {QUIET:.0f} dB (piso {FLOOR:.0f}) · {dup} duplicados · {voiced} con voz en el corte','',
    '| corte | en el crudo | sale (dB) | entra (dB) | silencio antes/después (fr) | parecido cola↔arranque | |','|---|---|---|---|---|---|---|']
for k,to,eo,ei,mo,mi,b,f in rows: md.append(f'| {k}→{k+1} | {to:.2f}s | {eo:.0f} | {ei:.0f} | {mo}/{mi} | {b:.2f} | {" · ".join(f)} |')
qa=os.path.join(W,'qa_words.json')
if os.path.exists(qa):
    q=json.load(open(qa));md+=['',f'## Whisper sin prompt ({len(q)} avisos)']+[f'- {x["msg"]}' for x in q]
open(os.path.join(W,'qa_cut.md'),'w').write('\n'.join(md)+'\n')
print(f'{cuts} cortes reales: {dup} con audio duplicado · {voiced} con voz sonando en el empalme (umbral {QUIET:.0f} dB)')
for k,to,eo,ei,mo,mi,b,f in rows:
    if f: print(f'  ⚠️  corte {k}→{k+1} en {to:.2f}s: {" + ".join(f)} (sale {eo:.0f} dB · entra {ei:.0f} dB · parecido {b:.2f})')
if os.path.exists(qa):
    for x in json.load(open(qa)): print('  ⚠️ ',x['msg'])
print('detalle:',os.path.join(W,'qa_cut.md'))
sys.exit(1 if dup else 0)
