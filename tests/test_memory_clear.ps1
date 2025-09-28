# tests/test_memory_clear.ps1 — v1.0
# Scénario automatisé pour valider memory:clear (STM+LTM) côté backend.
# Pré-requis :
#   - Backend ÉMERGENCE démarré sur $BaseUrl (dev mode ou token valide).
#   - Dépendances Python installées (chromadb, sentence-transformers, torch, ...).
#   - Les dossiers src/backend/data/db et vector_store accessibles en lecture/écriture.
#
# Étapes:
#   1. Injection d'une session factice dans la base SQLite (summary + concepts).
#   2. Déclenchement de /api/memory/tend-garden pour vectoriser ces concepts.
#   3. Appel de /api/memory/clear (DELETE) et vérifications STM/LTM.
#   4. Assertions post-conditions (summary NULL + vecteurs supprimés).
#
# Usage :
#   pwsh -File tests/test_memory_clear.ps1 [-BaseUrl http://...] [-AuthToken <JWT>] [-SessionId <custom>]
#
[CmdletBinding()]
param(
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [string]$SessionId,
    [string]$UserId = "memory-clear-qa",
    [string]$AgentId = "neo",
    [string]$SummaryText = "[QA] Vérification memory:clear",
    [string[]]$Concepts = @("[QA] concept mémoire clear"),
    [string]$Collection = "emergence_knowledge",
    [string]$AuthToken = $env:EMERGENCE_ID_TOKEN
)

try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}
$PSDefaultParameterValues['Out-File:Encoding'] = 'utf8'
$ErrorActionPreference = "Stop"

if (-not $SessionId -or -not $SessionId.Trim()) {
    $SessionId = "memclr-" + ([Guid]::NewGuid().ToString("N"))
}
if (-not $Concepts -or $Concepts.Count -eq 0) {
    $Concepts = @("[QA] concept mémoire clear")
}
$Concepts = $Concepts | ForEach-Object { $_.ToString() }

$repoRoot = (Get-Location)
$dbPath = Join-Path $repoRoot "src/backend/data/db/emergence_v7.db"
$vectorDir = Join-Path $repoRoot "src/backend/data/vector_store"
$repoRootEsc = $repoRoot.Path.Replace('\\', '\\\\')
$vectorDirEsc = $vectorDir.Replace('\\', '\\\\')
$summaryJson = (ConvertTo-Json $SummaryText -Compress)
$conceptsJson = (ConvertTo-Json $Concepts -Compress)

Write-Host "=== [memory:clear] Test automatisé ===" -ForegroundColor Green
Write-Host "Base URL : $BaseUrl"
Write-Host "Session ID : $SessionId"
Write-Host "Vector store : $vectorDir"

if (-not (Test-Path $dbPath)) {
    throw "Base SQLite introuvable : $dbPath (démarre le backend au moins une fois)."
}
if (-not (Test-Path $vectorDir)) {
    Write-Host "Création du répertoire vector_store manquant..."
    New-Item -ItemType Directory -Path $vectorDir | Out-Null
}

function Invoke-PythonBlock {
    param(
        [Parameter(Mandatory)] [string]$Code,
        [string]$Description = "python"
    )
    $tmpPath = Join-Path ([System.IO.Path]::GetTempPath()) ("memclr_{0}.py" -f [Guid]::NewGuid().ToString("N"))
    Set-Content -Path $tmpPath -Value $Code -Encoding UTF8
    try {
        Write-Host "▶ python ($Description)" -ForegroundColor DarkGray
        # Allow Chromadb telemetry warnings on stderr without aborting the test.
        $prevPreference = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        try {
            $output = & python $tmpPath 2>&1
            $exit = $LASTEXITCODE
        } finally {
            $ErrorActionPreference = $prevPreference
        }
        if ($output) { $output | ForEach-Object { Write-Host $_ } }
        if ($exit -ne 0) {
            throw "Bloc Python '$Description' en erreur (exit=$exit)."
        }
        return $output
    }
    finally {
        Remove-Item $tmpPath -ErrorAction SilentlyContinue
    }
}

Write-Host "`n=== [1] Injection de la session factice ==="
$seedCode = @"
import sqlite3, json, datetime, pathlib

repo_root = pathlib.Path(r"$repoRootEsc")
db_path = repo_root / "src" / "backend" / "data" / "db" / "emergence_v7.db"
session_id = "$SessionId"
user_id = "$UserId"
summary = json.loads(r'''$summaryJson''')
concepts = json.loads(r'''$conceptsJson''')
if not isinstance(concepts, list) or not concepts:
    concepts = ["[QA] concept mémoire clear"]
agent_id = "$AgentId"
history = [
    {"role": "user", "content": f"Peux-tu retenir: {concepts[0]} ?", "agent_id": agent_id},
    {"role": "assistant", "content": "C'est enregistré.", "agent_id": agent_id}
]
entities = ["qa-memory"]
now = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
conn = sqlite3.connect(db_path)
try:
    conn.execute("""
        INSERT INTO sessions (id, user_id, created_at, updated_at, session_data, summary, extracted_concepts, extracted_entities)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            user_id=excluded.user_id,
            updated_at=excluded.updated_at,
            session_data=excluded.session_data,
            summary=excluded.summary,
            extracted_concepts=excluded.extracted_concepts,
            extracted_entities=excluded.extracted_entities
    """, (
        session_id,
        user_id,
        now,
        now,
        json.dumps(history, ensure_ascii=False),
        summary,
        json.dumps(concepts, ensure_ascii=False),
        json.dumps(entities, ensure_ascii=False)
    ))
    conn.commit()
    print("SEED_OK")
finally:
    conn.close()
"@
Invoke-PythonBlock -Code $seedCode -Description "seed session" | Out-Null

$vectorCountCode = @"
import json, pathlib
import chromadb
from chromadb.config import Settings

repo_root = pathlib.Path(r"$repoRootEsc")
vector_dir = pathlib.Path(r"$vectorDirEsc")
vector_dir.mkdir(parents=True, exist_ok=True)
# Disable Chromadb telemetry to avoid stderr noise during checks.
client = chromadb.PersistentClient(path=str(vector_dir), settings=Settings(anonymized_telemetry=False))
col = client.get_or_create_collection(name="$Collection")
res = col.get(where={"$or": [{"session_id": "$SessionId"}, {"source_session_id": "$SessionId"}]})
ids = res.get("ids") or []
count = 0
if ids:
    if isinstance(ids, list) and ids and isinstance(ids[0], list):
        count = sum(len(x or []) for x in ids)
    else:
        count = len(ids)
print(json.dumps({"count": int(count)}, ensure_ascii=False))
"@

Write-Host "`n=== [2] Vecteurs avant tend-garden ==="
$beforeRaw = Invoke-PythonBlock -Code $vectorCountCode -Description "vector count (before)"
$beforeStats = ($beforeRaw | Select-Object -Last 1 | ConvertFrom-Json)
if ($beforeStats.count -ne 0) {
    Write-Warning "Des vecteurs existent déjà pour $SessionId. Le test continuera mais vérifiera la décrémentation."
}

Write-Host "`n=== [3] POST /api/memory/tend-garden ==="
$headers = @{
    "Content-Type" = "application/json"
    "X-Session-Id" = $SessionId
    "X-User-Id" = $UserId
}
if ($AuthToken) {
    $headers["Authorization"] = "Bearer $AuthToken"
}
try {
    $tend = Invoke-RestMethod -Uri "$BaseUrl/api/memory/tend-garden" -Method Post -Headers $headers -Body "{}"
    Write-Host ($tend | ConvertTo-Json -Depth 6)
} catch {
    throw "Appel tend-garden échoué : $($_.Exception.Message)"
}
if (-not $tend -or ($tend.status -ne "success")) {
    throw "tend-garden n'a pas renvoyé un statut success."
}

Write-Host "`n=== [4] Vérification des vecteurs après tend-garden ==="
$afterRaw = Invoke-PythonBlock -Code $vectorCountCode -Description "vector count (after tend-garden)"
$afterStats = ($afterRaw | Select-Object -Last 1 | ConvertFrom-Json)
if ([int]$afterStats.count -lt 1) {
    throw "Aucun vecteur créé pour la session test. Vérifie les logs du backend."
}
Write-Host "Vecteurs créés : $($afterStats.count)" -ForegroundColor Cyan

Write-Host "`n=== [5] DELETE /api/memory/clear ==="
$clearHeaders = @{
    "X-Session-Id" = $SessionId
    "X-User-Id" = $UserId
}
if ($AuthToken) {
    $clearHeaders["Authorization"] = "Bearer $AuthToken"
}
$clearUrl = "$BaseUrl/api/memory/clear?session_id=$([uri]::EscapeDataString($SessionId))"
try {
    $clear = Invoke-RestMethod -Uri $clearUrl -Method Delete -Headers $clearHeaders
    Write-Host ($clear | ConvertTo-Json -Depth 6)
} catch {
    throw "Appel memory:clear échoué : $($_.Exception.Message)"
}
if (-not $clear -or ($clear.status -ne "success")) {
    throw "memory:clear n'a pas renvoyé 'success'."
}
if ($clear.cleared.session_id -ne $SessionId) {
    throw "Le payload 'cleared.session_id' ne correspond pas à la session injectée."
}
if (-not $clear.cleared.stm) {
    throw "Le champ 'stm' est faux : la purge SQL a échoué."
}
if ([int]$clear.cleared.ltm_before -lt 1) {
    throw "ltm_before indique 0 alors que des vecteurs avaient été créés."
}
if ($clear.cleared.ltm_before -ne $clear.cleared.ltm_deleted) {
    throw "ltm_deleted différent de ltm_before (purge partielle)."
}

Write-Host "`n=== [6] Vérification base SQLite (summary/concepts NULL) ==="
$verifyDbCode = @"
import json, sqlite3, pathlib

repo_root = pathlib.Path(r"$repoRootEsc")
db_path = repo_root / "src" / "backend" / "data" / "db" / "emergence_v7.db"
conn = sqlite3.connect(db_path)
try:
    cur = conn.execute("SELECT summary, extracted_concepts, extracted_entities FROM sessions WHERE id = ?", ("$SessionId",))
    row = cur.fetchone()
finally:
    conn.close()
if row is None:
    print(json.dumps({"found": False}))
else:
    summary, concepts, entities = row
    print(json.dumps({
        "found": True,
        "summary": summary,
        "concepts": concepts,
        "entities": entities
    }, ensure_ascii=False))
"@
$dbCheckRaw = Invoke-PythonBlock -Code $verifyDbCode -Description "sqlite post-clear"
$dbStats = ($dbCheckRaw | Select-Object -Last 1 | ConvertFrom-Json)
if (-not $dbStats.found) {
    throw "La session injectée est introuvable après memory:clear."
}
if ($dbStats.summary -ne $null -or $dbStats.concepts -ne $null -or $dbStats.entities -ne $null) {
    throw "Les colonnes summary/concepts/entities ne sont pas nulles après purge."
}

Write-Host "`n=== [7] Vérification absence de vecteurs ==="
$afterClearRaw = Invoke-PythonBlock -Code $vectorCountCode -Description "vector count (after clear)"
$afterClearStats = ($afterClearRaw | Select-Object -Last 1 | ConvertFrom-Json)
if ([int]$afterClearStats.count -ne 0) {
    throw "Des vecteurs subsistent pour $SessionId après memory:clear ($($afterClearStats.count))."
}

Write-Host "`n=== ✅ Test memory:clear terminé avec succès ===" -ForegroundColor Green
