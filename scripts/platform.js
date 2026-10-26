// Utilidades multiplataforma (macOS / Windows / Linux) para render.js y director.js
const fs=require('fs'),path=require('path'),{pathToFileURL}=require('url'),os=require('os');
const L=process.env.LOCALAPPDATA||'',PF=process.env.ProgramFiles||'C:\\Program Files',PF86=process.env['ProgramFiles(x86)']||'C:\\Program Files (x86)';
// Chrome/Chromium: variable CHROME o rutas habituales
exports.CHROME=process.env.CHROME||[
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome','/Applications/Chromium.app/Contents/MacOS/Chromium',
  path.join(PF,'Google','Chrome','Application','chrome.exe'),path.join(PF86,'Google','Chrome','Application','chrome.exe'),path.join(L,'Google','Chrome','Application','chrome.exe'),
  path.join(PF86,'Microsoft','Edge','Application','msedge.exe'),
  '/usr/bin/google-chrome','/usr/bin/chromium','/usr/bin/chromium-browser'].find(p=>p&&fs.existsSync(p));
exports.fileURL=p=>pathToFileURL(p).href;
// Cronómetro: mismo formato que timing.py (<work>/timing.json)
exports.logTime=(WD,step,secs)=>{try{const f=path.join(WD,'timing.json');let d={start:null,steps:[]};
  try{d=JSON.parse(fs.readFileSync(f,'utf8'));}catch(e){}
  d.steps.push({step,secs:+secs.toFixed(1),at:Math.round(Date.now()/1000)});fs.writeFileSync(f,JSON.stringify(d,null,1));}catch(e){}};
// Perfil de hardware: 'potente' (≥ 12 GB de RAM, ej. Mac M) o 'liviano' (notebooks de 8 GB, ej. la Windows de Javier).
// Se puede forzar con --perfil=liviano|potente, EDICION_PERFIL o "perfil" en config.json.
exports.perfil=(cfg={})=>{const ram=os.totalmem()/2**30,cpu=os.cpus().length;
  const arg=(process.argv.find(a=>a.startsWith('--perfil='))||'').slice(9);
  const name=arg||process.env.EDICION_PERFIL||cfg.perfil||(ram<12?'liviano':'potente');
  const tabs=Math.max(1,Math.floor(ram/2.4));   // ~2,4 GB por pestaña de Chrome a 1080×1920
  return name==='liviano'
    // liviano: pocas pestañas, PNG comprimido (menos RAM y menos tráfico) y paciencia con capturas lentas
    ? {name,ram,cpu,par:Math.max(2,Math.min(3,tabs)),fastShot:false,protocolTimeout:900000}
    // potente: 6 pestañas y captura rápida (sin optimizeForSpeed un cuadro con grano tarda 2,2× más en una M5 Pro)
    : {name,ram,cpu,par:Math.max(2,Math.min(6,tabs)),fastShot:true,protocolTimeout:180000};};
