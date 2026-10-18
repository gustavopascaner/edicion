#!/usr/bin/env python3
"""Mezcla: deja la música de fondo (Envato) POR DEBAJO de la voz y comprueba el resultado con mediciones. uso: python3 -I mix.py <workdir> [--below=18]
  1 · arma la voz de la línea de tiempo (clips del master) y mide su nivel
  2 · prepara la cama de música: recorte desde `music.offset`, hueco de EQ para la voz (−3,5 dB a 2,8 kHz, −1,5 dB a 250 Hz), compresión suave
      (cama pareja) y nivel = voz − `below` LU (default 18) con loudnorm en 2 pasadas → Assets/Envato/<NAME>_music_bed.wav
  3 · mide voz vs música cada 0,4 s mientras habla la voz; si el 10 % peor queda a menos de 14 dB, baja la música lo que falte y repite
  4 · mezcla de referencia (voz + música + SFX de sfx.json) → LUFS integrados, true peak, SFX vs voz → <work>/mix_report.md
  5 · escribe en config.json music.bed (el XML usa ese archivo a nivel 1.0, sin recorte ni offset)
Sale con código 1 si el true peak de la mezcla supera −1 dBTP o la música sigue compitiendo con la voz.
"""
import os as _o,sys as _s,subprocess as _sp
if _o.name=='nt' and __name__=='__main__' and not _s.flags.utf8_mode: _s.exit(_sp.run([_s.executable,'-X','utf8','-I',_o.path.abspath(__file__),*_s.argv[1:]]).returncode)  # Windows: acentos en UTF-8
import json,math,os,re,struct,subprocess,sys,time,wave
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)));import audiochain as ac,timing
W=sys.argv[1];opts=dict((a[2:].split('=',1)+['1'])[:2] for a in sys.argv[2:] if a.startswith('--'))
CF=os.path.join(W,'config.json');cfg=json.load(open(CF));edl=json.load(open(os.path.join(W,'edl.json')));FPS=cfg.get('fps',30)
t0=time.time();BELOW=float(opts.get('below',cfg.get('mix',{}).get('music_below_lu',18)));MIN_RATIO=14.0
M=cfg.get('music') if isinstance(cfg.get('music'),dict) else None
if not M or not M.get('path'): sys.exit('✗ no hay música en config.json (music.path): elegirla con envato.py use … music o poner la ruta')
T=edl['total']/FPS;MD=os.path.join(W,'mix');os.makedirs(MD,exist_ok=True)
run=lambda c:subprocess.run(['ffmpeg','-v','error','-y']+c,check=True)
# 1 · voz de la línea de tiempo
clips=edl['clips'];fc=';'.join(f'[0:a]atrim=start={c["src_in"]/FPS:.5f}:end={c["src_out"]/FPS:.5f},asetpts=PTS-STARTPTS[a{i}]' for i,c in enumerate(clips))
fc+=';'+''.join(f'[a{i}]' for i in range(len(clips)))+f'concat=n={len(clips)}:v=0:a=1,aformat=sample_fmts=s16:channel_layouts=stereo,aresample=48000[o]'
open(os.path.join(MD,'fc_voice.txt'),'w').write(fc);VOICE=os.path.join(MD,'voice.wav')
run(['-i',cfg['src'],'-/filter_complex',os.path.join(MD,'fc_voice.txt'),'-map','[o]','-c:a','pcm_s16le',VOICE])
vi=ac.ebur(VOICE)
# 2 · cama de música
off=float(M.get('offset',0));src=M['path']   # siempre se parte de la canción original: mix.py se puede repetir
EQ=('aformat=channel_layouts=stereo,aresample=48000,highpass=f=50,equalizer=f=250:t=q:w=1.0:g=-1.5,equalizer=f=2800:t=q:w=0.8:g=-3.5,lowpass=f=15000,'
    'acompressor=threshold=0.15:ratio=2:attack=30:release=300:makeup=1')
pre=f'atrim=start={off:.3f}:duration={T+0.5:.3f},asetpts=PTS-STARTPTS,{EQ}'
BED=os.path.join(cfg['edit_dir'],'Assets','Envato',f"{cfg['name']}_music_bed.wav");os.makedirs(os.path.dirname(BED),exist_ok=True)
def mono16(p):
    d=os.path.join(MD,'t.wav');run(['-i',p,'-ac','1','-ar','16000','-c:a','pcm_s16le',d])
    w=wave.open(d);raw=w.readframes(w.getnframes());return struct.unpack('<%dh'%(len(raw)//2),raw)
def wins(S,hop=.4,sr=16000):
    n=int(sr*hop);return [20*math.log10(max(1,math.sqrt(sum(x*x for x in S[i:i+n])/n))/32768) for i in range(0,len(S)-n,n)]
SV=mono16(VOICE);WV=wins(SV);vtop=sorted(WV)[int(len(WV)*.9)];speak=[i for i,x in enumerate(WV) if x>vtop-12]   # ventanas en las que habla la voz (hasta 12 dB bajo su nivel fuerte)
target=vi['I']-BELOW;ratio=None
for it in range(3):
    r=subprocess.run(['ffmpeg','-hide_banner','-nostats','-i',src,'-vn','-af',f'{pre},loudnorm=I={target:.1f}:TP=-8:LRA=15:print_format=json','-f','null','-'],capture_output=True,text=True).stderr
    mm=re.search(r'\{[^{}]*"input_i"[^{}]*\}',r,re.S);meas=json.loads(mm.group(0)) if mm else None
    run(['-i',src,'-vn','-af',f'{pre},{ac.loudnorm_apply(meas,i=round(target,1),tp=-8,lra=15)},aresample=48000,asetpts=N/SR/TB,atrim=0:{T+0.5:.3f}','-c:a','pcm_s16le','-ar','48000',BED])
    SM=mono16(BED);WM=wins(SM);n=min(len(WV),len(WM))
    diffs=sorted(WV[i]-WM[i] for i in speak if i<n);p10=diffs[len(diffs)//10];med=diffs[len(diffs)//2];ratio=(med,p10)
    print(f'  música: objetivo {target:.1f} LUFS · voz − música mientras habla: mediana {med:.1f} dB · 10 % peor {p10:.1f} dB')
    if p10>=MIN_RATIO: break
    target-= (MIN_RATIO-p10)+0.5   # baja lo que falta
bi=ac.ebur(BED)
# 3 · mezcla de referencia con fade-out de la música y los SFX de sfx.json
sfx=json.load(open(os.path.join(W,'sfx.json'))) if os.path.exists(os.path.join(W,'sfx.json')) else []
LIB=os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','assets','sfx');ins=['-i',VOICE,'-i',BED];fl=[f'[1:a]afade=t=out:st={max(0,T-0.8):.3f}:d=0.8,atrim=0:{T:.3f},asetpts=PTS-STARTPTS[m]','[0:a]anull[v]'];sl=[]
for k,x in enumerate(sfx):
    p=os.path.join(LIB,x['file'])
    if not os.path.exists(p): continue
    ins+=['-i',p];j=len(ins)//2-1
    fl.append(f'[{j}:a]atrim=start={x.get("sin",0)}:duration={x["dur"]},asetpts=PTS-STARTPTS,aformat=channel_layouts=stereo,aresample=48000,volume={x["gain"]},adelay={int(x["start"]*1000)}|{int(x["start"]*1000)}[s{k}]');sl.append(f'[s{k}]')
fl.append((f'{"".join(sl)}amix=inputs={len(sl)}:normalize=0:duration=longest,apad,atrim=0:{T:.3f}[sfx];' if sl else f'anullsrc=r=48000:cl=stereo,atrim=0:{T:.3f}[sfx];')+f'[v][m][sfx]amix=inputs=3:normalize=0:duration=first,atrim=0:{T:.3f}[out]')
MIX=os.path.join(MD,'mezcla_referencia.wav');SFXW=os.path.join(MD,'sfx_only.wav')
run(ins+['-filter_complex',';'.join(fl),'-map','[out]','-c:a','pcm_s16le',MIX])
mi=ac.ebur(MIX)
# SFX vs voz: nivel de cada SFX (ventana de 0,4 s) contra la voz en el mismo instante
rows=[]
for x in sfx:
    a=int(x['start']/0.4);
    if a<len(WV): rows.append((x['id'],x['start'],WV[a]))
md=['# Mezcla (voz · música · SFX)','',f'- Voz de la línea de tiempo: **{vi["I"]:.1f} LUFS** (tal cual se grabó) · true peak {vi["TP"]} dBTP',
    f'- Cama de música: **{bi["I"]:.1f} LUFS** = voz − {vi["I"]-bi["I"]:.1f} LU · EQ con hueco para la voz (−3,5 dB a 2,8 kHz) · compresión suave',
    f'- Voz − música mientras habla: mediana **{ratio[0]:.1f} dB** · 10 % peor **{ratio[1]:.1f} dB** (mínimo exigido {MIN_RATIO:g})',
    f'- Mezcla de referencia: **{mi["I"]:.1f} LUFS** integrados · LRA {mi["LRA"]} · true peak **{mi["TP"]} dBTP**',f'- SFX: {len(sfx)} (la verificación fina de niveles está en sfx.json / director.js)','']
bad=[]
if mi['TP'] is not None and mi['TP']>-1.0: bad.append(f'true peak de la mezcla {mi["TP"]} dBTP (> −1): bajar SFX/música o la voz')
if ratio[1]<MIN_RATIO-0.5: bad.append(f'la música compite con la voz en el 10 % de los tramos ({ratio[1]:.1f} dB < {MIN_RATIO:g})')
if abs(mi['I']-vi['I'])>3: bad.append(f'la mezcla quedó en {mi["I"]:.1f} LUFS, lejos de la voz ({vi["I"]:.1f})')
md+=['## Problemas']+([f'- ✗ {b}' for b in bad] or ['- Ninguno ✓'])
open(os.path.join(W,'mix_report.md'),'w').write('\n'.join(md)+'\n')
# 4 · config: el XML usa la cama ya procesada
M['bed']=BED;M['bed_lufs']=round(bi['I'],1);M['bed_below_lu']=round(vi['I']-bi['I'],1);cfg['music']=M
json.dump(cfg,open(CF,'w'),ensure_ascii=False,indent=1)
print('\n'.join(md[2:]));print('cama de música →',BED)
timing.log(W,'Mezcla (música vs voz)',time.time()-t0)
sys.exit(1 if bad else 0)
