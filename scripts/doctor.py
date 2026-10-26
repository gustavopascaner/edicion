#!/usr/bin/env python3
"""Chequea que esté todo lo necesario para la skill (macOS y Windows). Sale con código 1 si falta algo.
uso: python3 -I doctor.py      (Windows: py -3 -X utf8 -I doctor.py)
"""
import os as _o,sys as _s,subprocess as _sp
if _o.name=='nt' and __name__=='__main__' and not _s.flags.utf8_mode: _s.exit(_sp.run([_s.executable,'-X','utf8','-I',_o.path.abspath(__file__),*_s.argv[1:]]).returncode)  # Windows: acentos en UTF-8
import os,shutil,subprocess,sys,glob
SK=os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),'..'));WIN=os.name=='nt'
MODEL=os.path.expanduser('~/.cache/whisper-cpp/ggml-large-v3-turbo.bin')
WHISPER=os.environ.get('WHISPER_CLI') or shutil.which('whisper-cli') or os.path.join(os.environ.get('LOCALAPPDATA',''),'whisper-cpp','whisper-cli.exe')
FIX_MAC={'python':'xcode-select --install','ffmpeg':'brew install ffmpeg','whisper':'brew install whisper-cpp','node':'brew install node','chrome':'brew install --cask google-chrome',
         'deps':'bash scripts/install.sh','model':'bash scripts/install.sh','sfx':'bash scripts/install.sh <ruta>/edicion-sfx.zip'}
FIX_WIN={'python':'winget install Python.Python.3.12','ffmpeg':'winget install Gyan.FFmpeg','whisper':'powershell -ExecutionPolicy Bypass -File scripts\\install.ps1','node':'winget install OpenJS.NodeJS.LTS',
         'chrome':'winget install Google.Chrome','deps':'powershell -ExecutionPolicy Bypass -File scripts\\install.ps1','model':'powershell -ExecutionPolicy Bypass -File scripts\\install.ps1',
         'sfx':'powershell -ExecutionPolicy Bypass -File scripts\\install.ps1 <ruta>\\edicion-sfx.zip'}
FIX=FIX_WIN if WIN else FIX_MAC
def ver(cmd):
    try: return subprocess.run(cmd,capture_output=True,text=True,timeout=20).stdout.strip().splitlines()[0]
    except Exception: return None
def chrome():
    L=os.environ.get('LOCALAPPDATA','');PF=os.environ.get('ProgramFiles',r'C:\Program Files');PF86=os.environ.get('ProgramFiles(x86)',r'C:\Program Files (x86)')
    c=[os.environ.get('CHROME'),'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome','/Applications/Chromium.app/Contents/MacOS/Chromium',
       os.path.join(PF,'Google','Chrome','Application','chrome.exe'),os.path.join(PF86,'Google','Chrome','Application','chrome.exe'),os.path.join(L,'Google','Chrome','Application','chrome.exe'),
       os.path.join(PF86,'Microsoft','Edge','Application','msedge.exe'),'/usr/bin/google-chrome','/usr/bin/chromium']
    return next((p for p in c if p and os.path.exists(p)),None)
rows=[];bad=0
def row(ok,name,info,fix=None):
    global bad
    bad+=0 if ok else 1;rows.append(f"{'✓' if ok else '✗'} {name:24s} {info if ok else (info+'  →  '+FIX[fix] if fix else info)}")
row(sys.version_info>=(3,9),'Python 3.9+',sys.version.split()[0],'python')
v=ver(['ffmpeg','-version']);row(bool(v),'ffmpeg',v[:40] if v else 'no encontrado','ffmpeg')
v=ver(['ffprobe','-version']);row(bool(v),'ffprobe',v[:40] if v else 'no encontrado','ffmpeg')
w=WHISPER if os.path.exists(WHISPER or '') or shutil.which(WHISPER or '') else None;row(bool(w),'whisper-cli',w or 'no encontrado','whisper')
row(os.path.exists(MODEL) and os.path.getsize(MODEL)>1e9,'Modelo de Whisper',MODEL if os.path.exists(MODEL) else 'no descargado','model')
v=ver(['node','--version']);ok=bool(v) and int(v.lstrip('v').split('.')[0])>=18;row(ok,'Node 18+',v or 'no encontrado','node')
row(os.path.isdir(os.path.join(SK,'engine','node_modules','puppeteer-core')),'Dependencias de Node','engine/node_modules' if os.path.isdir(os.path.join(SK,'engine','node_modules','puppeteer-core')) else 'faltan','deps')
c=chrome();row(bool(c),'Google Chrome',c or 'no encontrado','chrome')
n=len(glob.glob(os.path.join(SK,'assets','sfx','*','*.wav')));row(n>0,'Efectos de sonido',f'{n} archivos' if n else 'faltan (edicion-sfx.zip)','sfx')
for d in ('~/.claude/skills/edicion','~/.codex/skills/edicion'):
    p=os.path.expanduser(d);rows.append(f"{'✓' if os.path.exists(os.path.join(p,'SKILL.md')) else '·'} {'Skill en '+d:24s} {'instalada' if os.path.exists(os.path.join(p,'SKILL.md')) else 'no instalada (opcional)'}")
BD=os.path.expanduser('~/.config/motion/brands');nb=sorted(x for x in os.listdir(BD) if os.path.exists(os.path.join(BD,x,'brand.json'))) if os.path.isdir(BD) else []
rows.append(f"{'✓' if nb else '·'} {'Marcas (de motion)':24s} {', '.join(nb) if nb else 'ninguna además de editorial (se crean con la skill motion)'}")
print('\n'.join(rows));print('\nTodo listo ✓' if not bad else f'\nFaltan {bad} cosa(s): correr los comandos indicados.');sys.exit(1 if bad else 0)
