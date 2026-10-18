#!/usr/bin/env python3
"""Auditoría de la librería de SFX (assets/sfx): mide cada .wav y lo compara con catalog.json.
Detecta: archivo faltante, duración/LUFS/true-peak que no coinciden, anchor incorrecto (el golpe no cae donde dice el catálogo),
clics (el archivo no arranca/termina en cero), agudos estridentes, picos > -1 dBTP, categorías automáticas con < 3 variantes
y, para cada sonido, el nivel que va a tener en la mezcla (dB relativos a la voz, ver catalog.levels).

uso:  python3 -I sfx_audit.py            (resumen + problemas; exit 1 si hay errores)
      python3 -I sfx_audit.py --fix      (corrige en el catálogo dur/lufs/tp/anchor medidos)
      python3 -I sfx_audit.py --cat hit  (solo esa categoría)  ·  -v  (tabla completa)
"""
import os as _o,sys as _s,subprocess as _sp
if _o.name=='nt' and __name__=='__main__' and not _s.flags.utf8_mode: _s.exit(_sp.run([_s.executable,'-X','utf8','-I',_o.path.abspath(__file__),*_s.argv[1:]]).returncode)
import array,json,math,os,re,subprocess,sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import sfx_import as I

def samples(f):
    raw=subprocess.run(['ffmpeg','-v','error','-i',f,'-ac','2','-ar','48000','-f','s16le','-'],capture_output=True,check=True).stdout
    return array.array('h',raw)
def hf_ratio(f):
    """dB de la energía > 6 kHz respecto de la total (si es > -9 dB suena estridente)."""
    def rms(af):
        r=subprocess.run(['ffmpeg','-hide_banner','-i',f,'-af',af+',astats=metadata=0','-f','null','-'],capture_output=True).stderr.decode('utf-8','replace')
        v=re.findall(r'RMS level dB:\s+(-?[\d.inf]+)',r);return float(v[-1]) if v and v[-1] not in('-inf',) else -99.0
    return rms('highpass=f=6000')-rms('anull')
def level_for(c,s):
    """Misma cuenta que render.js: pico = voz(pico) - rel_db; LUFS ≤ voz - lufs_rel; tope duro -3 dBFS."""
    L=c.get('levels',{});voice=L.get('voice_lufs',-16);ref=voice+L.get('voice_crest_db',12);lr=L.get('lufs_rel',{'short':12,'mid':14,'long':16})
    C=c['categories'].get(s['cat'],{});rel=s.get('rel_db',C.get('rel_db'))
    if rel is None: g=C.get('gain',.25);return 20*math.log10(g),None
    tail=s.get('tail',C.get('tail',99));eff=min(s['dur'],s['anchor']+tail)
    k=lr['short'] if eff<.8 else lr['mid'] if eff<2 else lr['long']
    db=min(ref-rel-s['tp'],voice-k-s['lufs'] if s['lufs']>-60 else 99,-3-s['tp'])
    return db,db+s['tp']

def main():
    a=sys.argv[1:];c=I.load();fix='--fix' in a;vb='-v' in a;only=a[a.index('--cat')+1] if '--cat' in a else None
    err=[];warn=[];rows=[];changed=False
    for id,s in c['sounds'].items():
        if only and s['cat']!=only: continue
        f=os.path.join(I.SFX,s['file'])
        if not os.path.exists(f): warn.append(f'{id}: falta el archivo {s["file"]}');continue
        sh=I.shape(f);I_,P=I.loudness(f);x=samples(f);first=max(abs(x[0]),abs(x[1]))/32768;last=max(abs(x[-1]),abs(x[-2]))/32768
        an=sh['peak'] if s['anchor_mode']=='peak' else sh['onset'] if s['anchor_mode']=='onset' else s['anchor']
        if s['anchor_mode']=='onset': an=0.0 if sh['onset']<.03 else sh['onset']
        hf=hf_ratio(f);gdb,pk=level_for(c,s)
        if abs(sh['dur']-s['dur'])>.01: (err if abs(sh['dur']-s['dur'])>.05 else warn).append(f'{id}: duración medida {sh["dur"]:.3f} s ≠ catálogo {s["dur"]}')
        if abs(an-s['anchor'])>.02: err.append(f'{id}: anchor {s["anchor"]} s pero el {s["anchor_mode"]} real está en {an:.3f} s (el golpe no caería en el evento)')
        if P>-0.95: err.append(f'{id}: true-peak {P:.1f} dBTP (> -1)')
        if abs(P-s['tp'])>.3 or (I_>-60 and abs(I_-s['lufs'])>.3): warn.append(f'{id}: LUFS/TP medidos ({I_:.1f}/{P:.1f}) ≠ catálogo ({s["lufs"]}/{s["tp"]})')
        if first>.02: err.append(f'{id}: arranca en {first:.3f} (clic al inicio; faltan los 3 ms de fade-in)')
        if last>.01: warn.append(f'{id}: termina en {last:.3f} (posible clic al final)')
        if hf>-9 and s['cat'] not in('glitch','click'): warn.append(f'{id}: mucho agudo >6 kHz ({hf:.1f} dB): puede sonar estridente')
        if sh['onset']<.0005 and first>.005: pass
        rows.append((s['cat'],id,sh['dur'],s['anchor'],an,I_,P,hf,gdb,pk))
        if fix:
            s.update(dur=round(sh['dur'],3),anchor=round(an,3),lufs=I_,tp=P);changed=True
    if fix and changed: I.save(c);print('catálogo actualizado con lo medido')
    for cat,v in c['categories'].items():
        if only and cat!=only: continue
        n=[i for i,s in c['sounds'].items() if s['cat']==cat and s.get('rotate',True)]
        if v.get('auto') and len(n)<3: warn.append(f'categoría {cat}: solo {len(n)} variante(s) en la rotación (mínimo 3)')
    print(f'{len(c["sounds"])} sonidos · {len(c["categories"])} categorías')
    if vb or only:
        print(f'{"cat":8s} {"id":16s}  dur   anchor(real) LUFS   TP   >6k   nivel mezcla   pico mezcla')
        for r in rows: print(f'{r[0]:8s} {r[1]:16s} {r[2]:5.2f} {r[3]:5.2f}({r[4]:5.2f}) {r[5]:6.1f} {r[6]:5.1f} {r[7]:5.1f}  {r[8]:6.1f} dB    '+(f'{r[9]:6.1f} dBFS' if r[9] is not None else '-'))
    for w in warn: print('⚠️ ',w)
    for e in err: print('✗ ',e)
    print(f'{len(err)} error(es), {len(warn)} aviso(s)')
    sys.exit(1 if err else 0)
if __name__=='__main__': main()
