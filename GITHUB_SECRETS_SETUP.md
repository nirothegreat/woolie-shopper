# 🔐 GitHub Secrets Setup Guide

## Overview

Your API keys are now stored as **GitHub Secrets** instead of being hardcoded in the repository. This is a security best practice!

---

## 🎯 **Step 1: Add Your API Key as a GitHub Secret**

### **Via GitHub Website**:

1. **Go to your repository**: https://github.com/nirothegreat/woolie-shopper

2. **Click on Settings** (top right of repo page)

3. **In the left sidebar**, click:
   - **Secrets and variables** → **Actions**

4. **Click "New repository secret"**

5. **Add your secret**:
   - **Name**: `ANTHROPIC_API_KEY`
   - **Value**: `your-actual-anthropic-api-key-here`
   - **Click "Add secret"**

6. **Done!** ✅

---

## 🚀 **Step 2: Use the Secret Locally**

### **For Local Development**:

Create a `.env` file in your project root:

```bash
# Create .env file
cat > .env << 'EOF'
ANTHROPIC_API_KEY=your-actual-anthropic-api-key-here
FLASK_ENV=development
EOF
```

**Note**: `.env` is already in `.gitignore` so it won't be committed!

### **For Deployment Script**:

```bash
# Option 1: Export for current session
export ANTHROPIC_API_KEY='your-key-here'
./deploy_google_cloud.sh

# Option 2: Add to your shell profile (permanent)
echo 'export ANTHROPIC_API_KEY="your-key-here"' >> ~/.zshrc
source ~/.zshrc
```

---

## 🤖 **Step 3: GitHub Actions (Optional)**

If you want to automate deployments with GitHub Actions, the secret is already available!

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Cloud Run

on:
  push:
    branches: [main]
  workflow_dispatch:  # Manual trigger

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
      
      - name: Setup Google Cloud
        uses: google-github-actions/setup-gcloud@v1
        with:
          service_account_key: ${{ secrets.GCP_SA_KEY }}
          project_id: woolies-shopper-1763510471
      
      - name: Deploy to Cloud Run
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          gcloud run deploy woolies-shopper \
            --source . \
            --region=us-central1 \
            --platform=managed \
            --allow-unauthenticated \
            --set-env-vars ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
            --memory=1Gi \
            --cpu=2 \
            --timeout=300
```

**Note**: You'll also need to add `GCP_SA_KEY` as a GitHub Secret for this to work.

---

## 🔒 **Security Benefits**

### **Before** (Hardcoded):
```bash
❌ API key visible in code
❌ API key in git history
❌ API key visible to anyone who clones repo
❌ Can't share repo safely
```

### **After** (GitHub Secrets):
```bash
✅ API key stored securely in GitHub
✅ Never committed to git
✅ Only accessible to you and GitHub Actions
✅ Can share repo publicly
✅ Easy to rotate keys
```

---

## 🔄 **Rotating Your API Key**

If you need to change your API key:

1. **Generate new key** from Anthropic console

2. **Update GitHub Secret**:
   - Go to Settings → Secrets → Actions
   - Click on `ANTHROPIC_API_KEY`
   - Click "Update secret"
   - Paste new key
   - Click "Update secret"

3. **Update local `.env`** file with new key

4. **Redeploy** if needed

---

## 📋 **Additional Secrets to Add**

You may want to add these as GitHub Secrets too:

### **1. GCP_SA_KEY** (for GitHub Actions deployment)
- **Name**: `GCP_SA_KEY`
- **Value**: Your Google Cloud service account JSON key
- **Used for**: Automated deployments via GitHub Actions

### **2. WOOLWORTHS_COOKIES** (if automating)
- **Name**: `WOOLWORTHS_COOKIES`
- **Value**: Your Woolworths session cookies
- **Used for**: Automated product search

---

## 🧪 **Testing Your Setup**

### **Test Locally**:
```bash
# Make sure .env exists
cat .env

# Run Flask app
python flask_app.py

# Should see: "✅ Claude AI initialized"
```

### **Test Deployment**:
```bash
# Export the key
export ANTHROPIC_API_KEY='your-key-here'

# Run deployment script
./deploy_google_cloud.sh

# Should see: "API Key: sk-ant-api03... ✓"
```

---

## 🚨 **Troubleshooting**

### **Error: "ANTHROPIC_API_KEY environment variable not set"**

**Solution**:
```bash
# Check if it's set
echo $ANTHROPIC_API_KEY

# If empty, export it
export ANTHROPIC_API_KEY='your-key-here'
```

### **GitHub Actions failing with "API key not found"**

**Solution**:
1. Go to repo Settings → Secrets → Actions
2. Verify `ANTHROPIC_API_KEY` exists
3. Check the workflow YAML uses `${{ secrets.ANTHROPIC_API_KEY }}`

---

## 📚 **Best Practices**

✅ **DO**:
- Store all API keys as secrets
- Use `.env` for local development
- Add `.env` to `.gitignore`
- Rotate keys periodically
- Use different keys for dev/prod

❌ **DON'T**:
- Commit API keys to git
- Share secrets in chat/email
- Use production keys in dev
- Hardcode secrets in code

---

## ✅ **Summary**

**What Changed**:
- ❌ Removed hardcoded API key from `deploy_google_cloud.sh`
- ✅ Script now reads from environment variable
- ✅ Repository is now safe to share publicly

**Setup Steps**:
1. Add `ANTHROPIC_API_KEY` as GitHub Secret
2. Create `.env` file locally (or export variable)
3. Deploy using `./deploy_google_cloud.sh`

**Your API key is now secure!** 🔐
