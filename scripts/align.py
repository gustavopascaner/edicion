#!/usr/bin/env python3
"""Verifica el corte re-transcribiéndolo SIN prompt (Whisper con tiempos por palabra) y alinea los subtítulos a la voz real.
uso: python3 -I align.py <workdir>      (lo llama edl.py; necesita cut.wav y edl.json)
Salida: words.json (palabras alineadas) · qa_words.json (problemas) · edl.json con los tiempos de cada palabra de los subtítulos.
Sin prompt a propósito: con el texto esperado de prompt Whisper "completa" palabras cortadas y la verificación no sirve.
Avisa de: palabras esperadas que no se oyen (¿última letra / arranque comido?), palabras que se oyen y no están en el guion
(¿fragmento repetido?) y palabras dichas dos veces seguidas.
"""
import os as _o,sys as _s,subprocess as _sp
if _o.name=='nt' and __name__=='__main__' and not _s.flags.utf8_mode: _s.exit(_sp.run([_s.executable,'-X','utf8','-I',_o.path.abspath(__file__),*_s.argv[1:]]).returncode)  # Windows: acentos en UTF-8
import json,os,re,sys,subprocess,unicodedata,difflib
MODEL=os.path.expanduser('~/.cache/whisper-cpp/ggml-large-v3-turbo.bin')
WHISPER=os.environ.get('WHISPER_CLI') or __import__('shutil').which('whisper-cli') or os.path.join(os.environ.get('LOCALAPPDATA',''),'whisper-cpp','whisper-cli.exe')
W=sys.argv[1];E=json.load(open(os.path.join(W,'edl.json')));FPS=E['fps'];cut=os.path.join(W,'cut.wav')
norm=lambda s:re.sub(r'[^a-z0-9ñ]','',unicodedata.normalize('NFD',s.lower()).replace('ñ','\0').encode('ascii','ignore').decode().replace('\0','ñ'))
# 1 · Whisper con una palabra por segmento
base=os.path.join(W,'cut_words');js=base+'.json'
for dtw in (['-dtw','large.v3.turbo'],[]):
    if os.path.exists(js): os.unlink(js)
    subprocess.run([WHISPER,'-m',MODEL,'-f',cut,'-l','es','-np','-t','8','-ml','1','-sow','-ojf','-of',base]+dtw,capture_output=True)
    if os.path.exists(js): break
if not os.path.exists(js): sys.exit('✗ Whisper no generó tiempos por palabra: no se pudo verificar el corte')
asr=[]
for s in json.load(open(js)).get('transcription',[]):
    tx=s['text'];o=s['offsets']
    if not norm(tx): continue
    if asr and not tx.startswith(' ') and not re.match(r'^[¿¡]',tx): asr[-1]['to']=o['to'];asr[-1]['t']+=tx;asr[-1]['n']=norm(asr[-1]['t']);continue   # sub-palabra → pegar a la anterior
    asr.append(dict(t=tx.strip(),n=norm(tx),frm=o['from'],to=o['to']))
# 2 · palabras esperadas (las de los subtítulos, en orden)
exp=[(ci,wi,wd) for ci,c in enumerate(E['caps']) for wi,wd in enumerate(c['words'])]
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
# 3 · tiempos: lo que Whisper oyó; si una palabra no se oyó, se reparte entre sus vecinas. Si difiere >0,9 s de la estimación por letras (outlier), se queda la estimación.
clipb=[(c['tl_in'],c['tl_out']) for c in E['clips']]
t0=[None]*len(exp)
for i,j in match.items():
    f=round(asr[j]['frm']/1000*FPS);old=exp[i][2]['s']
    if abs(f-old)<=0.9*FPS: t0[i]=f
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
json.dump([dict(w=a['t'],s=a['frm']/1000,e=a['to']/1000) for a in asr],open(os.path.join(W,'words.json'),'w'),ensure_ascii=False)
json.dump(issues,open(os.path.join(W,'qa_words.json'),'w'),ensure_ascii=False,indent=1)
print(' '.join(a['t'] for a in asr))
print(f'\nsubtítulos alineados a la voz: {ok}/{len(exp)} palabras con tiempo real · problemas del corte: {len(issues)}')
for x in issues: print('  ⚠️ ',x['msg'])
