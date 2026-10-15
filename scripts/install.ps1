# Instala la skill "edicion" en Windows para Codex y Claude Code, con todo lo que necesita.
# uso (PowerShell, desde la carpeta clonada del repo):
#   powershell -ExecutionPolicy Bypass -File scripts\install.ps1 [ruta\a\edicion-sfx.zip]
# Instala con winget lo que falte: Git, Python 3, Node LTS, FFmpeg y Google Chrome; whisper.cpp (binario oficial)
# y el modelo de Whisper; las dependencias de Node; los efectos de sonido; y enlaza la skill en ~/.codex y ~/.claude.
param([string]$SfxZip = "")
$ErrorActionPreference = "Stop"
$SK = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
function Ok($m)   { Write-Host "OK  $m" -ForegroundColor Green }
function Info($m) { Write-Host "... $m" -ForegroundColor Cyan }
function Warn($m) { Write-Host "!!  $m" -ForegroundColor Yellow }
function Refresh-Path { $env:Path = [Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [Environment]::GetEnvironmentVariable("Path","User") }
function Has($cmd) { [bool](Get-Command $cmd -ErrorAction SilentlyContinue) }

if (-not (Has "winget")) { Warn "Falta winget (App Installer). Instalalo desde Microsoft Store: 'App Installer', y volvé a correr este script."; exit 1 }
$W = @("--exact","--silent","--accept-package-agreements","--accept-source-agreements")

# 1 · Programas base
$pkgs = @(
  @{cmd="git";    id="Git.Git";               name="Git"},
  @{cmd="py";     id="Python.Python.3.12";    name="Python 3"},
  @{cmd="node";   id="OpenJS.NodeJS.LTS";     name="Node.js LTS"},
  @{cmd="ffmpeg"; id="Gyan.FFmpeg";           name="FFmpeg"}
)
foreach ($p in $pkgs) {
  if (Has $p.cmd) { Ok "$($p.name) ya instalado" }
  else { Info "Instalando $($p.name)..."; winget install --id $p.id @W | Out-Null; Refresh-Path; if (Has $p.cmd) { Ok $p.name } else { Warn "$($p.name): instalado, pero hace falta abrir una terminal nueva para usarlo" } }
}
$chrome = @("$env:ProgramFiles\Google\Chrome\Application\chrome.exe","${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe","$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
if ($chrome) { Ok "Google Chrome ya instalado" } else { Info "Instalando Google Chrome..."; winget install --id Google.Chrome @W | Out-Null; Ok "Google Chrome" }

# 2 · whisper.cpp (binario oficial para Windows) en %LOCALAPPDATA%\whisper-cpp
$WD = Join-Path $env:LOCALAPPDATA "whisper-cpp"
if ((Has "whisper-cli") -or (Test-Path (Join-Path $WD "whisper-cli.exe"))) { Ok "whisper.cpp ya instalado" }
else {
  Info "Descargando whisper.cpp..."
  $asset = if ($env:PROCESSOR_ARCHITECTURE -eq "ARM64") { "whisper-bin-win-cpu-arm64.zip" } else { "whisper-bin-x64.zip" }
  $rels = Invoke-RestMethod "https://api.github.com/repos/ggml-org/whisper.cpp/releases?per_page=15" -Headers @{ "User-Agent" = "edicion-skill" }
  $url = ($rels | ForEach-Object { $_.assets } | Where-Object { $_.name -eq $asset } | Select-Object -First 1).browser_download_url
  if (-not $url) { Warn "No encontré $asset en las versiones de whisper.cpp"; exit 1 }
  $zip = Join-Path $env:TEMP $asset; $tmp = Join-Path $env:TEMP "whisper-cpp-unzip"
  Invoke-WebRequest $url -OutFile $zip -UseBasicParsing
  if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force }
  Expand-Archive $zip -DestinationPath $tmp -Force
  $exe = Get-ChildItem $tmp -Recurse -Filter "whisper-cli.exe" | Select-Object -First 1
  New-Item -ItemType Directory -Force -Path $WD | Out-Null
  Copy-Item (Join-Path $exe.DirectoryName "*") $WD -Recurse -Force
  Remove-Item $tmp -Recurse -Force; Remove-Item $zip -Force
  $up = [Environment]::GetEnvironmentVariable("Path","User")
  if ($up -notlike "*$WD*") { [Environment]::SetEnvironmentVariable("Path", "$up;$WD", "User") }
  Refresh-Path; Ok "whisper.cpp en $WD"
}

# 3 · Modelo de Whisper (~1,6 GB)
$M = Join-Path $HOME ".cache\whisper-cpp\ggml-large-v3-turbo.bin"
if ((Test-Path $M) -and ((Get-Item $M).Length -gt 1GB)) { Ok "Modelo de Whisper ya descargado" }
else {
  Info "Descargando el modelo de Whisper (~1,6 GB, tarda unos minutos)..."
  New-Item -ItemType Directory -Force -Path (Split-Path $M) | Out-Null
  curl.exe -L --fail -o $M "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo.bin"
  Ok "Modelo de Whisper"
}

# 4 · Dependencias de Node del motor de gráficos
Info "Instalando dependencias de Node..."
Push-Location (Join-Path $SK "engine"); npm ci --silent; Pop-Location; Ok "Dependencias de Node"

# 5 · Efectos de sonido
if ($SfxZip) { Expand-Archive $SfxZip -DestinationPath (Join-Path $SK "assets\sfx") -Force; Ok "Efectos de sonido instalados" }
elseif (-not (Get-ChildItem (Join-Path $SK "assets\sfx") -Recurse -Filter *.wav -ErrorAction SilentlyContinue)) { Warn "Faltan los efectos de sonido: volvé a correr con la ruta a edicion-sfx.zip" }

# 6 · Enlazar la skill para Codex y Claude Code (junction: no requiere permisos de administrador)
foreach ($d in @("$HOME\.codex\skills", "$HOME\.claude\skills")) {
  New-Item -ItemType Directory -Force -Path $d | Out-Null
  $link = Join-Path $d "edicion"
  if (Test-Path $link) {
    $it = Get-Item $link -Force
    if ($it.LinkType) { Remove-Item $link -Force } else { Warn "$link ya existe y no es un enlace: lo dejo como está"; continue }
  }
  New-Item -ItemType Junction -Path $link -Target $SK | Out-Null; Ok "Skill enlazada en $link"
}

# 7 · Chequeo final
Write-Host ""
py -3 -I (Join-Path $SK "scripts\doctor.py")
Write-Host ""
Write-Host "Listo. En Codex: `$edicion <video>   ·   En Claude Code: /edicion <video>"
Write-Host "Si algo figura con una X, cerrá y abrí la terminal y volvé a correr este script."
