# CreddyPens GCP Setup Script
# This script enables APIs, creates a Cloud SQL instance, and prepares the project for deployment.

$PROJECT_ID = "gen-lang-client-0308728735"
$REGION = "us-central1"
$INSTANCE_NAME = "creddypens-db-v1"
$DB_USER = "creddypens_admin"
$DB_PASS = "CreddyPass2026!" # Recommended: Change this after first setup
$DB_NAME = "creddypens"

Write-Host "--- Setting Google Cloud Project: $PROJECT_ID ---" -ForegroundColor Cyan
gcloud config set project $PROJECT_ID

Write-Host "--- Enabling Required APIs ---" -ForegroundColor Cyan
gcloud services enable `
    run.googleapis.com `
    cloudbuild.googleapis.com `
    sqladmin.googleapis.com `
    compute.googleapis.com `
    secretmanager.googleapis.com

Write-Host "--- Creating Cloud SQL (PostgreSQL 16) Instance ---" -ForegroundColor Yellow
Write-Host "Note: This can take 5-10 minutes. If it already exists, this step will be skipped."
gcloud sql instances create $INSTANCE_NAME `
    --database-version=POSTGRES_16 `
    --tier=db-f1-micro `
    --region=$REGION `
    --storage-type=HDD `
    --no-assign-ip

Write-Host "--- Creating Database and User ---" -ForegroundColor Cyan
gcloud sql databases create $DB_NAME --instance=$INSTANCE_NAME
gcloud sql users create $DB_USER --instance=$INSTANCE_NAME --password=$DB_PASS

Write-Host "--- Setup Complete ---" -ForegroundColor Green
Write-Host "You can now run: gcloud builds submit --config cloudbuild.yaml ." -ForegroundColor Cyan
