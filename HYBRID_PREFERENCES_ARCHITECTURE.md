# Hybrid Preferences Architecture

## Overview

The system uses a **hybrid approach** combining:
1. **Database** (Firestore) - User-specific preferences with fallbacks
2. **Prompts** (AI) - Intelligent fallback logic and reasoning

This gives you the best of both worlds: flexibility + intelligence.

---

## Why Hybrid?

### ❌ Database Only
```javascript
{ingredient: "yogurt", stockcode: 571487}
// Problem: What if out of stock? No fallback logic.
```

### ❌ Prompts Only
```
"Always use Woolworths Greek Yogurt (571487)"
// Problem: Hardcoded, requires redeployment, not user-specific
```

### ✅ Hybrid (Best!)
```javascript
// Database: User's choices + fallbacks
{
  ingredient: "greek yogurt",
  stockcode: 571487,          // Primary choice
  fallback_stockcodes: [      // If primary unavailable
    123456,  // Chobani Greek Yogurt
    789012   // Jalna Greek Yogurt
  ]
}
```

```json
// Prompts: AI reasoning
"💚 PREFERRED PRODUCTS FALLBACK LOGIC:
- Try primary → Try fallbacks → Search similar products
- Maintain quality level, brand preference, price range"
```

---

## How It Works

### Flow Diagram

```
Shopping List: "greek yogurt - 500g"
        ↓
┌───────────────────────────────────────┐
│  STEP 1: Check Database               │
│  Query: greek yogurt → User's prefs   │
└───────────┬───────────────────────────┘
            ↓
    Found preference?
            ↓
    ┌───YES───┐
    ↓         
┌───────────────────────────────────────┐
│  STEP 2: Try Primary Product          │
│  Stockcode: 571487                    │
│  Check: Is it available?              │
└───────────┬───────────────────────────┘
            ↓
    Available?
    ↓         ↓
  YES        NO
    ↓         ↓
  USE IT   ┌────────────────────────────┐
           │  STEP 3: Try Fallbacks     │
           │  Loop through: [123456...] │
           │  Check each for availability│
           └────────┬───────────────────┘
                    ↓
            Found available?
            ↓              ↓
          YES             NO
            ↓              ↓
          USE IT    ┌──────────────────┐
                    │  STEP 4: AI       │
                    │  Search + reason  │
                    │  Use prompt logic │
                    └──────────────────┘
```

---

## Architecture Components

### 1. Database Schema (Firestore)

```javascript
Collection: preferred_products

Document: {
  // Identity
  user_id: "default",
  ingredient_name: "greek yogurt",      // Normalized
  original_name: "Greek Yogurt",       // As entered
  
  // Primary choice
  stockcode: 571487,
  product_name: "Woolworths Natural Greek Style Yoghurt 1kg",
  price: 3.80,
  image_url: "https://...",
  
  // Fallback chain (NEW!)
  fallback_stockcodes: [
    123456,  // Chobani Greek Yogurt 907g
    789012   // Jalna Greek Yogurt 1kg
  ],
  
  // Metadata
  added_date: timestamp,
  last_used: timestamp,
  use_count: 5
}
```

### 2. Prompts Logic (AI)

```json
"💚 PREFERRED PRODUCTS FALLBACK LOGIC:
- The system may have saved preferred products
- If preferred product unavailable:
  * Try fallback alternatives (from database)
  * Search for similar products (organic, brand, size)
  * Maintain quality level
  * Keep similar price range
- Example: Woolworths yogurt → Chobani → search 'organic greek yogurt'"
```

### 3. Code Logic (Matcher)

```python
def search_product(ingredient):
    # 1. Check database for preference
    pref = get_preferred_product(ingredient)
    
    if pref:
        # 2. Try primary
        if is_available(pref.stockcode):
            return pref  # ✅ Use it!
        
        # 3. Try fallbacks
        for fallback in pref.fallback_stockcodes:
            if is_available(fallback):
                return fallback  # ✅ Use fallback!
        
        # 4. All unavailable - log and search
        print("⚠️ All preferences unavailable")
    
    # 5. Search Woolworths (AI uses prompt logic)
    return search_woolworths(ingredient)
```

---

## Usage Examples

### Example 1: Primary Available

```python
# Database has:
{
  ingredient: "greek yogurt",
  stockcode: 571487,
  fallback_stockcodes: [123456, 789012]
}

# Shopping list: "greek yogurt - 500g"
# Matcher: Check 571487 → Available ✅
# Result: Woolworths Natural Greek Style Yoghurt 1kg
```

**Log:**
```
💚 Checking preferred product for 'greek yogurt': Woolworths Natural Greek Style Yoghurt 1kg
✅ Using preferred: Woolworths Natural Greek Style Yoghurt 1kg
```

### Example 2: Fallback Used

```python
# Database has:
{
  ingredient: "greek yogurt",
  stockcode: 571487,  # Out of stock
  fallback_stockcodes: [123456, 789012]
}

# Shopping list: "greek yogurt - 500g"
# Matcher: Check 571487 → Unavailable ❌
# Matcher: Try 123456 → Available ✅
# Result: Chobani Greek Yogurt 907g
```

**Log:**
```
💚 Checking preferred product for 'greek yogurt': Woolworths Natural Greek Style Yoghurt 1kg
⚠️ Preferred product unavailable, trying 2 fallbacks...
✅ Using fallback: Chobani Greek Yogurt 907g
```

### Example 3: All Unavailable - AI Search

```python
# Database has:
{
  ingredient: "greek yogurt",
  stockcode: 571487,  # Out of stock
  fallback_stockcodes: [123456, 789012]  # Both out
}

# Shopping list: "greek yogurt - 500g"
# Matcher: Check 571487 → Unavailable ❌
# Matcher: Try 123456 → Unavailable ❌
# Matcher: Try 789012 → Unavailable ❌
# Matcher: Search Woolworths (AI prompt guides search)
# Result: Finds similar organic greek yogurt
```

**Log:**
```
💚 Checking preferred product for 'greek yogurt'
⚠️ Preferred product unavailable, trying 2 fallbacks...
⚠️ All fallbacks unavailable, searching...
🔍 Searching for 'greek yogurt'...
✅ Found: Farmers Union Greek Style Yoghurt 1kg
```

---

## Setting Preferences

### Method 1: Simple (Primary Only)

```python
from preferred_products_manager import get_preferred_products_manager

manager = get_preferred_products_manager()

manager.set_preferred_product(
    ingredient_name="greek yogurt",
    stockcode=571487
)
```

### Method 2: With Fallbacks (Recommended)

```python
manager.set_preferred_product(
    ingredient_name="greek yogurt",
    stockcode=571487,              # Primary
    product_name="Woolworths Natural Greek Style Yoghurt 1kg",
    price=3.80,
    fallback_stockcodes=[          # Fallbacks
        123456,  # Chobani
        789012   # Jalna
    ]
)
```

### Method 3: Via Chat (Future)

```
User: "For greek yogurt, use stockcode 571487, and if unavailable try 123456 or 789012"
Assistant: ✅ Saved preference with 2 fallbacks
```

---

## Benefits

### 1. Resilient to Stock Issues
- Primary out? → Try fallback #1
- Fallback #1 out? → Try fallback #2
- All out? → AI searches intelligently

### 2. User-Specific
- Each user can have different preferences
- Stored in database, not code
- Easy to update without redeployment

### 3. Intelligent Fallback
- AI understands context from prompts
- Searches for "similar" products
- Maintains quality/price expectations

### 4. Flexible
- Add more fallbacks anytime
- Update preferences easily
- Works with existing AI logic

---

## Comparison Table

| Feature | Database Only | Prompts Only | Hybrid |
|---------|--------------|--------------|--------|
| User-specific | ✅ | ❌ | ✅ |
| Fallback logic | ❌ | ✅ | ✅ |
| Update without deploy | ✅ | ❌ | ✅ |
| AI reasoning | ❌ | ✅ | ✅ |
| Multiple fallbacks | ❌ | ⚠️ Limited | ✅ |
| Easy to manage | ✅ | ❌ | ✅ |

---

## Real-World Scenario

**Your Shopping Habits:**
- You love **Woolworths Natural Greek Style Yoghurt 1kg** (571487)
- But sometimes it's out of stock
- You're okay with **Chobani** (123456) as backup
- Or **Jalna** (789012) if Chobani is also out

**Setup:**
```python
manager.set_preferred_product(
    "greek yogurt",
    571487,
    fallback_stockcodes=[123456, 789012]
)
```

**Results Over Time:**

| Week | Primary | Fallback 1 | Fallback 2 | Result |
|------|---------|------------|------------|--------|
| 1 | ✅ Available | - | - | Used Woolworths |
| 2 | ❌ Out | ✅ Available | - | Used Chobani |
| 3 | ✅ Available | - | - | Used Woolworths |
| 4 | ❌ Out | ❌ Out | ✅ Available | Used Jalna |
| 5 | ✅ Available | - | - | Used Woolworths |

**You always get greek yogurt, even when your favorite is out!** ✅

---

## Migration Path

### Step 1: Current Simple Preferences
```python
# What you have now
manager.set_preferred_product("greek yogurt", 571487)
```

### Step 2: Add Fallbacks Later
```python
# Update with fallbacks
manager.set_preferred_product(
    "greek yogurt", 
    571487,
    fallback_stockcodes=[123456, 789012]
)
```

### Step 3: AI Learns (Future)
```
System notices when fallbacks are used
AI suggests: "Want to add 789012 as fallback for greek yogurt?"
```

---

## Best Practices

### 1. Start Simple
Add primary preference first, add fallbacks as you discover them.

### 2. Test Fallbacks
Make sure fallback products are actually similar (size, quality).

### 3. Order Fallbacks by Preference
Put your 2nd favorite first, 3rd favorite second, etc.

### 4. Use 2-3 Fallbacks Max
Too many fallbacks = confusion. Keep it simple.

### 5. Update When Products Change
If a fallback is discontinued, remove it.

---

## Summary

**Hybrid = Database + Prompts**

✅ Database stores your choices (flexible, user-specific)  
✅ Prompts guide AI behavior (intelligent, context-aware)  
✅ Code orchestrates the flow (resilient, fallback handling)  

**Result:** The most robust and user-friendly preference system! 🎯

---

## Date Created
November 27, 2025

## Related Files
- `preferred_products_manager.py` - Database operations
- `shopping_list_matcher.py` - Fallback logic
- `prompts.json` - AI reasoning
- `PREFERRED_PRODUCTS_GUIDE.md` - User guide
