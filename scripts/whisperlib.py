#!/usr/bin/env python3
"""Whisper para el perfil LIVIANO (notebooks de 8 GB, ej. la Windows del editor). En el perfil potente (Mac) no se usa:
los scripts siguen llamando a whisper-cli como siempre.
Liviano = mismo criterio que platform.js: EDICION_PERFIL, "perfil" en config.json o RAM < 12 GB.
En el liviano TODO Whisper es remoto (OpenAI vía n8n): transcribe.py, tighten.py, check.py y align.py. Nada corre en local;
si el remoto no está configurado o falla 3 veces, el paso se corta con un error claro.
uso: python3 -I whisperlib.py status|stop      (stop apaga un whisper-server local que haya quedado de versiones anteriores)
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
# Whisper remoto (OpenAI vía n8n), obligatorio en el perfil liviano (los scripts del potente no pasan por acá).
# ~/.config/edicion/whisper_remoto.json {"url": "...", "token": "..."} o EDICION_WHISPER_REMOTO / EDICION_WHISPER_TOKEN.
def _remote_cfg():
    c={}
    try: c=json.load(open(os.path.expanduser('~/.config/edicion/whisper_remoto.json'),encoding='utf-8'))
    except Exception: pass
    url=os.environ.get('EDICION_WHISPER_REMOTO') or c.get('url');tok=os.environ.get('EDICION_WHISPER_TOKEN') or c.get('token')
    return (url,tok,c.get('model')) if url and tok else None
REMOTE=_remote_cfg()
def _remote(wav,prompt=None,words=False):
    import urllib.parse
    if os.path.getsize(wav)>24*2**20: raise RuntimeError('audio > 24 MB (límite de OpenAI)')
    url,tok,mdl=REMOTE;q={k:v for k,v in (('words','1' if words else ''),('prompt',(prompt or '')[:600]),('model',mdl or '')) if v}
    req=urllib.request.Request(url+('?'+urllib.parse.urlencode(q) if q else ''),data=open(wav,'rb').read(),headers={'Content-Type':'audio/wav','x-edicion-token':tok})
    with urllib.request.urlopen(req,timeout=300) as r: return json.loads(r.read().decode('utf-8'))
def remote(wav,prompt=None,words=False,tries=3):
    """Pedido al remoto con reintentos. Sin remoto configurado, o si falla las 3 veces, corta: en el liviano no hay Whisper local."""
    if not REMOTE: sys.exit('✗ perfil liviano sin Whisper remoto: falta ~/.config/edicion/whisper_remoto.json (o EDICION_WHISPER_REMOTO y EDICION_WHISPER_TOKEN). En el liviano no se usa Whisper local.')
    for k in range(tries):
        try: return _remote(wav,prompt,words)
        except Exception as e:
            if k==tries-1: sys.exit(f'✗ Whisper remoto falló {tries} veces ({e}). En el perfil liviano no se usa Whisper local: revisar internet o el workflow de n8n y volver a correr este paso.')
            print(f'⚠️  Whisper remoto falló ({e}); reintento en {3*(k+1)} s',file=sys.stderr);time.sleep(3*(k+1))
def remote_words(wav):
    """Palabras [{t,a,b}] (segundos, tal cual los da OpenAI) del wav, del remoto. Las palabras vienen sin puntuación: si coinciden en cantidad, se usan las del texto."""
    r=remote(wav,words=True);ws=r.get('words') or [];tx=(r.get('text') or '').split()
    return [dict(t=tx[i] if len(tx)==len(ws) else w['word'],a=w['start'],b=w['end']) for i,w in enumerate(ws)]

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
def stop():
    try: st=json.load(open(STATE))
    except Exception: return False
    try:
        if os.name=='nt': subprocess.run(['taskkill','/PID',str(st['pid']),'/T','/F'],capture_output=True)
        else: os.kill(st['pid'],15)
    except Exception: pass
    os.remove(STATE);return True
def text(wav,W=None,prompt=None):
    """Texto de un wav corto (sin tiempos), del remoto."""
    return ' '.join((remote(wav,prompt).get('text') or '').split())

# --- una pasada: todo el audio una vez con tiempos por palabra ---
def words(W,wav):
    """Palabras [{t,a}] (a = arranque en segundos) de todo el wav, transcripto una sola vez. Se guarda en <W>/words_full.json mientras el wav no cambie."""
    st=os.stat(wav);key=[st.st_size,int(st.st_mtime)];cache=os.path.join(W,'words_full.json')
    try:
        c=json.load(open(cache,encoding='utf-8'))
        if c['key']==key: return c['words']
    except Exception: pass
    # OpenAI pega el arranque de cada palabra al final de la anterior (se come el silencio): el arranque real sale del final
    t0=time.time();out=[dict(t=w['t'],a=round(max(w['a'],w['b']-0.2),2)) for w in remote_words(wav)]
    if not out: return None
    json.dump(dict(key=key,words=out,src='remoto'),open(cache,'w',encoding='utf-8'),ensure_ascii=False)
    print(f'transcripción de una pasada (remota): {len(out)} palabras en {time.time()-t0:.0f}s',file=sys.stderr);return out
def span(ws,a,b):
    """Texto de las palabras que arrancan en [a, b] (DTW marca el arranque con ~0,1 s de margen)."""
    return ' '.join(w['t'] for w in ws if a-0.12<=w['a']<=b+0.08)

def assign(ws,rs,txt):
    """Reparte el texto del guion (txt) entre las regiones de voz rs=[[a,b],...] de una frase: cada palabra del guion se empareja
    con la que oyó Whisper y va a la región donde arranca esa palabra (en un silencio → la región siguiente); las que no se
    emparejan siguen a su vecina. Devuelve el texto de cada región."""
    import difflib,re,unicodedata
    nm=lambda x:re.sub(r'[^a-z0-9ñ]','',unicodedata.normalize('NFD',x.lower().replace('ñ','\0')).encode('ascii','ignore').decode().replace('\0','ñ'))
    heard=[w for w in ws if rs[0][0]-0.12<=w['a']<=rs[-1][1]+0.08];words=txt.split()
    reg=lambda t:sum(t>=r[0] for r in rs[1:])
    k=[None]*len(words)
    for tag,i1,i2,j1,j2 in difflib.SequenceMatcher(None,[nm(x) for x in words],[nm(w['t']) for w in heard],autojunk=False).get_opcodes():
        if tag=='equal' or (tag=='replace' and i2-i1==j2-j1):
            for d in range(i2-i1): k[i1+d]=reg(heard[j1+d]['a'])
    last=0
    for i in range(len(k)):   # sin emparejar → la región de la anterior; y nunca hacia atrás
        k[i]=max(last,k[i] if k[i] is not None else last);last=k[i]
    out=[[] for _ in rs]
    for w,r in zip(words,k): out[r].append(w)
    return [' '.join(x) for x in out]

if __name__=='__main__':
    c=sys.argv[1] if len(sys.argv)>1 else 'status'
    if c=='stop': print('whisper-server detenido ✓' if stop() else 'whisper-server no estaba corriendo')
    else: print(f"perfil {perfil()} ({ram_gb():.0f} GB) · Whisper {('remoto: '+REMOTE[0]) if REMOTE else 'remoto SIN CONFIGURAR (el liviano no funciona sin él)'} · server local {'corriendo (sobra: python3 -I whisperlib.py stop)' if _ready() else 'detenido'}" if liviano() else f"perfil {perfil()} ({ram_gb():.0f} GB) · Whisper local (whisper-cli)")
