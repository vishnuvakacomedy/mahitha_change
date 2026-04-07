#!/bin/bash
# ── GCP Project Setup for Mahitha Vaka Booking App ──────────────────────────
# Run this ONCE before deploying.
#
# Prerequisites:
#   - gcloud CLI installed and logged in  (gcloud auth login)
#   - firebase CLI installed              (npm install -g firebase-tools)
#   - A GCP project already created at console.cloud.google.com
#
# Usage: ./gcp_setup.sh <GCP_PROJECT_ID> <YOUR_EMAIL>
#
# Example: ./gcp_setup.sh mahitha-booking mahitha@mahithavaka.com
# ─────────────────────────────────────────────────────────────────────────────

set -e

PROJECT_ID="${1:?Usage: ./gcp_setup.sh <GCP_PROJECT_ID> <YOUR_EMAIL>}"
OWNER_EMAIL="${2:?Usage: ./gcp_setup.sh <GCP_PROJECT_ID> <YOUR_EMAIL>}"
REGION="us-central1"
SA_NAME="mahitha-booking-sa"
SA_EMAIL="$SA_NAME@$PROJECT_ID.iam.gserviceaccount.com"
KEY_FILE="backend/serviceAccount.json"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Setting up GCP project: $PROJECT_ID"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 1. Set active project
echo "▶ Setting active project..."
gcloud config set project "$PROJECT_ID"

# 2. Enable required APIs
echo "▶ Enabling APIs (Cloud Run, Cloud Build, Firestore, Container Registry)..."
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  firestore.googleapis.com \
  containerregistry.googleapis.com \
  --project "$PROJECT_ID"
echo "  ✓ APIs enabled"

# 3. Create Firestore database (native mode)
echo "▶ Creating Firestore database..."
gcloud firestore databases create \
  --location="$REGION" \
  --project "$PROJECT_ID" 2>/dev/null || echo "  ℹ Firestore already exists — skipping"

# 4. Create service account for the backend
echo "▶ Creating service account..."
gcloud iam service-accounts create "$SA_NAME" \
  --display-name="Mahitha Booking Service Account" \
  --project "$PROJECT_ID" 2>/dev/null || echo "  ℹ Service account already exists — skipping"

# 5. Grant Firestore access to the service account
echo "▶ Granting Firestore permissions..."
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/datastore.user" \
  --quiet

# 6. Download service account key
echo "▶ Downloading service account key to $KEY_FILE..."
gcloud iam service-accounts keys create "$KEY_FILE" \
  --iam-account="$SA_EMAIL" \
  --project "$PROJECT_ID"
echo "  ✓ Key saved to $KEY_FILE"
echo "  ⚠  Keep this file secret — never commit it to git!"

# 7. Set up Firebase Hosting
echo ""
echo "▶ Initializing Firebase Hosting..."
firebase login --no-localhost 2>/dev/null || true
firebase use --add "$PROJECT_ID" 2>/dev/null || true

# 8. Create Firestore indexes (needed for availability queries)
echo "▶ Creating Firestore composite index for availability..."
cat > /tmp/firestore_index.json << 'EOF'
{
  "indexes": [
    {
      "collectionGroup": "availability",
      "queryScope": "COLLECTION",
      "fields": [
        { "fieldPath": "booked", "order": "ASCENDING" },
        { "fieldPath": "datetime", "order": "ASCENDING" }
      ]
    },
    {
      "collectionGroup": "availability",
      "queryScope": "COLLECTION",
      "fields": [
        { "fieldPath": "booked", "order": "ASCENDING" },
        { "fieldPath": "date", "order": "ASCENDING" },
        { "fieldPath": "datetime", "order": "ASCENDING" }
      ]
    }
  ],
  "fieldOverrides": []
}
EOF

gcloud firestore indexes composite create \
  --collection-group=availability \
  --field-config=field-path=booked,order=ascending \
  --field-config=field-path=datetime,order=ascending \
  --project "$PROJECT_ID" 2>/dev/null || echo "  ℹ Index already exists or being created"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ GCP setup complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Next steps:"
echo ""
echo "  1. Copy backend/.env.example → backend/.env and fill in:"
echo "       GOOGLE_APPLICATION_CREDENTIALS=serviceAccount.json"
echo "       SENDGRID_API_KEY=SG.xxxx         ← get from sendgrid.com (free)"
echo "       SENDER_EMAIL=noreply@mahithavaka.com"
echo "       HOST_EMAIL=mahitha@mahithavaka.com"
echo ""
echo "  2. Seed Firestore with sessions + available slots:"
echo "       source venv/bin/activate"
echo "       cd backend"
echo "       python seed.py"
echo ""
echo "  3. Deploy everything:"
echo "       ./deploy.sh $PROJECT_ID"
echo ""
echo "  4. Add custom domain in Firebase Hosting console:"
echo "       https://console.firebase.google.com/project/$PROJECT_ID/hosting"
echo "       Add domain: schedule.mahithavaka.com"
echo "       Then add CNAME in Wix DNS panel as instructed"
echo ""
