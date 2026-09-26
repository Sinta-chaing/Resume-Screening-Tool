# Test the live Resume Screening Tool API (datasciences.engineer)
# Works against the deployed backend. Uses multitail=false.
#
# Usage:
#   cd backend\scripts
#   .\api_test.ps1 -Resume "C:\path\to\resume.pdf" -Jd "C:\path\to\jd.txt"
#
# Optional flags:
#   -ChatQuestion "Does the candidate know Python?"   # also run RAG chat step
#   -SessionId "<uuid>"                                # reuse an existing session (skips analyze)

param(
    [Parameter(Mandatory = $true)]
    [string]$Resume,
    [Parameter(Mandatory = $true)]
    [string]$Jd,
    [string]$ChatQuestion = "",
    [string]$SessionId = "",
    [int]$PollSeconds = 15,
    [int]$MaxPolls = 60
)

$ErrorActionPreference = "Stop"
$BaseUrl = "https://datasciences.engineer"

function Invoke-Json {
    param([string]$Method, [string]$Path, [object]$Body = $null, [object]$Form = $null)
    $args = @("-s", "-X", $Method, "$BaseUrl$Path")
    if ($Body) { $args += @("-H", "Content-Type: application/json", "-d", ($Body | ConvertTo-Json -Compress)) }
    if ($Form) { $args += @("-F", $Form) }
    $raw = & curl.exe @args
    return $raw | ConvertFrom-Json
}

Write-Host ""
Write-Host "== 1. Health check =="
$health = Invoke-Json -Method "GET" -Path "/api/health"
$health | Format-List | Out-String | Write-Host

if (-not $SessionId) {
    Write-Host "== 2. Analyze (async upload) =="
    $analyze = Invoke-Json -Method "POST" -Path "/api/analyze" -Form "resume=@$Resume" -Form "jd=@$Jd"
    $analyze | Out-String | Write-Host

    if ($analyze.status -ne "pending" -or -not $analyze.sessionId) {
        throw "Analyze did not return a pending session: $($analyze | ConvertTo-Json -Compress)"
    }
    $SessionId = $analyze.sessionId
} else {
    Write-Host "== 2. Analyze skipped (using provided SessionId: $SessionId) =="
}

Write-Host "== 3. Poll until completed =="
$record = $null
for ($i = 1; $i -le $MaxPolls; $i++) {
    $record = Invoke-Json -Method "GET" -Path "/api/records/$SessionId"
    Write-Host ("poll {0}: status = {1}" -f $i, $record.status)
    if ($record.status -in @("completed", "failed")) { break }
    Start-Sleep -Seconds $PollSeconds
}
if ($record.status -ne "completed") { throw "Analysis did not complete: status = $($record.status)" }

Write-Host ""
Write-Host "== 4. Evaluation result =="
$record.evaluation | ConvertTo-Json -Depth 5 | Write-Host
Write-Host ""
Write-Host "Candidate: $($record.candidateName)  |  Position: $($record.position)  |  Score: $($record.evaluation.score)"

Write-Host ""
Write-Host "== 5. Ranked records =="
$records = Invoke-Json -Method "GET" -Path "/api/records?order=desc"
$records.records | Select-Object id, candidateName, position, score, status | Format-Table | Out-String | Write-Host

if ($ChatQuestion) {
    Write-Host "== 6. RAG chat =="
    $chat = Invoke-Json -Method "POST" -Path "/api/chat" -Body @{ sessionId = $SessionId; question = $ChatQuestion }
    Write-Host "Q: $ChatQuestion"
    Write-Host "A: $($chat.answer)"
    Write-Host ""
    Write-Host "Sources:"
    $chat.sources | ForEach-Object { Write-Host ("  - {0} (chunk {1})" -f $_.sessionId, $_.chunkIndex) }
}

Write-Host ""
Write-Host "Done. SessionId = $SessionId" -ForegroundColor Green