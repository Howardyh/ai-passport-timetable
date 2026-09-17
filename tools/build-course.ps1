param([string]$IdfPath=$env:IDF_PATH)
$ErrorActionPreference='Stop'
if (!$IdfPath) { throw 'Activate ESP-IDF 5.5.3 first.' }
$repoRoot=Split-Path $PSScriptRoot -Parent
$buildRoot=Join-Path $repoRoot 'build/verified'
Push-Location $repoRoot
try {
    $env:SDKCONFIG_DEFAULTS=Join-Path $repoRoot 'sdkconfig.defaults'
    & python "$IdfPath/tools/idf.py" -B $buildRoot -D "SDKCONFIG=$buildRoot/sdkconfig" build
    if($LASTEXITCODE) { throw 'Firmware build failed' }
    & python "$IdfPath/tools/idf.py" -B $buildRoot merge-bin -o "$buildRoot/FoloToy-AI-Passport-full.bin"
    if($LASTEXITCODE) { throw 'Firmware merge failed' }
    & python tools/verify_firmware.py $buildRoot
    if($LASTEXITCODE) { throw 'Firmware verification failed' }
    & python tools/archive_firmware.py create $buildRoot --archive-root "$repoRoot/build/firmware"
    if($LASTEXITCODE) { throw 'Firmware archive failed' }
} finally { Pop-Location }
