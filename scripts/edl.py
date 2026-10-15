#!/usr/bin/env python3
"""Paso 3: arma la línea de tiempo (un clip por región de voz) y VERIFICA el corte re-transcribiéndolo.
uso: python3 -I edl.py <workdir> [--no-verify]   → <workdir>/edl.json (+ cut.wav y transcripción del corte)
Lee config.json (fps, tail = segundos extra al final para que se lea el último gráfico).
"""
import json,os,sys,subprocess
MODEL=os.path.expanduser('~/.cache/whisper-cpp/ggml-large-v3-turbo.bin')
W=sys.argv[1];cfg=json.load(open(os.path.join(W,'config.json')))
import atexit,time;sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)));import timing;_t0=time.time();atexit.register(lambda:timing.log(W,'Línea de tiempo + verificación',time.time()-_t0))
FPS=cfg.get('fps',30);PRE,POST=0.04,0.06;TAIL=cfg.get('tail',1.2)
P=json.load(open(os.path.join(W,'tight.json')))
f=lambda x:int(round(x*FPS))
clips=[];caps=[];t=0
for ci,p in enumerate(P):
    a=p['a']-PRE;b=p['b']+POST+(TAIL if ci==len(P)-1 else 0);sin,sout=f(a),f(b);dur=sout-sin
    clips.append(dict(i=ci,seg=p['seg'],src_in=sin,src_out=sout,tl_in=t,tl_out=t+dur,text=p['t']))
    words=p['t'].split();groups=[];cur=[]
    for w in words:
        cur.append(w)
        if len(' '.join(cur))>=14 or w.endswith((',',':','?','...','!')): groups.append(cur);cur=[]
    if cur:
        if groups and len(' '.join(cur))<6: groups[-1]+=cur
        else: groups.append(cur)
    pa,pb=p['a'],p['b'];tot=sum(len(' '.join(g)) for g in groups) or 1;s=pa
    for g in groups:
        d=(pb-pa)*len(' '.join(g))/tot;wl=[];ws=s;gl=sum(len(w) for w in g)
        for w in g:
            wd=d*len(w)/gl;wl.append(dict(w=w,s=round((ws-a)*FPS+t),e=round((ws+wd-a)*FPS+t)));ws+=wd
        caps.append(dict(clip=ci,seg=p['seg'],tl_in=round((s-a)*FPS+t),tl_out=round((s+d-a)*FPS+t),text=' '.join(g),words=wl));s+=d
    t+=dur
for k in range(len(caps)-1):
    if caps[k+1]['tl_in']-caps[k]['tl_out']<12: caps[k]['tl_out']=caps[k+1]['tl_in']
json.dump(dict(fps=FPS,total=t,clips=clips,caps=caps),open(os.path.join(W,'edl.json'),'w'),ensure_ascii=False,indent=1)
segs={}
for c in clips: segs.setdefault(c['seg'],[c['tl_in'],c['tl_out']]);segs[c['seg']][1]=c['tl_out']
print('total %.2fs · %d clips'%(t/FPS,len(clips)));print(' '.join('%d:%.1f-%.1f'%(k,v[0]/FPS,v[1]/FPS) for k,v in segs.items()))
if '--no-verify' not in sys.argv:
    fc=';'.join('[0:a]atrim=start=%.4f:end=%.4f,asetpts=PTS-STARTPTS[a%d]'%(c['src_in']/FPS,c['src_out']/FPS,i) for i,c in enumerate(clips))
    fc+=';'+''.join('[a%d]'%i for i in range(len(clips)))+'concat=n=%d:v=0:a=1[out]'%len(clips)
    open(os.path.join(W,'fc_cut.txt'),'w').write(fc)
    cut=os.path.join(W,'cut.wav')
    subprocess.run(['ffmpeg','-v','error','-y','-i',os.path.join(W,'audio16k.wav'),'-/filter_complex',os.path.join(W,'fc_cut.txt'),'-map','[out]',cut],check=True)
    print('\n--- transcripción del corte (verificar que no falten palabras) ---')
    print(subprocess.run(['whisper-cli','-m',MODEL,'-f',cut,'-l','es','-np','-t','8'],capture_output=True,text=True).stdout)
