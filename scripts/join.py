#!/usr/bin/env python3
"""Paso 0 (opcional): une un crudo grabado en varias partes en un solo archivo, que pasa a ser config.src.
uso: python3 -I join.py <workdir> <edit_dir> parte1.mp4 parte2.mp4 ... [--order name|date|given] [--name NOMBRE]
  --order name  (default) orden natural por nombre de archivo: IMG_0012 < IMG_0103, "parte 2" < "parte 10"
          date  fecha de grabación (creation_time; si no está, fecha del archivo)
          given el orden de los argumentos
Si todas las partes tienen el mismo formato (codec, tamaño, rotación, fps, audio) se unen sin recodificar;
si no, se recodifican a 1080×1920, 30 fps CFR, H.264 CRF 16 + AAC 48 kHz (con la rotación ya aplicada).
Salida: <edit_dir>/Assets/Crudo/<NOMBRE>_crudo_unido.mp4 + <workdir>/parts.json (offset de cada parte).
"""
import os as _o,sys as _s,subprocess as _sp
if _o.name=='nt' and __name__=='__main__' and not _s.flags.utf8_mode: _s.exit(_sp.run([_s.executable,'-X','utf8','-I',_o.path.abspath(__file__),*_s.argv[1:]]).returncode)  # Windows: acentos en UTF-8
import json,os,re,sys,subprocess,time,tempfile
from datetime import datetime
args=[a for a in sys.argv[1:] if not a.startswith('--')];opts=dict(a[2:].split('=',1) if '=' in a else (a[2:],'') for a in sys.argv[1:] if a.startswith('--'))
# también acepta "--order date" separado
for k in ('order','name'):
    if k in opts and not opts[k] and ('--'+k) in sys.argv:
        i=sys.argv.index('--'+k)
        if i+1<len(sys.argv): opts[k]=sys.argv[i+1];args.remove(sys.argv[i+1])
if len(args)<3: print(__doc__);sys.exit(1)
W,EDIT,parts=args[0],args[1],[os.path.abspath(p) for p in args[2:]]
os.makedirs(W,exist_ok=True)
import atexit;sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)));import timing;_t0=time.time();atexit.register(lambda:timing.log(W,'Unir partes del crudo',time.time()-_t0))
for p in parts:
    if not os.path.isfile(p): sys.exit(f'✗ no existe: {p}')

def probe(p):
    d=json.loads(subprocess.run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',p],capture_output=True,text=True).stdout or '{}')
    v=next((s for s in d.get('streams',[]) if s.get('codec_type')=='video' and not (s.get('disposition') or {}).get('attached_pic')),None)
    a=next((s for s in d.get('streams',[]) if s.get('codec_type')=='audio'),None)
    if not v: sys.exit(f'✗ sin video: {p}')
    rot=0
    for sd in v.get('side_data_list',[]) or []:
        if 'rotation' in sd: rot=int(round(float(sd['rotation'])))
    if not rot and (v.get('tags') or {}).get('rotate'): rot=-int(v['tags']['rotate'])
    rot%=360
    num,den=(v.get('avg_frame_rate') or '0/1').split('/');fps=float(num)/float(den) if float(den) else 0
    ct=(v.get('tags') or {}).get('creation_time') or (d.get('format',{}).get('tags') or {}).get('creation_time') \
       or (d.get('format',{}).get('tags') or {}).get('com.apple.quicktime.creationdate')
    try: when=datetime.fromisoformat(ct.replace('Z','+00:00')).timestamp() if ct else None
    except Exception: when=None
    fl=lambda x:float(x) if x not in (None,'N/A','') else None
    rf=(lambda n,dn:float(n)/float(dn) if float(dn) else 0)(*(v.get('r_frame_rate') or '0/1').split('/'))
    vfr=bool(rf) and abs(fps-rf)/rf>0.004
    return dict(vdur=fl(v.get('duration')),adur=a and fl(a.get('duration')),vfr=vfr,path=p,dur=float(d['format']['duration']),vcodec=v.get('codec_name'),w=v.get('width'),h=v.get('height'),rot=rot,
                fps=round(fps,2),pix=v.get('pix_fmt'),acodec=a and a.get('codec_name'),ar=a and a.get('sample_rate'),ch=a and a.get('channels'),
                when=when if when else os.path.getmtime(p),when_src='grabación' if when else 'archivo')

nat=lambda p:[int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)',os.path.basename(p))]
info={p:probe(p) for p in parts}
order=opts.get('order') or 'name'
if order=='name': parts.sort(key=nat)
elif order=='date': parts.sort(key=lambda p:(info[p]['when'],nat(p)))
elif order!='given': sys.exit('✗ --order tiene que ser name, date o given')
P=[info[p] for p in parts]

# ¿el orden es dudoso? nombres sin números y sin fecha de grabación → avisar
if order=='name' and not all(re.search(r'\d',os.path.basename(p)) for p in parts):
    print('⚠️  algunos nombres no tienen numeración: confirmá el orden (o usá --order date / --order given)')
if order=='name':
    ws=[x['when'] for x in P if x['when_src']=='grabación']
    if len(ws)==len(P) and ws!=sorted(ws): print('⚠️  el orden por nombre no coincide con la fecha de grabación: revisalo (--order date para usar la fecha)')

KEY=('vcodec','w','h','rot','fps','pix','acodec','ar','ch')
# Sin recodificar SOLO si además cada parte es CFR y su audio mide lo mismo que su video (±1 fotograma): en modo copy las diferencias
# de largo de cada parte se acumulan y el audio de las partes siguientes queda corrido (desfase). Ante la duda se recodifica con relleno.
def clean(x): return not x['vfr'] and x['vdur'] is not None and x['adur'] is not None and abs(x['vdur']-x['adur'])<=1/max(x['fps'],1)
same=all(all(x[k]==P[0][k] for k in KEY) for x in P) and P[0]['acodec'] is not None and all(clean(x) for x in P)
if not same and all(all(x[k]==P[0][k] for k in KEY) for x in P): print('ℹ️  las partes tienen fps variable o audio y video de distinto largo: se recodifican para que el audio no se corra')
name=opts.get('name') or (json.load(open(os.path.join(W,'config.json'))).get('name') if os.path.exists(os.path.join(W,'config.json')) else None) \
     or os.path.basename(os.path.normpath(EDIT)).removesuffix('_EDIT')
outdir=os.path.join(EDIT,'Assets','Crudo');os.makedirs(outdir,exist_ok=True)
out=os.path.join(outdir,f'{name}_crudo_unido.mp4')

if same:
    mode='sin recodificar'
    lst=tempfile.NamedTemporaryFile('w',suffix='.txt',delete=False,dir=W)
    for x in P: lst.write("file '"+x['path'].replace("'","'\\''")+"'\n")
    lst.close()
    cmd=['ffmpeg','-v','error','-y','-f','concat','-safe','0','-i',lst.name,'-map','0:v:0','-map','0:a:0','-c','copy','-movflags','+faststart',out]
else:
    mode='recodificado (las partes tienen formatos distintos)'
    cmd=['ffmpeg','-v','error','-y'];fc=[]
    for i,x in enumerate(P):
        cmd+=['-i',x['path']]
        # video estirado hasta la duración de la parte (WhatsApp/celulares: el video suele ser más corto que el audio
        # y sin esto cada parte siguiente arranca con el video adelantado → desincronizado en Premiere)
        fc.append(f'[{i}:v:0]setpts=PTS-STARTPTS,scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=30,tpad=stop_mode=clone:stop_duration=2,trim=duration={x["dur"]:.3f},setpts=PTS-STARTPTS,format=yuv420p[v{i}]')
        # async=1:first_pts=0 rellena con silencio los huecos de marcas de tiempo (WhatsApp: el 1er paquete de audio
        # "dura" ~0,2 s; sin esto el audio queda adelantado al video en Premiere/transcripción)
        if x['acodec']: fc.append(f'[{i}:a:0]aresample=48000:async=1:first_pts=0,aformat=channel_layouts=stereo,apad,atrim=0:{x["dur"]:.3f},asetpts=N/SR/TB[a{i}]')
        else: fc.append(f'anullsrc=r=48000:cl=stereo,atrim=0:{x["dur"]:.3f}[a{i}]')
    fc.append(''.join(f'[v{i}][a{i}]' for i in range(len(P)))+f'concat=n={len(P)}:v=1:a=1[v][a]')
    cmd+=['-filter_complex',';'.join(fc),'-map','[v]','-map','[a]','-fps_mode','cfr','-r','30','-c:v','libx264','-preset','medium','-crf','16','-c:a','aac','-b:a','256k','-ar','48000','-movflags','+faststart',out]
    print('… recodificando (tarda unos minutos)',flush=True)
r=subprocess.run(cmd)
if same: os.unlink(lst.name)
if r.returncode: sys.exit('✗ ffmpeg falló uniendo las partes')

# offsets reales: en modo copy la duración de cada parte puede variar unos ms
rows=[];t=0
for i,x in enumerate(P):
    rows.append(dict(part=i+1,path=x['path'],file=os.path.basename(x['path']),start=round(t,3),dur=round(x['dur'],3)));t+=x['dur']
total=float(subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',out],capture_output=True,text=True).stdout.strip() or 0)
json.dump(dict(out=out,mode=mode,order=order,parts=rows,total=round(total,3)),open(os.path.join(W,'parts.json'),'w'),indent=1,ensure_ascii=False)
tc=lambda s:f'{int(s//60)}:{s%60:05.2f}'
print(f'✓ {len(P)} partes unidas ({mode}), orden: {order}')
for x in rows: print(f'  Parte {x["part"]}: {x["file"]} · {tc(x["dur"])} · arranca en {tc(x["start"])}')
print(f'  total {tc(total)} (suma de partes {tc(t)})'+('  ⚠️ difiere' if abs(total-t)>0.5 else ''))
print(f'→ src: {out}')
