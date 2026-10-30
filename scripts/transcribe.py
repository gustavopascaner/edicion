#!/usr/bin/env python3
"""Paso 1: extrae audio y transcribe el crudo en frases (pieces) con tiempos.
uso: python3 -I transcribe.py <video.mp4> <workdir>
salida: <workdir>/audio16k.wav, <workdir>/pieces.json (frases con tiempos), <workdir>/words_full.json (todas las palabras con su arranque),
imprime una línea por frase. Los pedazos cortos se transcriben SIN prompt (con el texto del bloque de prompt Whisper repetía palabras sueltas).
Los umbrales de pausa son RELATIVOS al piso de ruido (un crudo con piso −38 dB no tiene "silencios" a −38): sin esto el crudo salía como
una sola frase sin tiempos y los tiempos de segs.json se inventaban a mano (desfase de segundos en los subtítulos, GUION3 30/10/2026).
Las frases largas (> 8 s sin pausa detectable) se parten por oraciones con los tiempos por palabra, en el punto más callado, y cada parte
se vuelve a transcribir: texto y tiempo salen del mismo tramo. Los tiempos de pieces.json son los que van a segs.json: NUNCA inventarlos.
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
import whisperlib as WL;LIV=WL.liviano(W)   # perfil liviano (8 GB): modelo q5 + whisper-server cargado una vez; el potente (Mac) no cambia
A=os.path.join(W,'audio16k.wav')
if not os.path.exists(A):
    subprocess.run(['ffmpeg','-v','error','-y','-i',src,'-vn','-ac','1','-ar','16000','-c:a','pcm_s16le',A],check=True)
# Nivel de análisis: los umbrales de voz/silencio de tighten.py, edl.py y qa_cut.py son absolutos (dB). Un crudo grabado bajo (WhatsApp ≈ −36 dB)
# haría que no se detecte la voz: se sube SOLO la copia de análisis (el audio del XML no se toca) hasta que la voz fuerte (p95) quede en ≈ −14 dB.
import wave,struct,math
def _envelope(p):   # dB RMS cada 20 ms
    w=wave.open(p);SR=w.getframerate();raw=w.readframes(w.getnframes());S=struct.unpack('<%dh'%(len(raw)//2),raw);n=int(SR*0.02)
    return [20*math.log10(max(1,math.sqrt(sum(x*x for x in S[i:i+n])/n))/32768) for i in range(0,len(S)-n,n)]
ENV=_envelope(A);_p=sorted(ENV)[int(len(ENV)*0.95)]
if _p<-20 and not os.path.exists(os.path.join(W,'analysis_gain.json')):
    _g=min(30.0,-14-_p);_t=A+'.tmp.wav'
    subprocess.run(['ffmpeg','-v','error','-y','-i',A,'-af',f'volume={_g:.1f}dB,alimiter=limit=0.95','-c:a','pcm_s16le',_t],check=True);os.replace(_t,A)
    json.dump(dict(gain_db=round(_g,1),voz_p95_antes=round(_p,1)),open(os.path.join(W,'analysis_gain.json'),'w'));print(f'ℹ️  crudo grabado bajo (voz ≈ {_p:.0f} dB): audio de análisis +{_g:.1f} dB (solo para detectar voz; el XML usa el audio original)')
    ENV=_envelope(A)
FLOOR=sorted(ENV)[len(ENV)//10]   # piso de ruido (percentil 10 del envolvente), igual que tighten.py / edl.py
dur=float(subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',A],capture_output=True,text=True).stdout)
def sil(n,d):
    out=subprocess.run(['ffmpeg','-i',A,'-af',f'silencedetect=noise={n}dB:d={d}','-f','null','-'],capture_output=True,text=True).stderr
    return list(zip([float(x) for x in re.findall(r'silence_start: ([\d.]+)',out)],[float(x) for x in re.findall(r'silence_end: ([\d.]+)',out)]))
# umbrales de pausa relativos al piso: con un piso de −38 dB (habitación ruidosa, ganancia baja) nada baja de −38/−36 y el crudo salía
# como UNA sola frase de principio a fin, sin tiempos. Con piso bajo (−55) quedan los −38/−36 de siempre.
NB=max(-38,FLOOR+6);NS=max(-36,FLOOR+8)
if NB>-38: print(f'ℹ️  piso de ruido {FLOOR:.0f} dB: umbrales de pausa {NB:.0f}/{NS:.0f} dB (relativos al piso)')
big=[s for s in sil(NB,0.25) if s[1]-s[0]>=0.9];small=sil(NS,0.15)
chunks=[];prev=0
for a,b in big:
    if a-prev>0.2: chunks.append((prev,a))
    prev=b
if dur-prev>0.2: chunks.append((prev,dur))
def tr(a,b,f,prompt=None):
    if WD is not None: return WL.span(WD,a,b)
    subprocess.run(['ffmpeg','-v','error','-y','-ss',str(max(0,a-0.08)),'-to',str(b+0.08),'-i',A,f])
    if LIV: return WL.text(f,W,prompt)
    cmd=[WHISPER,'-m',MODEL,'-f',f,'-l','es','-otxt','-of',f[:-4],'-t',str(min(8,os.cpu_count() or 4)),'-np']
    if prompt: cmd+=['--prompt',prompt]
    o=f[:-4]+'.txt'
    if os.path.exists(o): os.remove(o)  # no reusar el .txt de una corrida anterior
    for _ in range(3):  # whisper-cli a veces termina sin escribir el .txt (Windows): reintentar
        subprocess.run(cmd,capture_output=True)
        if os.path.exists(o): return open(o,encoding='utf-8').read().strip().replace('\n',' ')
    print(f'⚠️  sin transcripción para {os.path.basename(f)}',file=sys.stderr);return ''
WDS=WL.words(W,A)   # una pasada con tiempos por palabra (words_full.json): en el liviano es la transcripción; en el potente sirve para partir frases largas y para check
WD=WDS if LIV else None   # liviano: todo el audio de una pasada (en CPU cada pedacito cuesta 30 s de cómputo)
res=[]
for ci,(a,b) in enumerate(chunks):
    full=tr(a,b,os.path.join(W,'sub',f'c{ci:02d}.wav'))
    inner=[(s,e) for s,e in small if s>a+0.05 and e<b-0.05]
    pts=[a]+[x for s,e in inner for x in (s,e)]+[b]
    pieces=[(pts[k],pts[k+1]) for k in range(0,len(pts),2) if pts[k+1]-pts[k]>=0.3]   # < 0,3 s entre dos pausas = respiración/ruido: Whisper alucina ("Gracias", "CC por…")
    if len(pieces)<=1: res.append(dict(c=ci,a=round(a,2),b=round(b,2),t=full));continue
    for j,(pa,pb) in enumerate(pieces): res.append(dict(c=ci,a=round(pa,2),b=round(pb,2),t=tr(pa,pb,os.path.join(W,'sub',f'p{ci:02d}_{j}.wav'))))
# frases largas sin pausa detectable (voz continua): partirlas por oraciones con los tiempos por palabra, con el borde en el punto más
# callado cercano, y volver a transcribir cada parte (así el texto y el tiempo salen del mismo tramo y segs.json no necesita inventar nada)
MAXP=8.0
def quiet(t,rad=1.2):   # punto más callado (promedio de 100 ms) a ±rad s de t
    i0=max(2,int((t-rad)/0.02));i1=min(len(ENV)-3,int((t+rad)/0.02))
    return (min(range(i0,i1+1),key=lambda k:sum(ENV[k-2:k+3])) if i1>=i0 else int(t/0.02))*0.02
def cortes(ws,a,b,ends):
    out=[];last=a
    for i,w in enumerate(ws[:-1]):
        if w['t'].rstrip().endswith(ends):
            t=quiet(ws[i+1]['a'])
            if t-last>=1.0 and b-t>=1.0: out.append(t);last=t
    return out
out=[];nsplit=0
for p in res:
    if p['b']-p['a']<=MAXP or not WDS: out.append(p);continue
    ws=[w for w in WDS if p['a']-0.12<=w['a']<=p['b']+0.08]
    pts=[p['a']]+cortes(ws,p['a'],p['b'],('.','?','!',';','…'))+[p['b']]
    fin=[pts[0]]
    for x,y in zip(pts,pts[1:]):   # lo que sigue largo, también por comas
        if y-x>MAXP: fin+=cortes([w for w in ws if x-0.12<=w['a']<=y+0.08],x,y,(',',))
        fin.append(y)
    if len(fin)<=2: out.append(p);continue
    for j,(x,y) in enumerate(zip(fin,fin[1:])):
        t=tr(x,y,os.path.join(W,'sub',f's{p["c"]:02d}_{j}.wav'))
        if t.strip(): out.append(dict(c=p['c'],a=round(x,2),b=round(y,2),t=t,split=True))
    nsplit+=1
res=out
for p in res: print(f"{p['c']:02d} {p['a']:7.2f}-{p['b']:7.2f} {'÷ ' if p.get('split') else ''}{p['t']}")
if nsplit: print(f'÷ {nsplit} frase(s) de más de {MAXP:.0f} s partidas por oraciones (tiempos por palabra + punto más callado; cada parte re-transcripta)')
json.dump(res,open(os.path.join(W,'pieces.json'),'w'),ensure_ascii=False,indent=1)
print(f'\nduración {dur:.1f}s · {len(res)} frases')
