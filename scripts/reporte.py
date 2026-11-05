#!/usr/bin/env python3
"""Avisa a n8n que una edición terminó, para el reporte diario. Lo llaman solos build_xml.py (/edicion) y finish.sh/.ps1 (/motion).
uso: python3 -I reporte.py <work> [edicion|motion]
Nunca frena una entrega: siempre termina con exit 0. Sin internet, el aviso queda en ~/.config/edicion/reporte_cola.jsonl y sale con el próximo.
Usa la URL y el token de ~/.config/edicion/whisper_remoto.json. Opcionales: "quien" en ese archivo o EDICION_QUIEN (nombre en el reporte),
EDICION_REPORTE_URL (otra URL) y EDICION_REPORTE=0 (no avisar).
Solo viajan datos de la edición: nunca el video, el guion ni rutas completas.
"""
import getpass,hashlib,json,os,socket,subprocess,sys,time,urllib.request
CFG=os.path.expanduser('~/.config/edicion/whisper_remoto.json')
COLA=os.path.expanduser('~/.config/edicion/reporte_cola.jsonl')
NOMBRES={'guspascaner':'Gus'}
def leer(p,d=None):
    try:
        with open(p,encoding='utf-8') as f: return json.load(f)
    except Exception: return d
def duracion(W,c,tipo):
    edl=leer(os.path.join(W,'edl.json'))
    if tipo=='edicion' and edl and edl.get('total'): return round(edl['total']/(c.get('fps') or 30),1)
    mp4=os.path.join(c.get('out_dir') or c.get('edit_dir') or '',f"{c.get('name')}.mp4")
    try:
        r=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',mp4],capture_output=True,text=True,timeout=20)
        return round(float(r.stdout.strip()),1)
    except Exception: return 0
def proceso(W):
    """Tiempo de la primera vez que se terminó: rearmar el XML días después (originales de Envato) no lo infla."""
    st=(leer(os.path.join(W,'timing.json'),{}) or {}).get('start') or 0
    p=os.path.join(W,'reporte.json');g=leer(p,{}) or {}
    if st and g.get('start')==st: return st,g.get('secs',0)
    secs=round(time.time()-st) if st else 0
    try:
        with open(p,'w',encoding='utf-8') as f: json.dump({'start':st,'secs':secs},f)
    except Exception: pass
    return st,secs
def datos(W,tipo,r):
    c=leer(os.path.join(W,'config.json'),{}) or {}
    carpeta=c.get('edit_dir') or c.get('out_dir') or W
    marca=c.get('brand') or 'editorial'
    # sin marca propia, el cliente es la carpeta que contiene a la edición
    cliente=marca if marca!='editorial' else os.path.basename(os.path.dirname(os.path.normpath(carpeta))) or marca
    extras=list((c.get('broll') or {}).values())+[c.get('music') or {}]
    pend=sum(1 for b in extras if isinstance(b,dict) and b.get('envato') and b['envato'].get('status')!='licensed')
    st,secs=proceso(W);ver=c.get('version') or 1;nombre=c.get('name') or os.path.basename(os.path.dirname(os.path.normpath(W)))
    usuario=getpass.getuser()
    # El inicio del cronómetro va en la clave: rearmar actualiza la misma fila; una versión nueva es otra edición.
    clave='|'.join([tipo,hashlib.sha1(os.path.abspath(carpeta).encode('utf-8')).hexdigest()[:8],nombre,f'v{ver}',str(int(st))])
    return dict(clave=clave,tipo=tipo,quien=os.environ.get('EDICION_QUIEN') or r.get('quien') or NOMBRES.get(usuario,usuario),maquina=socket.gethostname(),
                cliente=cliente,video=nombre,version=ver,duracion_s=duracion(W,c,tipo),proceso_s=secs,envato_pendiente=pend)
def enviar(url,tok,d):
    req=urllib.request.Request(url,data=json.dumps(d).encode('utf-8'),method='POST',headers={'Content-Type':'application/json','x-edicion-token':tok})
    with urllib.request.urlopen(req,timeout=10) as x: return 200<=x.status<300
def main():
    if len(sys.argv)<2 or os.environ.get('EDICION_REPORTE')=='0': return
    W=os.path.abspath(sys.argv[1]);tipo=sys.argv[2] if len(sys.argv)>2 else 'edicion'
    r=leer(CFG,{}) or {}
    nuevo=datos(W,tipo,r)
    pend=[]
    try:
        with open(COLA,encoding='utf-8') as f: pend=[json.loads(l) for l in f if l.strip()]
    except Exception: pass
    pend=[p for p in pend if p.get('clave')!=nuevo['clave']]+[nuevo]
    url=os.environ.get('EDICION_REPORTE_URL') or r.get('reporte_url') or (r.get('url') or '').replace('edicion-whisper','edicion-reporte')
    tok=r.get('token') or os.environ.get('EDICION_WHISPER_TOKEN');quedan=pend
    if url and tok:
        quedan=[]
        for k,p in enumerate(pend):
            try:
                if not enviar(url,tok,p): raise OSError('respuesta inesperada')
            except Exception:
                quedan=pend[k:];break
    os.makedirs(os.path.dirname(COLA),exist_ok=True)
    if quedan:
        with open(COLA,'w',encoding='utf-8') as f: f.write(''.join(json.dumps(p)+'\n' for p in quedan))
        print(f'Reporte diario: {len(quedan)} aviso(s) en cola, salen con la próxima edición')
    else:
        if os.path.exists(COLA): os.remove(COLA)
        print(f"Reporte diario: avisado ({nuevo['quien']} · {nuevo['video']})")
if __name__=='__main__':
    try: main()
    except Exception as e: print(f'Reporte diario: no se pudo avisar ({type(e).__name__}); la entrega sigue igual')
