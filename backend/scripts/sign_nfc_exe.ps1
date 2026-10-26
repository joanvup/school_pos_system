<#
.SYNOPSIS
Firma y verifica Authenticode el ejecutable del lector NFC (ACR122U_NFC.exe).

.DESCRIPTION
Usa signtool.exe si esta disponible (Windows SDK); si no, cae a
Set-AuthenticodeSignature. Firma con SHA-256 y sello de tiempo (RFC 3161 con
signtool).

El certificado puede estar en el almacen del usuario actual (-Thumbprint) o
en un PFX (-PfxPath). Un PFX se importa temporalmente al almacen del usuario y
se elimina al terminar, para no exponer la contrasena en la linea de comandos.
Si el PFX no tiene contrasena, omita -PfxPassword.

Al final escribe <exe>.sha256 con el hash del archivo firmado.

.PARAMETER AllowUntrusted
Solo para pruebas con un certificado autofirmado: acepta una verificacion
"UnknownError" (raiz no confiable). Nunca usar para distribuir el ejecutable.

.EXAMPLE
# Certificado instalado en Cert:\CurrentUser\My
.\sign_nfc_exe.ps1 -Thumbprint 0123456789ABCDEF...

.EXAMPLE
# PFX con contrasena (se captura de forma segura)
$pwd = Read-Host -AsSecureString
.\sign_nfc_exe.ps1 -PfxPath .\certificado.pfx -PfxPassword $pwd

.EXAMPLE
# Verificar una firma existente
.\sign_nfc_exe.ps1 -VerifyOnly
#>
[CmdletBinding(DefaultParameterSetName = 'Store')]
param(
    [string]$ExePath = (Join-Path $PSScriptRoot '..\dist\ACR122U_NFC.exe'),

    [Parameter(ParameterSetName = 'Store')]
    [string]$Thumbprint,

    [Parameter(ParameterSetName = 'Pfx', Mandatory = $true)]
    [string]$PfxPath,

    [Parameter(ParameterSetName = 'Pfx')]
    [Security.SecureString]$PfxPassword,

    [string]$TimestampUrl = 'http://timestamp.digicert.com',

    [switch]$VerifyOnly,
    [switch]$NoTimestamp,
    [switch]$AllowUntrusted
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$CodeSigningEku = '1.3.6.1.5.5.7.3.3'

function Write-Step {
    param([string]$Message)
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Resolve-FullPath {
    param([string]$Path, [string]$Label)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "$Label no existe: $Path"
    }
    return (Resolve-Path -LiteralPath $Path).ProviderPath
}

function Find-SignTool {
    $command = Get-Command signtool.exe -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }

    $roots = @(
        "${env:ProgramFiles(x86)}\Windows Kits\10\bin",
        "$env:ProgramFiles\Windows Kits\10\bin",
        "${env:ProgramFiles(x86)}\Windows Kits\8.1\bin",
        "$env:ProgramFiles\Windows Kits\8.1\bin"
    )

    foreach ($root in $roots) {
        if (-not (Test-Path -LiteralPath $root)) { continue }
        $candidate = Get-ChildItem -LiteralPath $root -Recurse -Filter 'signtool.exe' -ErrorAction SilentlyContinue |
            Where-Object { $_.FullName -match '\\x64\\' } |
            Sort-Object FullName -Descending |
            Select-Object -First 1
        if ($candidate) { return $candidate.FullName }
    }
    return $null
}

function Get-StoreCertificate {
    param([string]$Thumb)
    $normalized = ($Thumb -replace '\s', '').ToUpperInvariant()
    $cert = Get-ChildItem -Path 'Cert:\CurrentUser\My' -ErrorAction SilentlyContinue |
        Where-Object { $_.Thumbprint -eq $normalized } |
        Select-Object -First 1
    if (-not $cert) {
        throw "No se encontro el certificado $normalized en Cert:\CurrentUser\My"
    }
    return $cert
}

function Get-EkuOids {
    param([System.Security.Cryptography.X509Certificates.X509Certificate2]$Certificate)

    $values = @()
    foreach ($usage in $Certificate.EnhancedKeyUsageList) {
        foreach ($name in @('ObjectId', 'Value')) {
            $property = $usage.PSObject.Properties[$name]
            if ($property -and $property.Value) {
                $values += [string]$property.Value
                break
            }
        }
    }
    return $values
}

function Assert-CodeSigningCertificate {
    param([System.Security.Cryptography.X509Certificates.X509Certificate2]$Certificate)

    if (-not $Certificate.HasPrivateKey) {
        throw "El certificado $($Certificate.Thumbprint) no tiene clave privada disponible."
    }
    if ($Certificate.NotAfter -lt (Get-Date)) {
        throw "El certificado $($Certificate.Thumbprint) expiro el $($Certificate.NotAfter)."
    }
    $eku = @(Get-EkuOids -Certificate $Certificate)
    if ($eku.Count -gt 0 -and $eku -notcontains $CodeSigningEku) {
        throw "El certificado $($Certificate.Thumbprint) no es de firma de codigo (EKU $CodeSigningEku)."
    }
    Write-Host "    Certificado: $($Certificate.Subject)" -ForegroundColor DarkGray
    Write-Host "    Huella:      $($Certificate.Thumbprint)" -ForegroundColor DarkGray
    Write-Host "    Vence:       $($Certificate.NotAfter)" -ForegroundColor DarkGray
}

function Invoke-SignToolSign {
    param([string]$SignTool, [string]$File, [string]$Thumb)

    $arguments = @('sign', '/fd', 'SHA256', '/sha1', $Thumb, '/v')
    if (-not $NoTimestamp) {
        $arguments += @('/tr', $TimestampUrl, '/td', 'SHA256')
    }
    $arguments += $File

    & $SignTool @arguments
    if ($LASTEXITCODE -ne 0) {
        throw "signtool sign fallo con codigo $LASTEXITCODE."
    }
}

function Invoke-PowerShellSign {
    param(
        [System.Security.Cryptography.X509Certificates.X509Certificate2]$Certificate,
        [string]$File
    )

    $parameters = @{
        FilePath      = $File
        Certificate   = $Certificate
        HashAlgorithm = 'SHA256'
    }
    if (-not $NoTimestamp) {
        $parameters['TimestampServer'] = $TimestampUrl
    }

    $result = Set-AuthenticodeSignature @parameters
    Write-Host "    Estado de la firma: $($result.Status)" -ForegroundColor DarkGray

    if ($result.Status -eq 'Valid') { return }
    if ($AllowUntrusted -and $result.Status -eq 'UnknownError') {
        Write-Warning "Firma creada con certificado no confiable (solo valido para pruebas)."
        return
    }
    throw "Set-AuthenticodeSignature devolvio estado $($result.Status): $($result.StatusMessage)"
}

function Test-Signature {
    param([string]$SignTool, [string]$File)

    if ($SignTool) {
        & $SignTool verify /pa /v $File | Out-Host
        return ($LASTEXITCODE -eq 0)
    }

    $signature = Get-AuthenticodeSignature -LiteralPath $File
    Write-Host "    Estado: $($signature.Status) - $($signature.StatusMessage)" -ForegroundColor DarkGray
    return ($signature.Status -eq 'Valid')
}

function Write-HashSidecar {
    param([string]$File)
    $hash = (Get-FileHash -LiteralPath $File -Algorithm SHA256).Hash.ToLowerInvariant()
    $sidecar = "$File.sha256"
    "$hash  $(Split-Path -Leaf $File)" | Set-Content -LiteralPath $sidecar -Encoding ASCII
    Write-Host "    SHA-256: $hash" -ForegroundColor Green
    Write-Host "    Archivo: $sidecar" -ForegroundColor DarkGray
    return $hash
}

$ExePath = Resolve-FullPath -Path $ExePath -Label 'Ejecutable'
$signTool = Find-SignTool
Write-Step "Ejecutable: $ExePath"
Write-Host "    Tamanio: $((Get-Item -LiteralPath $ExePath).Length) bytes" -ForegroundColor DarkGray
if ($signTool) {
    Write-Host "    signtool: $signTool" -ForegroundColor DarkGray
} else {
    Write-Host "    signtool: no encontrado (se usara Set-AuthenticodeSignature)" -ForegroundColor Yellow
}

if ($VerifyOnly) {
    Write-Step 'Verificando firma existente'
    $valid = Test-Signature -SignTool $signTool -File $ExePath
    if (-not $valid) {
        $current = Get-AuthenticodeSignature -LiteralPath $ExePath
        if ($AllowUntrusted -and $current.Status -eq 'UnknownError' -and $current.SignerCertificate) {
            Write-Warning 'Firma presente con certificado no confiable (modo de prueba).'
        } else {
            throw "La firma no es valida: $($current.Status) - $($current.StatusMessage)"
        }
    }
    Write-HashSidecar -File $ExePath | Out-Null
    Write-Step 'Verificacion completada'
    exit 0
}

function Get-PrivateKeyIdentity {
    param([System.Security.Cryptography.X509Certificates.X509Certificate2]$Certificate)

    $rsa = [System.Security.Cryptography.X509Certificates.RSACertificateExtensions]::GetRSAPrivateKey($Certificate)
    if (-not $rsa) { return $null }

    if ($rsa -is [System.Security.Cryptography.RSACng]) {
        $identity = [pscustomobject]@{
            Store    = 'CNG'
            Name     = $rsa.Key.KeyName
            Provider = $rsa.Key.Provider
        }
        $rsa.Dispose()
        return $identity
    }

    if ($rsa -is [System.Security.Cryptography.RSACryptoServiceProvider]) {
        $identity = [pscustomobject]@{
            Store    = 'CAPI'
            Name     = $rsa.CspKeyContainerInfo.KeyContainerName
            Provider = $rsa.CspKeyContainerInfo.ProviderName
        }
        $rsa.Dispose()
        return $identity
    }

    $rsa.Dispose()
    return $null
}

function Remove-TemporaryPrivateKey {
    param($Identity)

    if (-not $Identity -or -not $Identity.Name) { return }

    try {
        if ($Identity.Store -eq 'CNG') {
            $key = if ($Identity.Provider) {
                [System.Security.Cryptography.CngKey]::Open($Identity.Name, $Identity.Provider)
            } else {
                [System.Security.Cryptography.CngKey]::Open($Identity.Name)
            }
            $key.Delete()
        } elseif ($Identity.Store -eq 'CAPI') {
            & certutil.exe -delkey -csp $Identity.Provider $Identity.Name | Out-Null
            if ($LASTEXITCODE -ne 0) {
                throw "certutil -delkey fallo con codigo $LASTEXITCODE"
            }
        }
    } catch {
        Write-Warning "No se pudo eliminar la clave privada importada: $($_.Exception.Message)"
    }
}

$importedThumbprint = $null
$importedKey = $null
$certificate = $null

try {
    if ($PSCmdlet.ParameterSetName -eq 'Pfx') {
        $PfxPath = Resolve-FullPath -Path $PfxPath -Label 'PFX'
        $securePassword = if ($PfxPassword) {
            $PfxPassword
        } else {
            ConvertTo-SecureString -String '' -AsPlainText -Force
        }

        Write-Step 'Importando PFX al almacen del usuario'
        try {
            $certificate = Import-PfxCertificate -FilePath $PfxPath -CertStoreLocation 'Cert:\CurrentUser\My' -Password $securePassword
        } catch {
            throw "No se pudo importar el PFX. Verifique la contrasena con -PfxPassword. Detalle: $($_.Exception.Message)"
        }
        $importedThumbprint = $certificate.Thumbprint
        $importedKey = Get-PrivateKeyIdentity -Certificate $certificate
        if ($importedKey) {
            Write-Verbose "Clave privada importada: $($importedKey.Store) $($importedKey.Name)"
        }
    } else {
        if (-not $Thumbprint) {
            throw 'Indique -Thumbprint (certificado en Cert:\CurrentUser\My) o -PfxPath.'
        }
        Write-Step 'Buscando certificado en el almacen del usuario'
        $certificate = Get-StoreCertificate -Thumb $Thumbprint
    }

    Assert-CodeSigningCertificate -Certificate $certificate

    Write-Step 'Firmando ejecutable'
    if ($signTool) {
        Invoke-SignToolSign -SignTool $signTool -File $ExePath -Thumb $certificate.Thumbprint
    } else {
        Invoke-PowerShellSign -Certificate $certificate -File $ExePath
    }

    Write-Step 'Verificando firma'
    $valid = Test-Signature -SignTool $signTool -File $ExePath
    if (-not $valid) {
        $current = Get-AuthenticodeSignature -LiteralPath $ExePath
        if ($AllowUntrusted -and $current.Status -eq 'UnknownError') {
            Write-Warning 'Verificacion no confiable: esperado con certificado autofirmado.'
        } else {
            throw "La firma generada no verifica: $($current.Status) - $($current.StatusMessage)"
        }
    }

    Write-HashSidecar -File $ExePath | Out-Null
    Write-Step 'Firma completada'
}
finally {
    if ($importedThumbprint) {
        Write-Step 'Eliminando certificado y clave privada temporales'
        Remove-TemporaryPrivateKey -Identity $importedKey
        Remove-Item -LiteralPath "Cert:\CurrentUser\My\$importedThumbprint" -Force -ErrorAction SilentlyContinue
    }
}
