#!/usr/bin/env python3
"""Auditoría de SINCRONÍA del XML ya armado. Si algo no cierra sale con código 1 y build_xml.py frena la entrega.
uso: python3 -I sync_check.py <workdir>
Comprueba (todo debe dar ✓):
  1 · el XML usa el master conformado (CFR 30, audio y video juntos desde 0, mismo largo) y no el crudo original
  2 · cada clip de V1 tiene su clip de A1 idéntico (mismo start/end/in/out, mismo archivo) → el audio no puede correrse del video
  3 · A1 sin huecos ni solapes en la línea de tiempo, empieza en 0 y termina donde termina la secuencia
  4 · ningún clip se sale del archivo (in/out dentro del master)
  5 · el audio del origen no se repite entre clips (ningún rango del master suena dos veces)
  6 · cada motion graphic / subtítulo (.mov) existe y mide exactamente los fotogramas del clip que ocupa (si no, se corre de la voz)
  7 · lo que dijo Whisper del corte (qa_words.json): palabras que faltan / sobran (aviso, no bloquea)
"""
import os as _o,sys as _s,subprocess as _sp
if _o.name=='nt' and __name__=='__main__' and not _s.flags.utf8_mode: _s.exit(_sp.run([_s.executable,'-X','utf8','-I',_o.path.abspath(__file__),*_s.argv[1:]]).returncode)  # Windows: acentos en UTF-8
import json,os,sys,subprocess,urllib.parse
import xml.etree.ElementTree as ET
W=sys.argv[1];cfg=json.load(open(os.path.join(W,'config.json')));FPS=cfg.get('fps',30)
edl=json.load(open(os.path.join(W,'edl.json')));jobs=json.load(open(os.path.join(W,'jobs.json')))
xml=os.path.join(cfg['edit_dir'],f"{cfg['name']}_v{cfg.get('version',1)}_premiere.xml")
bad=[];warn=[];ok=[]
def probe(p,*ent,sel=None):
    c=['ffprobe','-v','error']+(['-select_streams',sel] if sel else [])+['-show_entries',('stream=' if sel else 'format=')+','.join(ent),'-of','json',p]
    try: return json.loads(subprocess.run(c,capture_output=True,text=True).stdout or '{}')
    except Exception: return {}
fnum=lambda r:(lambda n,d:float(n)/float(d) if float(d) else 0.0)(*(r or '0/1').split('/'))
# 1 · master
SRC=cfg['src'];cj=os.path.join(W,'conform.json');master=None
if os.path.exists(cj): master=json.load(open(cj)).get('master')
if cfg.get('use_parts'): warn.append('config.use_parts: V1/A1 apuntan a los fragmentos originales (sin master): la sincronía depende de que cada fragmento esté limpio')
elif not master or os.path.abspath(SRC)!=os.path.abspath(master):
    (warn if cfg.get('allow_unconformed') else bad).append(f'config.src no es el master conformado ({os.path.basename(SRC)}): correr conform.py y volver a empezar desde la transcripción (el crudo original puede tener fps variable o el audio desplazado)')
else:
    v=(probe(SRC,'start_time','r_frame_rate','avg_frame_rate','duration',sel='v:0').get('streams') or [{}])[0];a=(probe(SRC,'start_time','duration',sel='a:0').get('streams') or [{}])[0]
    fl=lambda x:float(x) if x not in(None,'N/A','') else 0.0
    if fnum(v.get('r_frame_rate'))!=FPS or abs(fnum(v.get('avg_frame_rate'))-FPS)>1e-6: bad.append(f"el master no es CFR {FPS}")
    elif abs(fl(v.get('start_time')))>1e-4 or abs(fl(a.get('start_time')))>1e-4: bad.append('el master no arranca en 0 (video/audio)')
    elif abs(fl(v.get('duration'))-fl(a.get('duration')))>1/FPS: bad.append(f"audio y video del master difieren ({fl(a.get('duration')):.3f}s vs {fl(v.get('duration')):.3f}s)")
    else: ok.append(f'master conformado: CFR {FPS}, audio y video juntos desde 0, mismo largo')
# 2-5 · XML
try: root=ET.parse(xml).getroot()
except Exception as e: sys.exit(f'✗ no puedo leer {xml}: {e}')
seq=root.find('sequence');total=int(seq.find('duration').text)
vt=seq.find('media/video').findall('track');at=seq.find('media/audio').findall('track')
g=lambda ci,k:int(ci.find(k).text)
def fid(ci):
    f=ci.find('file');return f.get('id') if f is not None else None
V1=vt[0].findall('clipitem');A1=at[0].findall('clipitem')
if len(V1)!=len(A1): bad.append(f'V1 tiene {len(V1)} clips y A1 {len(A1)}')
pairs=0;prev_end=0;ranges=[]
for i,(v,a) in enumerate(zip(V1,A1)):
    for k in('start','end','in','out'):
        if g(v,k)!=g(a,k): bad.append(f'clip {i}: {k} distinto entre video ({g(v,k)}) y audio ({g(a,k)}) → el audio se correría');break
    else: pairs+=1
    if fid(v)!=fid(a): bad.append(f'clip {i}: video y audio apuntan a archivos distintos')
    if g(a,'out')-g(a,'in')!=g(a,'end')-g(a,'start'): bad.append(f'clip {i}: la duración en origen ({g(a,"out")-g(a,"in")}) no coincide con la de la línea de tiempo ({g(a,"end")-g(a,"start")}): velocidad distinta = desfase')
    if g(a,'start')!=prev_end: bad.append(f'A1 clip {i}: {"hueco" if g(a,"start")>prev_end else "solape"} de {abs(g(a,"start")-prev_end)} fotogramas en {prev_end/FPS:.2f}s')
    prev_end=g(a,'end');ranges.append((g(a,'in'),g(a,'out'),i,g(a,'start')))
    if g(a,'in')<0 or g(a,'out')>g(a,'duration'): bad.append(f'clip {i}: se sale del archivo (in {g(a,"in")}, out {g(a,"out")}, archivo {g(a,"duration")} fotogramas)')
if A1 and g(A1[0],'start')!=0: bad.append('A1 no empieza en 0')
if prev_end!=total: bad.append(f'A1 termina en {prev_end} y la secuencia dura {total}')
if pairs==len(V1)==len(A1): ok.append(f'{pairs} clips: video y audio idénticos (start/end/in/out/archivo), sin huecos ni solapes, la secuencia dura {total/FPS:.2f}s')
rs=sorted(ranges)
for (a0,a1,i,_),(b0,b1,j,_) in zip(rs,rs[1:]):
    if b0<a1: bad.append(f'audio repetido: los clips {i} y {j} usan los mismos {a1-b0} fotogramas del crudo ({(a1-b0)/FPS*1000:.0f} ms)')
if not any('audio repetido' in b for b in bad): ok.append('ningún tramo del audio se usa dos veces')
# 6 · MG y subtítulos
mg=0;miss=[]
for tr in vt[1:]:
    for ci in tr.findall('clipitem'):
        nm=ci.find('name').text;f=ci.find('file');pu=f.find('pathurl') if f is not None else None
        if pu is None: continue
        p=urllib.parse.unquote(pu.text.replace('file://localhost',''))
        if p.startswith('/') and len(p)>2 and p[2]==':': p=p[1:]
        if '/Assets/MG/' not in p.replace('\\','/') and '/Assets/Subtitulos/' not in p.replace('\\','/'): continue
        mg+=1
        if not os.path.exists(p): miss.append(os.path.basename(p));continue
        d=probe(p,'duration');dur=float((d.get('format') or {}).get('duration') or 0)
        n=g(ci,'end')-g(ci,'start')
        if abs(dur*FPS-n)>1.01: bad.append(f'{os.path.basename(p)}: mide {dur*FPS:.1f} fotogramas y ocupa {n} en la línea de tiempo (se correría de la voz): volver a renderizar ese job')
if miss: bad.append(f'faltan {len(miss)} .mov sin renderizar: '+', '.join(miss[:6])+('…' if len(miss)>6 else ''))
elif mg and not any('mide' in b for b in bad): ok.append(f'{mg} motion graphics / subtítulos: cada .mov mide exactamente los fotogramas que ocupa')
# 7 · cortes (Whisper sin prompt)
qa=os.path.join(W,'qa_words.json')
if os.path.exists(qa):
    q=json.load(open(qa))
    for x in q: warn.append(x['msg'])
    if not q: ok.append('Whisper (sin prompt) oye todas las palabras del guion y ninguna de más')
else: warn.append('sin qa_words.json: no se verificó el corte con Whisper (edl.py --no-verify)')
print('── Auditoría de sincronía ──')
for x in ok: print('✓',x)
for x in warn: print('⚠️ ',x)
for x in bad: print('✗',x)
print('RESULTADO:','TODO SINCRONIZADO ✓' if not bad else f'{len(bad)} problema(s) que bloquean la entrega')
sys.exit(1 if bad else 0)
