param([switch]$SmokeTest)
# Uses the established railway fixture with the optimized renderer default.
& "$PSScriptRoot/phase6-demo.ps1" -SmokeTest:$SmokeTest
