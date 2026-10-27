#!/usr/bin/env python3
"""Verifica zonas dudosas: transcribe sin prompt + envolvente de energía (dB cada 0.1s).
uso: python3 -I check.py <workdir> a-b [a-b ...]      ej: 21.9-26.3 139.8-142.3
Habla ≈ -5..-25 dB; ruido de fondo ≈ -48..-70 dB. Si Whisper dice "Gracias" y la energía es de ruido → no es habla.
"""
import os as _o,sys as _s,subprocess as _sp
if _o.name=='nt' and __name__=='__main__' and not _s.flags.utf8_mode: _s.exit(_sp.run([_s.executable,'-X','utf8','-I',_o.path.abspath(__file__),*_s.argv[1:]]).returncode)  # Windows: acentos en UTF-8
import sys,os,subprocess,wave,struct,math
MODEL=os.path.expanduser('~/.cache/whisper-cpp/ggml-large-v3-turbo.bin')
WHISPER=os.environ.get('WHISPER_CLI') or __import__('shutil').which('whisper-cli') or os.path.join(os.environ.get('LOCALAPPDATA',''),'whisper-cpp','whisper-cli.exe')
W=sys.argv[1];A=os.path.join(W,'audio16k.wav');T=os.path.join(W,'t.wav')
import atexit,time;sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)));import timing;_t0=time.time();atexit.register(lambda:timing.log(W,'Verificación de audio',time.time()-_t0))
import whisperlib as WL;LIV=WL.liviano(W)   # perfil liviano (8 GB): modelo q5 + whisper-server cargado una vez; el potente (Mac) no cambia
w=wave.open(A);SR=w.getframerate();raw=w.readframes(w.getnframes());S=struct.unpack('<%dh'%(len(raw)//2),raw)
def env(a,b,st=0.1):
    out=[];t=a
    while t<b:
        i=int(t*SR);seg=S[i:i+int(SR*st)] or [0];out.append('%.1f:%d'%(t,20*math.log10(max(1,math.sqrt(sum(x*x for x in seg)/len(seg)))/32768)));t+=st
    return ' '.join(out)
for r in sys.argv[2:]:
    a,b=map(float,r.split('-'))
    subprocess.run(['ffmpeg','-v','error','-y','-ss',str(a),'-to',str(b),'-i',A,T])
    t=WL.text(T,W) if LIV else subprocess.run([WHISPER,'-m',MODEL,'-f',T,'-l','es','-np','-nt'],capture_output=True,text=True).stdout.strip().replace('\n',' ')
    print(f'{a}-{b}: «{t}»\n   {env(a,b)}')
