// Ejemplo real (video "sign spinner"). Cada bloque = un segmento de segs.json.
// ctx: J(id,escena,pista,inicio,fin,params[,sfx]) — sin sfx = diseño sonoro automático; 'pop' | 'bass-drop' | ['pop',['ding',1.2]] | null = manual (SKILL.md 4b)
//      F(seg,'punch'|'wide'|'tight'|'push'|'snap'|'pull') fuerza el encuadre (SKILL.md 4c)
//      S(sfx,segundo,{gain,dur}) sonido suelto de la librería · B(clave_broll,seg_origen,inicio,dur,[kb0,kb1]) · X(audio_abs,inicio,dur,gain,seg_origen)
//      W(seg,'palabra',n) · C(seg) inicio · CE(seg) fin · R(s,t) relativo · H(txt) resaltado
module.exports=({J,B,X,S,F,W,C,CE,R,H,cfg,edl,FPS})=>{
// La música (config.music) y su volumen (gancho fuerte → fondo bajo → cierre) los arma build_xml.py: no hace falta X().
// 0 · GANCHO: cara → b-roll kling del médico revoleando el cartel + sticker con flecha + música fuerte
{const k0=W(0,'tenes')-.05,e=CE(0);
 J('01_hook_medico','sticker','ov',C(0)+.05,k0,{kick:'SI SOS',text:'MÉDICO<br>ESPECIALISTA',size:130,y:260,aw:1},'pop');
 B('kl',0,k0,Math.min(4.03,e-k0));
 J('02_hook_loco','sticker','ov',k0,e,{kick:'SÍ, COMO ESTE',text:'LOCO',size:170,x:70,y:240,ax:230,ay:180,aw:260},'whoosh');}
// 1 · sello + foto con Ken Burns
{const s=C(1)+.05,e=CE(1),b0=W(1,'revolear')-.1;
 J('03_no_literal','stamp','ov',s,b0+.15,{kick:'OJO',text:'NO<br>LITERAL',at:R(s,W(1,'literal')),y:760},'hit');
 B('s1',0,b0,e-b0,[100,112]);}
{const s=C(2)+.05,e=CE(2)-.05;J('04_funcion','textcard','ov',s,e,{kick:'PERO SÍ ENTENDÉ',size:104,lines:['LA FUNCIÓN','DE ESTOS TIPOS',H('Y SUS CARTELES')],at:[R(s,W(2,'funcion'))-.2,R(s,W(2,'tipos'))-.3,R(s,W(2,'carteles'))-.2]},'pop');}
{const s=C(3)+.05,e=CE(4)-.05;J('05_su_funcion','listCard','ov',s,e,{kick:'SU FUNCIÓN',items:[{t:'Llamar la atención de las personas correctas',at:R(s,W(3,'llamar')),mark:'num'},{t:'Hacer que miren para donde vos querés',at:R(s,W(4,'hacer')),mark:'num'}]},'pop');}
{const s=C(5),e=CE(5);J('06_tu_contenido','fsTitle','fs',s,e,{kick:'ESO MISMO',lines:['DEBERÍA','HACER','<span style="color:var(--hot)">TU CONTENIDO</span>'],size:190,top:520},'whoosh');}
{const s=C(6)+.05,e=CE(8)-.05;J('07_seguro','listCard','ov',s,e,{kick:'ESTOY SEGURO DE QUE',items:[{t:'Sos excelente atendiendo',at:R(s,W(6,'excelente')),mark:'check'},{t:'Hiciste mil posgrados y cursos',at:R(s,W(7,'posgrados')),mark:'check'},{t:'Te seguís formando',at:R(s,W(7,'formando')),mark:'check'},{t:'Años de experiencia',at:R(s,W(8,'anos')),mark:'check'}]},['pop',['ding',R(s,W(6,'excelente'))],['ding',R(s,W(7,'posgrados'))],['ding',R(s,W(7,'formando'))],['ding',R(s,W(8,'anos'))]]);}
{const s=C(9)+.05,e=CE(9)-.05;J('08_problema','target','ov',s,e,{kick:'TU DIFERENCIAL',a:'Resolvés muy bien',b:'UN PROBLEMA',bs:104,c:'…particularmente uno.',precAt:R(s,W(9,'problema'))-.2,qAt:R(s,W(9,'particularmente'))},'pop');}
{const s=C(10),e=CE(10);J('09_jodido','bigword','fs',s,e,{kick:'PERO SI NADIE SABE QUE EXISTÍS',lines:['ESTÁS','JODIDO.'],size:260},'hit');}
{const s=C(11)+.05,e=CE(11)-.05;J('10_scroll','scroll','ov',s,e,{stopAt:R(s,W(11,'frenar'))},'whoosh');}
{const s=C(12)+.05,e=CE(13)-.05;J('11_tu_contenido_tiene','listCard','ov',s,e,{kick:'TU CONTENIDO TIENE QUE',items:[{t:'Frenar el scroll',at:.15,mark:'check'},{t:'Que el paciente se sienta identificado',at:R(s,W(12,'identificado'))-.3,mark:'check'},{t:'Mostrar en segundos que entendés lo que le pasa',at:R(s,W(13,'entendes'))-.2,mark:'check'}]},'pop');}
{const s=C(14)+.05,b0=W(14,'ay')-.1,e=CE(14);
 J('12_porque_si','textcard','ov',s,b0,{kick:'NO SE TRATA DE',size:100,lines:['LLAMAR LA','ATENCIÓN',H('PORQUE SÍ')],at:[.15,.25,R(s,W(14,'porque'))]},'pop');
 B('s3',0,b0,e-b0,[104,100]);
 J('13_lindo','sticker','ov',b0,e,{kick:'✕ NI DE',text:'“¡MIREN QUÉ<br>LINDO QUE SOY!”',size:96,y:1400,aw:1,bg:'var(--paper)'},null);}
{const s=C(15)+.05,e=CE(15)-.05;J('14_correctas','textcard','ov',s,e,{kick:'SE TRATA DE LLAMAR A',size:110,lines:['LAS PERSONAS',H('CORRECTAS'),'<span class="serif" style="text-transform:none;font-size:80px">y de forma estratégica</span>'],at:[.2,R(s,W(15,'correctas'))-.15,R(s,W(15,'estrategica'))-.3]},'pop');}
{const s=C(16)+.05,e=CE(16)-.05;J('15_encontrar','search','ov',s,e,{kick:'ANTES DE ELEGIRTE…',query:'médico especialista Palermo',typeAt:R(s,W(16,'decida')),pickAt:R(s,W(16,'encontrar')),youSub:'PRIMERO TE ENCONTRÓ'},'pop');}
// CTA: chat de DM y luego remate, con cola de 1.2 s (config.tail)
{const s=C(17)+.05,m=W(17,'para')-.1,e=CE(17)-.05;
 J('16_cta_mensaje','dm','ov',s,m,{opt:'ESCRIBIME',msg:'Hola Gus, te cuento mi caso',reply:'¡Dale! Lo vemos juntos',replyAt:R(s,W(17,'comentamos'))},'pop');
 J('17_cta_frena','textcard','ov',m,e,{kick:'VEAMOS JUNTOS',size:104,lines:['¿QUÉ TE ESTÁ','FRENANDO HOY?','<span class="serif" style="text-transform:none;font-size:70px">para que lleguen más pacientes</span>'],at:[R(m,W(17,'que'))-.1,R(m,W(17,'frenando'))-.1,R(m,W(17,'pacientes'))-.4]},'pop');}
};
