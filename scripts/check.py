#!/usr/bin/env python3
"""Verifica zonas dudosas: transcribe sin prompt + envolvente de energía (dB cada 0.1s).
uso: python3 -I check.py <workdir> a-b [a-b ...]      ej: 21.9-26.3 139.8-142.3
Habla ≈ -5..-25 dB; ruido de fondo ≈ -48..-70 dB. Si Whisper dice "Gracias" y la energía es de ruido → no es habla.
"""
import sys,os,subprocess,wave,struct,math
MODEL=os.path.expanduser('~/.cache/whisper-cpp/ggml-large-v3-turbo.bin')
W=sys.argv[1];A=os.path.join(W,'audio16k.wav');T=os.path.join(W,'t.wav')
w=wave.open(A);SR=w.getframerate();raw=w.readframes(w.getnframes());S=struct.unpack('<%dh'%(len(raw)//2),raw)
def env(a,b,st=0.1):
    out=[];t=a
    while t<b:
        i=int(t*SR);seg=S[i:i+int(SR*st)] or [0];out.append('%.1f:%d'%(t,20*math.log10(max(1,math.sqrt(sum(x*x for x in seg)/len(seg)))/32768)));t+=st
    return ' '.join(out)
for r in sys.argv[2:]:
    a,b=map(float,r.split('-'))
    subprocess.run(['ffmpeg','-v','error','-y','-ss',str(a),'-to',str(b),'-i',A,T])
    t=subprocess.run(['whisper-cli','-m',MODEL,'-f',T,'-l','es','-np','-nt'],capture_output=True,text=True).stdout.strip().replace('\n',' ')
    print(f'{a}-{b}: «{t}»\n   {env(a,b)}')
