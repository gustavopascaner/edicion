#!/usr/bin/env python3
"""Cronómetro de la edición. Los scripts anotan solos cuánto tarda cada paso en <work>/timing.json.
uso: python3 -I timing.py start <work>    (al empezar: marca el inicio)
     python3 -I timing.py report <work>   (al terminar: tiempo total + desglose; también lo guarda en timing.md)
"""
import os as _o,sys as _s,subprocess as _sp
if _o.name=='nt' and __name__=='__main__' and not _s.flags.utf8_mode: _s.exit(_sp.run([_s.executable,'-X','utf8','-I',_o.path.abspath(__file__),*_s.argv[1:]]).returncode)  # Windows: acentos en UTF-8
import json,os,sys,time
def _p(W): return os.path.join(W,'timing.json')
def _load(W):
    try: return json.load(open(_p(W)))
    except Exception: return {'start':None,'steps':[]}
def log(W,step,secs):
    if not os.path.isdir(W): return
    d=_load(W);d['steps'].append({'step':step,'secs':round(secs,1),'at':round(time.time())});json.dump(d,open(_p(W),'w'),indent=1)
def fmt(s):
    s=int(round(s));return f'{s//3600} h {s%3600//60:02d} min' if s>=3600 else f'{s//60} min {s%60:02d} s' if s>=60 else f'{s} s'
def report(W):
    d=_load(W);now=time.time();st=d['start'] or (min([x['at']-x['secs'] for x in d['steps']]) if d['steps'] else now)
    tot=now-st;agg={}
    for x in d['steps']:
        if x['at']>=st: agg[x['step']]=agg.get(x['step'],0)+x['secs']
    proc=sum(agg.values())
    lines=[f'**Tiempo total de procesamiento: {fmt(tot)}**','','| Paso | Tiempo |','|---|---|']
    lines+=[f'| {k} | {fmt(v)} |' for k,v in agg.items()]
    lines+=[f'| Análisis, decisiones y revisión del agente | {fmt(max(0,tot-proc))} |']
    txt='\n'.join(lines);open(os.path.join(W,'timing.md'),'w').write(txt+'\n');print(txt)
if __name__=='__main__':
    cmd,W=sys.argv[1],sys.argv[2]
    if cmd=='start': os.makedirs(W,exist_ok=True);json.dump({'start':time.time(),'steps':[]},open(_p(W),'w'),indent=1);print('⏱  cronómetro iniciado')
    elif cmd=='report': report(W)
