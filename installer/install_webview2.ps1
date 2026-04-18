$ErrorActionPreference = "Stop"

function Test-WebView2Installed {
    $clientId = "{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"
    $paths = @(
        "HKCU:\SOFTWARE\Microsoft\EdgeUpdate\Clients\$clientId",
        "HKCU:\SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\$clientId",
        "HKLM:\SOFTWARE\Microsoft\EdgeUpdate\Clients\$clientId",
        "HKLM:\SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\$clientId"
    )

    foreach ($path in $paths) {
        if (Test-Path $path) {
            $version = (Get-ItemProperty -Path $path -ErrorAction SilentlyContinue).pv
            if ($version) {
                return $true
            }
        }
    }

    return $false
}

if (Test-WebView2Installed) {
    exit 0
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$bundledInstallers = @(
    (Join-Path $scriptDir "MicrosoftEdgeWebView2RuntimeInstallerX64.exe"),
    (Join-Path $scriptDir "MicrosoftEdgeWebView2Setup.exe")
)
$bootstrapperUrl = "https://go.microsoft.com/fwlink/p/?LinkId=2124703"
$tempFile = Join-Path $env:TEMP "MicrosoftEdgeWebView2Setup.exe"
$installerPath = $null

try {
    foreach ($candidate in $bundledInstallers) {
        if (Test-Path $candidate) {
            $installerPath = $candidate
            break
        }
    }

    if (-not $installerPath) {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -Uri $bootstrapperUrl -OutFile $tempFile -UseBasicParsing
        $installerPath = $tempFile
    }

    $process = Start-Process -FilePath $installerPath -ArgumentList "/silent", "/install" -PassThru -Wait
    if ($process.ExitCode -ne 0 -and -not (Test-WebView2Installed)) {
        exit $process.ExitCode
    }
}
catch {
    if (-not (Test-WebView2Installed)) {
        throw
    }
}
finally {
    if ($installerPath -eq $tempFile -and (Test-Path $tempFile)) {
        Remove-Item -LiteralPath $tempFile -Force -ErrorAction SilentlyContinue
    }
}

exit 0
