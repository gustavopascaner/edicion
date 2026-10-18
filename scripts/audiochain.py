"""Utilidades de medición de audio (ebur128 y loudnorm de 2 pasadas) para mix.py. NO procesa la voz."""
import json,re,subprocess

def loudnorm_measure(src,pre,i=-16.0,tp=-1.5,lra=15):
    """Primera pasada de loudnorm: mide (después de los filtros `pre`). Devuelve el dict de mediciones o None."""
    f=f'{pre},loudnorm=I={i}:TP={tp}:LRA={lra}:print_format=json'
    r=subprocess.run(['ffmpeg','-hide_banner','-nostats','-i',src,'-vn','-af',f,'-f','null','-'],capture_output=True,text=True)
    m=re.search(r'\{[^{}]*"input_i"[^{}]*\}',r.stderr,re.S)
    return json.loads(m.group(0)) if m else None

def loudnorm_apply(m,i=-16.0,tp=-1.5,lra=15):
    """Segunda pasada lineal (sin bombeo): ganancia fija con los valores medidos."""
    if not m: return f'loudnorm=I={i}:TP={tp}:LRA={lra}'
    return (f'loudnorm=I={i}:TP={tp}:LRA={lra}:measured_I={m["input_i"]}:measured_TP={m["input_tp"]}:measured_LRA={m["input_lra"]}'
            f':measured_thresh={m["input_thresh"]}:offset={m["target_offset"]}:linear=true')

def ebur(p):
    """LUFS integrados, LRA y true peak de un archivo (ebur128)."""
    r=subprocess.run(['ffmpeg','-hide_banner','-nostats','-i',p,'-af','ebur128=peak=true','-f','null','-'],capture_output=True,text=True).stderr
    last=r[r.rfind('Summary:'):] if 'Summary:' in r else r
    g=lambda k:(lambda m:float(m.group(1)) if m else None)(re.search(k+r':\s+(-?[\d.]+)',last))
    return dict(I=g(r'\n\s*I'),LRA=g(r'LRA'),TP=g(r'Peak'))
