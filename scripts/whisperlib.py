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
# PRUEBA · Whisper remoto (OpenAI vía n8n): solo si está configurado, y solo en el perfil liviano (los scripts del potente no pasan por acá).
# ~/.config/edicion/whisper_remoto.json {"url": "...", "token": "..."} o EDICION_WHISPER_REMOTO / EDICION_WHISPER_TOKEN. Si falla, sigue con Whisper local.
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
_failed=False   # si el server no arrancó una vez, no reintentar en cada frase (cada intento recarga el modelo)
def start(W=None,wait=180):
    global _failed
    if _ready(): return True
    if _failed: return False
    _failed=True
    if not (os.path.exists(SERVER) or shutil.which(SERVER)): return False
    m=model(W);os.makedirs(CACHE,exist_ok=True);log=open(os.path.join(CACHE,'server.log'),'w')
    kw=dict(creationflags=0x00000008|0x00000200|0x08000000) if os.name=='nt' else dict(start_new_session=True)   # DETACHED | NEW_GROUP | NO_WINDOW
    print('arrancando whisper-server…',file=sys.stderr)
    p=subprocess.Popen([SERVER,'-m',m,'-t',str(THREADS),'-l','es','--host','127.0.0.1','--port',str(PORT)],stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,**kw)
    json.dump(dict(pid=p.pid,port=PORT,model=m),open(STATE,'w'))
    t0=time.time()
    while time.time()-t0<wait:
        if p.poll() is not None: break
        if _ready(): _failed=False;print(f'whisper-server listo ({os.path.basename(m)}, {THREADS} hilos, {time.time()-t0:.0f}s)',file=sys.stderr);return True
        time.sleep(0.5)
    print('⚠️  whisper-server no arrancó (ver ~/.cache/whisper-cpp/server.log): sigo con whisper-cli',file=sys.stderr)
    try: p.kill()
    except Exception: pass
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
    """Texto de un wav corto (sin tiempos). Remoto si está configurado; si no, el server; si falla, whisper-cli con el mismo modelo y todos los hilos."""
    if REMOTE:
        try: return ' '.join((_remote(wav,prompt).get('text') or '').split())
        except Exception as e: print(f'⚠️  Whisper remoto falló ({e}); sigo con el local',file=sys.stderr)
    if start(W):
        try: return ' '.join(_post(wav,prompt).split())
        except Exception as e: print(f'⚠️  whisper-server falló ({e}); sigo con whisper-cli',file=sys.stderr)
    cmd=[WHISPER,'-m',model(W),'-f',wav,'-l','es','-np','-nt','-t',str(THREADS)]+(['--prompt',prompt] if prompt else [])
    return ' '.join(subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8').stdout.split())

# --- una pasada: todo el audio una vez con tiempos por palabra (en CPU cada pedido cuesta una ventana de 30 s aunque dure 0,2 s) ---
def words(W,wav):
    """Palabras [{t,a}] (a = arranque en segundos) de todo el wav, transcripto una sola vez. Se guarda en <W>/words_full.json mientras el wav no cambie."""
    st=os.stat(wav);key=[st.st_size,int(st.st_mtime)];cache=os.path.join(W,'words_full.json')
    try:
        c=json.load(open(cache,encoding='utf-8'))
        if c['key']==key: return c['words']
    except Exception: pass
    if REMOTE:
        try:
            t0=time.time();r=_remote(wav,words=True);ws=r.get('words') or []
            tx=(r.get('text') or '').split()   # las palabras vienen sin puntuación: si coinciden en cantidad, usar las del texto (con comas y puntos)
            # OpenAI pega el arranque de cada palabra al final de la anterior (se come el silencio): el arranque real sale del final
            out=[dict(t=tx[i] if len(tx)==len(ws) else w['word'],a=round(max(w['start'],w['end']-0.2),2)) for i,w in enumerate(ws)]
            if out:
                json.dump(dict(key=key,words=out,src='remoto'),open(cache,'w',encoding='utf-8'),ensure_ascii=False)
                print(f'transcripción de una pasada (remota): {len(out)} palabras en {time.time()-t0:.0f}s',file=sys.stderr);return out
        except Exception as e: print(f'⚠️  Whisper remoto falló ({e}); sigo con el local',file=sys.stderr)
    stop()   # no tener el server y whisper-cli con el modelo en RAM a la vez
    base=os.path.join(W,'words_full_raw');js=base+'.json';t0=time.time()
    if os.path.exists(js): os.unlink(js)
    # DTW = tiempos por palabra precisos; con flash attention whisper.cpp lo ignora sin avisar (-nfa)
    subprocess.run([WHISPER,'-m',model(W),'-f',wav,'-l','es','-np','-t',str(THREADS),'-ml','1','-sow','-ojf','-of',base,'-dtw','large.v3.turbo','-nfa'],capture_output=True)
    if not os.path.exists(js): return None
    out=[]
    for x in json.load(open(js,encoding='utf-8')).get('transcription',[]):
        tx=x['text'];tk=[t for t in x.get('tokens',[]) if not t['text'].startswith('[_')]
        if not tx.strip() or tx.strip().startswith('[') or not tk: continue
        on=next((t['t_dtw'] for t in tk if t.get('t_dtw',-1)>=0),x['offsets']['from']/10)/100   # inicio de la palabra (DTW, en centésimas)
        if out and not tx.startswith(' ') and not tx[0] in '¿¡': out[-1]['t']+=tx;continue   # sub-palabra → pegar a la anterior
        out.append(dict(t=tx.strip(),a=round(on,2)))
    json.dump(dict(key=key,words=out),open(cache,'w',encoding='utf-8'),ensure_ascii=False)
    print(f'transcripción de una pasada: {len(out)} palabras en {time.time()-t0:.0f}s',file=sys.stderr);return out
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
    if c=='start': ok=start();print('whisper-server corriendo ✓' if ok else '✗ no arrancó (ver ~/.cache/whisper-cpp/server.log): se usa whisper-cli');sys.exit(0 if ok else 1)
    elif c=='stop': print('whisper-server detenido ✓' if stop() else 'whisper-server no estaba corriendo')
    else: print(f"perfil {perfil()} ({ram_gb():.0f} GB) · modelo {os.path.basename(model())} · server {'corriendo' if _ready() else 'detenido'} en {URL} · remoto {'configurado: '+REMOTE[0] if REMOTE else 'no'}")
