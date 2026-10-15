#!/usr/bin/env python3
"""Importa efectos de sonido a la librería de la skill (assets/sfx).
Recorta silencios, normaliza volumen (-16 LUFS, pico ≤ -1 dBTP), convierte a WAV 48 kHz estéreo
y registra cada sonido en assets/sfx/catalog.json con su duración y punto de sincronía (anchor).

uso:  python3 -I sfx_import.py <archivo.wav> --id ding-2 --cat ding [--anchor peak|onset] [--max 4] [--desc "..."]
      python3 -I sfx_import.py --batch lista.json      (lista de {src,id,cat,anchor,max,desc})
      python3 -I sfx_import.py --list                  (muestra el catálogo)
anchor: momento del sonido que cae justo en el evento (peak = golpe más fuerte, onset = arranque).
"""
import os as _o,sys as _s,subprocess as _sp
if _o.name=='nt' and __name__=='__main__' and not _s.flags.utf8_mode: _s.exit(_sp.run([_s.executable,'-X','utf8','-I',_o.path.abspath(__file__),*_s.argv[1:]]).returncode)  # Windows: acentos en UTF-8
import array,json,math,os,re,subprocess,sys
SFX=os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','assets','sfx');CAT=os.path.join(SFX,'catalog.json')
TARGET=-16.0;CEIL=-1.0;SR=48000

def envelope(f):
    raw=subprocess.run(['ffmpeg','-v','error','-i',f,'-ac','1','-ar',str(SR),'-f','s16le','-'],capture_output=True,check=True).stdout
    a=array.array('h',raw);hop=SR//1000
    return [max((abs(x) for x in a[i:i+hop]),default=0)/32768 for i in range(0,len(a),hop)]
def shape(f):
    e=envelope(f);pk=max(e) or 1e-9;db=lambda v:20*math.log10(max(v,1e-9)/pk)
    on=next(i for i,v in enumerate(e) if db(v)>-40);end=len(e)-next(i for i,v in enumerate(reversed(e)) if db(v)>-45)
    return dict(dur=len(e)/1000,onset=on/1000,peak=e.index(pk)/1000,end=end/1000)
def loudness(f):
    r=subprocess.run(['ffmpeg','-hide_banner','-nostats','-i',f,'-af','ebur128=peak=true','-f','null','-'],capture_output=True).stderr.decode('utf-8','replace')
    I=re.findall(r'I:\s+(-?[\d.]+) LUFS',r);P=re.findall(r'Peak:\s+(-?[\d.]+) dBFS',r)
    return float(I[-1]),float(P[-1])

def load():
    return json.load(open(CAT)) if os.path.exists(CAT) else {'target_lufs':TARGET,'categories':{},'sounds':{}}
def save(c):
    c['sounds']=dict(sorted(c['sounds'].items(),key=lambda kv:(kv[1]['cat'],kv[0])))
    json.dump(c,open(CAT,'w'),indent=1,ensure_ascii=False);open(CAT,'a').write('\n')

def add(c,src,id,cat,anchor='peak',desc='',**kw):
    assert re.fullmatch(r'[a-z0-9-]+',id),f'id inválido: {id} (usar minúsculas, números y guiones)'
    assert id not in c['categories'],f'el id {id} choca con una categoría: usar {id}-2, etc.'
    lim=kw.get('max');s=shape(src)
    a=round(max(0,s['onset']-0.005),3);b=s['end']+0.08;cut=False
    if lim and b-a>lim: b=a+lim;cut=True
    b=min(b,s['dur']);fo=0.3 if cut else 0.04
    tmp=os.path.join(SFX,'.tmp.wav')
    flt=f'atrim=start={a}:end={b},asetpts=PTS-STARTPTS,afade=t=in:d=0.003,afade=t=out:st={max(0,b-a-fo):.3f}:d={fo}'
    subprocess.run(['ffmpeg','-v','error','-y','-i',src,'-af',flt,'-ar',str(SR),'-ac','2','-c:a','pcm_s16le',tmp],check=True)
    I,P=loudness(tmp)
    g=CEIL-P if I<-60 else min(TARGET-I,CEIL-P)   # sonidos muy cortos: LUFS no mide, normalizar por pico
    rel=os.path.join(cat,id+'.wav');out=os.path.join(SFX,rel);os.makedirs(os.path.dirname(out),exist_ok=True)
    subprocess.run(['ffmpeg','-v','error','-y','-i',tmp,'-af',f'volume={g:.2f}dB','-ar',str(SR),'-ac','2','-c:a','pcm_s16le',out],check=True);os.remove(tmp)
    s2=shape(out);I2,P2=loudness(out)
    c['sounds'][id]=dict(cat=cat,file=rel,dur=round(s2['dur'],3),anchor=round(s2['peak'] if anchor=='peak' else 0.0,3),
                         anchor_mode=anchor,lufs=I2,tp=P2,desc=desc,source=os.path.basename(src))
    c['categories'].setdefault(cat,{'gain':0.35,'auto':False,'desc':''})
    print(f"{id:18s} {cat:10s} {s2['dur']:5.2f}s  anchor {c['sounds'][id]['anchor']:5.2f}  {I2:6.1f} LUFS  {P2:5.1f} dBTP")

if __name__=='__main__':
    args=sys.argv[1:];c=load()
    if not args or args[0] in('-h','--help'): print(__doc__);sys.exit()
    if args[0]=='--list':
        for k,v in c['categories'].items():
            print(f"\n{k}  (gain {v['gain']}) {v.get('desc','')}")
            for i,s in c['sounds'].items():
                if s['cat']==k: print(f"   {i:18s} {s['dur']:5.2f}s  anchor {s['anchor']:5.2f}  {s['desc']}")
        sys.exit()
    if args[0]=='--batch': items=json.load(open(args[1]))
    else:
        o={'src':args[0]};k=1
        while k<len(args): o[args[k][2:]]=args[k+1];k+=2
        if 'max' in o:o['max']=float(o['max'])
        items=[o]
    for it in items: add(c,**it)
    save(c)
