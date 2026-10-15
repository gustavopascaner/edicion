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
