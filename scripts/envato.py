#!/usr/bin/env python3
"""B-roll y música de Envato Elements.
El MCP público de Envato (https://mcp.envato.com/mcp) solo BUSCA: no descarga ni licencia. Este script lo llama por HTTP
(no hace falta tenerlo configurado en el agente), baja las vistas previas con marca de agua para elegir y ubicar el
material. Al elegir (use) NO se usa la vista previa: se licencia y descarga el original enseguida y collect lo registra.

uso:
  envato.py search <work> video "<términos en inglés>" [--n 8] [--vertical] [--sub Medical] [--min 5] [--max 30]
  envato.py search <work> music "<términos>" [--n 6] [--mood inspiring] [--tempo "Medium (90-110 BPM)"] [--genre corporate]
        → <work>/envato/<kind>_<slug>.json + hoja de candidatos <work>/envato/<kind>_<slug>.jpg (videos) / perfil de energía (música)
  envato.py use <work> <clave> <búsqueda>#<n> [--preview]  (ej. kl video_doctor-talking#3) → registra la elección en config.json
        (broll[clave] o music) como PENDIENTE de descarga; --preview = usar la vista previa con marca de agua (solo si no se puede licenciar ya)
  envato.py collect <work> [--from ~/Downloads] [--wait 300] [--file <clave> <archivo>]  → toma los originales licenciados de Descargas
        (por nombre; si Envato lo bajó con otro nombre, los videos se reconocen comparándolos con la vista previa)
        (los copia a Assets/Envato y borra de Descargas lo bajado, para no duplicar)
        (--wait = esperar hasta N s a que terminen de bajar)
  envato.py report <work>                          → tabla de procedencia (para el LEEME)
"""
import os as _o,sys as _s,subprocess as _sp
if _o.name=='nt' and __name__=='__main__' and not _s.flags.utf8_mode: _s.exit(_sp.run([_s.executable,'-X','utf8','-I',_o.path.abspath(__file__),*_s.argv[1:]]).returncode)  # Windows: acentos en UTF-8
import json,os,re,subprocess,sys,time,urllib.request,zipfile,shutil,math,array
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)));import timing
MCP=os.environ.get('ENVATO_MCP_URL','https://mcp.envato.com/mcp');UA={'User-Agent':'Mozilla/5.0'}
slug=lambda s:re.sub(r'[^a-z0-9]+','-',s.lower()).strip('-')[:40]
norm=lambda s:re.sub(r'[^a-z0-9]','',s.lower())

def mcp(tool,args):
    body=json.dumps({'jsonrpc':'2.0','id':1,'method':'tools/call','params':{'name':tool,'arguments':args}}).encode()
    req=urllib.request.Request(MCP,body,{**UA,'Content-Type':'application/json','Accept':'application/json, text/event-stream'})
    raw=urllib.request.urlopen(req,timeout=40).read().decode()
    data=json.loads(next(l[6:] for l in raw.splitlines() if l.startswith('data: ')) if 'data: ' in raw else raw)
    if 'error' in data: raise SystemExit(f"Envato MCP: {data['error']}")
    return json.loads(data['result']['content'][0]['text'])
def get(url,dst=None):
    r=urllib.request.urlopen(urllib.request.Request(url,headers=UA),timeout=60).read()
    if dst: open(dst,'wb').write(r)
    return r
def probe(p):
    o=json.loads(subprocess.run(['ffprobe','-v','error','-show_entries','stream=codec_type,width,height,r_frame_rate,nb_frames:stream_side_data=rotation:format=duration','-of','json',p],capture_output=True,text=True).stdout)
    v=next((s for s in o.get('streams',[]) if s['codec_type']=='video'),None);d=float(o['format']['duration'])
    if not v: return dict(dur=d)
    n,dd=map(int,v['r_frame_rate'].split('/'));rate=round(n/dd,3);w,h=v['width'],v['height']
    rot=abs(int(next((x.get('rotation',0) for x in v.get('side_data_list',[])),0)))
    if rot in(90,270): w,h=h,w
    return dict(dur=d,w=w,h=h,rate=rate if abs(rate-round(rate))>0.01 else int(round(rate)),frames=int(v.get('nb_frames') or d*rate))
def preview_url(page,kind,cover):
    h=get(page).decode('utf-8','replace')
    if kind=='video':
        urls=re.findall(r'https://video-previews\.elements\.envatousercontent\.com/[^"\\\s]+?\.mp4',h)
        uid=re.search(r'files/([0-9a-f-]{36})/',cover or '');own=[u for u in urls if uid and uid.group(1) in u]
        return (own or urls or [None])[0]
    return (re.findall(r'https://audio-previews\.elements\.envatousercontent\.com/[^"\\\s]+?\.mp3',h) or [None])[0]
def energy(p,step=5):
    raw=subprocess.run(['ffmpeg','-v','error','-i',p,'-ac','1','-ar','8000','-f','s16le','-'],capture_output=True).stdout
    a=array.array('h',raw);n=8000*step;bars='▁▂▃▄▅▆▇█'
    rms=[math.sqrt(sum(x*x for x in a[i:i+n:20])/max(1,len(a[i:i+n:20]))) for i in range(0,len(a),n)];m=max(rms) or 1
    return ''.join(bars[min(7,int(r/m*7.99))] for r in rms)

def search(W,kind,terms,o):
    E=os.path.join(W,'envato');os.makedirs(E,exist_ok=True);name=f'{kind}_{slug(terms)}';n=int(o.get('n',8 if kind=='video' else 6))
    f={}
    if kind=='video':
        f['categories']='Stock Footage'
        if 'vertical' in o: f['orientation']='vertical'
        if 'sub' in o: f['subcategories']=o['sub']
        if 'min' in o: f['min_media_length']=int(o['min'])
        if 'max' in o: f['max_media_length']=int(o['max'])
        res=mcp('search_stock_video',{'searchTerms':terms[:60],'perPage':n,'sortBy':'relevance','languageCode':'en','filters':f})
    else:
        f={'categories':'Music Tracks','vocals_in_audio':'No Vocals'}
        for k in('mood','tempo','genre','theme'):
            if k in o: f[k]=o[k]
        res=mcp('search_music',{'searchTerms':terms[:60],'perPage':n,'sortBy':'relevance','languageCode':'en','filters':f})
    items=res['items'][:n]
    def fetch(i_it):
        i,it=i_it;it['n']=i+1;ext='mp4' if kind=='video' else 'mp3'
        try:
            u=preview_url(it['item_url'],kind,it.get('cover_image'));p=os.path.join(E,f"{name}_{i+1}.{ext}")
            if u and not os.path.exists(p):
                get(u,p);ar=it.get('aspect_ratio')
                if kind=='video' and ar:   # las vistas previas vienen en 16:9 con barras: recortar al formato real
                    q=probe(p)
                    if abs(q['w']/q['h']-ar)>0.05:
                        cw,ch=(q['h']*ar,q['h']) if ar<q['w']/q['h'] else (q['w'],q['w']/ar);cw,ch=int(cw)//2*2,int(ch)//2*2
                        subprocess.run(['ffmpeg','-v','error','-y','-i',p,'-vf',f'crop={cw}:{ch}','-an','-c:v','libx264','-crf','20','-preset','veryfast',p+'.tmp.mp4'],check=True);os.replace(p+'.tmp.mp4',p)
            if u: it['preview']=p;it.update(probe(p))
        except Exception as e: it['error']=str(e)[:120]
        return it
    with ThreadPoolExecutor(6) as ex: items=list(ex.map(fetch,enumerate(items)))
    json.dump({'kind':kind,'terms':terms,'filters':f,'items':items},open(os.path.join(E,name+'.json'),'w'),indent=1,ensure_ascii=False)
    if kind=='video':
        rows=[]
        for it in items:
            if 'preview' not in it: continue
            r=os.path.join(E,f"_{name}_{it['n']}.jpg")
            vf=f"fps=4/{max(it['dur'],1):.2f},scale=300:300:force_original_aspect_ratio=decrease,pad=300:300:(ow-iw)/2:(oh-ih)/2,tile=4x1,pad=1200:310:0:0:color=0x111111"
            subprocess.run(['ffmpeg','-v','error','-y','-i',it['preview'],'-vf',vf,'-frames:v','1',r]);rows.append(r) if os.path.exists(r) else None
        if rows:
            sheet=os.path.join(E,name+'.jpg')
            subprocess.run(['ffmpeg','-v','error','-y']+sum((['-i',r] for r in rows),[])+(['-filter_complex',f"vstack=inputs={len(rows)}"] if len(rows)>1 else [])+[sheet])
            for r in rows: os.remove(r)
            print('hoja de candidatos:',sheet,'(una fila por candidato, en orden: fila 1 = #'+str(int(rows[0].rsplit('_',1)[1][:-4]))+')' if rows else '')
    for it in items:
        extra=f"{it.get('w','?')}x{it.get('h','?')} {it.get('dur',0):.0f}s" if kind=='video' else f"{it.get('dur',0):.0f}s  energía {energy(it['preview']) if 'preview' in it else '?'}"
        print(f"#{it['n']:<2} {it['title'][:50]:50s} · {it['author'][:18]:18s} · {extra}{'  ⚠️ '+it['error'] if 'error' in it else ''}")
    print(f'→ elegir con: envato.py use "{W}" <clave> {name}#<n>')

def cfgio(W,c=None):
    p=os.path.join(W,'config.json')
    if c is None: return json.load(open(p))
    json.dump(c,open(p,'w'),indent=1,ensure_ascii=False)
def use(W,key,ref,preview=False):
    name,n=ref.split('#');d=json.load(open(os.path.join(W,'envato',name+'.json')));it=next(x for x in d['items'] if x['n']==int(n))
    if preview and 'preview' not in it: raise SystemExit('ese candidato no tiene vista previa descargable; elegir otro')
    c=cfgio(W);env=dict(url=it['item_url'],title=it['title'],author=it['author'],kind=d['kind'],search=d['terms'],status='preview' if preview else 'pending',preview=it.get('preview'),chosen=time.time())
    if d['kind']=='video':
        b=dict(envato=env,frames=it.get('frames'),rate=it.get('rate'),w=it.get('w'),h=it.get('h'))   # w/h/frames de la vista previa: se pisan con el original en collect
        if preview: b['path']=it['preview']
        c.setdefault('broll',{})[key]=b
    else:
        m=c.get('music') if isinstance(c.get('music'),dict) else {}
        m.pop('path',None);m.update(dur=round(it.get('dur',0),2),envato=env)
        if preview: m['path']=it['preview']
        c['music']=m;c.pop('music_dur',None)
    cfgio(W,c)
    if preview: print(f"✓ {key} = {it['title']} (vista previa con marca de agua hasta licenciar) · {it['item_url']}")
    else: print(f"✓ {key} = {it['title']} · LICENCIAR Y DESCARGAR AHORA → {it['item_url']}\n  después: envato.py collect \"{W}\" --wait 300")

def entries(c):
    for k,b in (c.get('broll') or {}).items():
        if b.get('envato'): yield k,b
    if isinstance(c.get('music'),dict) and c['music'].get('envato'): yield 'music',c['music']
PART=('.crdownload','.download','.part','.tmp')
def thumbs(p,dur,n=3):
    """huella del video: n cuadros en gris de 16×16 (al 25/50/75 %)"""
    out=[]
    for i in range(1,n+1):
        r=subprocess.run(['ffmpeg','-v','error','-ss',f'{dur*i/(n+1):.2f}','-i',p,'-vf','scale=16:16:flags=area,format=gray','-frames:v','1','-f','rawvideo','-'],capture_output=True).stdout
        if len(r)!=256: return None
        out.append(r)
    return out
def match_by_content(e,files,used):
    """Envato baja los archivos con un nombre distinto del de la página (ej. «medical-professional-scanning-…» para
    «dentist-scanning-patients-…»): si no coincide el nombre, se reconoce el original comparándolo con la vista previa
    (duración ±1 s y 3 cuadros chicos). Devuelve (archivo, diferencia) o (None, motivo)."""
    if e['kind']!='video': return None,'la música se reconoce por el nombre (su vista previa junta todas las versiones del tema)'
    pv=e.get('preview')
    if not pv or not os.path.exists(pv): return None,'sin vista previa para comparar'
    try: dp=probe(pv)['dur']
    except Exception: return None,'no se pudo leer la vista previa'
    best=(None,999)
    for f in files:
        if f in used: continue
        try: d=probe(f)['dur']
        except Exception: continue
        if abs(d-dp)>1.0: continue
        a,b=thumbs(pv,min(d,dp)),thumbs(f,min(d,dp))
        if not a or not b: continue
        diff=sum(abs(x-y) for ta,tb in zip(a,b) for x,y in zip(ta,tb))/768   # medido: el original da 3–5, otro video ≥ 30
        if diff<best[1]: best=(f,diff)
    return (best[0],best[1]) if best[0] and best[1]<15 else (None,'ningún video de Descargas se parece a la vista previa')
def collect(W,src,manual=None,wait=0):
    if wait>300: print(f'ℹ️  --wait {wait:.0f} s es demasiado: espero 300 s como máximo (si no llegan, usar --preview y seguir; SKILL.md 4a)');wait=300
    t_end=time.time()+wait
    while True:
        pend=_collect(W,src,manual)
        if not pend or manual: break
        if time.time()>=t_end: print('⏱  se terminó la espera: los que faltan quedan pendientes (envato.py use … --preview para seguir sin ellos)');break
        time.sleep(5)
def _collect(W,src,manual=None):
    c=cfgio(W);dst=os.path.join(c['edit_dir'],'Assets','Envato');os.makedirs(dst,exist_ok=True);tmp=os.path.join(W,'envato','_unzip')
    VID=('.mp4','.mov','.m4v');AUD=('.wav','.aif','.aiff','.mp3','.m4a')
    used=set()
    for k,b in entries(c):
        e=b['envato']
        if e['status']=='licensed' and not manual: continue
        if manual and manual[0]!=k: continue
        m=re.search(r'/([a-z0-9-]+)-([A-Z0-9]{6,})/?$',e['url']);base,iid=(norm(m.group(1)),m.group(2).lower()) if m else (norm(e['title']),'#')
        if manual: found=manual[1]
        else:
            cands=[os.path.join(src,f) for f in os.listdir(src) if ((base and base in norm(f)) or iid in f.lower()) and not f.lower().endswith(PART)]
            cands=[p for p in cands if os.path.getmtime(p)>=e.get('chosen',0)-86400*30]
            if not cands:
                loose=[os.path.join(src,f) for f in os.listdir(src) if f.lower().endswith(VID) and not f.lower().endswith(PART) and os.path.getmtime(os.path.join(src,f))>=e.get('chosen',0)-3600]
                f,why=match_by_content(e,loose,used)
                if not f: print(f'… {k}: todavía no está en {src} ({e["title"]}; {why})');continue
                print(f'  {k}: reconocido por contenido → {os.path.basename(f)} (diferencia {why:.1f})');cands=[f]
            found=max(cands,key=os.path.getmtime);sz=os.path.getsize(found);time.sleep(1)
            if os.path.getsize(found)!=sz: print(f'… {k}: todavía bajando');continue
        used.add(found);dl=found   # lo descargado (archivo o zip): se borra de Descargas cuando el original ya quedó copiado en Assets
        if found.lower().endswith('.zip'):
            shutil.rmtree(tmp,ignore_errors=True);zipfile.ZipFile(found).extractall(tmp)
            media=[os.path.join(r,f) for r,_,fs in os.walk(tmp) for f in fs if '__MACOSX' not in r and f.lower().endswith(VID if e['kind']=='video' else AUD)]
            if e['kind']=='music': media.sort(key=lambda p:(not p.lower().endswith(('.wav','.aif','.aiff')),-os.path.getsize(p)))
            else: media.sort(key=lambda p:-os.path.getsize(p))
            if not media: print(f'⚠️ {k}: el zip no trae {"video" if e["kind"]=="video" else "audio"}');continue
            found=media[0]
        out=os.path.join(dst,f"{k}_{slug(e['title'])}{os.path.splitext(found)[1].lower()}");shutil.copyfile(found,out);p=probe(out)
        if e['kind']=='video': b.update(path=out,frames=p['frames'],rate=p['rate'],w=p['w'],h=p['h'])
        else: b.update(path=out,dur=round(p['dur'],2))
        e.update(status='licensed',file=out);print(f'✓ {k}: original licenciado → {out}')
        if os.path.dirname(os.path.abspath(dl))==os.path.abspath(src) and os.path.getsize(out)==os.path.getsize(found):
            os.remove(dl);print(f'  borrado de {src}: {os.path.basename(dl)} (ya está en Assets)')
    shutil.rmtree(tmp,ignore_errors=True);cfgio(W,c)
    pend=[k for k,b in entries(c) if b['envato']['status']!='licensed']
    print('pendientes:',', '.join(pend) if pend else 'ninguno ✓');return pend
def report(W):
    c=cfgio(W);rows=list(entries(c))
    if not rows: print('Sin material de Envato.');return
    print('| Clave | Tipo | Título | Autor | Estado | Link |\n|---|---|---|---|---|---|')
    for k,b in rows:
        e=b['envato'];print(f"| {k} | {'B-roll' if e['kind']=='video' else 'Música'} | {e['title']} | {e['author']} | {'✅ licenciado' if e['status']=='licensed' else '⚠️ vista previa con marca de agua: falta licenciar' if e['status']=='preview' else '⏳ falta licenciar y descargar'} | {e['url']} |")

if __name__=='__main__':
    a=sys.argv[1:];t0=time.time()
    if not a or a[0] in('-h','--help'): print(__doc__);sys.exit()
    cmd,W=a[0],a[1];o={};pos=[];i=2
    while i<len(a):
        if a[i].startswith('--'):
            if a[i] in('--vertical','--preview'): o[a[i][2:]]=True;i+=1
            elif a[i]=='--file': o['file']=(a[i+1],a[i+2]);i+=3
            else: o[a[i][2:]]=a[i+1];i+=2
        else: pos.append(a[i]);i+=1
    if cmd=='search': search(W,pos[0],pos[1],o)
    elif cmd=='use': use(W,pos[0],pos[1],o.get('preview',False))
    elif cmd=='collect': collect(W,os.path.expanduser(o.get('from','~/Downloads')),o.get('file'),float(o.get('wait',0)))
    elif cmd=='report': report(W)
    if cmd in('search','collect'): timing.log(W,f'envato {cmd}',time.time()-t0)
