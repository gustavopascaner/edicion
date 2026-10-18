#!/usr/bin/env python3
"""Sintetiza con ffmpeg (lavfi) los sonidos propios de la librería (sin licencias de terceros) y los registra
en assets/sfx/catalog.json con el mismo flujo que sfx_import.py (recorte, fade corto, −16 LUFS / pico ≤ −1 dBTP).
Son sutiles a propósito: sin agudos estridentes, ataques de pocos ms y colas suaves.

uso:  python3 -I sfx_synth.py            (genera todos los que falten)
      python3 -I sfx_synth.py --force    (regenera todos)
      python3 -I sfx_synth.py pop-soft-1 ding-bell-2   (solo esos)
"""
import os,subprocess,sys,tempfile
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import sfx_import as I

SR=48000
N0='(random(0)*2-1)';N1='(random(1)*2-1)'   # ruido blanco por canal
def tone(f0,f1,tau):   # fase de un barrido exponencial de f0 a f1 (constante de tiempo tau)
    return f'2*PI*({f1}*t+({f0}-{f1})*{tau}*(1-exp(-t/{tau})))'
def atk(ta=0.003): return f'(1-exp(-t/{ta}))'
def gauss(tc,w): return f'exp(-pow((t-{tc})/{w},2))'

def synth(layers,dur,post,out):
    """layers: [(expr_L, expr_R | None, prefiltro)] → mezcla → post → wav 48 kHz estéreo."""
    ins=[];fc=[]
    for k,(l,r,pre) in enumerate(layers):
        ex=f"{l}|{r or l}"
        fc.append(f"aevalsrc=exprs='{ex}':s={SR}:d={dur}"+(f',{pre}' if pre else '')+f',aformat=channel_layouts=stereo[l{k}]')
    mix=''.join(f'[l{k}]' for k in range(len(layers)))
    fc.append(f"{mix}amix=inputs={len(layers)}:normalize=0:duration=longest,{post},alimiter=limit=0.9:level=disabled[o]")
    subprocess.run(['ffmpeg','-v','error','-y','-filter_complex',';'.join(fc),'-map','[o]','-ar',str(SR),'-ac','2','-c:a','pcm_s16le',out],check=True)

def noise_bands(bands,amp=1.0):
    """Ruido por bandas con envolvente gaussiana escalonada (simula un barrido): bands = [(fc, q, tc, w, amp)]."""
    return [(f'{N0}*{a*amp}*{gauss(tc,w)}',f'{N1}*{a*amp}*{gauss(tc,w)}',f'bandpass=f={f}:width_type=q:w={q}') for f,q,tc,w,a in bands]

R={}   # id → (cat, anchor, desc, layers, dur, post)
def add(id,cat,desc,layers,dur,post='anull',anchor='peak'): R[id]=(cat,anchor,desc,layers,dur,post)

# ── pop: gotas/burbujas suaves (seno con caída de tono) ──
for k,(f0,f1,tau,td) in enumerate([(640,270,.025,.050),(840,340,.020,.040),(500,210,.032,.075)],1):
    e=f'{atk(.002)}*exp(-t/{td})'
    add(f'pop-soft-{k}','pop',f'Pop suave de burbuja ({f0}→{f1} Hz).',
        [(f'0.9*sin({tone(f0,f1,tau)})*{e}',None,''),(f'0.18*sin(2*{tone(f0,f1,tau)})*{e}',None,'')],.35,'lowpass=f=4500')
# ── click: ticks secos y cortos ──
for k,(fb,fs_,q) in enumerate([(3000,1700,1.2),(2200,1200,1.0),(3800,2100,1.4)],1):
    add(f'click-tick-{k}','click',f'Tick de interfaz, seco y corto (banda {fb} Hz).',
        [(f'{N0}*exp(-t/.004)*{atk(.0008)}',f'{N1}*exp(-t/.004)*{atk(.0008)}',f'bandpass=f={fb}:width_type=q:w={q}'),
         (f'0.5*sin(2*PI*{fs_}*t)*exp(-t/.009)*{atk(.0008)}',None,'')],.18,'highpass=f=700,lowpass=f=6500')
# ── ding: campanitas con parciales inarmónicos y brillo recortado ──
for k,f in enumerate([784,932,1047],1):
    p=lambda m,a,d:f'{a}*sin(2*PI*{f*m}*t)*exp(-t/{d})'
    ex=f"{atk(.003)}*({p(1,1,.7)}+{p(2.0,.35,.4)}+{p(2.76,.14,.22)}+{p(4.1,.05,.1)})"
    add(f'ding-bell-{k}','ding',f'Campanita suave ({f} Hz).',[(ex,None,'')],1.9,'lowpass=f=6500')
# ── hit: sub-golpes con transitorio blando ──
for k,(f0,f1,tau,td,nb) in enumerate([(150,48,.040,.34,.45),(130,42,.050,.45,.35),(180,58,.030,.26,.55)],1):
    add(f'hit-sub-{k}','hit',f'Golpe grave con cuerpo ({f1} Hz de fondo).',
        [(f'{atk(.002)}*sin({tone(f0,f1,tau)})*exp(-t/{td})',None,''),
         (f'{nb}*{N0}*exp(-t/.045)',f'{nb}*{N1}*exp(-t/.045)','lowpass=f=420'),
         (f'0.25*{N0}*exp(-t/.003)',f'0.25*{N1}*exp(-t/.003)','bandpass=f=1600:width_type=q:w=1')],1.6,'lowpass=f=3500')
# ── whoosh: aire por bandas, subiendo / bajando / corto ──
add('whoosh-air-1','whoosh','Aire que sube y pasa (pico hacia los 0,3 s).',
    noise_bands([(350,.7,.20,.14,1),(800,.8,.27,.14,1),(1700,.9,.34,.14,.8),(3200,1,.40,.14,.45)]),.9,'lowpass=f=4800')
add('whoosh-air-2','whoosh','Aire que baja y se va (pico a los 0,2 s).',
    noise_bands([(3000,1,.14,.13,.45),(1600,.9,.20,.14,.8),(800,.8,.27,.14,1),(380,.7,.34,.16,1)]),.9,'lowpass=f=4800')
add('whoosh-soft-3','whoosh','Whoosh corto y suave, de paso rápido.',
    noise_bands([(500,.8,.11,.08,1),(1200,.9,.15,.08,1),(2400,1,.19,.08,.6)]),.5,'lowpass=f=4500')
# ── zoom: barrido tonal + aire hacia el punch ──
for k,(f0,f1,T) in enumerate([(220,880,.5),(300,1100,.42)],1):
    kk=__import__('math').log(f1/f0)/T
    env=f'if(lt(t,{T}),pow(t/{T},1.7),exp(-(t-{T})/.05))'
    add(f'zoom-sweep-{k}','zoom',f'Barrido ascendente {f0}→{f1} Hz que cierra en el acercamiento.',
        [(f'0.7*sin(2*PI*{f0}/{kk}*(exp({kk}*min(t,{T}))-1))*{env}',None,''),
         (f'0.5*{N0}*{env}',f'0.5*{N1}*{env}','bandpass=f=1400:width_type=q:w=.7')],T+.4,'lowpass=f=5000')
# ── wind: brillo mágico suave ──
for k,(f,tc) in enumerate([(880,1.1),(1175,1.0),(1397,1.2)],1):
    g=gauss(tc,.55)
    add(f'wind-shimmer-{k}','wind','Brillo suave de aparición (aire y armónicos).',
        [(f'0.9*{N0}*{g}',f'0.9*{N1}*{g}','bandpass=f=1500:width_type=q:w=.6'),
         (f'0.5*sin(2*PI*{f}*t)*{g}*(0.75+0.25*sin(2*PI*5*t))',None,''),
         (f'0.3*sin(2*PI*{f*1.5}*t)*{g}*(0.75+0.25*sin(2*PI*4.3*t))',None,'')],2.6,'lowpass=f=5500')
# ── build: risers cortos que terminan en el evento ──
for k,(T,f1) in enumerate([(2.0,1500),(3.0,1800)],1):
    ramp=f'pow(t/{T},2.2)'
    add(f'riser-short-{k}','build',f'Riser suave de {T:g} s; el pico es el final (evento).',
        noise_bands([(300,.8,T*.80,T*.38,.8),(900,.9,T*.92,T*.32,1),(2200,1,T*1.0,T*.26,.9)],.9)+
        [(f'0.35*sin({tone(180,f1,T/3)})*{ramp}',None,'')],T+.05,f'volume=0.4,lowpass=f=5500,afade=t=out:st={T:.3f}:d=0.05')
# ── poof: soplido ──
for k,(fl,td) in enumerate([],1):   # poof-air-1/2 eliminados a pedido de Gus (quedan en ~/.claude/skills/edicion_sfx_eliminados)
    add(f'poof-air-{k}','poof','Soplido suave de algo que se esfuma.',
        [(f'{N0}*{atk(.008)}*exp(-t/{td})',f'{N1}*{atk(.008)}*exp(-t/{td})',f'highpass=f=250,lowpass=f={fl}')],.7)
# ── bounce / error ──
add('bounce-boing','bounce','Boing de resorte, tono de humor.',
    [(f'0.9*sin(2*PI*330*t+4*sin(2*PI*8*t)*exp(-t/.2))*{atk(.003)}*exp(-t/.2)',None,'')],.75,'lowpass=f=3500')
add('error-buzz-soft','error','Dos tonos graves descendentes, suave (✗).',
    [(f'{atk(.004)}*(if(lt(t,.2),sin(2*PI*233*t),if(gt(t,.22),sin(2*PI*174*t),0)))*(if(lt(t,.2),exp(-t/.25),exp(-(t-.22)/.3)))+'
      f'0.25*(if(lt(t,.2),sin(2*PI*466*t),0))*exp(-t/.1)',None,'')],.75,'lowpass=f=1800',anchor='onset')
add('error-thud-soft','error','Golpecito grave y opaco de "no va" (✗).',
    [(f'{atk(.003)}*sin({tone(190,95,.06)})*exp(-t/.14)',None,''),(f'0.5*{N0}*exp(-t/.02)',f'0.5*{N1}*exp(-t/.02)','lowpass=f=700')],.5,'lowpass=f=1800',anchor='onset')
add('glitch-digital-2','glitch','Tartamudeo digital corto (pasos de tono y ruido en ráfagas).',
    [('0.5*sin(2*PI*(500+260*mod(floor(t*38),5))*t)*if(lt(mod(t,.026),.016),1,0)*exp(-t/.25)',None,''),
     (f'0.5*{N0}*if(lt(mod(t,.04),.012),1,0)*exp(-t/.2)',f'0.5*{N1}*if(lt(mod(t,.04),.012),1,0)*exp(-t/.2)','bandpass=f=2200:width_type=q:w=.8')],.6,'lowpass=f=5500')

def main():
    a=sys.argv[1:];force='--force' in a;only=[x for x in a if not x.startswith('--')]
    c=I.load();os.makedirs(I.SFX,exist_ok=True);tmp=tempfile.mkdtemp(prefix='sfxsynth-')
    for id,(cat,anchor,desc,layers,dur,post) in R.items():
        if only and id not in only: continue
        if id in c['sounds'] and not force and not only: continue
        raw=os.path.join(tmp,id+'.wav');synth(layers,dur,post,raw)
        I.add(c,raw,id,cat,anchor,desc);c['sounds'][id]['source']='sintetizado (sfx_synth.py)'
    I.save(c)
if __name__=='__main__': main()
