#!/usr/bin/env python3
"""Verifica el corte re-transcribiéndolo SIN prompt (Whisper con tiempos por palabra) y alinea los subtítulos a la voz real.
uso: python3 -I align.py <workdir>      (lo llama edl.py; necesita cut.wav y edl.json)
Salida: words.json (palabras alineadas) · qa_words.json (problemas) · edl.json con los tiempos de cada palabra de los subtítulos.
Sin prompt a propósito: con el texto esperado de prompt Whisper "completa" palabras cortadas y la verificación no sirve.
En el potente se transcribe CADA CLIP por separado (ventanas cortas: tiempos por palabra confiables; sobre el corte entero Whisper
se corre 1–2 s) y el tiempo real reemplaza SIEMPRE a la estimación por letras (antes se descartaba si difería > 0,9 s: justo los
desfases grandes quedaban sin corregir, GUION3 30/10/2026).
Avisa de: palabras esperadas que no se oyen (¿última letra / arranque comido?), palabras sueltas que se oyen y no están en el guion
y palabras dichas dos veces seguidas. BLOQUEA la entrega (✗, exit 1, lo hace valer sync_check.py) cuando el corte no coincide con el
guion: una palabra del subtítulo de un clip se oye en OTRO clip, un clip no contiene su texto (clip de silencio con subtítulo) o
suena una frase entera que no está en el guion (toma repetida). Esos casos = tiempos equivocados en segs.json → check.py y corregir.
"""
import os as _o,sys as _s,subprocess as _sp
if _o.name=='nt' and __name__=='__main__' and not _s.flags.utf8_mode: _s.exit(_sp.run([_s.executable,'-X','utf8','-I',_o.path.abspath(__file__),*_s.argv[1:]]).returncode)  # Windows: acentos en UTF-8
import json,os,re,sys,subprocess,unicodedata,difflib
MODEL=os.path.expanduser('~/.cache/whisper-cpp/ggml-large-v3-turbo.bin')
WHISPER=os.environ.get('WHISPER_CLI') or __import__('shutil').which('whisper-cli') or os.path.join(os.environ.get('LOCALAPPDATA',''),'whisper-cpp','whisper-cli.exe')
W=sys.argv[1];E=json.load(open(os.path.join(W,'edl.json')));FPS=E['fps'];cut=os.path.join(W,'cut.wav')
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)));import whisperlib as WL
LIV=WL.liviano(W)   # liviano: Whisper remoto (tiempos por palabra de OpenAI), nada local
norm=lambda s:re.sub(r'[^a-z0-9ñ]','',unicodedata.normalize('NFD',s.lower()).replace('ñ','\0').encode('ascii','ignore').decode().replace('\0','ñ'))
clip_at=lambda s:max((c['i'] for c in E['clips'] if c['tl_in']/FPS<=s+1e-6),default=0)
# 1 · Whisper con una palabra por segmento. Cada palabra sabe en qué clip del corte suena ('clip').
asr=[]
if LIV:   # remoto: whisper-1 marca cada palabra ~0,25 s tarde en promedio frente al DTW local (medido en un corte de 48 s; error típico ±4 frames) → se adelanta 0,2 s
    asr=[dict(t=x['t'],n=norm(x['t']),frm=round(max(0,x['a']-0.2)*1000),to=round(x['b']*1000)) for x in WL.remote_words(cut) if norm(x['t'])]
    for a in asr: a['clip']=clip_at(a['frm']/1000)
else:   # potente: clip por clip (ventana corta = tiempos confiables; en el corte entero Whisper se corre 1–2 s y pierde palabras cortas)
    kw=os.path.join(W,'sub','k.wav');os.makedirs(os.path.dirname(kw),exist_ok=True)
    for c in E['clips']:
        a,b=c['tl_in']/FPS,c['tl_out']/FPS
        subprocess.run(['ffmpeg','-v','error','-y','-ss',f'{a:.3f}','-t',f'{b-a:.3f}','-i',cut,kw],check=True)
        for x in WL.local_words(kw):
            if norm(x['t']): asr.append(dict(t=x['t'],n=norm(x['t']),frm=round((a+x['a'])*1000),to=round((a+min(x['b'],b-a))*1000),clip=c['i']))
    if not asr and E['clips']: sys.exit('✗ Whisper no generó tiempos por palabra: no se pudo verificar el corte')
# 2 · palabras esperadas (las de los subtítulos, en orden)
exp=[(ci,wi,wd) for ci,c in enumerate(E['caps']) for wi,wd in enumerate(c['words'])]
# alucinaciones conocidas de Whisper sobre ruido/respiraciones: se sacan de lo oído (salvo que el guion las espere en ese clip) para no
# confundirlas con una toma repetida; un clip de silencio con subtítulo igual se detecta (no se oye su texto)
HALLU=[norm(x) for x in ('CC por Antarctica Films Argentina','Subtítulos realizados por la comunidad de Amara.org','Gracias por ver el video','Suscríbete al canal','Gracias','¡Gracias!')]
expn={(E['caps'][ci]['clip'],norm(wd['w'])) for ci,wi,wd in exp}
keep=[True]*len(asr)
for i in range(len(asr)):
    for L in range(min(7,len(asr)-i),0,-1):
        if ''.join(a['n'] for a in asr[i:i+L]) in HALLU and not any((a.get('clip'),a['n']) in expn for a in asr[i:i+L]):
            for k in range(i,i+L): keep[k]=False
            break
asr=[a for a,k in zip(asr,keep) if k]
en=[norm(w['w']) for _,_,w in exp];an=[a['n'] for a in asr]
match={}   # índice esperado → índice asr
sm=difflib.SequenceMatcher(None,en,an,autojunk=False);extra=[]
for tag,i1,i2,j1,j2 in sm.get_opcodes():
    if tag=='equal': match.update({i1+k:j1+k for k in range(i2-i1)})
    elif tag in('replace','insert'):
        jj=j1
        for i in range(i1,i2):
            best=None
            for j in range(jj,j2):
                r=difflib.SequenceMatcher(None,en[i],an[j]).ratio()
                if r>=.6 and (best is None or r>best[0]): best=(r,j)
            if best: match[i]=best[1];jj=best[1]+1
        used=set(match.values());extra+=[j for j in range(j1,j2) if j not in used]
# 3 · tiempos: lo que Whisper oyó manda (sin guarda de 0,9 s: los desfases grandes son justo los que hay que corregir); si una palabra
# no se oyó, se reparte entre sus vecinas. Una palabra que se oye en OTRO clip no aporta tiempo (es un error del corte: se bloquea abajo).
# En el liviano (una pasada remota sobre todo el corte) se descarta solo lo que difiere > 2,5 s, por deriva del remoto en cortes largos.
clipb=[(c['tl_in'],c['tl_out']) for c in E['clips']]
t0=[None]*len(exp)
for i,j in match.items():
    f=round(asr[j]['frm']/1000*FPS);old=exp[i][2]['s'];ci=E['caps'][exp[i][0]]['clip']
    if asr[j].get('clip',ci)!=ci: continue
    if LIV and abs(f-old)>2.5*FPS: continue
    t0[i]=f
issues=[];ok=0
for i,(ci,wi,wd) in enumerate(exp):
    if t0[i] is None: continue
    lo,hi=clipb[E['caps'][ci]['clip']];wd['s']=max(lo,min(hi-1,t0[i]));ok+=1
# monotonía y fin de cada palabra = inicio de la siguiente del mismo clip (o su fin estimado)
for ci,c in enumerate(E['caps']):
    ws=c['words']
    for k in range(1,len(ws)):
        if ws[k]['s']<ws[k-1]['s']: ws[k]['s']=ws[k-1]['s']
    for k,wd in enumerate(ws):
        nxt=ws[k+1]['s'] if k+1<len(ws) else c['tl_out']
        wd['e']=max(wd['s']+1,min(nxt,wd['s']+int(1.2*FPS))) if k+1<len(ws) else max(wd['s']+1,wd['e'])
    c['tl_in']=min(c['tl_in'],ws[0]['s']);c['tl_out']=max(c['tl_out'],ws[-1]['e'])
for k in range(len(E['caps'])-1):
    a,b=E['caps'][k],E['caps'][k+1]
    if b['tl_in']-a['tl_out']<12 and b['clip']==a['clip'] or (b['tl_in']-a['tl_out']<12 and b['tl_in']>=a['tl_out']): a['tl_out']=b['tl_in']
json.dump(E,open(os.path.join(W,'edl.json'),'w'),ensure_ascii=False,indent=1)
# 4 · chequeos del corte
tl=lambda ms:ms/1000
for i,(ci,wi,wd) in enumerate(exp):
    if i not in match: issues.append(dict(tipo='falta',t=round(wd['s']/FPS,2),w=wd['w'],msg=f"no se oye «{wd['w']}» en {wd['s']/FPS:.2f}s (¿arranque o última letra comida, o Whisper no la detectó?)"))
for j in extra:
    if len(an[j])>=2: issues.append(dict(tipo='sobra',t=round(tl(asr[j]['frm']),2),w=asr[j]['t'],msg=f"suena «{asr[j]['t']}» en {tl(asr[j]['frm']):.2f}s y no está en el guion (¿fragmento repetido o toma sobrante?)"))
for j in range(1,len(asr)):
    if an[j]==an[j-1] and len(an[j])>=2: issues.append(dict(tipo='repetida',t=round(tl(asr[j]['frm']),2),w=asr[j]['t'],msg=f"«{asr[j]['t']}» dicha dos veces seguidas en {tl(asr[j]['frm']):.2f}s"))
for k,c in enumerate(E['clips']):   # primera y última palabra de cada clip
    ws=[(i,x) for i,(ci,wi,x) in enumerate(exp) if E['caps'][ci]['clip']==k]
    if not ws: continue
    for lab,(i,x) in (('arranque',ws[0]),('final',ws[-1])):
        if i in match:
            r=difflib.SequenceMatcher(None,en[i],an[match[i]]).ratio()
            if r<.85 and len(en[i])>=4: issues.append(dict(tipo='borde',t=round(x['s']/FPS,2),w=x['w'],msg=f"clip {k} ({lab}): «{x['w']}» se oye «{asr[match[i]]['t']}» → revisar si se cortó la palabra"))
# 5 · el corte tiene que coincidir con el guion (BLOQUEA): cada palabra del subtítulo se oye en SU clip, cada clip contiene su texto
# y no suena ninguna frase que no esté en el guion. Si falla, los tiempos de segs.json están mal: mirar la zona con check.py y corregirlos.
tcl=lambda k:f"{E['clips'][k]['tl_in']/FPS:.2f}–{E['clips'][k]['tl_out']/FPS:.2f}s"
otro={}
for i,j in match.items():
    ci=E['caps'][exp[i][0]]['clip'];cj=asr[j].get('clip',ci)
    if cj==ci: continue
    t=asr[j]['frm']/1000;lo,hi=clipb[ci][0]/FPS,clipb[ci][1]/FPS
    otro.setdefault((ci,cj),[]).append((exp[i][2]['w'],max(lo-t,t-hi,0)))   # (palabra, a cuánto del borde de su clip se oyó)
for (ci,cj),ws in sorted(otro.items()):
    txt=' '.join(w for w,_ in ws[:8])+('…' if len(ws)>8 else '')
    # una sola palabra corta pegada al borde (< 0,35 s) suele ser Whisper eligiendo lado en el empalme: aviso. Dos o más palabras,
    # o una palabra de ≥ 4 letras bien adentro del otro clip = tiempos de segs.json mal puestos: bloquea.
    grave=len(ws)>=2 or (len(norm(ws[0][0]))>=4 and ws[0][1]>=0.35)
    if not grave and len(norm(ws[0][0]))<3: continue
    issues.append(dict(tipo='otro_clip' if grave else 'borde',t=round(E['clips'][ci]['tl_in']/FPS,2),w=txt,bloquea=grave,
        msg=f"«{txt}» está en el subtítulo del clip {ci} ({tcl(ci)}) pero se oye en el clip {cj} ({tcl(cj)}): "+("el corte no coincide con el guion → corregir los tiempos de esa frase en segs.json (check.py)" if grave else "está pegada al empalme: revisar con check.py que no se corte la palabra")))
for k,c in enumerate(E['clips']):
    exp_k=[i for i,(ci,wi,x) in enumerate(exp) if E['caps'][ci]['clip']==k]
    if not exp_k: continue
    heard=[a for a in asr if a.get('clip')==k];okk=[i for i in exp_k if i in match and asr[match[i]].get('clip',k)==k]
    if okk: continue
    sub=' '.join(exp[i][2]['w'] for i in exp_k[:8]);oyo=' '.join(a['t'] for a in heard[:10]);grave=len(exp_k)>=2   # con una sola palabra Whisper puede no oírla: aviso
    issues.append(dict(tipo='sin_texto',t=round(c['tl_in']/FPS,2),w=sub,bloquea=grave,
        msg=f"clip {k} ({tcl(k)}): no se oye su subtítulo «{sub}{'…' if len(exp_k)>8 else ''}»; "+(f"se oye «{oyo}»" if heard else 'no se oye voz (clip de silencio)')+(" → tiempos de segs.json equivocados (check.py)" if grave else " → confirmar con check.py")))
run=[]
for j in sorted(extra)+[None]:   # frases enteras que sobran (≥ 3 palabras seguidas que no están en el guion) = toma repetida o frase que falta en segs.json
    if j is not None and run and j==run[-1]+1: run.append(j);continue
    if len(run)>=3 and sum(len(an[x])>=2 for x in run)>=2:
        issues.append(dict(tipo='sobra_frase',t=round(asr[run[0]]['frm']/1000,2),w=' '.join(asr[x]['t'] for x in run),bloquea=True,
            msg=f"suena «{' '.join(asr[x]['t'] for x in run[:10])}{'…' if len(run)>10 else ''}» en {asr[run[0]]['frm']/1000:.2f}s (clip {asr[run[0]].get('clip','?')}) y no está en el guion: ¿toma repetida o frase que falta en segs.json? → corregir segs.json"))
    run=[j] if j is not None else []
json.dump([dict(w=a['t'],s=a['frm']/1000,e=a['to']/1000,clip=a.get('clip')) for a in asr],open(os.path.join(W,'words.json'),'w'),ensure_ascii=False)
json.dump(issues,open(os.path.join(W,'qa_words.json'),'w'),ensure_ascii=False,indent=1)
print(' '.join(a['t'] for a in asr))
blk=[x for x in issues if x.get('bloquea')]
print(f'\nsubtítulos alineados a la voz: {ok}/{len(exp)} palabras con tiempo real ({"una pasada remota" if LIV else "Whisper clip por clip"}) · problemas del corte: {len(issues)}'+(f' · {len(blk)} BLOQUEAN' if blk else ''))
for x in issues: print('  ✗ ' if x.get('bloquea') else '  ⚠️ ',x['msg'])
if blk: print(f'✗ el corte no coincide con el guion en {len(blk)} punto(s): corregir los tiempos en segs.json (check.py) y repetir tighten → edl. sync_check.py no deja entregar así.');sys.exit(1)
