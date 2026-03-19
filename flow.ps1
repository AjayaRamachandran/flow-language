param(
    [string]$FlowScript = "test.flow"
)

$projectRoot = $PSScriptRoot
$mainPath = Join-Path $projectRoot "main.py"

if (-not (Test-Path -Path $mainPath -PathType Leaf)) {
    Write-Error "Could not find main.py at '$mainPath'."
    exit 1
}

if ([System.IO.Path]::IsPathRooted($FlowScript)) {
    $targetScript = $FlowScript
}
else {
    $targetScript = Join-Path $projectRoot $FlowScript
}

if (-not (Test-Path -Path $targetScript -PathType Leaf)) {
    Write-Error "Flow script not found: $targetScript"
    exit 1
}

python "$mainPath" "$targetScript"
