# Managing Preferences via Chat Assistant

## Overview

You can now manage all your product preferences through natural conversation with the AI Shopping Assistant! No need to edit code or run scripts - just chat naturally.

---

## 🎯 What You Can Do

### 1. Save Preferred Products
Tell the assistant which products you prefer, and it will save them permanently.

### 2. Add Fallback Options
Specify alternatives in case your preferred product is out of stock.

### 3. View Your Preferences
Ask to see all your saved preferences at any time.

### 4. Remove Preferences
Delete preferences you no longer want.

---

## 💬 Example Conversations

### Save a Simple Preference

**User:** "For greek yogurt, use stockcode 571487"

**Assistant:** ✅ Saved preference: greek yogurt → Woolworths Natural Greek Style Yoghurt 1kg

**What happened:** The system:
1. Looked up product details for stockcode 571487
2. Saved it to Firestore
3. Next shopping list with "greek yogurt" will automatically use this product

---

### Save with Fallbacks

**User:** "For greek yogurt use 571487, and if that's out try 123456 or 789012"

**Assistant:** ✅ Saved preference: greek yogurt → Woolworths Natural Greek Style Yoghurt 1kg with 2 fallback(s)

**What happened:** 
- Primary: 571487
- Fallback 1: 123456  
- Fallback 2: 789012
- System tries in order until it finds one available

---

### Natural Language (Brand Preference)

**User:** "I always buy Macro Organic bananas"

**Assistant:** Let me find that for you... Would you like me to save Macro Organic Banana (stockcode 306510) as your preferred banana?

**User:** "Yes"

**Assistant:** ✅ Saved preference: banana → Macro Organic Banana

---

### View All Preferences

**User:** "What are my preferred products?"

**Assistant:** 📋 Your 5 preferred products:
  • greek yogurt → Woolworths Natural Greek Style Yoghurt 1kg (571487) - used 12 times
  • banana → Macro Organic Banana (306510) - used 8 times
  • eggs → Woolworths 12 Extra Large Free Range Eggs (205222) - used 5 times
  • milk → Woolworths Full Cream Milk 3L (888140) - used 3 times
  • chicken → Macro Organic Chicken Thigh Fillets (789012) - used 2 times

---

### Update an Existing Preference

**User:** "Actually for milk, use stockcode 999888 instead"

**Assistant:** ✅ Saved preference: milk → Pura Full Cream Milk 2L (updated)

**What happened:** The old preference was replaced with the new one.

---

### Remove a Preference

**User:** "Remove my preference for tomatoes"

**Assistant:** ✅ Removed preference for tomatoes

**What happened:** Next time you need tomatoes, the system will search normally.

---

### Add Fallback to Existing Preference

**User:** "For my greek yogurt preference, add 123456 as a fallback"

**Assistant:** ✅ Updated preference: greek yogurt → Woolworths Natural Greek Style Yoghurt 1kg with 1 fallback

---

## 🔍 Ways to Phrase Your Requests

### Setting Preferences

✅ "For [ingredient], use stockcode [XXXXX]"  
✅ "When I need [ingredient], always get [brand/product]"  
✅ "Save [brand] as my preferred [ingredient]"  
✅ "I prefer [brand] for [ingredient]"  
✅ "Always buy [product]"  

### With Fallbacks

✅ "For [ingredient] use [stockcode], and if unavailable try [fallback]"  
✅ "If [product] is out, get [alternative]"  
✅ "Add [stockcode] as a fallback for [ingredient]"  

### Viewing Preferences

✅ "What are my preferred products?"  
✅ "Show my preferences"  
✅ "What yogurt do I usually get?"  
✅ "List all my saved products"  

### Removing Preferences

✅ "Remove my preference for [ingredient]"  
✅ "Stop using [brand] for [ingredient]"  
✅ "Delete my [ingredient] preference"  
✅ "Forget my preference for [ingredient]"  

---

## 🎯 Real-World Workflow

### Scenario: First Time Setup

**Step 1: Start chatting**
```
User: "Hi! I want to set up my preferred products"
Assistant: "Great! I can help you save your favorite brands. 
Which products would you like to set preferences for?"
```

**Step 2: Save preferences**
```
User: "For greek yogurt use 571487"
Assistant: ✅ Saved preference: greek yogurt → Woolworths Natural Greek Style Yoghurt 1kg

User: "For bananas use 306510"
Assistant: ✅ Saved preference: banana → Macro Organic Banana

User: "For eggs use 205222, and if that's out try 205223"
Assistant: ✅ Saved preference: eggs → Woolworths 12 Extra Large Free Range Eggs with 1 fallback
```

**Step 3: Verify**
```
User: "What have I saved?"
Assistant: 📋 Your 3 preferred products:
  • greek yogurt → Woolworths Natural Greek Style Yoghurt 1kg (571487)
  • banana → Macro Organic Banana (306510)
  • eggs → Woolworths 12 Extra Large Free Range Eggs (205222) - 1 fallback
```

**Done!** Next shopping list will automatically use these products.

---

### Scenario: Update After Shopping

You went shopping and found a product you like better:

```
User: "I tried a different yogurt and prefer it - stockcode 999888"
Assistant: ✅ Saved preference: yogurt → Chobani Greek Yogurt 907g (updated)

User: "Show my yogurt preference"
Assistant: Your preference for yogurt: Chobani Greek Yogurt 907g (999888) - used 0 times
```

---

### Scenario: Handle Out of Stock

You notice your preferred product is often out of stock:

```
User: "My greek yogurt is often unavailable. Add 123456 as fallback"
Assistant: ✅ Updated preference: greek yogurt → Woolworths Natural Greek Style Yoghurt 1kg with 1 fallback

User: "Actually add one more fallback - 789012"
Assistant: ✅ Updated preference: greek yogurt → Woolworths Natural Greek Style Yoghurt 1kg with 2 fallbacks
```

Now your preference has a chain: 571487 → 123456 → 789012 → search

---

## 🛠️ How It Works Behind the Scenes

### When You Save a Preference

1. **AI receives your message**
   ```
   "For greek yogurt use 571487"
   ```

2. **AI calls set_preferred_product tool**
   ```python
   set_preferred_product(
       ingredient="greek yogurt",
       stockcode=571487
   )
   ```

3. **System looks up product details**
   - Queries Woolworths API for stockcode 571487
   - Gets: name, price, image, availability

4. **Saves to Firestore**
   ```javascript
   {
     ingredient_name: "greek yogurt",
     stockcode: 571487,
     product_name: "Woolworths Natural Greek Style Yoghurt 1kg",
     price: 3.80,
     fallback_stockcodes: [],
     added_date: "2025-11-27...",
     use_count: 0
   }
   ```

5. **Confirms to you**
   ```
   ✅ Saved preference: greek yogurt → Woolworths Natural Greek Style Yoghurt 1kg
   ```

### When You Generate a Shopping List

1. **Meal plan includes "greek yogurt - 500g"**

2. **Matcher checks Firestore**
   - Found preference: stockcode 571487

3. **Matcher checks availability**
   - Is 571487 available? YES → Use it! 💚
   - Not available? → Try fallback #1
   - Not available? → Try fallback #2
   - All out? → AI searches intelligently

4. **Result: Your preferred product (or best fallback)**

---

## 📊 Tracking & Stats

### Usage Tracking

Every time your preference is used:
- `use_count` increments
- `last_used` updates

**View stats:**
```
User: "What are my most used preferences?"
Assistant: Your top 3:
  • banana → used 45 times
  • milk → used 32 times
  • eggs → used 28 times
```

### History

The system tracks:
- When preference was added
- Last time it was used
- How many times used
- Current price (updated on use)

---

## 💡 Pro Tips

### Tip 1: Save After Finding Good Products

After searching and finding something you like:
```
User: "Search for organic chicken"
Assistant: [shows results]
User: "Save the first one as my chicken preference"
Assistant: ✅ Saved preference: chicken → Macro Organic Chicken Breast Fillets
```

### Tip 2: Set Up Fallbacks From the Start

```
User: "For eggs use 205222, with fallbacks 205223 and 205224"
```
Better than dealing with out-of-stock later!

### Tip 3: Be Specific with Ingredient Names

✅ "greek yogurt" (specific)  
❌ "yogurt" (too broad)

The matcher normalizes names, so these work:
- "Greek Yogurt" = "greek yogurt" = "Greek yoghurt" ✅

### Tip 4: Update Preferences When Prices Change

```
User: "My milk is too expensive. Find a cheaper one"
Assistant: [searches]
User: "Update my milk preference to stockcode [XXXXX]"
```

### Tip 5: Review Periodically

```
User: "Show my unused preferences"
Assistant: These haven't been used in 30+ days:
  • maple syrup (last used: 2 months ago)
  • quinoa (never used)
```

---

## 🚨 Troubleshooting

### "Could not find product details for stockcode"

**Problem:** Invalid or discontinued stockcode

**Solution:**
1. Search for the product first
2. Get the current stockcode
3. Save the new one

```
User: "Search for Woolworths greek yogurt"
Assistant: Found: Woolworths Natural Greek Style Yoghurt 1kg (571487)
User: "Save that as my preference"
```

### "No preference found for [ingredient]"

**Problem:** Trying to update/remove non-existent preference

**Solution:** Check your preferences first
```
User: "What are my preferences?"
[verify the ingredient name matches]
```

### Preference Not Being Used

**Problem:** Ingredient name doesn't match

**Solution:** Be consistent with naming
```
✅ Saved as "chicken" → Search for "chicken" (matches)
❌ Saved as "chicken breast" → Search for "chicken" (doesn't match)
```

---

## 🎊 Summary

**Old Way:**
```python
# Edit extract_cart_preferences.py
MANUAL_PREFERENCES = {
    "greek yogurt": 571487,
}
# Run script
python extract_cart_preferences.py
```

**New Way:**
```
User: "For greek yogurt use 571487"
Assistant: ✅ Saved!
```

**That's it!** No code, no scripts, just natural conversation. 🎉

---

## Related Documentation

- `PREFERRED_PRODUCTS_GUIDE.md` - Overall system guide
- `HYBRID_PREFERENCES_ARCHITECTURE.md` - Technical architecture
- `PREFERRED_PRODUCTS_IMPLEMENTATION.md` - Implementation details

---

## Date Created
November 27, 2025
