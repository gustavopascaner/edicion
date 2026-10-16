// ─────────────────────────────────────────────────────────────────────────────
// EJEMPLOS VIEJOS de animación conceptual (los 14 motivos que antes venían en engine.html).
// SOLO PARA APRENDER TÉCNICAS: cómo dibujar un trazo con dash(), cómo hacer aparecer con spop(),
// cómo sincronizar el momento clave con `a`, cómo mover partículas con semilla r().
// NO copiar ni reusar estas composiciones: cada video tiene su animación conceptual nueva en <work>/concept.js.
// render.js carga este archivo solo para ediciones viejas que todavía usan `motif` (el director lo marca ⚠️ reciclado).
// ─────────────────────────────────────────────────────────────────────────────
const MOT={};
MOT.growth=(g,p,a,D,r)=>{const n=p.n||5,base=820,x0=170,w=100,step=(660-w)/(n-1);
 sv('line',{x1:120,y1:base+10,x2:880,y2:base+10},g,`stroke:${SUB};stroke-width:8;stroke-linecap:round`);
 const hs=Array.from({length:n},(_,i)=>150+i*(470/(n-1))+(i&&i<n-1?(r()-.5)*60:0));
 const bars=hs.map((hh,i)=>sv('rect',{x:x0+i*step,y:base-hh,width:w,height:hh,rx:16},g,`fill:${i===n-1?HL:FG};opacity:${i===n-1?1:.85};transform-box:fill-box;transform-origin:50% 100%`));
 const pts=hs.map((hh,i)=>[x0+i*step+w/2,base-hh-55]);let L=0;for(let i=1;i<n;i++)L+=Math.hypot(pts[i][0]-pts[i-1][0],pts[i][1]-pts[i-1][1]);
 const ln=sv('polyline',{points:pts.map(q=>q.join(',')).join(' ')},g,`fill:none;stroke:${HL};stroke-width:12;stroke-linecap:round;stroke-linejoin:round`);
 const end=pts[n-1],dot=sv('circle',{cx:end[0],cy:end[1],r:26},g,`fill:${HL}`),rp=ripple(g,end[0],end[1]);
 return t=>{bars.forEach((b,i)=>{b.style.transform=`scaleY(${Math.max(0,E.back(P(t,.1+i*(Math.max(.4,a-.5)/n),.55)))})`;});dash(ln,L,E.io(P(t,a-.2,.8)));spop(dot,t,a+.55);rp(t,a+.7);};};
MOT.network=(g,p,a,D,r)=>{const N=p.n||7,C=[500,500],nodes=[C];for(let i=0;i<N-1;i++){const an=i/(N-1)*Math.PI*2-Math.PI/2+(r()-.5)*.35,rr=270+r()*90;nodes.push([500+Math.cos(an)*rr,500+Math.sin(an)*rr]);}
 const edges=[];for(let i=1;i<N;i++){edges.push([0,i]);edges.push([i,i%(N-1)+1]);}
 const ls=edges.map(([i,j])=>{const [x1,y1]=nodes[i],[x2,y2]=nodes[j];return {el:sv('line',{x1,y1,x2,y2},g,`stroke:${SUB};stroke-width:7;stroke-linecap:round`),L:Math.hypot(x2-x1,y2-y1),i,j}});
 const ns=nodes.map(([x,y],i)=>sv('circle',{cx:x,cy:y,r:i?34:58},g,`fill:${i?FG:HL}`));const rp=ripple(g,500,500);
 const ap=i=>.1+i*(Math.max(.5,a-.4)/N);
 return t=>{ns.forEach((n,i)=>spop(n,t,ap(i)));ls.forEach((o,k)=>{const s=Math.max(ap(o.i),ap(o.j))+.2;dash(o.el,o.L,E.o3(P(t,s,.4)));
   const on=t>=a+k*.04;o.el.style.stroke=on?HL:SUB;o.el.style.strokeWidth=on?9:7;});rp(t,a,1.2,180);};};
MOT.cycle=(g,p,a,D)=>{const R=300,grp=sv('g',{},g);sv('circle',{cx:500,cy:500,r:R},g,`fill:none;stroke:${SUB};stroke-width:6;stroke-dasharray:4 22;stroke-linecap:round`).parentNode.insertBefore(g.lastChild,grp);
 const arcs=[0,1,2].map(i=>{const a1=(i*120+12)*Math.PI/180,a2=(i*120+96)*Math.PI/180,pt=an=>[500+Math.cos(an)*R,500+Math.sin(an)*R];const [x1,y1]=pt(a1),[x2,y2]=pt(a2);
  const path=sv('path',{d:`M${x1},${y1} A${R},${R} 0 0 1 ${x2},${y2}`},grp,`fill:none;stroke:${FG};stroke-width:22;stroke-linecap:round`);
  const tx=-Math.sin(a2),ty=Math.cos(a2),nx=Math.cos(a2),ny=Math.sin(a2),hd=sv('path',{d:`M${x2+tx*40},${y2+ty*40} L${x2+nx*32},${y2+ny*32} L${x2-nx*32},${y2-ny*32} Z`},grp,`fill:${FG}`);
  return {path,hd,L:R*(84*Math.PI/180)}});
 const core=sv('circle',{cx:500,cy:500,r:90},g,`fill:${HL}`);const rp=ripple(g,500,500);
 return t=>{const sp=40+260*E.io(P(t,a,.9));const ang=t*40+260*Math.max(0,t-a)*E.io(P(t,a,.9))*.5;grp.setAttribute('transform',`rotate(${ang} 500 500)`);
  arcs.forEach((o,i)=>{dash(o.path,o.L,E.o3(P(t,.1+i*.15,.6)));o.hd.style.opacity=P(t,.55+i*.15,.1);const on=t>=a;o.path.style.stroke=on?HL:FG;o.hd.style.fill=on?HL:FG;});
  spop(core,t,.2);core.setAttribute('r',90+10*Math.sin(t*6)*(t>a));rp(t,a);};};
MOT.funnel=(g,p,a,D,r)=>{sv('path',{d:'M180,330 L820,330 L560,640 L560,720 L440,720 L440,640 Z'},g,`fill:none;stroke:${FG};stroke-width:12;stroke-linejoin:round;opacity:.9`);
 const N=26,keep=new Set([5,13,21]);const ps=Array.from({length:N},(_,i)=>{const k=keep.has(i);return {x0:230+r()*540,d:k?Math.max(.2,a-1.2)+[...keep].indexOf(i)*.25:.15+r()*Math.max(.6,D-1.6),k,el:sv('circle',{r:k?20:15},g,`fill:${k?HL:FG}`)}});
 return t=>{ps.forEach(o=>{const q=P(t,o.d,1.1),y=L(-40,640,Math.pow(q,1.5)),x=y<330?o.x0:L(o.x0,500,(y-330)/310);
   let X=x,Y=y,op=q>0?1:0;if(q>=1){if(o.k){const q2=E.o3(P(t,o.d+1.1,.6));Y=L(640,880,q2);X=500;}else op=1-P(t,o.d+1.05,.15);}
   o.el.setAttribute('cx',X);o.el.setAttribute('cy',Y);o.el.style.opacity=op;});};};
MOT.target=(g,p,a,D)=>{const rings=[380,285,190,100].map((rr,i)=>sv('circle',{cx:500,cy:500,r:rr},g,`fill:none;stroke:${FG};stroke-width:14;opacity:.85`));
 const ctr=sv('circle',{cx:500,cy:500,r:44},g,`fill:${HL}`);const dart=sv('g',{},g);sv('line',{x1:-170,y1:0,x2:0,y2:0},dart,`stroke:${HL};stroke-width:14;stroke-linecap:round`);
 sv('path',{d:'M10,0 L-40,-26 L-40,26 Z'},dart,`fill:${HL}`);const rp=ripple(g,500,500),rp2=ripple(g,500,500);
 return t=>{rings.forEach((c,i)=>spop(c,t,.05+i*.12,.5));spop(ctr,t,.5);const q=E.o3(P(t,a-.45,.45));const x=L(-150,500,q),y=L(1150,500,q);
  dart.setAttribute('transform',`translate(${x},${y}) rotate(${-50})`);dart.style.opacity=t>=a-.45?1:0;
  const sh=t>a&&t<a+.3?Math.sin((t-a)*80)*8*(1-(t-a)/.3):0;rings.forEach((c,i)=>{c.style.stroke=t>=a&&t<a+.25+i*.06?HL:FG;});g.style.transform=`translate(${sh}px,0)`;rp(t,a,1.4,220);rp2(t,a+.35,1.4,220);};};
MOT.balance=(g,p,a,D)=>{sv('path',{d:'M500,640 L430,800 L570,800 Z'},g,`fill:${FG}`);sv('line',{x1:330,y1:812,x2:670,y2:812},g,`stroke:${FG};stroke-width:12;stroke-linecap:round`);
 const beam=sv('g',{},g);sv('line',{x1:180,y1:640,x2:820,y2:640},beam,`stroke:${FG};stroke-width:16;stroke-linecap:round`);
 const L1=sv('g',{},beam),R1=sv('g',{},beam);[L1,R1].forEach((G,k)=>{const x=k?800:200;sv('line',{x1:x,y1:640,x2:x,y2:540},G,`stroke:${FG};stroke-width:6`);});
 sv('rect',{x:140,y:420,width:120,height:120,rx:20},L1,`fill:${HL}`);sv('circle',{cx:800,cy:480,r:62},R1,`fill:${FG}`);const piv=sv('circle',{cx:500,cy:640,r:22},g,`fill:${HL}`);
 return t=>{const ang=t<a?-14+Math.sin(t*3.2)*4:L(-14+Math.sin(a*3.2)*4,0,E.el(P(t,a,1.4)));beam.setAttribute('transform',`rotate(${ang} 500 640)`);
  [L1,R1].forEach((G,k)=>{const x=k?800:200;G.setAttribute('transform',`rotate(${-ang} ${x} 640)`);});spop(beam,t,.05,.5,E.o3);spop(piv,t,.2);};};
MOT.breakthrough=(g,p,a,D,r)=>{const br=[];for(let row=0;row<6;row++)for(let col=0;col<2;col++){const x=560+col*90+(row%2?45:0),y=230+row*92;br.push({x,y,el:sv('rect',{x,y,width:84,height:84,rx:10},g,`fill:${FG}`),dx:(r()*.8+.4)*420,dy:(r()-.5)*700,rot:(r()-.5)*260});}
 const trail=sv('line',{x1:0,y1:500,x2:0,y2:500},g,`stroke:${HL};stroke-width:10;stroke-linecap:round;opacity:.5`);const ball=sv('circle',{cx:150,cy:500,r:58},g,`fill:${HL}`);const rp=ripple(g,790,500);
 return t=>{br.forEach((b,i)=>{const q=E.o3(P(t,a,1));b.el.style.transformBox='fill-box';b.el.style.transformOrigin='center';
   const pop=E.back(P(t,.05+i*.04,.4));b.el.style.transform=`translate(${q*b.dx}px,${q*b.dy}px) rotate(${q*b.rot}deg) scale(${pop})`;b.el.style.opacity=(1-P(t,a+.4,.6))*P(t,.05+i*.04,.05);});
  const x=t<a?L(150,500,E.i3?E.i3(P(t,.4,a-.4)):Math.pow(P(t,.4,a-.4),3)):L(500,790,E.o3(P(t,a,.6)));ball.setAttribute('cx',x);spop(ball,t,.25);
  trail.setAttribute('x1',Math.max(150,x-220*P(t,.6,.3)));trail.setAttribute('x2',x);rp(t,a+.6);};};
MOT.order=(g,p,a,D,r)=>{const ds=Array.from({length:25},(_,i)=>({x:150+r()*700,y:150+r()*700,gx:260+(i%5)*120,gy:260+Math.floor(i/5)*120,ph:r()*6,el:sv('circle',{r:26},g,`fill:${FG}`)}));
 return t=>{ds.forEach((o,i)=>{const q=E.io(P(t,a+i*.025,.9));const jx=Math.sin(t*3+o.ph)*14*(1-q),jy=Math.cos(t*2.6+o.ph)*14*(1-q);
  o.el.setAttribute('cx',L(o.x,o.gx,q)+jx);o.el.setAttribute('cy',L(o.y,o.gy,q)+jy);o.el.style.fill=q>=1&&t>=a+.9+i*.02?HL:FG;o.el.style.opacity=L(.6,1,q)*P(t,.05+i*.015,.15);});};};
MOT.pulse=(g,p,a,D)=>{const d='M60,600 L300,600 L330,560 L360,600 L400,600 L440,330 L490,800 L530,600 L600,600 L630,540 L660,600 L940,600';
 const ln=sv('path',{d},g,`fill:none;stroke:${HL};stroke-width:12;stroke-linejoin:round;stroke-linecap:round`);const Lp=ln.getTotalLength?ln.getTotalLength()||1500:1500;
 const hg=sv('g',{},g),hp=sv('path',{d:'M0,30 C-60,-10 -60,-60 -25,-70 C-5,-75 0,-60 0,-50 C0,-60 5,-75 25,-70 C60,-60 60,-10 0,30 Z'},hg,`fill:${FG}`);
 return t=>{dash(ln,Lp,P(t,.1,Math.max(.8,a+.5)));const beats=[a,a+.75,a+1.5,a+2.25];let bump=0;beats.forEach(b=>{const q=t-b;if(q>=0&&q<.35)bump=Math.max(bump,Math.sin(q/.35*Math.PI));});
  const sc=2.4*(E.back(P(t,.1,.5)))*(1+.2*bump);hg.setAttribute('transform',`translate(500,250) scale(${Math.max(0,sc)})`);hp.style.fill=t>=a?HL:FG;};};
MOT.path=(g,p,a,D)=>{const d='M140,830 C320,830 260,560 470,560 S720,330 860,200';sv('path',{d},g,`fill:none;stroke:${SUB};stroke-width:10;stroke-dasharray:2 26;stroke-linecap:round`);
 const ln=sv('path',{d},g,`fill:none;stroke:${HL};stroke-width:14;stroke-linecap:round`);const Lp=ln.getTotalLength?ln.getTotalLength()||1200:1200;
 const st=sv('circle',{cx:140,cy:830,r:30},g,`fill:${FG}`);const mk=sv('circle',{r:34},g,`fill:${HL}`);
 const fl=sv('g',{},g);sv('line',{x1:860,y1:200,x2:860,y2:60},fl,`stroke:${FG};stroke-width:10;stroke-linecap:round`);sv('path',{d:'M860,60 L960,95 L860,130 Z'},fl,`fill:${HL}`);const rp=ripple(g,860,200);
 return t=>{spop(st,t,.05);const x=E.io(P(t,.2,Math.max(.8,a)));dash(ln,Lp,x);const pt=ln.getPointAtLength(Lp*x);mk.setAttribute('cx',pt.x);mk.setAttribute('cy',pt.y);mk.style.opacity=P(t,.2,.1);
  fl.style.transformBox='fill-box';fl.style.transformOrigin='0% 100%';fl.style.transform=`scaleY(${Math.max(0,E.back(P(t,a+.15,.5)))})`;rp(t,a+.2);};};
MOT.attract=(g,p,a,D,r)=>{const core=sv('circle',{cx:500,cy:500,r:80},g,`fill:${HL}`);const N=30;const ps=Array.from({length:N},()=>{const an=r()*Math.PI*2,rr=230+r()*240;
 return {x:500+Math.cos(an)*rr,y:500+Math.sin(an)*rr,d:.3+r()*Math.max(.6,a+.6),ph:r()*6,el:sv('circle',{r:12+r()*12},g,`fill:${FG}`)}});const rp=ripple(g,500,500);
 return t=>{let got=0;ps.forEach(o=>{const q=Math.pow(P(t,o.d,.9),2.2);const dx=Math.sin(t*2+o.ph)*10*(1-q);o.el.setAttribute('cx',L(o.x,500,q)+dx);o.el.setAttribute('cy',L(o.y,500,q));
   o.el.style.opacity=P(t,.05,.3)*(q>=1?0:1);if(q>=1)got++;});spop(core,t,.1);core.setAttribute('r',80+got*2.2);rp(t,a,1,160);};};
MOT.dialog=(g,p,a,D)=>{const A=sv('circle',{cx:230,cy:540,r:110},g,`fill:${FG}`),B=sv('circle',{cx:770,cy:540,r:110},g,`fill:${HL}`);
 const waves=Array.from({length:8},(_,i)=>sv('path',{d:'M0,-120 Q70,0 0,120'},g,`fill:none;stroke:${FG};stroke-width:18;stroke-linecap:round;opacity:0`));
 const hg=sv('g',{},g);sv('path',{d:'M0,30 C-60,-10 -60,-60 -25,-70 C-5,-75 0,-60 0,-50 C0,-60 5,-75 25,-70 C60,-60 60,-10 0,30 Z'},hg,`fill:${HL}`);
 return t=>{spop(A,t,.05);spop(B,t,.2);waves.forEach((w,i)=>{const back=i>=4,st=back?a+(i-4)*.2:.3+i*.22,q=P(t,st,.8);const x=back?L(650,350,q):L(350,650,q);
   w.setAttribute('transform',`translate(${x},540) scale(${back?-1:1},${L(.7,1.1,Math.sin(q*Math.PI))})`);w.style.opacity=q>0&&q<1?Math.min(1,Math.sin(q*Math.PI)*1.6):0;w.style.stroke=back?HL:FG;});
  const hq=E.back(P(t,a+.7,.5));hg.setAttribute('transform',`translate(500,330) scale(${Math.max(0,hq)*1.6})`);};};
MOT.split=(g,p,a,D)=>{const T='M500,900 L500,620',Lb='M500,620 C500,450 260,420 240,200',Rb='M500,620 C500,450 740,420 760,200';
 const tr=sv('path',{d:T},g,`fill:none;stroke:${FG};stroke-width:16;stroke-linecap:round`),lb=sv('path',{d:Lb},g,`fill:none;stroke:${FG};stroke-width:16;stroke-linecap:round`),rb=sv('path',{d:Rb},g,`fill:none;stroke:${FG};stroke-width:16;stroke-linecap:round`);
 const lt=lb.getTotalLength?lb.getTotalLength()||520:520;const n1=sv('circle',{cx:240,cy:200,r:40},g,`fill:${FG}`),n2=sv('circle',{cx:760,cy:200,r:48},g,`fill:${HL}`);const mk=sv('circle',{r:30},g,`fill:${HL}`);const rp=ripple(g,760,200);
 return t=>{dash(tr,280,E.o3(P(t,.05,.45)));dash(lb,lt,E.o3(P(t,.45,.55)));dash(rb,lt,E.o3(P(t,.45,.55)));spop(n1,t,.95);spop(n2,t,.95);
  const dim=E.o3(P(t,a,.4));lb.style.opacity=n1.style.opacity=String(L(1,.25,dim));rb.style.stroke=t>=a?HL:FG;rb.style.strokeWidth=t>=a?20:16;
  const q=E.io(P(t,a-.3,1.1));let pt;if(q<.35)pt={x:500,y:L(900,620,q/.35)};else pt=rb.getPointAtLength(lt*(q-.35)/.65);mk.setAttribute('cx',pt.x);mk.setAttribute('cy',pt.y);mk.style.opacity=t>=a-.3?1:0;rp(t,a+.8);};};
MOT.stack=(g,p,a,D)=>{const n=p.n||6,ws=Array.from({length:n},(_,i)=>440-i*40),bs=ws.map((w,i)=>sv('rect',{x:500-w/2,y:0,width:w,height:84,rx:14},g,`fill:${i===n-1?HL:FG}`));
 sv('line',{x1:180,y1:872,x2:820,y2:872},g,`stroke:${SUB};stroke-width:8;stroke-linecap:round`);const topY=860-n*90+84;const rp=ripple(g,500,topY-20);
 return t=>{bs.forEach((b,i)=>{const st=.1+i*(Math.max(.6,a-.1)/n),q=P(t,st,.5),y=860-(i+1)*90+6;const yy=q<1?L(-120,y,Math.pow(q,2)):y-Math.max(0,Math.sin((t-st-.5)*14)*14*(1-P(t,st+.5,.35)));
   b.setAttribute('y',yy);b.style.opacity=q>0?1:0;});rp(t,a+.4);};};
window.CONCEPT_LEGACY=MOT;
