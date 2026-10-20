$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot
python scripts/render_icon.py
if ($LASTEXITCODE) { throw 'Icon build failed' }
python scripts/render_version_info.py
if ($LASTEXITCODE) { throw 'Version build failed' }
python -m PyInstaller --noconfirm packaging/CodexLoop.spec
if ($LASTEXITCODE) { throw 'Application build failed' }
$version = python -c "from sentinel.product import PRODUCT; print(PRODUCT.version)"
$payload = Join-Path $repoRoot 'dist/CodexLoop' 
Copy-Item LICENSE,NOTICE.md,THIRD_PARTY_NOTICES.md -Destination $payload -Force
Copy-Item licenses -Destination $payload -Recurse -Force
& (Join-Path $payload 'CodexLoop.exe') --help
if ($LASTEXITCODE) { throw 'Packaged executable startup failed' }
$compiler = @(
  "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
  "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
  "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
) | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $compiler) { throw 'Inno Setup compiler missing on runner' }
& $compiler packaging/CodexLoop.iss
if ($LASTEXITCODE) { throw 'Setup build failed' }
$hash=(Get-FileHash dist/CodexLoop-Setup.exe -Algorithm SHA256).Hash.ToLowerInvariant()
Set-Content dist/CodexLoop-Setup.exe.sha256 "$hash  CodexLoop-Setup.exe" -Encoding ascii
Compress-Archive -LiteralPath $payload -DestinationPath "dist/CodexLoop-$version-windows-x64.zip" -Force
python scripts/package-release.py
if ($LASTEXITCODE) { throw 'Release assets failed' }
