#!/usr/bin/env python3
"""Whisper para el perfil LIVIANO (notebooks de 8 GB, ej. la Windows del editor). En el perfil potente (Mac) no se usa:
los scripts siguen llamando a whisper-cli como siempre.
Liviano = mismo criterio que platform.js: EDICION_PERFIL, "perfil" en config.json o RAM < 12 GB.
- Modelo cuantizado ggml-large-v3-turbo-q5_0.bin (~550 MB, casi la misma precisión) si está descargado.
- whisper-server: carga el modelo UNA vez y queda en segundo plano; transcribe.py, tighten.py y check.py le mandan
  cada pedazo por HTTP en vez de abrir whisper-cli (que recargaba 1,6 GB por frase). Si el server no arranca, vuelve a whisper-cli.
uso: python3 -I whisperlib.py status|start|stop      (stop libera la RAM antes del render)
"""
import os as _o,sys as _s,subprocess as _sp
if _o.name=='nt' and __name__=='__main__' and not _s.flags.utf8_mode: _s.exit(_sp.run([_s.executable,'-X','utf8','-I',_o.path.abspath(__file__),*_s.argv[1:]]).returncode)  # Windows: acentos en UTF-8
import os,sys,json,shutil,subprocess,time,uuid,urllib.request,urllib.error
CACHE=os.path.expanduser('~/.cache/whisper-cpp')
MODEL=os.path.join(CACHE,'ggml-large-v3-turbo.bin');MODEL_Q5=os.path.join(CACHE,'ggml-large-v3-turbo-q5_0.bin')
LAD=os.path.join(os.environ.get('LOCALAPPDATA',''),'whisper-cpp')
WHISPER=os.environ.get('WHISPER_CLI') or shutil.which('whisper-cli') or os.path.join(LAD,'whisper-cli.exe')
SERVER=os.environ.get('WHISPER_SERVER') or shutil.which('whisper-server') or os.path.join(LAD,'whisper-server.exe')
PORT=int(os.environ.get('EDICION_WHISPER_PORT','8178'));URL=f'http://127.0.0.1:{PORT}'
STATE=os.path.join(CACHE,'server.json')
THREADS=min(8,os.cpu_count() or 4)

def ram_gb():
    try:
        if os.name=='nt':
            import ctypes
            class M(ctypes.Structure): _fields_=[('l',ctypes.c_ulong),('m',ctypes.c_ulong)]+[(n,ctypes.c_ulonglong) for n in ('t','a','tp','ap','tv','av','ae')]
            m=M();m.l=ctypes.sizeof(M);ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m));return m.t/2**30
        if sys.platform=='darwin': return int(subprocess.run(['sysctl','-n','hw.memsize'],capture_output=True,text=True).stdout)/2**30
        return os.sysconf('SC_PAGE_SIZE')*os.sysconf('SC_PHYS_PAGES')/2**30
    except Exception: return 16
def perfil(W=None):
    arg=next((a[9:] for a in sys.argv if a.startswith('--perfil=')),'')
    cfg={}
    try: cfg=json.load(open(os.path.join(W,'config.json'),encoding='utf-8')) if W else {}
    except Exception: pass
    return arg or os.environ.get('EDICION_PERFIL') or cfg.get('perfil') or ('liviano' if ram_gb()<12 else 'potente')
def liviano(W=None): return perfil(W)=='liviano'
def model(W=None):
    if os.environ.get('EDICION_WHISPER_MODEL'): return os.environ['EDICION_WHISPER_MODEL']
    return MODEL_Q5 if liviano(W) and os.path.exists(MODEL_Q5) else MODEL

# --- server ---
def _get(path,timeout=2):
    try:
        with urllib.request.urlopen(URL+path,timeout=timeout) as r: return r.status
    except urllib.error.HTTPError as e: return e.code
    except Exception: return None
def _ready():
    s=_get('/health')
    return s==200 or s==404   # 404 = versión sin /health: si responde, ya cargó el modelo (escucha después de cargarlo)
def start(W=None,wait=180):
    if _ready(): return True
    if not (os.path.exists(SERVER) or shutil.which(SERVER)): return False
    m=model(W);os.makedirs(CACHE,exist_ok=True);log=open(os.path.join(CACHE,'server.log'),'w')
    kw=dict(creationflags=0x00000008|0x00000200|0x08000000) if os.name=='nt' else dict(start_new_session=True)   # DETACHED | NEW_GROUP | NO_WINDOW
    p=subprocess.Popen([SERVER,'-m',m,'-t',str(THREADS),'-l','es','--host','127.0.0.1','--port',str(PORT)],stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,**kw)
    json.dump(dict(pid=p.pid,port=PORT,model=m),open(STATE,'w'))
    t0=time.time()
    while time.time()-t0<wait:
        if p.poll() is not None: return False
        if _ready(): print(f'whisper-server listo ({os.path.basename(m)}, {THREADS} hilos, {time.time()-t0:.0f}s)',file=sys.stderr);return True
        time.sleep(0.5)
    return False
def stop():
    try: st=json.load(open(STATE))
    except Exception: return False
    try:
        if os.name=='nt': subprocess.run(['taskkill','/PID',str(st['pid']),'/T','/F'],capture_output=True)
        else: os.kill(st['pid'],15)
    except Exception: pass
    os.remove(STATE);return True
def _post(wav,prompt):
    b=uuid.uuid4().hex;parts=[]
    for k,v in (('language','es'),('response_format','text'),('temperature','0.0'),('prompt',prompt or '')):   # prompt siempre (vacío = sin prompt): que no quede el de un pedido anterior
        parts.append(f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    parts.append(f'--{b}\r\nContent-Disposition: form-data; name="file"; filename="a.wav"\r\nContent-Type: audio/wav\r\n\r\n'.encode()+open(wav,'rb').read()+b'\r\n')
    parts.append(f'--{b}--\r\n'.encode())
    req=urllib.request.Request(URL+'/inference',data=b''.join(parts),headers={'Content-Type':f'multipart/form-data; boundary={b}'})
    with urllib.request.urlopen(req,timeout=600) as r: return r.read().decode('utf-8')
def text(wav,W=None,prompt=None):
    """Texto de un wav corto (sin tiempos). Usa el server; si falla, whisper-cli con el mismo modelo y todos los hilos."""
    if start(W):
        try: return ' '.join(_post(wav,prompt).split())
        except Exception as e: print(f'⚠️  whisper-server falló ({e}); sigo con whisper-cli',file=sys.stderr)
    cmd=[WHISPER,'-m',model(W),'-f',wav,'-l','es','-np','-nt','-t',str(THREADS)]+(['--prompt',prompt] if prompt else [])
    return ' '.join(subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8').stdout.split())

if __name__=='__main__':
    c=sys.argv[1] if len(sys.argv)>1 else 'status'
    if c=='start': ok=start();print('whisper-server corriendo ✓' if ok else '✗ no arrancó (ver ~/.cache/whisper-cpp/server.log): se usa whisper-cli');sys.exit(0 if ok else 1)
    elif c=='stop': print('whisper-server detenido ✓' if stop() else 'whisper-server no estaba corriendo')
    else: print(f"perfil {perfil()} ({ram_gb():.0f} GB) · modelo {os.path.basename(model())} · server {'corriendo' if _ready() else 'detenido'} en {URL}")
