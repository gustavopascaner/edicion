#!/usr/bin/env python3
"""Paso 7: render de referencia MP4 con todo compuesto. uso: python3 -I preview.py <workdir>
→ <edit_dir>/<NAME>_v<N>_PREVIEW.mp4
"""
import json,os,subprocess,sys
W=sys.argv[1];cfg=json.load(open(os.path.join(W,'config.json')))
EDIT=cfg['edit_dir'];SRC=cfg['src'];FPS=cfg.get('fps',30);NAME=cfg['name'];VER=cfg.get('version',1)
e=json.load(open(os.path.join(W,'edl.json')));jobs=json.load(open(os.path.join(W,'jobs.json')));br=json.load(open(os.path.join(W,'broll.json')))
fr=lambda x:int(round(x*FPS))
out=os.path.join(EDIT,f'{NAME}_v{VER}_PREVIEW.mp4')
inputs=['-i',SRC];fc=[]
for c in e['clips']:
    i=c['i'];a=c['src_in']/FPS;b=c['src_out']/FPS
    z="scale=1080:1920" if i%2==0 else "scale=1274:-2,crop=1080:1920"
    fc.append(f"[0:v]trim=start={a:.4f}:end={b:.4f},setpts=PTS-STARTPTS,fps={FPS},{z},setsar=1,format=yuv420p[v{i}]")
    fc.append(f"[0:a]atrim=start={a:.4f}:end={b:.4f},asetpts=PTS-STARTPTS[a{i}]")
N=len(e['clips']);fc.append(''.join(f'[v{i}][a{i}]' for i in range(N))+f'concat=n={N}:v=1:a=1[base][dlg]')
last='base';k=1
for b in br['broll']:
    m=cfg['broll'][b['src']]
    if m.get('still'):
        z0,z1=[x/100 for x in (b.get('kb') or [100,100])];n=fr(b['dur'])
        inputs+=['-loop','1','-t',str(b['dur']),'-i',m['path']]
        fc.append(f"[{k}:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,zoompan=z='{z0}+({z1}-{z0})*on/{n}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1080x1920:fps={FPS},format=yuv420p,setpts=PTS-STARTPTS+{fr(b['start'])}/{FPS}/TB[o{k}]")
    else:
        inputs+=['-i',m['path']]
        fc.append(f"[{k}:v]trim=start={b['sin']}:duration={b['dur']},setpts=PTS-STARTPTS,fps={FPS},scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,setpts=PTS+{fr(b['start'])}/{FPS}/TB[o{k}]")
    fc.append(f"[{last}][o{k}]overlay=eof_action=pass[m{k}]");last=f'm{k}';k+=1
order={'cap':0,'ov':1,'ov2':2,'fs':3}
for j in sorted(jobs,key=lambda j:(order[j['track']],j['start'])):
    inputs+=['-i',os.path.join(EDIT,'Assets','Subtitulos' if j['track']=='cap' else 'MG',j['id']+'.mov')]
    fc.append(f"[{k}:v]setpts=PTS+{fr(j['start'])}/{FPS}/TB[o{k}]");fc.append(f"[{last}][o{k}]overlay=eof_action=pass:format=auto[m{k}]");last=f'm{k}';k+=1
LIB=os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','assets','sfx');sl=[]
sfx=json.load(open(os.path.join(W,'sfx.json'))) if os.path.exists(os.path.join(W,'sfx.json')) else []
for x in sfx:
    inputs+=['-i',os.path.join(LIB,x['file'])];d=int(x['start']*1000)
    fc.append(f"[{k}:a]atrim=start={x['sin']}:duration={x['dur']},asetpts=PTS-STARTPTS,volume={x['gain']},adelay={d}|{d}[s{k}]");sl.append(f'[s{k}]');k+=1
for x in br['extraSfx']:
    inputs+=['-i',x['file']];d=int(x['start']*1000)
    fc.append(f"[{k}:a]atrim=start={x['sin']}:duration={x['dur']},asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo,volume={x['gain']},adelay={d}|{d}[s{k}]");sl.append(f'[s{k}]');k+=1
fc.append(f"[dlg]{''.join(sl)}amix=inputs={1+len(sl)}:normalize=0:duration=first[aout]")
sc=os.path.join(W,'preview_fc.txt');open(sc,'w').write(';\n'.join(fc))
subprocess.run(['ffmpeg','-v','error','-y']+inputs+['-/filter_complex',sc,'-map',f'[{last}]','-map','[aout]','-c:v','libx264','-preset','veryfast','-crf','21','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-movflags','+faststart',out],check=True)
# hoja de contactos para revisión visual
sheet=os.path.join(W,'preview_sheet.jpg');dur=e['total']/FPS
subprocess.run(['ffmpeg','-v','error','-y','-i',out,'-vf',f'fps=1/{dur/32:.3f},scale=270:480,tile=8x4','-frames:v','1',sheet])
print('ok',out,'\nhoja:',sheet)
