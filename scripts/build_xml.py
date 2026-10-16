#!/usr/bin/env python3
"""Paso 6: XML para Premiere (FCP7 xmeml v4). uso: python3 -I build_xml.py <workdir>
Pistas: V1 video (alterna push-in 100→106% / punch-in 118%) · V2 b-roll · V3 subtítulos · V4 ov · V5 ov2 · V6 fs
        A1 diálogo · A2+ SFX/música.  Todo con rutas absolutas (file://localhost/...).
"""
import os as _o,sys as _s,subprocess as _sp
if _o.name=='nt' and __name__=='__main__' and not _s.flags.utf8_mode: _s.exit(_sp.run([_s.executable,'-X','utf8','-I',_o.path.abspath(__file__),*_s.argv[1:]]).returncode)  # Windows: acentos en UTF-8
import json,os,re,shutil,sys,subprocess,time,urllib.parse
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)));import timing;T0=time.time()
from xml.sax.saxutils import escape
W=sys.argv[1];cfg=json.load(open(os.path.join(W,'config.json')))
_pend=[k for k,b in list((cfg.get('broll') or {}).items())+[('music',cfg.get('music'))] if isinstance(b,dict) and not b.get('path') and b.get('envato')]
if _pend: sys.exit(f"⚠️  Envato sin descargar: {', '.join(_pend)} → licenciar/descargar y correr envato.py collect (o use --preview)")
EDIT=cfg['edit_dir'];SRC=cfg['src'];FPS=cfg.get('fps',30);NAME=cfg['name'];VER=cfg.get('version',1)
edl=json.load(open(os.path.join(W,'edl.json')));jobs=json.load(open(os.path.join(W,'jobs.json')));br=json.load(open(os.path.join(W,'broll.json')))
RATE=f'<rate><timebase>{FPS}</timebase><ntsc>FALSE</ntsc></rate>'
def url(p):   # macOS: file://localhost/Users/... · Windows: file://localhost/C%3a/Users/...
    p=os.path.abspath(p).replace('\\','/')
    if re.match(r'^[A-Za-z]:/',p): p='/'+p
    return 'file://localhost'+urllib.parse.quote(p,safe='/')
def fr(x): return int(round(x*FPS))
def probe_frames(p): return int(float(subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',p],capture_output=True,text=True).stdout)*FPS)
SRC_FRAMES=probe_frames(SRC)
uid=[0]
def nid(p): uid[0]+=1; return f'{p}-{uid[0]}'
done=set()
def file_el(fid,path,frames,video=True,audio=False,w=1080,h=1920,ch=2,rate=None):
    if fid in done: return f'<file id="{fid}"/>'
    done.add(fid);m='<media>'
    if video: m+=f'<video><samplecharacteristics>{RATE}<width>{w}</width><height>{h}</height><anamorphic>FALSE</anamorphic><pixelaspectratio>square</pixelaspectratio><fielddominance>none</fielddominance></samplecharacteristics></video>'
    if audio: m+=f'<audio><samplecharacteristics><depth>16</depth><samplerate>48000</samplerate></samplecharacteristics><channelcount>{ch}</channelcount></audio>'
    m+='</media>';FR=f'<rate><timebase>{rate}</timebase><ntsc>FALSE</ntsc></rate>' if rate else RATE
    return (f'<file id="{fid}"><name>{escape(os.path.basename(path))}</name><pathurl>{url(path)}</pathurl>{FR}<duration>{frames}</duration>'
            f'<timecode>{RATE}<string>00:00:00:00</string><frame>0</frame><displayformat>NDF</displayformat></timecode>{m}</file>')
def motion(scale,kf=None):
    v=f'<value>{scale}</value>'+(''.join(f'<keyframe><when>{w}</when><value>{s}</value></keyframe>' for w,s in kf) if kf else '')
    return ('<filter><effect><name>Basic Motion</name><effectid>basic</effectid><effectcategory>motion</effectcategory><effecttype>motion</effecttype><mediatype>video</mediatype>'
            f'<parameter authoringApp="PremierePro"><parameterid>scale</parameterid><name>Scale</name><valuemin>0</valuemin><valuemax>1000</valuemax>{v}</parameter></effect></filter>')
def level(g):
    return ('<filter><effect><name>Audio Levels</name><effectid>audiolevels</effectid><effectcategory>audiolevels</effectcategory><effecttype>audiolevels</effecttype><mediatype>audio</mediatype>'
            f'<parameter><parameterid>level</parameterid><name>Level</name><valuemin>0.00001</valuemin><valuemax>31.6228</valuemax><value>{g}</value></parameter></effect></filter>')
def clip(cid,name,fx,start,end,cin,cout,dur,extra='',srctrack=None):
    st=f'<sourcetrack><mediatype>audio</mediatype><trackindex>{srctrack}</trackindex></sourcetrack>' if srctrack else ''
    return (f'<clipitem id="{cid}"><name>{escape(name)}</name><enabled>TRUE</enabled><duration>{dur}</duration>{RATE}'
            f'<start>{start}</start><end>{end}</end><in>{cin}</in><out>{cout}</out>{fx}{st}{extra}</clipitem>')
def track(items): return '<track>'+''.join(items)+'<enabled>TRUE</enabled><locked>FALSE</locked></track>'
FRAMING={f['i']:f for f in json.load(open(os.path.join(W,'framing.json')))} if os.path.exists(os.path.join(W,'framing.json')) else {}
v1=[];a1=[]
for c in edl['clips']:
    i=c['i'];vid=f'v1-{i}';aid=f'a1-{i}'
    f=FRAMING.get(i)
    if not f: mot=motion(100,[(c['src_in'],100),(c['src_out'],106)]) if i%2==0 else motion(118)
    elif f['s0']==f['s1']: mot=motion(f['s0'])
    elif f.get('ramp'): r=min(c['src_out']-1,c['src_in']+fr(f['ramp']));mot=motion(f['s0'],[(c['src_in'],f['s0']),(r,f['s1']),(c['src_out'],f['s1']+1)])
    else: mot=motion(f['s0'],[(c['src_in'],f['s0']),(c['src_out'],f['s1'])])
    link=(f'<link><linkclipref>{vid}</linkclipref><mediatype>video</mediatype><trackindex>1</trackindex><clipindex>{i+1}</clipindex></link>'
          f'<link><linkclipref>{aid}</linkclipref><mediatype>audio</mediatype><trackindex>1</trackindex><clipindex>{i+1}</clipindex><groupindex>1</groupindex></link>')
    nm=f'{i:02d} · '+c['text'][:40]
    v1.append(clip(vid,nm,file_el('file-src',SRC,SRC_FRAMES,True,True),c['tl_in'],c['tl_out'],c['src_in'],c['src_out'],SRC_FRAMES,mot+link))
    # config.voice_gain_db: ganancia de la voz del crudo (crudos grabados muy bajos)
    vg=(level(round(10**(cfg['voice_gain_db']/20),4)) if cfg.get('voice_gain_db') else '')
    a1.append(clip(aid,nm,file_el('file-src',SRC,SRC_FRAMES,True,True),c['tl_in'],c['tl_out'],c['src_in'],c['src_out'],SRC_FRAMES,link+vg,srctrack=1))
v2=[]
for b in br['broll']:
    m=cfg['broll'][b['src']];p=m['path'];s=fr(b['start']);n=fr(b['dur'])
    if m.get('still'):
        base=round(max(1080/m['w'],1920/m['h'])*100,1);k0,k1=b.get('kb') or [100,100]
        v2.append(clip(nid('still'),os.path.basename(p),file_el(f"f-{b['src']}-{s}",p,n,True,False,m['w'],m['h']),s,s+n,0,n,n,
                       motion(round(base*k0/100,1),[(0,round(base*k0/100,1)),(n,round(base*k1/100,1))])))
    else:
        r=m.get('rate',FPS);nf=m['frames'];cin=fr(b['sin']);sc=round(max(1080/m['w'],1920/m['h'])*100+0.3,1)
        v2.append(clip(nid('broll'),('PREVIEW_' if (m.get('envato') or {}).get('status')=='preview' else '')+os.path.basename(p),file_el('f-'+b['src'],p,nf,True,False,m['w'],m['h'],rate=r),s,s+n,cin,cin+n,round(nf*FPS/r),motion(sc)))
def place(flt,folder):
    tracks=[]
    for j in sorted([j for j in jobs if flt(j)],key=lambda j:j['start']):
        s=fr(j['start']);n=fr(j['end']-j['start']);e=s+n;path=os.path.join(EDIT,'Assets',folder,j['id']+'.mov')
        for t in tracks:
            if t['end']<=s: break
        else: t={'end':0,'items':[]};tracks.append(t)
        t['items'].append(clip(nid('mg'),j['id'],file_el('f-'+j['id'],path,n),s,e,0,n,n));t['end']=e
    return [t['items'] for t in tracks]
vtracks=[v1]+([v2] if v2 else [])+place(lambda j:j['track']=='cap','Subtitulos')+place(lambda j:j['track']=='ov','MG')+place(lambda j:j['track']=='ov2','MG')+place(lambda j:j['track']=='fs','MG')
# SFX de la librería (resueltos por render.js en sfx.json): se copian a Assets/SFX para que el proyecto sea autónomo
LIB=os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','assets','sfx')
sfx=json.load(open(os.path.join(W,'sfx.json'))) if os.path.exists(os.path.join(W,'sfx.json')) else []
os.makedirs(os.path.join(EDIT,'Assets','SFX'),exist_ok=True)
sfx=[x for x in sfx if os.path.exists(os.path.join(LIB,x['file'])) or print('⚠️  falta el sonido',x['id'],'(se omite)')]
for x in {x['id']:x for x in sfx}.values(): shutil.copyfile(os.path.join(LIB,x['file']),os.path.join(EDIT,'Assets','SFX',x['id']+'.wav'))
st=[]
def put(item,s,e):
    for t in st:
        if t['end']<=s: break
    else: t={'end':0,'items':[]};st.append(t)
    t['items'].append(item);t['end']=e
for x in sfx:
    p=os.path.join(EDIT,'Assets','SFX',x['id']+'.wav');s=fr(x['start']);n=max(1,fr(x['dur']));cin=fr(x['sin']);fd=max(fr(x['fdur']),cin+n)
    put(clip(nid('sfx'),x['id'],file_el('f-sfx-'+x['id'],p,fd,False,True),s,s+n,cin,cin+n,fd,level(x['gain']),srctrack=1),s,s+n)
for x in br['extraSfx']:
    p=x['file'];s=fr(x['start']);n=fr(x['dur']);cin=fr(x['sin']);fd=probe_frames(p)
    put(clip(nid('sfx'),os.path.basename(p),file_el('f-x-'+p,p,fd,False,True),s,s+n,cin,cin+n,fd,level(x['gain']),srctrack=1),s,s+n)
# Música (config.music = {path, dur, bed_gain, offset}): volumen PAREJO todo el video (pedido del usuario: ni más alta al principio ni al final), solo fade-out final
mtrack=[];M=cfg.get('music')
if isinstance(M,dict) and M.get('path'):
    tot=edl['total'];mf=fr(M.get('dur') or probe_frames(M['path'])/FPS);off=fr(M.get('offset',0));n=min(tot,mf-off)
    bg=M.get('bed_gain',.08)
    if 'hook_gain' in M or 'outro_gain' in M: print('ℹ️  hook_gain/outro_gain se ignoran: la música va pareja en bed_gain todo el video')
    kf=[(0,bg),(max(0,n-fr(.8)),bg),(n,0.0001)]
    kf=[(w,g) for k,(w,g) in enumerate(kf) if k==0 or w>kf[k-1][0]]
    lv=('<filter><effect><name>Audio Levels</name><effectid>audiolevels</effectid><effectcategory>audiolevels</effectcategory><effecttype>audiolevels</effecttype><mediatype>audio</mediatype>'
        '<parameter><parameterid>level</parameterid><name>Level</name><valuemin>0.00001</valuemin><valuemax>31.6228</valuemax><value>'+str(bg)+'</value>'
        +''.join(f'<keyframe><when>{off+w}</when><value>{g}</value></keyframe>' for w,g in kf)+'</parameter></effect></filter>')
    nm=('PREVIEW_' if (M.get('envato') or {}).get('status')=='preview' else '')+os.path.basename(M['path'])
    mtrack=[clip(nid('music'),nm,file_el('f-music',M['path'],mf,False,True),0,n,off,off+n,mf,lv,srctrack=1)]
    if mf-off<tot: print(f'⚠️  la música dura menos que el video ({(mf-off)/FPS:.1f}s < {tot/FPS:.1f}s)')
SG=lambda i:[c for c in edl['clips'] if c['seg']==i][0]['tl_in']
mk=''.join(f'<marker><comment></comment><name>{escape(n)}</name><in>{SG(sg)}</in><out>-1</out></marker>' for n,sg in cfg.get('markers',[]))
vfmt=f'<format><samplecharacteristics>{RATE}<width>1080</width><height>1920</height><anamorphic>FALSE</anamorphic><pixelaspectratio>square</pixelaspectratio><fielddominance>none</fielddominance><colordepth>24</colordepth></samplecharacteristics></format>'
afmt='<format><samplecharacteristics><depth>16</depth><samplerate>48000</samplerate></samplecharacteristics></format>'
seq=(f'<sequence id="seq-1"><name>{NAME}_EDIT_v{VER}</name><duration>{edl["total"]}</duration>{RATE}'
     f'<timecode>{RATE}<string>00:00:00:00</string><frame>0</frame><displayformat>NDF</displayformat></timecode>'
     f'<media><video>{vfmt}'+''.join(track(t) for t in vtracks if t)+'</video>'
     f'<audio><numOutputChannels>2</numOutputChannels>{afmt}'+track(a1)+''.join(track(t['items']) for t in st)+(track(mtrack) if mtrack else '')+f'</audio></media>{mk}</sequence>')
out=os.path.join(EDIT,f'{NAME}_v{VER}_premiere.xml')
open(out,'w',encoding='utf-8').write('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE xmeml>\n<xmeml version="4">'+seq+'</xmeml>\n')
# SRT para subtítulos nativos
def tc(f):
    ms=round(f/FPS*1000);return f'{ms//3600000:02d}:{ms//60000%60:02d}:{ms//1000%60:02d},{ms%1000:03d}'
os.makedirs(os.path.join(EDIT,'Assets','Subtitulos'),exist_ok=True)
open(os.path.join(EDIT,'Assets','Subtitulos',f'{NAME}_v{VER}_subtitulos.srt'),'w').write('\n'.join(f"{k}\n{tc(c['tl_in'])} --> {tc(c['tl_out'])}\n{c['text']}\n" for k,c in enumerate(edl['caps'],1)))
import xml.dom.minidom;xml.dom.minidom.parse(out)   # valida que el XML esté bien formado
print('XML',out,'· pistas de video',len([t for t in vtracks if t]),'· pistas SFX',len(st),'· duración %.1fs'%(edl['total']/FPS))
timing.log(W,'XML para Premiere',time.time()-T0)
