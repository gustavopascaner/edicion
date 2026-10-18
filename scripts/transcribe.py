#!/usr/bin/env python3
"""Paso 1: extrae audio y transcribe el crudo en frases (pieces) con tiempos.
uso: python3 -I transcribe.py <video.mp4> <workdir>
salida: <workdir>/audio16k.wav, <workdir>/pieces.json, imprime una línea por frase.
Los pedazos cortos se transcriben SIN prompt (con el texto del bloque de prompt Whisper repetía palabras sueltas).
Ojo: Whisper alucina "Gracias", "Gracias por ver el video", "Suscríbete al canal", "CC por..." sobre ruido/respiraciones:
verificar esas zonas con check.py antes de decidir.
"""
import os as _o,sys as _s,subprocess as _sp
if _o.name=='nt' and __name__=='__main__' and not _s.flags.utf8_mode: _s.exit(_sp.run([_s.executable,'-X','utf8','-I',_o.path.abspath(__file__),*_s.argv[1:]]).returncode)  # Windows: acentos en UTF-8
import re,subprocess,json,sys,os
MODEL=os.path.expanduser('~/.cache/whisper-cpp/ggml-large-v3-turbo.bin')
WHISPER=os.environ.get('WHISPER_CLI') or __import__('shutil').which('whisper-cli') or os.path.join(os.environ.get('LOCALAPPDATA',''),'whisper-cpp','whisper-cli.exe')
src,W=sys.argv[1],sys.argv[2];os.makedirs(os.path.join(W,'sub'),exist_ok=True)
import atexit,time;sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)));import timing;_t0=time.time();atexit.register(lambda:timing.log(W,'Transcripción',time.time()-_t0))
A=os.path.join(W,'audio16k.wav')
if not os.path.exists(A):
    subprocess.run(['ffmpeg','-v','error','-y','-i',src,'-vn','-ac','1','-ar','16000','-c:a','pcm_s16le',A],check=True)
# Nivel de análisis: los umbrales de voz/silencio de tighten.py, edl.py y qa_cut.py son absolutos (dB). Un crudo grabado bajo (WhatsApp ≈ −36 dB)
# haría que no se detecte la voz: se sube SOLO la copia de análisis (el audio del XML no se toca) hasta que la voz fuerte (p95) quede en ≈ −14 dB.
import wave,struct,math
def _p95(p):
    w=wave.open(p);SR=w.getframerate();raw=w.readframes(w.getnframes());S=struct.unpack('<%dh'%(len(raw)//2),raw);n=int(SR*0.02)
    e=sorted(20*math.log10(max(1,math.sqrt(sum(x*x for x in S[i:i+n])/n))/32768) for i in range(0,len(S)-n,n));return e[int(len(e)*0.95)]
_p=_p95(A)
if _p<-20 and not os.path.exists(os.path.join(W,'analysis_gain.json')):
    _g=min(30.0,-14-_p);_t=A+'.tmp.wav'
    subprocess.run(['ffmpeg','-v','error','-y','-i',A,'-af',f'volume={_g:.1f}dB,alimiter=limit=0.95','-c:a','pcm_s16le',_t],check=True);os.replace(_t,A)
    json.dump(dict(gain_db=round(_g,1),voz_p95_antes=round(_p,1)),open(os.path.join(W,'analysis_gain.json'),'w'));print(f'ℹ️  crudo grabado bajo (voz ≈ {_p:.0f} dB): audio de análisis +{_g:.1f} dB (solo para detectar voz; el XML usa el audio original)')
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
    cmd=[WHISPER,'-m',MODEL,'-f',f,'-l','es','-otxt','-of',f[:-4],'-t','8','-np']
    if prompt: cmd+=['--prompt',prompt]
    subprocess.run(cmd,capture_output=True);return open(f[:-4]+'.txt').read().strip().replace('\n',' ')
res=[]
for ci,(a,b) in enumerate(chunks):
    full=tr(a,b,os.path.join(W,'sub',f'c{ci:02d}.wav'))
    inner=[(s,e) for s,e in small if s>a+0.05 and e<b-0.05]
    pts=[a]+[x for s,e in inner for x in (s,e)]+[b]
    pieces=[(pts[k],pts[k+1]) for k in range(0,len(pts),2)]
    if len(pieces)==1: res.append(dict(c=ci,a=round(a,2),b=round(b,2),t=full));continue
    for j,(pa,pb) in enumerate(pieces): res.append(dict(c=ci,a=round(pa,2),b=round(pb,2),t=tr(pa,pb,os.path.join(W,'sub',f'p{ci:02d}_{j}.wav'))))
for p in res: print(f"{p['c']:02d} {p['a']:7.2f}-{p['b']:7.2f} {p['t']}")
json.dump(res,open(os.path.join(W,'pieces.json'),'w'),ensure_ascii=False,indent=1)
print(f'\nduración {dur:.1f}s · {len(res)} frases')
