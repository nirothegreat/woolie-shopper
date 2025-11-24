#!/bin/bash
# Deploy Woolies Shopper to Google Cloud Run with Claude AI

echo "🚀 Deploying Woolies Shopper to Google Cloud Run"
echo "================================================"
echo ""

# Configuration
SERVICE_NAME="woolies-shopper"
REGION="us-central1"

# Get API key from environment variable
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "❌ Error: ANTHROPIC_API_KEY environment variable not set"
    echo ""
    echo "Set it with:"
    echo "  export ANTHROPIC_API_KEY='your-key-here'"
    echo ""
    echo "Or for GitHub Actions, add it as a repository secret:"
    echo "  Settings → Secrets and variables → Actions → New repository secret"
    exit 1
fi

echo "📋 Configuration:"
echo "  Service: $SERVICE_NAME"
echo "  Region: $REGION"
echo "  API Key: ${ANTHROPIC_API_KEY:0:20}... ✓"
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ Error: gcloud CLI is not installed"
    echo "Install it from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

echo "✅ gcloud CLI found"

# Check current project
CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null)
echo "📦 Current GCP Project: $CURRENT_PROJECT"
echo ""

read -p "Is this the correct project? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Please set the correct project with: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

echo ""
echo "🔨 Starting deployment..."
echo ""

# Deploy to Cloud Run
gcloud run deploy $SERVICE_NAME \
  --source . \
  --region=$REGION \
  --platform=managed \
  --allow-unauthenticated \
  --set-env-vars ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
  --set-env-vars FLASK_ENV=production \
  --memory=512Mi \
  --cpu=1 \
  --timeout=300 \
  --max-instances=3 \
  --min-instances=0

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Deployment successful!"
    echo ""
    echo "🌐 Service URL:"
    gcloud run services describe $SERVICE_NAME --region=$REGION --format="value(status.url)"
    echo ""
    echo "📊 Check logs with:"
    echo "  gcloud run services logs read $SERVICE_NAME --region=$REGION"
    echo ""
    echo "✨ Test your AI features:"
    SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format="value(status.url)")
    echo "  Home: $SERVICE_URL"
    echo "  Meal Plan: $SERVICE_URL/meal-plan"
    echo ""
else
    echo ""
    echo "❌ Deployment failed!"
    echo "Check the error messages above for details."
    exit 1
fi
