# 🎯 Prompt Management System

## Overview

All AI prompts are now **externalized** from the code! This means you can tune and improve the AI's behavior **without redeploying** the entire service.

---

## 📁 **Where Prompts Are Stored**

### **1. Local File** (Default)
**File**: `prompts.json`

```json
{
  "meal_plan_generation": {
    "system": "You are an expert meal planning assistant...",
    "user_template": "Create a meal plan..."
  },
  "shopping_list_optimization": {
    "system": "You are a smart shopping list optimizer...",
    "user_template": "INGREDIENTS FROM RECIPES:..."
  },
  "shopping_chat_assistant": {
    "system_template": "You are a helpful shopping assistant..."
  }
}
```

### **2. Firestore** (Optional - For Real-Time Updates)
**Collection**: `config`  
**Document**: `prompts`

Enable with environment variable:
```bash
USE_FIRESTORE_PROMPTS=true
```

---

## 🔧 **How to Update Prompts**

### **Method 1: Edit Local File** (Requires Redeploy)

1. **Edit** `prompts.json`
2. **Test locally** (prompts reload every 5 minutes in development)
3. **Deploy** to Cloud Run:
   ```bash
   gcloud run deploy woolies-shopper --source .
   ```

**Pros**: Simple, version controlled  
**Cons**: Requires redeployment

---

### **Method 2: Via Firestore** (Real-Time, No Redeploy!)

#### **Setup**:

1. **Enable Firestore prompts**:
   ```bash
   gcloud run services update woolies-shopper \
     --set-env-vars USE_FIRESTORE_PROMPTS=true \
     --region=us-central1
   ```

2. **Upload initial prompts** to Firestore:
   ```python
   from google.cloud import firestore
   import json
   
   db = firestore.Client()
   with open('prompts.json', 'r') as f:
       prompts = json.load(f)
   
   db.collection('config').document('prompts').set(prompts)
   print("✅ Prompts uploaded to Firestore!")
   ```

#### **Update Prompts** (No Deployment Needed!):

**Via Firebase Console**:
1. Go to https://console.firebase.google.com/
2. Select your project → Firestore Database
3. Navigate to `config` → `prompts`
4. Edit any prompt field
5. **Changes apply within 5 minutes!**

**Via Python Script**:
```python
from google.cloud import firestore

db = firestore.Client()
doc_ref = db.collection('config').document('prompts')

# Update a specific prompt
doc_ref.update({
    'shopping_list_optimization.system': 'New improved prompt here...'
})
```

**Pros**: Real-time updates, no redeploy  
**Cons**: Requires Firestore setup

---

## 📝 **Available Prompts**

### **1. Meal Plan Generation**

**Keys**:
- `meal_plan_generation.system` - System instructions
- `meal_plan_generation.user_template` - User prompt template

**Variables**:
- `{recipes_text}` - List of available recipes
- `{preferences_text}` - Family preferences
- `{additional_context}` - User's custom instructions

**What to Tune**:
- Adjust how AI handles Maya/Ehren specific meals
- Change leftover planning strategy
- Modify cuisine variety requirements
- Add/remove meal planning constraints

---

### **2. Shopping List Optimization**

**Keys**:
- `shopping_list_optimization.system` - System instructions
- `shopping_list_optimization.user_template` - User prompt template

**Variables**:
- `{ingredients_list}` - Raw ingredients from recipes
- `{staples_list}` - Staples to add
- `{organic_text}` - Organic preferences
- `{subs_text}` - Substitutions

**What to Tune**:
- Adjust duplicate combining rules
- Change categorization logic
- Modify quantity handling (THIS IS CRITICAL!)
- Add/remove formatting rules

**Example Fix for Cucumber Issue**:
Add more examples of correct combining:
```
- "cucumber 1" + "cucumber 0.75" + "cucumber 0.5" → "cucumber - 2.25" ✅
```

---

### **3. Shopping Chat Assistant**

**Keys**:
- `shopping_chat_assistant.system_template` - System instructions

**Variables**:
- `{list_text}` - Current shopping list

**What to Tune**:
- Adjust proactivity level
- Change how it suggests preferred products
- Modify personality/tone
- Add new features or suggestions

---

## 🎨 **Prompt Tuning Examples**

### **Example 1: Make Shopping List More Aggressive About Combining**

**Before**:
```json
"CRITICAL RULES:
1. NEVER REDUCE QUANTITIES!..."
```

**After** (add more emphasis):
```json
"⚠️⚠️⚠️ CRITICAL RULES - THIS IS EXTREMELY IMPORTANT:

1. NEVER EVER REDUCE QUANTITIES! This is the #1 rule!
   If you see cucumber appearing 3 times with quantities 1, 0.75, and 0.5,
   you MUST output cucumber with AT LEAST 2.25 (1 + 0.75 + 0.5).
   
   ❌ WRONG: Outputting anything less than the sum
   ✅ RIGHT: Sum all quantities, round UP if converting units..."
```

---

### **Example 2: Make Meal Planner More Varied**

**Before**:
```json
"- Lunch and dinner can repeat for 2-3 consecutive days (leftovers)"
```

**After** (more variety):
```json
"- Lunch and dinner can repeat for 2 days maximum
- Aim for different cuisines each day
- No recipe should appear more than once in the same week"
```

---

### **Example 3: Make Chat Assistant More Helpful**

**Add to prompt**:
```json
"PROACTIVE SUGGESTIONS YOU SHOULD MAKE:
- If list has chicken, suggest: 'Would you like me to add herbs, spices, or marinades?'
- If list has pasta, suggest: 'Should I add pasta sauce or cheese?'
- If list has vegetables, suggest: 'Would you like olive oil or butter for cooking?'
- Always ask: 'Do you have any of these items at home already?'"
```

---

## 🧪 **Testing Prompt Changes**

### **Local Testing**:

1. **Edit** `prompts.json`
2. **Restart Flask** (prompts reload on startup)
3. **Test** the feature:
   - Generate meal plan
   - Generate shopping list
   - Chat with assistant
4. **Verify** behavior changed as expected

### **Production Testing** (with Firestore):

1. **Update** prompt in Firestore Console
2. **Wait** 5 minutes (cache expires)
3. **Test** on live site
4. **Monitor** logs for issues:
   ```bash
   gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=woolies-shopper" --limit=20
   ```

---

## 🔍 **Monitoring Prompts**

### **Check Which Prompts Are Loaded**:

Add to Flask app:
```python
@app.route('/admin/prompts/current')
def view_current_prompts():
    pm = get_prompt_manager()
    prompts = pm.get_prompts()
    return jsonify(prompts)
```

Visit: `https://your-app.com/admin/prompts/current`

---

## 💡 **Best Practices**

### **1. Version Your Prompts**

Update metadata when you change prompts:
```json
"_metadata": {
  "version": "1.1.0",
  "last_updated": "2025-11-24",
  "changelog": "Fixed cucumber combining issue"
}
```

### **2. Keep Old Versions**

Before major changes:
```bash
cp prompts.json prompts_v1.0.0_backup.json
```

### **3. Test Incrementally**

- Change one prompt at a time
- Test thoroughly before changing another
- If something breaks, revert to previous version

### **4. Document Your Changes**

In the prompt itself:
```json
"shopping_list_optimization.user_template": "
  // Updated 2025-11-24: Added more examples for cucumber combining
  // Reason: AI was reducing quantities instead of adding them
  
  CRITICAL RULES:
  ..."
```

---

## 🚨 **Troubleshooting**

### **Prompts Not Loading?**

1. **Check syntax**:
   ```bash
   python3 -c "import json; json.load(open('prompts.json'))"
   ```

2. **Check logs**:
   ```bash
   gcloud logging read "resource.labels.service_name=woolies-shopper AND textPayload:prompt" --limit=10
   ```

3. **Force reload**:
   ```python
   pm = get_prompt_manager()
   pm.get_prompts(force_reload=True)
   ```

### **Changes Not Applying?**

- **File-based**: Redeploy required
- **Firestore**: Wait 5 minutes for cache to expire
- **Check**: Firestore is enabled (`USE_FIRESTORE_PROMPTS=true`)

---

## 📊 **Prompt Versioning Strategy**

### **Semantic Versioning**:

- **1.0.0** → Initial prompts
- **1.1.0** → Minor improvements (add examples)
- **1.2.0** → Add new features (new sections)
- **2.0.0** → Major changes (complete rewrite)

### **Track Changes**:

```json
"_metadata": {
  "version": "1.2.0",
  "last_updated": "2025-11-24",
  "changelog": [
    "1.2.0: Added more cucumber combining examples",
    "1.1.0: Improved categorization rules",
    "1.0.0: Initial prompts"
  ]
}
```

---

## 🎯 **Quick Reference**

| Task | File-Based | Firestore |
|------|-----------|-----------|
| **Update prompt** | Edit `prompts.json` | Edit Firestore doc |
| **Deploy changes** | Redeploy Cloud Run | None needed! |
| **Time to apply** | ~5-10 minutes | ~5 minutes |
| **Rollback** | Git revert + redeploy | Restore old doc |
| **Version control** | Git | Manual/scripted |

---

## ✅ **Summary**

**What Changed**:
- ✅ All AI prompts moved to `prompts.json`
- ✅ Optional Firestore storage for real-time updates
- ✅ 5-minute cache for performance
- ✅ No code changes needed to tune AI behavior

**Benefits**:
- 🚀 Iterate on prompts quickly
- 🔧 Fix issues without full redeploy
- 📝 Easy A/B testing
- 🎯 Better AI tuning workflow

**Get Started**:
1. Edit `prompts.json` for your needs
2. Test locally
3. Deploy
4. (Optional) Enable Firestore for real-time updates

---

**You can now improve the AI without touching code!** 🎉
