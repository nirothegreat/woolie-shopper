# AI-Driven Architecture

## Philosophy: Trust the AI

The Woolies Shopper system uses an **AI-driven architecture** where all intelligent decision-making happens in one place: **the AI layer via prompts**.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      RECIPES                                │
│  (ingredients needed for meals)                             │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                   AI LAYER (Claude)                         │
│                                                             │
│  Reads: prompts.json                                        │
│  ├─ Chicken tender rule                                    │
│  ├─ Pumpkin cubes rule                                     │
│  ├─ Organic preferences                                    │
│  ├─ Quantity combining logic                               │
│  └─ Duplicate detection                                    │
│                                                             │
│  Makes ALL intelligent decisions here ↓                    │
└─────────────────────────────────────────────────────────────┘
                          │
                          ↓
┌─────────────────────────────────────────────────────────────┐
│              OPTIMIZED SHOPPING LIST                        │
│  (AI has already done substitutions & deduplication)       │
│  Example:                                                   │
│  - "organic chicken tenderloins - 500g"                    │
│  - "butternut pumpkin cut - 1/2 pumpkin"                   │
│  - "macro organic chicken thigh - 600g"                    │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ↓
┌─────────────────────────────────────────────────────────────┐
│           MATCHER (shopping_list_matcher.py)                │
│                                                             │
│  Does: Simple product search in Woolworths                 │
│  Searches for exact terms from the list                    │
│  NO special logic - just searches!                         │
│                                                             │
│  Example:                                                   │
│  - Search "organic chicken tenderloins"                    │
│  - Search "butternut pumpkin cut"                          │
│  - Return stockcodes & prices                              │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ↓
┌─────────────────────────────────────────────────────────────┐
│              WOOLWORTHS PRODUCTS                            │
│  (actual products with stockcodes & prices)                │
└─────────────────────────────────────────────────────────────┘
```

## Single Source of Truth

### ✅ All Business Logic in `prompts.json`

- Chicken tender → organic substitution
- Pumpkin cubes → cut pumpkin substitution  
- Duplicate detection
- Quantity combining
- Organic preferences
- Cost optimization suggestions

### ❌ NO Business Logic in Code

- `shopping_list_matcher.py` is just a search utility
- No if/else for special cases
- No duplicate detection
- No substitution logic
- Just: "Search for this term in Woolworths"

## Benefits

### 1. **Easy to Update**
Change a rule? Just edit `prompts.json`. No code changes needed.

### 2. **Clear Responsibility**
- AI = Smart decisions
- Matcher = Dumb search
- No confusion about where logic lives

### 3. **Testable**
Test AI behavior by checking the shopping list it generates.
If list is wrong, fix the prompt. If search is wrong, fix the matcher.

### 4. **Maintainable**
New rules? Add to prompts. No need to update multiple files.

### 5. **Transparent**
All the "why" is in the prompts. Read the prompt to understand the behavior.

## Example: Chicken Tenders

### ❌ OLD WAY (Logic in Two Places)
```python
# In prompts.json
"prefer organic chicken tenderloins"

# In shopping_list_matcher.py
if 'chicken tender' in ingredient:
    search_query = 'organic chicken tenderloin'
    # ... filter frozen products
    # ... fallback to thigh fillets
```
→ Logic duplicated! Must update 2 places.

### ✅ NEW WAY (Single Source of Truth)
```python
# In prompts.json
"🐔 CHICKEN TENDERS SPECIAL RULE:
 - substitute with organic chicken tenderloins
 - fallback to Macro Organic Chicken Thigh Fillets"

# In shopping_list_matcher.py
def search_product(ingredient):
    return search_woolworths(ingredient)  # Simple!
```
→ AI does the substitution. Matcher just searches.

## When Would You NOT Use This?

This architecture works when:
- ✅ AI is reliable and follows prompts well
- ✅ Shopping list generation is always AI-powered
- ✅ You want easy updates via prompt changes

You might need code logic if:
- ❌ AI frequently ignores prompts
- ❌ Users manually create lists (no AI involved)
- ❌ Complex logic that AI can't handle

## Current Status

As of November 26, 2025:
- ✅ All special rules in `prompts.json`
- ✅ Matcher simplified to just search
- ✅ Documentation updated
- ✅ Cleaner architecture

## Files

- **Business Logic**: `prompts.json`
- **Search Utility**: `shopping_list_matcher.py`
- **Rule Docs**: 
  - `CHICKEN_TENDER_RULE.md`
  - `PUMPKIN_CUBES_RULE.md`
