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
# One region for everything (Firestore, Cloud Run, Scheduler) — matches
# deploy.sh/cloudbuild.yaml, and keeps Cloud Run <-> Firestore latency low.
CLOUD_RUN_REGION="us-east4"
# Matches the service account name deploy.sh/cloudbuild.yaml actually deploy with.
SA_NAME="mahitha-booking-api"
SA_EMAIL="$SA_NAME@$PROJECT_ID.iam.gserviceaccount.com"
SERVICE_NAME="mahitha-booking-api"
SCHEDULER_JOB_NAME="top-up-availability"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Setting up GCP project: $PROJECT_ID"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 1. Set active project
echo "▶ Setting active project..."
gcloud config set project "$PROJECT_ID"

# 2. Enable required APIs
echo "▶ Enabling APIs (Cloud Run, Cloud Build, Firestore, Container Registry,"
echo "  Cloud Scheduler, Calendar, IAM, IAM Credentials)..."
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  firestore.googleapis.com \
  containerregistry.googleapis.com \
  cloudscheduler.googleapis.com \
  calendar-json.googleapis.com \
  iam.googleapis.com \
  iamcredentials.googleapis.com \
  --project "$PROJECT_ID"
echo "  ✓ APIs enabled"

# 3. Create Firestore database (native mode)
echo "▶ Creating Firestore database..."
gcloud firestore databases create \
  --location="$CLOUD_RUN_REGION" \
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

# 5b. Let the service account impersonate itself to pick up Calendar scope
# (its default attached-identity token doesn't include non-GCP scopes like
# Calendar; self-impersonation via the IAM Credentials API is the standard
# key-file-free way to mint one). Used by backend/calendar_service.py.
echo "▶ Granting self-impersonation for Calendar sync..."
gcloud iam service-accounts add-iam-policy-binding "$SA_EMAIL" \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/iam.serviceAccountTokenCreator" \
  --project "$PROJECT_ID" \
  --quiet

# 6. Set up Firebase Hosting
echo ""
echo "▶ Initializing Firebase Hosting..."
firebase login --no-localhost 2>/dev/null || true
firebase use --add "$PROJECT_ID" 2>/dev/null || true

# 7. Create Firestore composite indexes (needed for availability queries)
echo "▶ Creating Firestore composite indexes for availability..."
gcloud firestore indexes composite create \
  --collection-group=availability \
  --field-config=field-path=booked,order=ascending \
  --field-config=field-path=datetime,order=ascending \
  --project "$PROJECT_ID" 2>/dev/null || echo "  ℹ Index already exists or being created"

# Needed for the /availability?date=... filtered query in backend/main.py,
# which adds an equality filter on "date" on top of booked+datetime.
gcloud firestore indexes composite create \
  --collection-group=availability \
  --field-config=field-path=booked,order=ascending \
  --field-config=field-path=date,order=ascending \
  --field-config=field-path=datetime,order=ascending \
  --project "$PROJECT_ID" 2>/dev/null || echo "  ℹ Index already exists or being created"

# 8. Create/update the weekly availability top-up Cloud Scheduler job.
# Needs the Cloud Run service to already be deployed (to read its URL and
# admin credentials) — safe to skip on a first run and re-run later via
# `./gcp_setup.sh <PROJECT_ID> <EMAIL>` again after `./deploy.sh` has run.
echo "▶ Setting up weekly availability top-up job..."
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
  --platform managed --region "$CLOUD_RUN_REGION" --project "$PROJECT_ID" \
  --format="value(status.url)" 2>/dev/null || true)

if [ -z "$SERVICE_URL" ]; then
  echo "  ℹ Cloud Run service [$SERVICE_NAME] not deployed yet — skipping."
  echo "    Run ./deploy.sh $PROJECT_ID, then re-run this script to finish this step."
else
  ADMIN_ENV_JSON=$(gcloud run services describe "$SERVICE_NAME" \
    --platform managed --region "$CLOUD_RUN_REGION" --project "$PROJECT_ID" \
    --format="json(spec.template.spec.containers[0].env)")
  # Values may be set inline or via a Secret Manager reference
  # (valueFrom.secretKeyRef); resolve either form.
  ADMIN_CREDS=$(echo "$ADMIN_ENV_JSON" | python3 -c "
import json, subprocess, sys

def resolve(env, name):
    for e in env:
        if e.get('name') != name:
            continue
        if 'value' in e:
            return e['value']
        secret_ref = e.get('valueFrom', {}).get('secretKeyRef', {})
        secret_name = secret_ref.get('name', '')
        version = secret_ref.get('key') or 'latest'
        if not secret_name:
            return ''
        result = subprocess.run(
            ['gcloud', 'secrets', 'versions', 'access', version,
             '--secret', secret_name, '--project', '$PROJECT_ID'],
            capture_output=True, text=True)
        return result.stdout.strip() if result.returncode == 0 else ''
    return ''

env = json.load(sys.stdin)['spec']['template']['spec']['containers'][0].get('env', [])
print(resolve(env, 'ADMIN_USERNAME'))
print(resolve(env, 'ADMIN_PASSWORD'))
")
  ADMIN_USERNAME_VAL=$(echo "$ADMIN_CREDS" | sed -n '1p')
  ADMIN_PASSWORD_VAL=$(echo "$ADMIN_CREDS" | sed -n '2p')

  if [ -z "$ADMIN_USERNAME_VAL" ] || [ -z "$ADMIN_PASSWORD_VAL" ]; then
    echo "  ℹ ADMIN_USERNAME/ADMIN_PASSWORD not set on the Cloud Run service yet — skipping."
  else
    AUTH_HEADER_VALUE="Basic $(printf '%s' "${ADMIN_USERNAME_VAL}:${ADMIN_PASSWORD_VAL}" | base64 | tr -d '\n')"

    if gcloud scheduler jobs describe "$SCHEDULER_JOB_NAME" \
        --project "$PROJECT_ID" --location "$CLOUD_RUN_REGION" >/dev/null 2>&1; then
      gcloud scheduler jobs update http "$SCHEDULER_JOB_NAME" \
        --project "$PROJECT_ID" --location "$CLOUD_RUN_REGION" \
        --schedule="0 6 * * 1" --time-zone="America/New_York" \
        --uri="${SERVICE_URL}/admin/top-up-availability" --http-method=POST \
        --update-headers="Authorization=${AUTH_HEADER_VALUE}" --quiet
      echo "  ✓ Updated existing Scheduler job [$SCHEDULER_JOB_NAME]"
    else
      gcloud scheduler jobs create http "$SCHEDULER_JOB_NAME" \
        --project "$PROJECT_ID" --location "$CLOUD_RUN_REGION" \
        --schedule="0 6 * * 1" --time-zone="America/New_York" \
        --uri="${SERVICE_URL}/admin/top-up-availability" --http-method=POST \
        --headers="Authorization=${AUTH_HEADER_VALUE}" \
        --description="Weekly rolling top-up of availability slots (keeps a 90-day booking window filled)" \
        --quiet
      echo "  ✓ Created Scheduler job [$SCHEDULER_JOB_NAME] (every Monday 6am ET)"
    fi
    unset AUTH_HEADER_VALUE ADMIN_USERNAME_VAL ADMIN_PASSWORD_VAL
  fi
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ GCP setup complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Next steps:"
echo ""
echo "  1. Copy backend/.env.example → backend/.env and fill in:"
echo "       GMAIL_USER=you@gmail.com"
echo "       GMAIL_APP_PASSWORD=xxxx          ← app password, not your Gmail password"
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
echo "  5. One manual step Google requires a logged-in human for — share the"
echo "     host's Google Calendar with the service account so bookings sync:"
echo "       In Google Calendar (as the host) → Settings → Settings for my"
echo "       calendars → select the calendar → Share with specific people →"
echo "       add $SA_EMAIL → permission \"Make changes to events\""
echo ""
