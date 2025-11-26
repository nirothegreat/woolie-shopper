# Chicken Tender Rule - Updated

## Overview
Special handling for chicken tenders to ensure fresh, organic options instead of frozen processed products.

## Rule Implementation

### When the shopping list contains "chicken tenders" or "chicken tenderloins":

1. **First Priority**: Search for organic fresh chicken tenderloins
   - Searches for: "organic chicken tenderloin"
   - Filters out any frozen products
   - Filters out Ingham's brand (typically frozen)

2. **Fallback Option**: If no organic chicken tenderloins found
   - Automatically substitutes with: "Macro Organic Chicken Thigh Fillets"
   - Fresh, high-quality organic alternative

## Architecture: AI-Driven Approach

This rule is implemented **ONLY in prompts.json** (the AI layer).

**Why?** We trust the AI completely to handle substitutions during list generation.
The matcher just does simple product search - no business logic.

### Single Source of Truth: `prompts.json`

Added chicken tender rule to the AI shopping list optimizer:
```
🐔 CHICKEN TENDERS SPECIAL RULE:
- If the list includes 'chicken tenders' or 'chicken tenderloins':
  * DO NOT use frozen chicken tenders (avoid Ingham's frozen or similar)
  * PREFER: Organic fresh chicken tenderloins (search for 'organic chicken tenderloins')
  * FALLBACK: If organic chicken tenderloins not available, substitute with 'Macro Organic Chicken Thigh Fillets'
  * This ensures fresh, high-quality chicken instead of frozen processed products
```

### What About `shopping_list_matcher.py`?

**Simple product search only** - no special logic needed.
The AI has already done the intelligent substitution when it created the list.

```
AI sees "chicken tenders" in recipe
  ↓
AI reads prompt rules
  ↓
AI writes "organic chicken tenderloins" to shopping list
  ↓
Matcher searches Woolworths for "organic chicken tenderloins"
  ↓
Done! ✅
```

## Benefits

✅ **Fresh over Frozen**: Always prioritizes fresh chicken
✅ **Organic Quality**: Seeks organic options first
✅ **Smart Fallback**: Has a good alternative if first choice unavailable
✅ **Consistent**: Works across both AI planning and product matching

## Testing

To test this rule:
1. Create a recipe with "chicken tenders" or "chicken tenderloins"
2. Generate a shopping list (AI will read the prompts)
3. Check the output - should say "organic chicken tenderloins" or "Macro Organic Chicken Thigh Fillets"
4. Should never see "frozen chicken tenders" or "Ingham's chicken tenders" in the list

## Date Created
November 26, 2025
