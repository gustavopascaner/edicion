#!/usr/bin/env python3
"""Paso 1: extrae audio y transcribe el crudo en frases (pieces) con tiempos.
uso: python3 -I transcribe.py <video.mp4> <workdir>
salida: <workdir>/audio16k.wav, <workdir>/pieces.json, imprime una línea por frase.
Ojo: Whisper alucina "Gracias", "Gracias por ver el video", "Suscríbete al canal", "CC por..." sobre ruido/respiraciones:
verificar esas zonas con check.py antes de decidir.
"""
import re,subprocess,json,sys,os
MODEL=os.path.expanduser('~/.cache/whisper-cpp/ggml-large-v3-turbo.bin')
src,W=sys.argv[1],sys.argv[2];os.makedirs(os.path.join(W,'sub'),exist_ok=True)
A=os.path.join(W,'audio16k.wav')
if not os.path.exists(A):
    subprocess.run(['ffmpeg','-v','error','-y','-i',src,'-vn','-ac','1','-ar','16000','-c:a','pcm_s16le',A],check=True)
dur=float(subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',A],capture_output=True,text=True).stdout)
def sil(n,d):
    out=subprocess.run(['ffmpeg','-i',A,'-af',f'silencedetect=noise={n}dB:d={d}','-f','null','-'],capture_output=True,text=True).stderr
    return list(zip([float(x) for x in re.findall(r'silence_start: ([\d.]+)',out)],[float(x) for x in re.findall(r'silence_end: ([\d.]+)',out)]))
big=[s for s in sil(-38,0.25) if s[1]-s[0]>=0.9];small=sil(-36,0.15)
chunks=[];prev=0
for a,b in big:
    if a-prev>0.2: chunks.append((prev,a))
    prev=b
if dur-prev>0.2: chunks.append((prev,dur))
def tr(a,b,f,prompt=None):
    subprocess.run(['ffmpeg','-v','error','-y','-ss',str(max(0,a-0.08)),'-to',str(b+0.08),'-i',A,f])
    cmd=['whisper-cli','-m',MODEL,'-f',f,'-l','es','-otxt','-of',f[:-4],'-t','8','-np']
    if prompt: cmd+=['--prompt',prompt]
    subprocess.run(cmd,capture_output=True);return open(f[:-4]+'.txt').read().strip().replace('\n',' ')
res=[]
for ci,(a,b) in enumerate(chunks):
    full=tr(a,b,os.path.join(W,'sub',f'c{ci:02d}.wav'))
    inner=[(s,e) for s,e in small if s>a+0.05 and e<b-0.05]
    pts=[a]+[x for s,e in inner for x in (s,e)]+[b]
    pieces=[(pts[k],pts[k+1]) for k in range(0,len(pts),2)]
    if len(pieces)==1: res.append(dict(c=ci,a=round(a,2),b=round(b,2),t=full));continue
    for j,(pa,pb) in enumerate(pieces): res.append(dict(c=ci,a=round(pa,2),b=round(pb,2),t=tr(pa,pb,os.path.join(W,'sub',f'p{ci:02d}_{j}.wav'),full)))
for p in res: print(f"{p['c']:02d} {p['a']:7.2f}-{p['b']:7.2f} {p['t']}")
json.dump(res,open(os.path.join(W,'pieces.json'),'w'),ensure_ascii=False,indent=1)
print(f'\nduración {dur:.1f}s · {len(res)} frases')
