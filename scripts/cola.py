#!/usr/bin/env python3
"""Modo lote de /edicion: varios crudos INDEPENDIENTES (nunca se unen), procesados en cola sin saturar la máquina.
Todo lo pesado (conform, Whisper, render, ffmpeg que reencodea) pasa por un candado global (~/.cache/edicion/pesado.lock):
corre UNO a la vez en toda la máquina, con prioridad baja (`nice` en Mac/Linux, BELOW_NORMAL en Windows) y hilos limitados.
Los logs van a archivo; en cola.json solo quedan 2-3 líneas. Funciona en macOS y Windows (candado fcntl / msvcrt).
Perfil liviano (8 GB, ej. la Windows del editor; mismo criterio que whisperlib/platform.js): 2 planificadores, 2 pestañas de render
(tope 3 aunque cola.json diga más; `--par N` lo pisa), la mitad de los núcleos (máx. 4) y apaga el whisper-server local antes de renderizar.
Se puede retomar: cada comando salta lo que ya está hecho según cola.json.

uso: python3 -I cola.py <comando> <carpeta> [...]
  init     <carpeta> [video ...] [--prefijo CIRO] [--marca ciro]   crea/actualiza <carpeta>/cola.json (reusa carpetas *_EDIT existentes)
  estado   <carpeta>                                                tabla corta (id · estado · nota)
  prep     <carpeta> [--id X]                                       conform + transcripción + config base + cara, de a uno → «preparado»
  listos   <carpeta> [N]                                            JSON con los N primeros «preparado» (para disparar planificadores)
  marcar   <carpeta> <id> <estado> [nota]                           pendiente|preparado|planificado|renderizado|error
  check    <work> a-b [a-b ...]                                     check.py con el candado global (para los planificadores)
  huellas  <carpeta>                                                arquetipo/héroe/gramática/metáforas de los videos de la carpeta
  rehacer  <carpeta> <id> <paso>                                   vuelve a «planificado» y rehace el render desde <paso> (tighten|edl|qa_cut|plan_mg|mix|director|mg|subs|xml)
  hojas    <carpeta> [--id X]                                       hoja de contacto de los MG renderizados (<work>/hojas_mg.jpg: una fila por MG, 4 momentos)
  envato   <carpeta>                                                junta lo de Envato en vista previa de todo el lote → <carpeta>/envato_lote.json (para licenciar en una sola tanda)
  envato-cerrar <carpeta> [--wait S]                                collect de los originales bajados + build_xml de cada video
  leeme    <carpeta>                                                LEEME.md de cada video renderizado (desde plan.json y los informes) + <carpeta>/LEEME_LOTE.md
  render   <carpeta> [--id X] [--par N]                             corte + MG + subtítulos + mezcla + XML de cada «planificado», de a uno
Concurrencia y hilos: "concurrencia" en cola.json (pesado=1 siempre; whisper_threads, render_par, nice, planificadores).
"""
import os as _o,sys as _s,subprocess as _sp
if _o.name=='nt' and __name__=='__main__' and not _s.flags.utf8_mode: _s.exit(_sp.run([_s.executable,'-X','utf8','-I',_o.path.abspath(__file__),*_s.argv[1:]]).returncode)  # Windows: acentos en UTF-8
import glob,hashlib,json,os,re,subprocess,sys,time,contextlib,unicodedata
WIN=os.name=='nt'
if WIN: import msvcrt
else: import fcntl
NFC=lambda p:unicodedata.normalize('NFC',p)   # macOS devuelve rutas en NFD: los scripts comparan en NFC
SK=os.path.dirname(os.path.dirname(os.path.abspath(__file__)));SC=os.path.join(SK,'scripts')
PY=[sys.executable]+(['-X','utf8'] if WIN else [])+['-I'];LOCKDIR=os.path.expanduser('~/.cache/edicion');os.makedirs(LOCKDIR,exist_ok=True)
sys.path.insert(0,SC);import whisperlib
LIVIANO=whisperlib.liviano()   # EDICION_PERFIL, --perfil= o RAM < 12 GB
DEF_CONC=({'pesado':1,'planificadores':2,'whisper_threads':max(1,min(4,(os.cpu_count() or 4)//2)),'render_par':2,'nice':10} if LIVIANO
          else {'pesado':1,'planificadores':3,'whisper_threads':6,'render_par':4,'nice':10})
def conc(q):
    """concurrencia efectiva: la de cola.json sobre los defaults del perfil; en el liviano, tope de pestañas e hilos (un cola.json hecho en la Mac no satura la notebook)"""
    C=dict(DEF_CONC);C.update(q.get('concurrencia') or {})
    if LIVIANO: C['render_par']=min(int(C['render_par']),3);C['whisper_threads']=min(int(C['whisper_threads']),DEF_CONC['whisper_threads'])
    return C
def bajo(cmd,C):
    """prioridad baja: nice en Mac/Linux; BELOW_NORMAL en Windows (los hijos la heredan: node, Chrome, ffmpeg)"""
    if WIN: return cmd,{'creationflags':getattr(subprocess,'BELOW_NORMAL_PRIORITY_CLASS',0x4000)}
    return ['nice','-n',str(C.get('nice',10))]+cmd,{}
ESTADOS=('pendiente','preparado','planificado','renderizado','error')
PLAN_IN=('segs.json','jobs.js','arte.json','concept.js','ilustra.js','plan.json')
now=lambda:time.strftime('%Y-%m-%d %H:%M:%S')

@contextlib.contextmanager
def lock(name):
    with open(os.path.join(LOCKDIR,name),'a+') as f:
        if WIN:   # msvcrt.locking(LK_LOCK) se rinde a los 10 s: reintentar sin límite (un render tarda minutos)
            f.seek(0)
            while True:
                try: msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1);break
                except OSError: time.sleep(1)
            try: yield
            finally: f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1)
        else:
            fcntl.flock(f,fcntl.LOCK_EX)
            try: yield
            finally: fcntl.flock(f,fcntl.LOCK_UN)

def qpath(c): return os.path.join(os.path.abspath(c),'cola.json')
def load(c):
    with open(qpath(c)) as f: return json.load(f)
def save(c,q):
    t=qpath(c)+'.tmp'
    with open(t,'w') as f: json.dump(q,f,ensure_ascii=False,indent=1)
    os.replace(t,qpath(c))
@contextlib.contextmanager
def edit(c):
    with lock('cola_'+hashlib.md5(os.path.abspath(c).encode()).hexdigest()[:8]+'.lock'):
        q=load(c);yield q;save(c,q)

def upd(c,vid,**kw):
    with edit(c) as q:
        v=next(x for x in q['videos'] if x['id']==vid);v.update(kw);v['actualizado']=now()
        if kw.get('estado') and kw['estado']!='error': v['error']=None

def tail(log,n=3):
    try: L=[l.strip() for l in open(log,errors='replace').read().splitlines() if l.strip()]
    except OSError: return ''
    return ' · '.join(L[-n:])[-400:]

def run(cmd,log,q,heavy=True):
    """Corre un paso con prioridad baja e hilos limitados; la salida va al log. Devuelve el código de salida."""
    C=conc(q);env=dict(os.environ,EDICION_THREADS=str(C['whisper_threads']),OMP_NUM_THREADS=str(C['whisper_threads']))
    full,kw=bajo(cmd,C)
    with (lock('pesado.lock') if heavy else contextlib.nullcontext()):
        with open(log,'a') as f:
            f.write(f'\n===== {now()} · {" ".join(cmd[1:3] if cmd[0]!="node" else cmd[:3])}\n');f.flush()
            return subprocess.run(full,stdout=f,stderr=subprocess.STDOUT,env=env,**kw).returncode

# ---------- init ----------
def nombre(src,prefijo):
    b=os.path.basename(src);m=re.search(r'(\d{4})-(\d{2})-(\d{2}) at (\d{2})\.(\d{2})\.(\d{2})',b)
    if m: return f'{prefijo}_{m[2]}{m[3]}_{m[4]}{m[5]}{m[6]}'
    return re.sub(r'[^A-Z0-9]+','_',os.path.splitext(b)[0].upper()).strip('_')

def existentes(carpeta):
    """carpetas *_EDIT de sesiones anteriores, por crudo original (conform.json.src_original)"""
    d={}
    for cj in glob.glob(os.path.join(carpeta,'*_EDIT','.work','conform.json')):
        try: d[os.path.basename(json.load(open(cj))['src_original'])]=os.path.dirname(os.path.dirname(cj))
        except Exception: pass
    return d

def cmd_init(c,args):
    pref=args[args.index('--prefijo')+1] if '--prefijo' in args else 'VIDEO'
    marca=args[args.index('--marca')+1] if '--marca' in args else None
    vids=[a for a in args if not a.startswith('--') and a not in (pref,marca)]
    c=NFC(os.path.abspath(c))
    if not vids: vids=sorted(f for f in glob.glob(os.path.join(c,'*')) if f.lower().endswith(('.mp4','.mov','.m4v')))
    q=load(c) if os.path.exists(qpath(c)) else {'version':1,'carpeta':c,'creado':now(),'concurrencia':DEF_CONC,'estilo':{'marca':marca},'videos':[]}
    if marca: q['estilo']['marca']=marca
    ex=existentes(c);ya={os.path.abspath(v['src']) for v in q['videos']}
    for s in (NFC(os.path.abspath(x)) for x in vids):
        if s in ya: continue
        ed=ex.get(os.path.basename(s)) or os.path.join(c,nombre(s,pref)+'_EDIT');n=os.path.basename(ed)[:-5]
        q['videos'].append({'id':n,'src':s,'edit_dir':ed,'work':os.path.join(ed,'.work'),'estado':'pendiente','error':None,'nota':'','actualizado':now()})
    save(c,q);cmd_estado(c)

def cmd_estado(c,_=None):
    q=load(c);k={}
    for v in q['videos']:
        k[v['estado']]=k.get(v['estado'],0)+1
        print(f"{v['id']:<24} {v['estado']:<12} {(v.get('error') or v.get('nota') or '')[:110]}")
    print('·',' · '.join(f'{e}: {k[e]}' for e in ESTADOS if e in k))

# ---------- prep (conform + transcripción + config base + cara) ----------
def pieces_ok(W):
    try: p=json.load(open(os.path.join(W,'pieces.json')))
    except Exception: return False
    return bool(p) and sum(1 for x in p if x.get('t','').strip())>=0.8*len(p) and os.path.exists(os.path.join(W,'words_full.json'))

def cmd_prep(c,args):
    only=args[args.index('--id')+1] if '--id' in args else None;q=load(c)
    for v in q['videos']:
        if only and v['id']!=only: continue
        if v['estado']!='pendiente' and not (v['estado']=='error' and v.get('etapa')=='prep'): continue
        W,ED,n=v['work'],v['edit_dir'],v['id'];os.makedirs(W,exist_ok=True);log=os.path.join(W,'cola_prep.log')
        master=NFC(os.path.join(ED,'Assets','Crudo',n+'_master.mov'));t0=time.time();print(f'… {n}',flush=True)
        def fail(paso):
            upd(c,n,estado='error',etapa='prep',error=f'{paso}: {tail(log)}');print(f'✗ {n} · {paso} (log: {log})',flush=True)
        if not os.path.exists(os.path.join(W,'timing.json')): run(PY+[os.path.join(SC,'timing.py'),'start',W],log,q,heavy=False)
        if not (os.path.exists(master) and os.path.exists(os.path.join(W,'conform.json'))):
            if run(PY+[os.path.join(SC,'conform.py'),W,ED,v['src'],'--name',n],log,q): fail('conform');continue
        if not pieces_ok(W):
            if run(PY+[os.path.join(SC,'transcribe.py'),master,W],log,q) or not pieces_ok(W): fail('transcripción (frases vacías)');continue
        cf=os.path.join(W,'config.json')
        if not os.path.exists(cf):
            json.dump({'name':n,'version':1,'fps':30,'tail':1.2,'brand':q.get('estilo',{}).get('marca') or 'editorial','src':master,'edit_dir':ED},open(cf,'w'),ensure_ascii=False,indent=1)
        if 'face' not in json.load(open(cf)):
            if run(['node',os.path.join(SC,'face.js'),W],log,q): fail('cara (face.js)');continue
        upd(c,n,estado='preparado',nota=f'prep {time.time()-t0:.0f} s');print(f'✓ {n} preparado ({time.time()-t0:.0f} s)',flush=True)
    cmd_estado(c)

def cmd_listos(c,args):
    N=int(args[0]) if args else 3;q=load(c)
    print(json.dumps([{'id':v['id'],'work':v['work'],'edit_dir':v['edit_dir']} for v in q['videos'] if v['estado']=='preparado'][:N],ensure_ascii=False))

def cmd_marcar(c,args):
    vid,est=args[0],args[1];nota=' '.join(args[2:])
    if est not in ESTADOS: sys.exit(f'estado inválido: {est}')
    upd(c,vid,estado=est,**({'error':nota,'etapa':'plan'} if est=='error' else {'nota':nota}));print(f'{vid} → {est}')

def cmd_check(W,args):
    q={'concurrencia':DEF_CONC};cq=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(W))),'cola.json')
    if os.path.exists(cq): q=json.load(open(cq))
    C=conc(q);env=dict(os.environ,EDICION_THREADS=str(C['whisper_threads']));full,kw=bajo(PY+[os.path.join(SC,'check.py'),W]+args,C)
    with lock('pesado.lock'):
        sys.exit(subprocess.run(full,env=env,**kw).returncode)

def cmd_huellas(c,_=None):
    for a in sorted(glob.glob(os.path.join(os.path.abspath(c),'*_EDIT','.work','arte.json'))):
        try: A=json.load(open(a))
        except Exception: continue
        W=os.path.dirname(a);P={}
        try: P=json.load(open(os.path.join(W,'plan.json')))
        except Exception: pass
        n=os.path.basename(os.path.dirname(W))[:-5]
        print(f"{n}: {A.get('arquetipo')} · héroe {A.get('heroe')} · concept {(A.get('concept') or {}).get('gramatica')} · subs {A.get('subtitulos')} · firma {str(A.get('firma'))[:50]}"
              +(f" · tema {P.get('tema','')[:60]}" if P else '')+f"\n   metáforas: {'; '.join(m[:45] for m in (A.get('metaforas') or []))}")

# ---------- render (sin IA) ----------
def plan_hash(W):
    h=hashlib.sha1()
    for f in PLAN_IN:
        p=os.path.join(W,f)
        if os.path.exists(p): h.update(open(p,'rb').read())
    return h.hexdigest()[:12]

def avisos(W):
    k=0
    for f in ('qa_cut.md','direction.md'):
        try: k+=open(os.path.join(W,f)).read().count('⚠️')
        except OSError: pass
    return k

def cmd_render(c,args):
    only=args[args.index('--id')+1] if '--id' in args else None;q=load(c);C=conc(q)
    par=args[args.index('--par')+1] if '--par' in args else str(C['render_par']);res=[]
    if LIVIANO: subprocess.run(PY+[os.path.join(SC,'whisperlib.py'),'stop'],capture_output=True)   # libera la RAM de un whisper-server que haya quedado
    print(f"perfil {'liviano' if LIVIANO else 'potente'} · {par} pestañas de render · {C['whisper_threads']} hilos",flush=True)
    for v in q['videos']:
        if only and v['id']!=only: continue
        if v['estado']!='planificado' and not (v['estado']=='error' and v.get('etapa')=='render' and v.get('reintentar')): continue
        W,n=v['work'],v['id'];log=os.path.join(W,'cola_render.log');t0=time.time()
        falta=[f for f in ('plan.json','segs.json','jobs.js','arte.json','concept.js') if not os.path.exists(os.path.join(W,f))]
        if falta: upd(c,n,estado='error',etapa='plan',error='faltan '+', '.join(falta));res.append(f'✗ {n}: faltan {falta}');continue
        h=plan_hash(W);R=v.get('render') or {}
        if R.get('hash')!=h: R={'hash':h,'hechos':[]}
        PASOS=[('tighten',PY+[os.path.join(SC,'tighten.py'),W]),('edl',PY+[os.path.join(SC,'edl.py'),W]),('qa_cut',PY+[os.path.join(SC,'qa_cut.py'),W]),
               ('plan_mg',['node',os.path.join(SC,'render.js'),W,'--plan']),('mix',PY+[os.path.join(SC,'mix.py'),W]),('director',['node',os.path.join(SC,'director.js'),W]),
               ('mg',['node',os.path.join(SC,'render.js'),W,'--only=^(?!cap)',f'--par={par}']),('subs',['node',os.path.join(SC,'render.js'),W,'--only=^cap',f'--par={par}']),
               ('xml',PY+[os.path.join(SC,'build_xml.py'),W]),('tiempo',PY+[os.path.join(SC,'timing.py'),'report',W])]
        run(PY+[os.path.join(SC,'timing.py'),'fase',W,'Render en cola (script)'],log,q,heavy=False);ok=True
        for paso,cmd in PASOS:
            if paso in R['hechos']: continue
            print(f'… {n} · {paso}',flush=True)
            if run(cmd,log,q,heavy=paso not in ('director','tiempo')):
                upd(c,n,estado='error',etapa='render',paso=paso,render=R,reintentar=False,error=f'{paso}: {tail(log)}')
                res.append(f'✗ {n} · {paso} → {tail(log,2)[:160]}');ok=False;break
            R['hechos'].append(paso);upd(c,n,render=R)
        if not ok: continue
        try: E=json.load(open(os.path.join(W,'edl.json')));dur=E['total']/(E.get('fps') or 30)   # total está en fotogramas
        except Exception: dur=0
        xml=next(iter(sorted(glob.glob(os.path.join(v['edit_dir'],'*_premiere.xml'))+glob.glob(os.path.join(v['edit_dir'],'*_resolve.xml')))),'')
        nota=f'{dur:.1f} s · {avisos(W)} avisos · render {(time.time()-t0)/60:.1f} min'
        upd(c,n,estado='renderizado',render=R,xml=xml,nota=nota,reintentar=False);res.append(f'✓ {n}: {nota}')
    print('\n'.join(res) if res else 'nada para renderizar (ningún «planificado»)');print();cmd_estado(c)

ORDEN=['tighten','edl','qa_cut','plan_mg','mix','director','mg','subs','xml','tiempo']
def cmd_rehacer(c,args):
    vid,paso=args[0],args[1];k=ORDEN.index(paso)
    with edit(c) as q:
        v=next(x for x in q['videos'] if x['id']==vid);R=v.get('render') or {}
        R['hechos']=[p for p in R.get('hechos',[]) if p in ORDEN[:k]];v.update(render=R,estado='planificado',error=None,actualizado=now())
    print(f'{vid} → planificado, rehace desde {paso}')

def cmd_hojas(c,args):
    only=args[args.index('--id')+1] if '--id' in args else None;q=load(c)
    for v in q['videos']:
        if (only and v['id']!=only) or v['estado']!='renderizado': continue
        movs=sorted(glob.glob(os.path.join(v['edit_dir'],'Assets','MG','*.mov')))
        if not movs: continue
        tmp=os.path.join(v['work'],'hojas_tmp');os.makedirs(tmp,exist_ok=True);rows=[];log=os.path.join(v['work'],'cola_hojas.log')
        for k,m in enumerate(movs):
            try: d=float(subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',m],capture_output=True,text=True).stdout)
            except ValueError: continue
            r=os.path.join(tmp,f'r{k:02d}.png');fr=[]
            for i,f in enumerate((.15,.45,.75,.95)):
                x=os.path.join(tmp,f'r{k:02d}_{i}.png')
                if not run(['ffmpeg','-v','error','-y','-ss',f'{d*f:.2f}','-i',m,'-frames:v','1','-vf','scale=216:384',x],log,q): fr.append(x)
            if len(fr)==4 and not run(['ffmpeg','-v','error','-y','-f','lavfi','-i','color=c=0x808080:s=864x384:d=1']+sum((['-i',x] for x in fr),[])+['-filter_complex',
                  '[0:v][1:v]overlay=0:0[a];[a][2:v]overlay=216:0[b];[b][3:v]overlay=432:0[c];[c][4:v]overlay=648:0','-frames:v','1',r],log,q): rows.append(r)
        out=os.path.join(v['work'],'hojas_mg.jpg')
        if rows and not run(['ffmpeg','-v','error','-y']+sum((['-i',r] for r in rows),[])+['-filter_complex',''.join(f'[{i}:v]' for i in range(len(rows)))+f'vstack={len(rows)}' if len(rows)>1 else 'null','-q:v','4',out],log,q):
            print(f'✓ {v["id"]}: {out} · filas: '+' | '.join(os.path.basename(m)[:-4] for m in movs))
        else: print(f'✗ {v["id"]}: hoja ({tail(log,1)})')

def _envato_items(v):
    try: c=json.load(open(os.path.join(v['work'],'config.json')))
    except Exception: return []
    it=[(k,b.get('envato')) for k,b in (c.get('broll') or {}).items()]+[('music',(c.get('music') or {}).get('envato'))]
    return [{'video':v['id'],'clave':k,'kind':e.get('kind') or ('music' if k=='music' else 'video'),'url':e.get('url'),'title':e.get('title')} for k,e in it if e and e.get('status')=='preview']

def cmd_envato(c,_=None):
    q=load(c);L=[x for v in q['videos'] if v['estado']=='renderizado' for x in _envato_items(v)]
    out=os.path.join(os.path.abspath(c),'envato_lote.json');json.dump(L,open(out,'w'),ensure_ascii=False,indent=1)
    print(f"{len(L)} para licenciar ({sum(1 for x in L if x['kind']!='music')} videos · {sum(1 for x in L if x['kind']=='music')} músicas) → {out}")

def cmd_envato_cerrar(c,args):
    w=args[args.index('--wait')+1] if '--wait' in args else '60';q=load(c);res=[]
    for v in q['videos']:
        if v['estado']!='renderizado' or not _envato_items(v): continue
        W=v['work'];log=os.path.join(W,'cola_envato.log')
        rc=run(PY+[os.path.join(SC,'envato.py'),'collect',W,'--wait',w],log,q,heavy=False)
        falta=len(_envato_items(v))
        if not rc and run(PY+[os.path.join(SC,'mix.py'),W],log,q)==0 and run(PY+[os.path.join(SC,'build_xml.py'),W],log,q)==0:
            upd(c,v['id'],nota=re.sub(r' · Envato.*','',v.get('nota',''))+(f' · Envato: faltan {falta}' if falta else ' · Envato licenciado'));res.append(f"{'✓' if not falta else '⚠️'} {v['id']}: faltan {falta}")
        else: res.append(f"✗ {v['id']}: {tail(log,2)[:160]}")
    print('\n'.join(res) or 'nada pendiente de Envato')

def _rd(p,default=''):
    try: return open(p,errors='replace').read()
    except OSError: return default

def cmd_leeme(c,_=None):
    q=load(c);filas=[]
    for v in q['videos']:
        if v['estado']!='renderizado': continue
        W,ED=v['work'],v['edit_dir'];P={}
        try: P=json.load(open(os.path.join(W,'plan.json')))
        except Exception: pass
        try: E=json.load(open(os.path.join(W,'edl.json')));dur=E['total']/(E.get('fps') or 30)
        except Exception: dur=0
        xmls=sorted(glob.glob(os.path.join(ED,'*_premiere.xml'))+glob.glob(os.path.join(ED,'*_resolve.xml')));xml=next(iter(xmls),'');srt=next(iter(glob.glob(os.path.join(ED,'*.srt'))),'')
        sync='TODO SINCRONIZADO ✓' if 'TODO SINCRONIZADO' in _rd(os.path.join(W,'cola_render.log'))+_rd(os.path.join(W,'cola_envato.log')) else '⚠️ revisar (no se encontró el resultado de la auditoría)'
        tt=(_rd(os.path.join(W,'timing.md')).splitlines() or [''])[0].strip('* ')
        A=P.get('arte') or {};cta=P.get('cta') or {}
        env=subprocess.run(PY+[os.path.join(SC,'envato.py'),'report',W],capture_output=True,text=True).stdout.strip()
        _t=lambda l:float((re.search(r' en ([0-9.]+)s',l) or [0,'0'])[1])
        pausas=[l.strip() for l in _rd(os.path.join(W,'qa_cut.md')).splitlines() if '⚠️' in l and ('pausa' in l or 'muletilla' in l) and _t(l)<dur-1.6]   # la última pausa es la cola (tail), a propósito
        L=[f"# {v['id']} — {P.get('tema','')}",'',
           f"- **Crudo**: {os.path.basename(v['src'])} → master conformado en `Assets/Crudo/`",
           f"- **Duración final**: {dur:.1f} s"+(f" · Reel {P['reel']}" if P.get('reel') else ''),
           f"- **XML**: "+' · '.join(f'`{os.path.basename(x)}`' for x in xmls)+(f" · subtítulos también en `{os.path.basename(srt)}`" if srt else ''),
           f"- **Sincronía**: {sync}",f"- **{tt}**" if tt else '','',
           '## Cómo importar','No mover ni renombrar la carpeta: los assets están enlazados con rutas absolutas.',
           '- **Premiere**: Archivo → Importar → `*_premiere.xml`. Los empalmes ya llevan un fade de audio de 1 fotograma.',
           '- **DaVinci Resolve**: `*_resolve.xml`, paso a paso en `IMPORTAR_EN_RESOLVE.md` (proyecto nuevo, Center crop with no resizing, File → Import → Timeline). Los empalmes llevan un crossfade de 2 fotogramas y los SFX y la música van ya procesados en `Assets/Audio_Resolve`.','',
           '## Decisiones',f"- **CTA**: {cta.get('elegido','')}"]
        L+=[f"  - alternativa {a[0]}: {a[1]}" for a in (cta.get('alternativas') or []) if isinstance(a,(list,tuple)) and len(a)>=2]
        L+=['- **Se sacó**: '+('; '.join(P.get('sacado') or []) or '—'),
            f"- **Dirección de arte**: {A.get('arquetipo','')} · héroe {A.get('heroe','')} · concept {A.get('gramatica','')}"+(f" · firma {A.get('firma')}" if A.get('firma') else ''),
            f"- **Música**: {P.get('musica','')}",'','## Material de Envato',env or '—','']
        if pausas: L+=['## Revisar en el editor (aire del corte)','Avisos que quedaron después de dos vueltas de corrección; varios son palabras que Whisper no reconoce en clips cortos, no pausas reales:']+[f'- {x[2:] if x.startswith("- ") else x}' for x in pausas]+['']
        if P.get('dudas'): L+=['## Dudas para revisar']+[f'- {d}' for d in P['dudas']]+['']
        if P.get('correcciones'): L+=['## Correcciones hechas durante el lote']+[f'- {d}' if isinstance(d,str) else f'- {json.dumps(d,ensure_ascii=False)}' for d in (P['correcciones'] if isinstance(P['correcciones'],list) else [P['correcciones']])]+['']
        open(os.path.join(ED,'LEEME.md'),'w').write('\n'.join(x for x in L if x is not None)+'\n')
        filas.append(f"| {v['id']} | {os.path.basename(v['src'])[-12:-4]} | {P.get('reel') or ''} | {P.get('tema','')[:60]} | {dur:.1f} s | {'✓' if 'TODO' in sync else '⚠️'} | {'falta licenciar' if 'falta licenciar' in env else 'licenciado'} |")
    lote=['# Lote Crudos 2 — ediciones independientes','','| Video | Crudo | Reel | Tema | Duración | Sincronía | Envato |','|---|---|---|---|---|---|---|']+filas+['','Cada carpeta `*_EDIT/` tiene sus XML para Premiere y DaVinci Resolve y su LEEME.md. Estado y retomar: `python3 -I ~/.claude/skills/edicion/scripts/cola.py estado "<esta carpeta>"`.']
    open(os.path.join(os.path.abspath(c),'LEEME_LOTE.md'),'w').write('\n'.join(lote)+'\n');print(f'{len(filas)} LEEME escritos + LEEME_LOTE.md')

if __name__=='__main__':
    if len(sys.argv)<3: sys.exit(__doc__)
    cmd,c,rest=sys.argv[1],sys.argv[2],sys.argv[3:]
    {'init':cmd_init,'estado':cmd_estado,'prep':cmd_prep,'listos':cmd_listos,'marcar':cmd_marcar,'check':cmd_check,'huellas':cmd_huellas,'rehacer':cmd_rehacer,'hojas':cmd_hojas,'envato':cmd_envato,'leeme':cmd_leeme,'envato-cerrar':cmd_envato_cerrar,'render':cmd_render}[cmd](c,rest)
