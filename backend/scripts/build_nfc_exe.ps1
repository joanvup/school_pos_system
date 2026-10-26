<#
.SYNOPSIS
Compila y firma el ejecutable del lector NFC con PyInstaller.

.DESCRIPTION
Pasos:
  1. Verifica que el interprete y PyInstaller existan.
  2. Ejecuta PyInstaller con ACR122U_NFC.spec (incluye metadatos de version).
  3. Valida que el .exe se haya generado.
  4. Firma con scripts\sign_nfc_exe.ps1 (Authenticode SHA-256 + timestamp).

Requiere que la firma se haga con un certificado de firma de codigo confiable
(OV/EV con token/HSM o servicio en la nube). Use -SkipSign para compilar sin
firmar en un entorno sin certificado.

.EXAMPLE
.\build_nfc_exe.ps1 -Thumbprint 0123456789ABCDEF...

.EXAMPLE
.\build_nfc_exe.ps1 -PfxPath C:\certs\codesign.pfx

.EXAMPLE
.\build_nfc_exe.ps1 -SkipSign
#>
[CmdletBinding(DefaultParameterSetName = 'Store')]
param(
    [string]$Python = (Join-Path $PSScriptRoot '..\venv\Scripts\python.exe'),
    [string]$Spec = (Join-Path $PSScriptRoot '..\ACR122U_NFC.spec'),
    [string]$DistDir = (Join-Path $PSScriptRoot '..\dist'),
    [string]$WorkDir = (Join-Path $PSScriptRoot '..\build'),

    [Parameter(ParameterSetName = 'Store')]
    [string]$Thumbprint,

    [Parameter(ParameterSetName = 'Pfx', Mandatory = $true)]
    [string]$PfxPath,

    [Parameter(ParameterSetName = 'Pfx')]
    [Security.SecureString]$PfxPassword,

    [string]$TimestampUrl = 'http://timestamp.digicert.com',
    [switch]$SkipSign
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Write-Step {
    param([string]$Message)
    Write-Host "==> $Message" -ForegroundColor Cyan
}

$backendRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).ProviderPath

foreach ($path in @($Python, $Spec)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "No existe: $path"
    }
}
$Python = (Resolve-Path -LiteralPath $Python).ProviderPath
$Spec = (Resolve-Path -LiteralPath $Spec).ProviderPath

$pyInstallerVersion = & $Python -c "import PyInstaller; print(PyInstaller.__version__)" 2>&1
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller no esta instalado en $Python. Ejecute: $Python -m pip install -r requirements.txt"
}
Write-Step "Python: $Python"
Write-Host "    PyInstaller: $pyInstallerVersion" -ForegroundColor DarkGray
Write-Host "    Spec:        $Spec" -ForegroundColor DarkGray

if (-not $SkipSign -and -not $Thumbprint -and -not $PfxPath) {
    throw 'Indique -Thumbprint o -PfxPath para firmar, o use -SkipSign.'
}

Push-Location -LiteralPath $backendRoot
try {
    Write-Step 'Compilando con PyInstaller'
    & $Python -m PyInstaller --noconfirm --clean --distpath $DistDir --workpath $WorkDir $Spec
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller fallo con codigo $LASTEXITCODE."
    }
}
finally {
    Pop-Location
}

$exePath = Join-Path $DistDir 'ACR122U_NFC.exe'
if (-not (Test-Path -LiteralPath $exePath -PathType Leaf)) {
    throw "PyInstaller no genero el ejecutable esperado: $exePath"
}

$file = Get-Item -LiteralPath $exePath
Write-Step 'Ejecutable generado'
Write-Host "    Ruta:    $($file.FullName)" -ForegroundColor DarkGray
Write-Host "    Tamanio: $($file.Length) bytes" -ForegroundColor DarkGray
Write-Host "    Version: $($file.VersionInfo.FileVersion)" -ForegroundColor DarkGray

if ($SkipSign) {
    Write-Warning 'Compilacion sin firma (-SkipSign). No distribuir este ejecutable.'
    exit 0
}

$signScript = Join-Path $PSScriptRoot 'sign_nfc_exe.ps1'
$signParameters = @{
    ExePath      = $exePath
    TimestampUrl = $TimestampUrl
}
if ($PfxPath) {
    $signParameters['PfxPath'] = $PfxPath
    if ($PfxPassword) { $signParameters['PfxPassword'] = $PfxPassword }
} else {
    $signParameters['Thumbprint'] = $Thumbprint
}

Write-Step 'Firmando ejecutable'
& $signScript @signParameters
if (-not $?) {
    throw 'La firma del ejecutable fallo.'
}

Write-Step 'Compilacion y firma completadas'
