#!/bin/bash
# ── Deployment script for Mahitha Vaka Booking App ──────────────────────────
# Usage: ./deploy.sh <GCP_PROJECT_ID>

set -e

PROJECT_ID="${1:?Usage: ./deploy.sh <GCP_PROJECT_ID>}"
REGION="us-east4"
SERVICE_NAME="mahitha-booking-api"
SA_EMAIL="mahitha-booking-api@$PROJECT_ID.iam.gserviceaccount.com"
IMAGE="us-east4-docker.pkg.dev/$PROJECT_ID/mahitha-booking/$SERVICE_NAME"

echo "▶ Building and deploying to Cloud Run (frontend + backend)..."
# cloudbuild.yaml builds the frontend itself, so there's no local build step here.
# Cloud Build needs frontend files accessible — build from project root
gcloud builds submit . \
  --config cloudbuild.yaml \
  --substitutions="_IMAGE=$IMAGE" \
  --project "$PROJECT_ID"

gcloud run deploy "$SERVICE_NAME" \
  --image "$IMAGE" \
  --platform managed \
  --region "$REGION" \
  --allow-unauthenticated \
  --service-account "$SA_EMAIL" \
  --project "$PROJECT_ID"

APP_URL=$(gcloud run services describe "$SERVICE_NAME" \
  --platform managed --region "$REGION" \
  --project "$PROJECT_ID" \
  --format 'value(status.url)')

echo ""
echo "✅ Done! Your app is live at: $APP_URL"
echo ""
echo "Next: point schedule.mahithavaka.com → $APP_URL"
echo "  In Wix DNS: add CNAME  schedule → ${APP_URL#https://}"
