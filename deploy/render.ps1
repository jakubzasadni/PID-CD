# deploy/render.ps1
# Renders ConfigMap from configmap.env, injects IMAGE into job.yaml.tpl,
# applies manifests, waits for Job, then copies artifacts to .out (Windows).
param(
  [string]$Image = $env:IMAGE
)

$ErrorActionPreference = "Stop"
$ns = "pid-sim-dev"
$cmEnv = "deploy/configmap.env"
$cmYaml = "deploy/configmap.yaml"
$jobTpl = "deploy/job.yaml.tpl"
$jobYaml = "deploy/job.yaml"

if (-not $Image) {
  Write-Host "IMAGE not set. Use: `n`$env:IMAGE='your.registry/pid-sim:tag'"
  exit 1
}

# 1) Namespace
kubectl apply -f deploy/namespace.yaml | Out-Null

# 2) Build ConfigMap YAML from ENV-style file (key=value per line)
@"
apiVersion: v1
kind: ConfigMap
metadata:
  name: pid-sim-config
  namespace: $ns
data:
"@ | Set-Content -NoNewline $cmYaml -Encoding UTF8

Get-Content $cmEnv | ForEach-Object {
  $line = $_.Trim()
  if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
    $k,$v = $line.Split("=",2)
    $vEsc = $v.Replace('"','\"')
    Add-Content -Encoding UTF8 $cmYaml ("  {0}: ""{1}""`n" -f $k,$vEsc)
  }
}

kubectl apply -f $cmYaml | Out-Null

# 3) Render Job manifest: substitute ${IMAGE}
$content = Get-Content $jobTpl -Raw
$content = $content -replace '\$\{IMAGE\}', [Regex]::Escape($Image)
Set-Content -Path $jobYaml -Value $content -Encoding UTF8

kubectl apply -f $jobYaml | Out-Null

# 4) Wait for Job completion (up to 10 minutes)
$wait = & kubectl -n $ns wait --for=condition=complete job/pid-sim-validate --timeout=10m 2>&1
if ($LASTEXITCODE -ne 0) {
  Write-Host $wait
  Write-Host "Job failed or timed out. Logs:"
  kubectl -n $ns logs job/pid-sim-validate || $true
  exit 1
}

# 5) Copy artifacts to .out
$pod = kubectl -n $ns get pods -l job-name=pid-sim-validate -o jsonpath='{.items[0].metadata.name}'
if (-not (Test-Path ".out")) { New-Item -ItemType Directory ".out" | Out-Null }
kubectl -n $ns cp "$pod:/out" ".out"  # copies folder /out into .\.out
Write-Host "Artefakty dostępne w .\.out"
