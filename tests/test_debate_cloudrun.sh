#!/usr/bin/env bash
set -euo pipefail

# =========================
# ÉMERGENCE - Cloud Run test /api/debate/ + logs
# Prérequis: gcloud auth login && gcloud config set project emergence-469005
# =========================

PROJECT="emergence-469005"
REGION="europe-west1"
SVC="emergence-app"

echo "== Contexte =="
gcloud config set project "$PROJECT" >/dev/null
gcloud config set run/region "$REGION" >/dev/null

echo
echo "== Service URL & révision =="
URL=$(gcloud run services describe "$SVC" --region "$REGION" --format="value(status.url)")
REV=$(gcloud run services describe "$SVC" --region "$REGION" --format="value(status.latestReadyRevisionName)")
if [[ -z "${URL}" ]]; then
  echo "Service introuvable: $SVC ($REGION)" >&2
  exit 1
fi
echo "URL: ${URL}"
echo "Revision: ${REV}"

echo
echo "== Identity Token =="
TOKEN=$(gcloud auth print-identity-token)
if [[ -z "${TOKEN}" ]]; then
  echo "Impossible d'obtenir l'identity token." >&2
  exit 1
fi

authHeader="Authorization: Bearer ${TOKEN}"

echo
echo "== Sanity check /api/health =="
set +e
HEALTH=$(curl -sS -m 60 -H "$authHeader" "${URL}/api/health")
code=$?
set -e
if [[ $code -ne 0 || -z "$HEALTH" ]]; then
  echo "Health check KO. Logs récents:"
  gcloud logs read --limit=50 --freshness="1h" \
    --format="table(timestamp,severity,logName,resource.labels.revision_name,short_message)" \
    --filter="resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"$SVC\""
  exit 1
fi
echo "$HEALTH"

echo
echo "== GET /api/debate/ =="
set +e
DEBATES=$(curl -sS -m 120 -H "$authHeader" "${URL}/api/debate/")
code=$?
set -e
if [[ $code -ne 0 || -z "$DEBATES" ]]; then
  echo "!! ERREUR sur /api/debate/ -> collecte logs ciblés"

  COMMON_FILTER="resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"$SVC\" AND resource.labels.location=\"$REGION\""

  echo
  echo "-- Dernières erreurs (1h) --"
  gcloud logs read --limit=100 --freshness="1h" \
    --format="json" \
    --filter="$COMMON_FILTER AND severity>=ERROR" | \
    jq -r '.[] | [.timestamp, .severity, (.resource.labels.revision_name // ""), (.textPayload // .jsonPayload.message // .protoPayload.status.message // "no-msg")] | @tsv'

  echo
  echo "-- Erreurs liées à /api/debate (1h) --"
  gcloud logs read --limit=100 --freshness="1h" \
    --format="json" \
    --filter="$COMMON_FILTER AND (textPayload:\"/api/debate\" OR jsonPayload.message:\"/api/debate\" OR protoPayload.resource:\"/api/debate\") AND severity>=ERROR" | \
    jq -r '.[] | [.timestamp, .severity, (.resource.labels.revision_name // ""), (.textPayload // .jsonPayload.message // .protoPayload.status.message // "no-msg")] | @tsv'

  echo
  echo "-- Stacktraces (si présents) --"
  gcloud logs read --limit=50 --freshness="1h" \
    --format="value(textPayload, jsonPayload.stack, protoPayload.status.message)" \
    --filter="$COMMON_FILTER AND severity>=ERROR"

  echo
  echo "-- Tail live logs (Ctrl+C pour arrêter) --"
  echo "gcloud logs tail --format=\"json\" --filter='$COMMON_FILTER'"
  exit 1
fi

echo "$DEBATES" | jq .

# Si un id est présent, tester le détail
FIRST_ID=$(echo "$DEBATES" | jq -r '.[0].id // empty')
if [[ -n "$FIRST_ID" ]]; then
  echo
  echo "== GET /api/debate/${FIRST_ID} =="
  curl -sS -m 120 -H "$authHeader" "${URL}/api/debate/${FIRST_ID}" | jq .
else
  echo
  echo "== Aucun débat en base. =="
fi

echo
echo "== Fini =="
