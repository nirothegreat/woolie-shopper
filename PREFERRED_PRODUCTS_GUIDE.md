# Preferred Products System - Complete Guide

## Overview

The Preferred Products system lets you save your favorite Woolworths products for specific ingredients. When generating shopping lists, the system will automatically use your preferred products instead of searching.

### Benefits

✅ **Consistent**: Always get the brands/products you like  
✅ **Faster**: No need to search, uses saved stockcodes  
✅ **Flexible**: Update preferences anytime via chat  
✅ **Smart**: Tracks usage and preferences per ingredient  

---

## How It Works

```
Shopping List: "greek yogurt - 500g"
         ↓
Check: Is there a preferred product?
         ↓
    YES → Use Woolworths Natural Greek Style Yoghurt (571487)
     NO → Search Woolworths for "greek yogurt"
         ↓
Matched Product Ready!
```

---

## Initial Setup (One-Time)

### Method 1: Manual Entry (Recommended First Time)

1. **Add items to your Woolworths cart manually**
   - Go to woolworths.com.au
   - Add all your preferred items (the ones you already know you like)
   - Note down the stockcodes

2. **Extract preferences**

   Edit `extract_cart_preferences.py` and add your preferences:
   
   ```python
   MANUAL_PREFERENCES = {
       "greek yogurt": 571487,
       "banana": 306510,
       "eggs": 205222,
       "milk": 888140,
       # Add more...
   }
   ```

3. **Run the extraction script**
   ```bash
   python extract_cart_preferences.py
   ```

### Method 2: From Current Cart (via MCP)

If you have items in your current Woolworths cart:

```python
from preferred_products_manager import get_preferred_products_manager

# Get cart via MCP tools
cart_items = mcp0_woolworths_get_cart()

# Import to preferences
manager = get_preferred_products_manager()
manager.import_from_cart(cart_items['Products'])
```

---

## Using via Shopping Chat Assistant

Once set up, you can manage preferences through the chat interface:

### View Current Preferences

```
User: "What are my preferred products?"
Assistant: Shows list of all saved preferences
```

### Add New Preference

```
User: "For greek yogurt, always use stockcode 571487"
Assistant: ✅ Saved preference: greek yogurt → Woolworths Natural Greek Style Yoghurt 1kg
```

```
User: "When I need bananas, get the organic ones - stockcode 306510"
Assistant: ✅ Saved preference: banana → Macro Organic Banana
```

### Update Existing Preference

```
User: "Actually, for milk use stockcode 123456 instead"
Assistant: ✅ Updated preference: milk → [New Product Name]
```

### Remove Preference

```
User: "Remove my preference for tomatoes"
Assistant: ✅ Removed preference for tomatoes
```

---

## How It Affects Shopping Lists

### Without Preferences
```
Shopping List:
  - greek yogurt - 500g

Matcher searches Woolworths → finds first result
Result: May vary each time
```

### With Preferences
```
Shopping List:
  - greek yogurt - 500g

Matcher checks preferences → finds stockcode 571487
Result: Always gets Woolworths Natural Greek Style Yoghurt 1kg ✅
```

---

## Example: Complete Workflow

### 1. First Time Setup

```bash
# You already have items in your cart from manual shopping
# Current cart has:
# - Woolworths Natural Greek Style Yoghurt 1kg (571487)
# - Macro Organic Banana (306510)
# - Woolworths 12 Extra Large Free Range Eggs (205222)

# Edit extract_cart_preferences.py:
MANUAL_PREFERENCES = {
    "greek yogurt": 571487,
    "banana": 306510,
    "eggs": 205222,
}

# Run extraction:
$ python extract_cart_preferences.py
✅ Saved: greek yogurt → Woolworths Natural Greek Style Yoghurt 1kg
✅ Saved: banana → Macro Organic Banana
✅ Saved: eggs → Woolworths 12 Extra Large Free Range Eggs
```

### 2. Generate Shopping List

```python
# Create meal plan with recipes that need greek yogurt

# Generate shopping list
# When it gets to "greek yogurt - 500g"
# System checks preferences → finds 571487
# Uses Woolworths Natural Greek Style Yoghurt 1kg ✅
```

### 3. Update Preferences via Chat

```
User: "For chicken, always use Macro Organic Chicken Thigh Fillets - stockcode 789012"
Assistant: ✅ Added preference: chicken → Macro Organic Chicken Thigh Fillets
```

---

## API Reference

### PreferredProductsManager

```python
from preferred_products_manager import get_preferred_products_manager

manager = get_preferred_products_manager()
```

#### Set Preference

```python
manager.set_preferred_product(
    ingredient_name="greek yogurt",
    stockcode=571487,
    product_name="Woolworths Natural Greek Style Yoghurt 1kg",
    price=3.80,
    user_id="default"  # Multi-user support
)
```

#### Get Preference

```python
pref = manager.get_preferred_product("greek yogurt")
# Returns: {'stockcode': 571487, 'product_name': '...', ...}
```

#### List All Preferences

```python
prefs = manager.list_all_preferences()
for pref in prefs:
    print(f"{pref['ingredient_name']} → {pref['product_name']}")
```

#### Remove Preference

```python
manager.remove_preferred_product("greek yogurt")
```

---

## Storage Structure

Preferences are stored in Firestore:

```javascript
Collection: preferred_products

{
  user_id: "default",
  ingredient_name: "greek yogurt",     // Normalized
  original_name: "Greek Yoghurt",     // As entered
  stockcode: 571487,
  product_name: "Woolworths Natural Greek Style Yoghurt 1kg",
  price: 3.80,
  image_url: "https://...",
  added_date: "2025-11-26T...",
  last_used: "2025-11-26T...",
  use_count: 5                         // Tracks popularity
}
```

---

## Tips & Best Practices

### 1. Start Small
Don't add all items at once. Start with 5-10 items you buy most frequently.

### 2. Normalize Names
The system normalizes ingredient names, so:
- "Greek Yogurt"
- "greek yogurt"
- "Greek yoghurt"

All match to the same preference ✅

### 3. Review Periodically
Check your preferences occasionally:
```python
prefs = manager.list_all_preferences()
# See which items you use most (use_count)
```

### 4. Use Chat for Updates
Instead of editing code, just tell the assistant:
```
"Update my yogurt preference to stockcode 123456"
```

### 5. Track New Items
When you try a new product and like it:
```
"Save this as my preferred [ingredient] - stockcode [XXXXX]"
```

---

## Integration Points

### 1. Shopping List Matcher
`shopping_list_matcher.py` automatically checks preferences before searching.

### 2. Shopping Chat Assistant
Chat tools for managing preferences (to be added).

### 3. Meal Planning
Works seamlessly - just generate meal plans as normal.

---

## Troubleshooting

### Preference Not Being Used

**Check:**
1. Is the ingredient name normalized correctly?
2. Is the stockcode still valid/available?
3. Are preferences enabled in the matcher?

**Debug:**
```python
manager = get_preferred_products_manager()
pref = manager.get_preferred_product("your ingredient")
print(pref)  # Should show the preference
```

### Stockcode Not Found

The product may be discontinued or out of stock.

**Solution:**
1. Find new product on woolworths.com.au
2. Get new stockcode
3. Update preference:
   ```python
   manager.set_preferred_product("ingredient", new_stockcode, ...)
   ```

---

## Future Enhancements

- 🎯 Auto-suggest preferences based on purchase history
- 📊 Analytics on most-used preferences
- 🔄 Sync preferences across devices
- 💰 Track price changes on preferred products
- 🎨 UI for managing preferences

---

## Quick Reference

| Task | Command |
|------|---------|
| Setup first time | Edit `extract_cart_preferences.py` + run it |
| Add via chat | "For [ingredient] use stockcode [XXXXX]" |
| View all | `manager.list_all_preferences()` |
| Remove | `manager.remove_preferred_product("ingredient")` |
| Check if used | Look for 💚 in matcher logs |

---

## Date Created
November 26, 2025

## Related Files
- `preferred_products_manager.py` - Core logic
- `shopping_list_matcher.py` - Uses preferences
- `extract_cart_preferences.py` - Initial setup
- `shopping_chat_agent_native.py` - Chat interface (to be updated)
