#!/usr/bin/env python3
"""Paso 2c: CONFORMA el crudo en un master a 30 fps constantes con el audio alineado al fotograma. Garantía anti-desfase.
uso: python3 -I conform.py <workdir> <edit_dir> <crudo.mp4> [--name NOMBRE] [--force] 
Por qué: los crudos de celular/WhatsApp suelen ser de fps variable (VFR), arrancar el audio unos ms antes/después que el video,
tener audio y video de distinto largo o ser de 24 fps dentro de una secuencia de 30. Si Whisper, los cortes y Premiere leen
archivos/relojes distintos, el audio se corre del video (a veces solo de a poco, por eso "a veces"). Con el master hay UN solo reloj:
  · todo (transcripción, cortes, XML) se hace sobre el master → es la línea de tiempo de Premiere por construcción
  · video CFR 30 fps vertical 1080×1920 (rotación aplicada), audio PCM 48 kHz estéreo (sin retraso de AAC), empiezan juntos en 0
  · el audio mide lo mismo que el video (al fotograma) y se comprueba con la correlación contra el original (arranque Y final: detecta deriva)
El audio NO se procesa (sin EQ, sin reducción de ruido, sin compresión ni normalización): el master tiene la voz tal cual se grabó; solo se mide su nivel (voice_lufs en conform.json).
Salida: <edit_dir>/Assets/Crudo/<NOMBRE>_master.mov + <workdir>/conform.json → usar "master" como config.src y como entrada de transcribe.py.
"""
import os as _o,sys as _s,subprocess as _sp
if _o.name=='nt' and __name__=='__main__' and not _s.flags.utf8_mode: _s.exit(_sp.run([_s.executable,'-X','utf8','-I',_o.path.abspath(__file__),*_s.argv[1:]]).returncode)  # Windows: acentos en UTF-8
import json,os,sys,subprocess,time,wave,struct,math,tempfile
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)));import audiochain as ac
argv=sys.argv[1:];opts={};args=[]
i=0
while i<len(argv):
    x=argv[i]
    if x=='--name': opts['name']=argv[i+1] if i+1<len(argv) else '';i+=1
    elif x.startswith('--name='): opts['name']=x[7:]
    elif x.startswith('--'): k,_,v=x[2:].partition('=');opts[k]=v or '1'
    else: args.append(x)
    i+=1
if len(args)<3: print(__doc__);sys.exit(1)
W,EDIT,SRC=args[0],args[1],os.path.abspath(args[2]);FPS=30
os.makedirs(W,exist_ok=True)
import atexit;sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)));import timing;_t0=time.time();atexit.register(lambda:timing.log(W,'Conformar crudo (anti-desfase)',time.time()-_t0))
name=opts.get('name') or None
if not name:
    cf=os.path.join(W,'config.json');name=(json.load(open(cf)).get('name') if os.path.exists(cf) else None) or os.path.basename(os.path.normpath(EDIT)).removesuffix('_EDIT')
OUT=os.path.join(EDIT,'Assets','Crudo',f'{name}_master.mov');os.makedirs(os.path.dirname(OUT),exist_ok=True)
def probe(p):
    d=json.loads(subprocess.run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',p],capture_output=True,text=True).stdout or '{}')
    v=next((s for s in d.get('streams',[]) if s.get('codec_type')=='video' and not (s.get('disposition') or {}).get('attached_pic')),None)
    a=next((s for s in d.get('streams',[]) if s.get('codec_type')=='audio'),None)
    return d,v,a
fnum=lambda r:(lambda n,d:float(n)/float(d) if float(d) else 0.0)(*(r or '0/1').split('/'))
fl=lambda x,default=0.0:float(x) if x not in (None,'N/A','') else default
d,v,a=probe(SRC)
if not v: sys.exit('✗ el archivo no tiene video')
if not a: sys.exit('✗ el archivo no tiene audio')
rot=0
for sd in v.get('side_data_list',[]) or []:
    if 'rotation' in sd: rot=int(round(float(sd['rotation'])))
vs,as_=fl(v.get('start_time')),fl(a.get('start_time'));a_off=as_-vs
vdur=fl(v.get('duration'),fl(d['format'].get('duration')));adur=fl(a.get('duration'),fl(d['format'].get('duration')))
r_fps,avg=fnum(v.get('r_frame_rate')),fnum(v.get('avg_frame_rate'));vfr=r_fps>0 and abs(avg-r_fps)/r_fps>0.004
notes=[]
if vfr: notes.append(f'fps variable (VFR): {avg:.3f} promedio de {r_fps:g}')
if abs(avg-FPS)>0.5 and not vfr: notes.append(f'el crudo es de {avg:.2f} fps y la secuencia es de {FPS}')
if abs(a_off)>0.002: notes.append(f'el audio arranca {a_off*1000:+.1f} ms respecto del video')
if abs(adur-vdur)>1/FPS: notes.append(f'audio ({adur:.3f}s) y video ({vdur:.3f}s) no miden lo mismo')
if v.get('color_transfer') in ('arib-std-b67','smpte2084'): notes.append('⚠️ HDR (HLG/PQ): el master sale SDR sin tone-mapping; si se ve lavado grabar en SDR')
print('crudo:',os.path.basename(SRC),f'· {v.get("width")}×{v.get("height")} rot {rot} · {avg:.3f} fps · video {vdur:.3f}s · audio {adur:.3f}s')
print('  detectado:',('; '.join(notes) if notes else 'nada raro (igual se conforma: un solo reloj para todo)'))
# ya conformado y vigente → reusar
CJ=os.path.join(W,'conform.json')
if os.path.exists(OUT) and os.path.exists(CJ) and 'force' not in opts:
    try:
        c=json.load(open(CJ))
        if c.get('src_original')==SRC and c.get('src_mtime')==os.path.getmtime(SRC) and os.path.getmtime(OUT)>=os.path.getmtime(SRC): print('✓ master vigente:',OUT);print('→ src:',OUT);sys.exit(0)
    except Exception: pass
T=round(vdur*FPS)/FPS   # largo del master: múltiplo exacto de un fotograma
# audio: los dos relojes se llevan a 0 = arranque del VIDEO (asetpts resta ese arranque); aresample(first_pts=0) rellena con silencio (o recorta)
# la diferencia de arranque del audio y fija el largo exacto con apad/atrim → el audio queda donde estaba respecto del video, al milisegundo
afix=f'asetpts=PTS-{vs:.6f}/TB,'
chain=''
fc=(f'[0:v:0]setpts=PTS-STARTPTS,scale=1080:1920:force_original_aspect_ratio=increase:out_color_matrix=bt709:out_range=tv,crop=1080:1920,setsar=1,'
    f'fps={FPS}:round=near,tpad=stop_mode=clone:stop_duration=2,trim=duration={T:.6f},setpts=PTS-STARTPTS,format=yuv420p[v];'
    f'[0:a:0]{afix}aresample=48000:async=1:first_pts=0,{chain}aformat=sample_fmts=s16:channel_layouts=stereo,apad,atrim=0:{T:.6f},asetpts=PTS-STARTPTS[a]')
cmd=['ffmpeg','-v','error','-y','-i',SRC,'-filter_complex',fc,'-map','[v]','-map','[a]','-c:v','libx264','-preset','fast','-crf','14','-g','15',
     '-colorspace','bt709','-color_primaries','bt709','-color_trc','bt709','-video_track_timescale','30000','-c:a','pcm_s16le','-ar','48000','-fps_mode','cfr','-r',str(FPS),OUT]
print('… conformando el crudo (1 minuto de video tarda ~20-40 s)',flush=True)
if subprocess.run(cmd).returncode: sys.exit('✗ ffmpeg falló conformando el crudo')
# ── verificación del master ──
d2,v2,a2=probe(OUT)
nb=int(subprocess.run(['ffprobe','-v','error','-count_packets','-select_streams','v:0','-show_entries','stream=nb_read_packets','-of','csv=p=0',OUT],capture_output=True,text=True).stdout.strip().strip(',') or 0)
errs=[]
if fnum(v2.get('r_frame_rate'))!=FPS or abs(fnum(v2.get('avg_frame_rate'))-FPS)>1e-6: errs.append(f'el master no es CFR 30 (r {v2.get("r_frame_rate")}, avg {v2.get("avg_frame_rate")})')
if (int(v2['width']),int(v2['height']))!=(1080,1920): errs.append(f'el master mide {v2["width"]}×{v2["height"]}, no 1080×1920')
if abs(fl(v2.get('start_time')))>1e-4 or abs(fl(a2.get('start_time')))>1e-4: errs.append(f'el master no arranca en 0 (video {v2.get("start_time")}, audio {a2.get("start_time")})')
vd2,ad2=nb/FPS,fl(a2.get('duration'),fl(d2['format'].get('duration')))
if abs(vd2-ad2)>1/FPS: errs.append(f'audio ({ad2:.3f}s) y video ({vd2:.3f}s) del master difieren más de 1 fotograma')
if abs(vd2-T)>1.5/FPS: errs.append(f'el master dura {vd2:.3f}s y el crudo {T:.3f}s')
# correlación de la envolvente de energía master vs original, al arranque Y al final (deriva)
HOP=0.005;SR=8000
def env(p,trim=0.0):
    tmp=tempfile.mkdtemp();f=os.path.join(tmp,'a.wav')
    subprocess.run(['ffmpeg','-v','error','-y','-i',p,'-vn','-ac','1','-ar',str(SR),'-c:a','pcm_s16le',f],check=True)
    with wave.open(f) as w: raw=w.readframes(w.getnframes())
    S=struct.unpack('<%dh'%(len(raw)//2),raw);n=int(SR*HOP)
    e=[math.log10(1+math.sqrt(sum(x*x for x in S[i*n:(i+1)*n])/n)) for i in range(len(S)//n)]
    os.unlink(f);os.rmdir(tmp);return e
eo,em=env(SRC),env(OUT)
shift=round(a_off/HOP)   # el master es el original corrido +a_off
def lag(i0,i1,rng=24):
    A=em[i0:i1];ma=sum(A)/len(A);A=[x-ma for x in A];na=math.sqrt(sum(x*x for x in A)) or 1;best=None
    for L in range(-rng,rng+1):
        j0=i0-shift+L
        if j0<0 or j0+len(A)>len(eo): continue
        B=eo[j0:j0+len(A)];mb=sum(B)/len(B);B=[x-mb for x in B];nb_=math.sqrt(sum(x*x for x in B)) or 1
        sc=sum(x*y for x,y in zip(A,B))/(na*nb_)
        if best is None or sc>best[0]: best=(sc,L)
    return best or (0,0)
n=min(len(em),len(eo));win=int(min(10,n*HOP/3.2)/HOP)
lags=[]
if n*HOP>=6:
    for lab,(i0,i1) in (('arranque',(int(1/HOP),int(1/HOP)+win)),('final',(n-win-int(1/HOP),n-int(1/HOP)))):
        s,L=lag(i0,i1);lags.append((lab,L*HOP*1000,s))
    for lab,ms,s in lags:
        if abs(ms)>10: errs.append(f'el audio del master está corrido {ms:+.0f} ms respecto del original al {lab}')
    if abs(lags[1][1]-lags[0][1])>15: errs.append(f'deriva de audio: {lags[0][1]:+.0f} ms al arranque → {lags[1][1]:+.0f} ms al final')
vlufs=ac.ebur(OUT)
print(f'  voz tal cual se grabó: {vlufs["I"]} LUFS · true peak {vlufs["TP"]} dBTP')
print(f'  master: {nb} fotogramas · {vd2:.3f}s · audio {ad2:.3f}s · desfase audio vs original: '+(' / '.join(f'{lab} {ms:+.0f} ms' for lab,ms,s in lags) or 'n/a (muy corto)'))
if errs:
    print('✗ EL MASTER NO PASÓ LA VERIFICACIÓN:');[print('  ·',e) for e in errs];sys.exit(2)
json.dump(dict(voice_lufs=vlufs['I'],src_original=SRC,src_mtime=os.path.getmtime(SRC),master=OUT,frames=nb,dur=nb/FPS,audio_offset_ms=round(a_off*1000,2),vfr=vfr,src_fps=round(avg,3),notes=notes,lags=[(l,round(m,1)) for l,m,_ in lags]),open(CJ,'w'),ensure_ascii=False,indent=1)
print('✓ master verificado (CFR 30 · audio y video juntos desde 0 · sin deriva)\n→ src (config.json) y entrada de transcribe.py:',OUT)
