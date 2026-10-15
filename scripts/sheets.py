#!/usr/bin/env python3
"""Compone los PNG de prueba (render.js --test) sobre un cuadro del video y arma hojas de 4x2.
uso: python3 -I sheets.py <workdir>     (usa <workdir>/bg.png; lo extrae del crudo si no existe)
→ <workdir>/sheets/sNN.png  (leerlas con Read para revisar diseño)
"""
import os as _o,sys as _s,subprocess as _sp
if _o.name=='nt' and __name__=='__main__' and not _s.flags.utf8_mode: _s.exit(_sp.run([_s.executable,'-X','utf8','-I',_o.path.abspath(__file__),*_s.argv[1:]]).returncode)  # Windows: acentos en UTF-8
import os,sys,subprocess,glob,json
W=sys.argv[1];cfg=json.load(open(os.path.join(W,'config.json')))
import atexit,time;sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)));import timing;_t0=time.time();atexit.register(lambda:timing.log(W,'Hojas de prueba',time.time()-_t0))
bg=os.path.join(W,'bg.png')
if not os.path.exists(bg): subprocess.run(['ffmpeg','-v','error','-y','-ss','20','-i',cfg['src'],'-frames:v','1','-vf','scale=1080:1920',bg])
dst=os.path.join(W,'sheets');os.makedirs(dst,exist_ok=True)
files=sorted(glob.glob(os.path.join(W,'test','*.png')));per=8
for k in range(0,len(files),per):
    grp=files[k:k+per];args=[]
    for f in grp: args+=['-i',bg,'-i',f]
    fc=''.join(f'[{2*i}][{2*i+1}]overlay,scale=360:640[c{i}];' for i in range(len(grp)))
    n=len(grp);lay='|'.join(f'{(i%4)*360}_{(i//4)*640}' for i in range(n))
    fc+=''.join(f'[c{i}]' for i in range(n))+(f'xstack=inputs={n}:layout={lay}:fill=black' if n>1 else 'null')
    subprocess.run(['ffmpeg','-v','error','-y']+args+['-filter_complex',fc,os.path.join(dst,f's{k//per:02d}.png')])
print('\n'.join(os.path.join(dst,x) for x in sorted(os.listdir(dst))))
