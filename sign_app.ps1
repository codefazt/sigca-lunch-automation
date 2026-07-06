# sign_app.ps1
# =============================================================================
# SiGCABot — Script de Firma Digital Autofirmada (Silencioso)
# =============================================================================
# Genera un certificado de firma de código autofirmado local en el almacén personal,
# exporta el certificado público (.cer) para su posterior confianza manual,
# y firma el ejecutable SiGCABot.exe sin levantar diálogos interactivos que
# puedan bloquear procesos de automatización o compilación.
# =============================================================================

$exePath = "dist\SiGCABot_Release\SiGCABot.exe"
if (-not (Test-Path $exePath)) {
    Write-Host "[ERROR] No se encontro el ejecutable en $exePath. Ejecuta build.bat primero." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "    Firmando ejecutable SiGCABot.exe (Silencioso)" -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host ""

$certSubject = "CN=SiGCABot,O=Developer,C=Local"
$certFriendlyName = "SiGCABot Code Signing"

Write-Host "[1/3] Buscando certificado de firma en el almacen personal..." -ForegroundColor Gray
$cert = Get-ChildItem -Path Cert:\CurrentUser\My | Where-Object { $_.Subject -eq $certSubject -and $_.FriendlyName -eq $certFriendlyName } | Select-Object -First 1

if ($null -eq $cert) {
    Write-Host "[INFO] No se encontro un certificado existente. Creando uno nuevo..." -ForegroundColor Yellow
    # Crear el certificado autofirmado para firma de código (duración de 5 años)
    $cert = New-SelfSignedCertificate -Type CodeSigningCert -Subject $certSubject -FriendlyName $certFriendlyName -CertStoreLocation "Cert:\CurrentUser\My" -NotAfter (Get-Date).AddYears(5)
    Write-Host "[EXITO] Certificado de firma de codigo creado con Thumbprint: $($cert.Thumbprint)" -ForegroundColor Green
} else {
    Write-Host "[INFO] Certificado existente encontrado con Thumbprint: $($cert.Thumbprint)" -ForegroundColor Green
}

Write-Host "[2/3] Exportando certificado publico para instalacion manual..." -ForegroundColor Gray
$cerOutDir = "dist\SiGCABot_Release"
$cerPath = Join-Path $cerOutDir "SiGCABot.cer"
try {
    # Exportar el certificado para que el usuario pueda instalarlo si desea confiar en él en otras máquinas
    Export-Certificate -Cert $cert -FilePath $cerPath -Force | Out-Null
    Write-Host "[EXITO] Certificado exportado a: $cerPath" -ForegroundColor Green
    Write-Host "[INFO] Para confiar en este certificado en esta u otra PC, puedes ejecutar:" -ForegroundColor Gray
    Write-Host "       Import-Certificate -FilePath '$cerPath' -CertStoreLocation Cert:\CurrentUser\Root" -ForegroundColor Cyan
} catch {
    Write-Host "[WARN] No se pudo exportar el archivo del certificado: $_" -ForegroundColor Yellow
}

Write-Host "[3/3] Aplicando firma digital al ejecutable..." -ForegroundColor Gray
# Firmar usando el comando integrado Set-AuthenticodeSignature
# Se intenta usar marca de tiempo para que la firma sea permanente
$timestampServer = "http://timestamp.digicert.com"

Write-Host "[INFO] Firmando con Timestamp (DigiCert)..." -ForegroundColor Yellow
$signResult = Set-AuthenticodeSignature -FilePath $exePath -Certificate $cert -TimestampServer $timestampServer -ErrorAction SilentlyContinue

if ($signResult.Status -eq "Valid") {
    Write-Host "[EXITO] El ejecutable ha sido firmado digitalmente de forma correcta y con marca de tiempo." -ForegroundColor Green
} else {
    # Reintento sin timestamp en caso de no tener internet o fallos de red
    Write-Host "[WARN] Firma con Timestamp fallida ($($signResult.Status)). Reintentando firma basica..." -ForegroundColor Yellow
    $signResult = Set-AuthenticodeSignature -FilePath $exePath -Certificate $cert
    if ($signResult.Status -eq "Valid" -or $signResult.Status -eq "UnknownError") {
        Write-Host "[EXITO] El ejecutable ha sido firmado digitalmente de forma basica (sin marca de tiempo)." -ForegroundColor Green
    } else {
        Write-Host "[ERROR] Fallo al firmar el ejecutable. Estado: $($signResult.Status)" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "Detalles de la Firma Digital de la Aplicacion:" -ForegroundColor Gray
Get-AuthenticodeSignature -FilePath $exePath | Format-Table -AutoSize
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host ""
