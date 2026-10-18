// Marcas compartidas con la skill motion: ~/.config/motion/brands/<marca>/brand.json (se crean con motion: scripts/brand.py).
// Acá no se crean ni se editan: solo se leen para cambiar colores, tipografías y subtítulos. Sin marca (o "editorial") = el look de siempre.
// uso: node brand.js list          → marcas disponibles
//      node brand.js show <marca>  → cómo se mapea a este motor
//      node brand.js detect <carpeta> → adivina la marca de la carpeta de videos (archivo .marca, ediciones anteriores, nombre de carpeta)
//      node brand.js remember <carpeta> <marca> → guarda .marca en la carpeta para la próxima
const fs=require('fs'),path=require('path'),os=require('os');
const {fileURL}=require('./platform.js');
const H=os.homedir();
const ROOTS=[path.join(H,'.config','motion','brands'),...['.claude','.codex'].map(d=>path.join(H,d,'skills','motion','brands'))];

function dirOf(slug){if(path.isAbsolute(slug))return slug;return ROOTS.map(r=>path.join(r,slug)).find(d=>fs.existsSync(path.join(d,'brand.json')));}

function list(){const seen=new Map();
  for(const r of ROOTS)for(const s of fs.existsSync(r)?fs.readdirSync(r):[]){const f=path.join(r,s,'brand.json');
    if(!seen.has(s)&&fs.existsSync(f))try{seen.set(s,JSON.parse(fs.readFileSync(f,'utf8')));}catch(e){}}
  return [...seen].map(([slug,b])=>({slug,name:b.name||slug,colors:b.colors||{},font:((b.fonts||{}).display||{}).family}));}

// contraste WCAG entre dos hex
const lum=h=>{h=h.replace('#','');const [r,g,b]=[0,2,4].map(i=>parseInt(h.slice(i,i+2),16)/255).map(v=>v<=.03928?v/12.92:((v+.055)/1.055)**2.4);return .2126*r+.7152*g+.0722*b;};
const con=(a,b)=>{const x=lum(a),y=lum(b);return (Math.max(x,y)+.05)/(Math.min(x,y)+.05);};

function loadBrand(slug){if(!slug||slug==='editorial')return null;
  const d=dirOf(slug);if(!d)throw new Error(`No existe la marca "${slug}". Marcas: ${list().map(x=>x.slug).join(', ')||'(ninguna)'} — se crean con la skill motion (reference/marca-nueva.md)`);
  const b=JSON.parse(fs.readFileSync(path.join(d,'brand.json'),'utf8'));const c=b.colors||{};
  for(const k of['dark','light','accent'])if(!/^#[0-9a-f]{6}$/i.test(c[k]||''))throw new Error(`La marca "${slug}" no tiene el color "${k}" en formato #RRGGBB`);
  for(const [k,f] of Object.entries(b.fonts||{}))for(const x of f.files||[]){const p=path.isAbsolute(x.file)?x.file:path.join(d,x.file);
    if(!fs.existsSync(p))throw new Error(`Falta la tipografía ${p}: correr en motion "brand.py setup ${slug}"`);x.url=fileURL(p);}
  b.slug=slug;return b;}

// colores del motor: ink=oscuro · paper=claro · hot=acento · lime=acento 2 si se lee bien sobre el oscuro (se usa como texto/resaltado ahí), si no el acento
function palette(b){const c=b.colors,a2=c.accent2&&con(c.accent2,c.dark)>=4.5?c.accent2:c.accent;
  return {ink:c.dark,paper:c.light,hot:c.accent,lime:a2,mute:c.mute||null};}

// tonos derivados: % de papel sobre tinta, medidos sobre los tonos originales del motor (engine.html :root)
const MIX={ink2:5.7,p1:98.1,p2:94.9,p3:93,p4:90.6,p5:88.5,p6:81.6,t1:63.8,t2:39.3,d1:6.1,d2:13.7,d3:18.9,d4:25,d5:30.4};
function css(b){const P=palette(b),f=b.fonts||{},out=[];
  // mismos nombres de familia que usa el motor: Brico (títulos) · Inter (texto) · Mono (etiquetas) · Serif (acento itálico)
  const alias={Brico:f.display,Inter:f.body,Mono:f.mono,Serif:f.accent};
  for(const [fam,ff] of Object.entries(alias))for(const x of ((ff||f.body||{}).files||[]))
    out.push(`@font-face{font-family:${fam};src:url("${x.url}");font-weight:${x.weight||400};font-style:${x.style||(fam==='Serif'?'italic':'normal')}}`);
  const v=[`--ink:${P.ink}`,`--paper:${P.paper}`,`--hot:${P.hot}`,`--lime:${P.lime}`,`--mute:${P.mute||`color-mix(in srgb,${P.paper} 52%,${P.ink})`}`,
    ...Object.entries(MIX).map(([k,n])=>`--${k}:color-mix(in srgb,${P.paper} ${n}%,${P.ink})`)];
  out.push(`:root{${v.join(';')}}`);
  const d=f.display||{};
  out.push(`.disp{font-weight:${d.weight||800};font-stretch:${d.stretch||'100%'};letter-spacing:${d.tracking||'-0.02em'};line-height:${d.leading||.9};text-transform:${d.upper===false?'none':'uppercase'}}`);
  return out.join('\n');}

// subtítulos: la palabra activa en el acento que mejor se lee con texto oscuro encima
// estilo de subtítulos propio de la marca (opcional): brand.json "captions": {style:'box'|'underline'|'pop'|'karaoke'|'minimal'|'stacked', size?, case:'upper'|'none', font:'display'|'body'|'serif', dy?}
// OJO: la skill motion ya usa "captions" ({on, upper, size}) para lo suyo: acá solo cuenta si trae "style" (si no, el look de siempre)
// config.caption_style y arte.json "subtitulos" lo pisan
function captionStyle(b){const c=b&&b.captions;if(typeof c==='string')return {style:c};if(!c||!c.style)return null;
  const {on,upper,...r}=c;return {...r,case:r.case||(upper===false?'none':undefined)};}
function captionColors(b){const c=b.colors,best=[c.accent,c.accent2].filter(Boolean).sort((x,y)=>con(y,c.dark)-con(x,c.dark))[0];return {act:best,kwAct:'#fff',kw:best};}

// en la página del motor: saca las @font-face originales (si no, se mezclan con las de la marca) y aplica la marca
// Los layouts del motor están medidos para una tipografía de títulos condensada (Bricolage al 76 %): si la de la marca es más
// ancha, los títulos se achican en la misma proporción para no cortarse (se mide el ancho de una frase con las dos).
async function apply(page,b){if(!b)return null;
  const W=()=>page.evaluate(async()=>{const e=document.createElement('span');e.className='disp';e.style.cssText='position:absolute;visibility:hidden;font-size:100px;white-space:nowrap';
    e.textContent='MARKETING MÉDICO PACIENTES';document.body.appendChild(e);const cs=getComputedStyle(e);await document.fonts.load(`${cs.fontWeight} 100px Brico`,e.textContent);const w=e.getBoundingClientRect().width;e.remove();return w;});
  await page.evaluate(()=>document.fonts.ready);const w0=await W();
  await page.evaluate(()=>{for(const sh of document.styleSheets)for(let i=sh.cssRules.length-1;i>=0;i--)if(sh.cssRules[i] instanceof CSSFontFaceRule)sh.deleteRule(i);});
  await page.addStyleTag({content:css(b)});await page.evaluate(()=>document.fonts.ready);
  const k=Math.max(.6,Math.min(1,w0/await W()));
  if(k<.98)await page.evaluate(k=>{const o=window.setup;window.setup=(n,p,d)=>{const r=o(n,p,d);
    const els=[...document.querySelectorAll('#stage .disp,#stage [style*="font-family:Brico"]')],fs=els.map(e=>parseFloat(getComputedStyle(e).fontSize));
    els.forEach((e,i)=>e.style.fontSize=(fs[i]*k).toFixed(2)+'px');return r;};},k);
  return k;}

// Detecta la marca de una carpeta de videos. Orden: 1) archivo .marca (en la carpeta o hasta 3 niveles arriba),
// 2) "brand" del config.json de ediciones anteriores (<x>_EDIT/.work en la carpeta y sus vecinas; gana la más reciente),
// 3) nombre de la carpeta o de sus padres = slug o nombre de una marca (sin tildes ni mayúsculas).
const norm=t=>String(t).normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'');
function detect(dir){dir=path.resolve(dir);if(fs.existsSync(dir)&&!fs.statSync(dir).isDirectory())dir=path.dirname(dir);
  const valid=new Set(['editorial',...list().map(x=>x.slug)]);const ups=[];
  for(let d=dir,i=0;i<4&&d!==H&&d!==path.dirname(d);i++,d=path.dirname(d))ups.push(d);
  for(const d of ups){const f=path.join(d,'.marca');if(fs.existsSync(f)){const s=fs.readFileSync(f,'utf8').trim();
    if(valid.has(s))return {slug:s,why:`archivo ${f}`};}}
  const cfgs=[];for(const d of ups.slice(0,2)){let ents=[];try{ents=fs.readdirSync(d);}catch(e){}
    for(const e of ents)if(/_EDIT$/.test(e)){const f=path.join(d,e,'.work','config.json');
      try{const c=JSON.parse(fs.readFileSync(f,'utf8'));if(c.brand&&valid.has(c.brand))cfgs.push({slug:c.brand,f,t:fs.statSync(f).mtimeMs});}catch(x){}}
    if(cfgs.length)break;}
  if(cfgs.length){cfgs.sort((a,b)=>b.t-a.t);return {slug:cfgs[0].slug,why:`edición anterior ${cfgs[0].f}`};}
  const names=list().map(x=>({slug:x.slug,keys:[norm(x.slug),norm(x.name)]}));
  for(const d of ups){const seg=norm(path.basename(d));if(!seg)continue;
    const exact=names.find(n=>n.keys.includes(seg));if(exact)return {slug:exact.slug,why:`nombre de carpeta "${path.basename(d)}"`};
    const part=names.filter(n=>!/-v\d+$/.test(n.slug)&&n.keys.some(k=>k.length>=4&&(`-${seg}-`).includes(`-${k}-`)));
    if(part.length===1)return {slug:part[0].slug,why:`nombre de carpeta "${path.basename(d)}"`};}
  return null;}

module.exports={loadBrand,list,css,palette,captionColors,captionStyle,apply,detect};

if(require.main===module){const [cmd,slug,arg3]=process.argv.slice(2);
  try{if(cmd==='list'){console.log('editorial            Editorial (la de siempre)      #0E0D0C #F3EEE5 #FF5A1F #D4FF3A · Bricolage Grotesque');
      for(const x of list().filter(x=>x.slug!=='editorial'))console.log(`${x.slug.padEnd(20)} ${String(x.name).slice(0,30).padEnd(30)} ${x.colors.dark} ${x.colors.light} ${x.colors.accent} ${x.colors.accent2||''} · ${x.font||'-'}`);}
    else if(cmd==='show'){const b=loadBrand(slug);if(!b){console.log('editorial: el look de siempre del motor');process.exit(0);}
      const P=palette(b),f=b.fonts||{};console.log(`${b.name||slug}\n  colores: ink ${P.ink} · paper ${P.paper} · hot ${P.hot} · lime ${P.lime}`);
      console.log(`  tipografías: títulos ${(f.display||{}).family} · texto ${(f.body||{}).family} · etiquetas ${(f.mono||{}).family} · acento ${(f.accent||{}).family}`);
      console.log(`  subtítulos: activa ${captionColors(b).act} · estilo ${(captionStyle(b)||{style:'box'}).style}${captionStyle(b)?'':' (default; se cambia con "captions":{"style":…} en brand.json o config.caption_style)'}`);}
    else if(cmd==='detect'){const r=detect(slug||'.');if(!r){console.log('(sin marca detectada)');process.exit(2);}console.log(`${r.slug}\t${r.why}`);}
    else if(cmd==='remember'){if(arg3!=='editorial')loadBrand(arg3);const d=fs.statSync(slug).isDirectory()?slug:path.dirname(slug);
      fs.writeFileSync(path.join(d,'.marca'),arg3+'\n');console.log(`✓ ${path.join(d,'.marca')} → ${arg3}`);}
    else console.log('uso: node brand.js list | show <marca> | detect <carpeta> | remember <carpeta> <marca>');}
  catch(e){console.error('✗',e.message);process.exit(1);}}
