# Chat Assistant Error Debugging Guide

## Overview

When the chat assistant shows "I encountered an error," it's now much more helpful with specific error messages and detailed server logs.

---

## Improved Error Messages

### Before
```
❌ Generic: "I encountered an error. Could you please rephrase your request?"
```

### After
```
✅ Specific error messages:
- "API rate limit reached. Please wait a moment and try again."
- "Request timed out. Please try again."
- "API authentication issue. Please check your API key."
- "Database connection issue. Your message was received but couldn't be saved."
- "(ValueError: Invalid stockcode format)"
```

---

## Common Errors & Solutions

### 1. Rate Limit Error
**Message:** "API rate limit reached. Please wait a moment and try again."

**Cause:** Too many API requests in short time

**Solution:**
- Wait 1-2 minutes before trying again
- Reduce frequency of requests
- Consider upgrading API tier

---

### 2. Timeout Error
**Message:** "Request timed out. Please try again."

**Cause:** API took too long to respond

**Solution:**
- Try again (usually temporary)
- Simplify your request
- Check internet connection

---

### 3. Authentication Error
**Message:** "API authentication issue. Please check your API key."

**Cause:** Invalid or expired ANTHROPIC_API_KEY

**Solution:**
```bash
# Check if API key is set
echo $ANTHROPIC_API_KEY

# Set it in Cloud Run
gcloud run services update woolies-shopper \
  --update-env-vars ANTHROPIC_API_KEY=sk-ant-...
```

---

### 4. Database Error
**Message:** "Database connection issue. Your message was received but couldn't be saved."

**Cause:** Firestore connection problem

**Solution:**
- Check Firestore is enabled in GCP console
- Verify service account has Firestore permissions
- Check network connectivity

---

### 5. Tool Input Error
**Message:** "Invalid tool parameters. Could you rephrase your request?"

**Cause:** AI provided invalid parameters to a tool

**Solution:**
- Rephrase your request more clearly
- Use specific stockcodes (numbers only)
- Example: "For yogurt use 571487" instead of "For yogurt use stockcode 571487abc"

---

### 6. Other Errors
**Message:** "(ErrorType: error details...)"

**Cause:** Unexpected error with details included

**Solution:**
- Check server logs for full traceback
- Note the error type and message
- Try rephrasing your request

---

## Server Logs

### What Gets Logged

When a chat request comes in, you'll see:

```
🤖 Chat request: 'For greek yogurt use 571487'
📋 Shopping list categories: 5 categories
📝 System message length: 2847 chars
🔄 Calling Claude API (model: claude-3-haiku-20240307)...
✅ Claude API responded (stop_reason: tool_use)
📤 Response action: set_preferred
```

### Where to Find Logs

**Local Development:**
```bash
# Flask console output
python flask_app.py
```

**Google Cloud Run:**
```bash
# View logs
gcloud run services logs read woolies-shopper --limit 50

# Follow logs in real-time
gcloud run services logs tail woolies-shopper
```

**GCP Console:**
1. Go to https://console.cloud.google.com/run
2. Click on `woolies-shopper` service
3. Click "LOGS" tab
4. Filter by severity or search for errors

---

## Debugging Steps

### Step 1: Try Again
Sometimes errors are temporary. Try your request again.

### Step 2: Simplify Request
If complex request fails, break it down:

**Instead of:**
```
"Set preferences for yogurt 571487, milk 888140, and eggs 205222"
```

**Try:**
```
"For yogurt use 571487"
[wait for response]
"For milk use 888140"
[wait for response]
```

### Step 3: Check Logs
View server logs to see the full error:

```bash
gcloud run services logs read woolies-shopper --limit 50 | grep -A 10 "Chat error"
```

### Step 4: Verify Input Format
Make sure your input matches expected format:

**Correct:**
- ✅ "For greek yogurt use 571487"
- ✅ "For yogurt use 571487, fallbacks 123456 and 789012"
- ✅ "What are my preferences?"

**Incorrect:**
- ❌ "For yogurt use stockcode-571487" (letters in number)
- ❌ "Set preference yogurt = 571487" (wrong syntax)
- ❌ "Save 571487" (missing ingredient name)

---

## Error Log Examples

### Successful Request
```
🤖 Chat request: 'For greek yogurt use 571487'
📋 Shopping list categories: 0 categories
📝 System message length: 2134 chars
🔄 Calling Claude API (model: claude-3-haiku-20240307)...
✅ Claude API responded (stop_reason: tool_use)
📤 Response action: set_preferred
💚 Using preferred product for 'greek yogurt': ...
✅ Saved preference: greek yogurt → Woolworths Natural Greek Style Yoghurt 1kg
```

### Failed Request (Rate Limit)
```
🤖 Chat request: 'For banana use 306510'
📋 Shopping list categories: 0 categories
📝 System message length: 2134 chars
🔄 Calling Claude API (model: claude-3-haiku-20240307)...
Chat error: rate_limit_error: Rate limit exceeded
Traceback (most recent call last):
  ...
  anthropic.RateLimitError: Rate limit exceeded
```

### Failed Request (Invalid Stockcode)
```
🤖 Chat request: 'For yogurt use abc123'
📋 Shopping list categories: 0 categories
📝 System message length: 2134 chars
🔄 Calling Claude API (model: claude-3-haiku-20240307)...
✅ Claude API responded (stop_reason: tool_use)
📤 Response action: set_preferred
❌ Error saving preference: invalid literal for int() with base 10: 'abc123'
```

---

## Prevention Tips

### 1. Use Valid Stockcodes
Always use numeric stockcodes from Woolworths products.

### 2. Be Specific
Use clear, specific ingredient names.

### 3. One Action at a Time
For complex operations, break into multiple requests.

### 4. Check Responses
Wait for confirmation before sending next request.

### 5. Monitor API Usage
Keep track of your API quota to avoid rate limits.

---

## Testing Error Handling

### Test Rate Limit Handling
```
# Send many requests quickly (don't do this in production!)
for i in {1..20}; do
  curl -X POST http://localhost:5000/api/shopping-chat \
    -H "Content-Type: application/json" \
    -d '{"message": "test"}'
done
```

### Test Invalid Input
```
"For yogurt use invalid_stockcode"
→ Should show: "(ValueError: invalid literal...)"
```

### Test Database Error
```
# Stop Firestore temporarily, then:
"What are my preferences?"
→ Should show: "Database connection issue..."
```

---

## Getting Help

If you encounter persistent errors:

1. **Check server logs** for detailed error trace
2. **Note the exact error message** shown to user
3. **Copy the request** that caused the error
4. **Check API status** at status.anthropic.com
5. **Verify environment variables** are set correctly

---

## Recent Improvements

### Version: November 27, 2025

**Added:**
- ✅ Specific error messages for common issues
- ✅ Detailed server logging with emojis
- ✅ Error type and details in response
- ✅ Full traceback in server logs
- ✅ Stop reason logging from Claude API

**Improved:**
- ✅ Rate limit error detection
- ✅ Timeout error detection
- ✅ Authentication error detection
- ✅ Database error detection
- ✅ Tool input validation error detection

---

## Date Created
November 27, 2025
