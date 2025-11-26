# Pumpkin Cubes Rule - Updated

## Overview
Special handling for pumpkin cubes to use fresh cut pumpkin instead of pre-packaged cubes, and avoid duplicates.

## Rule Implementation

### When the shopping list contains "pumpkin cubes" or "pre-cut pumpkin cubes":

1. **Substitution**: Replace with "1/2 cut pumpkin" or "butternut pumpkin cut"
   - Searches for: "butternut pumpkin cut"
   - Gets fresh cut pumpkin instead of pre-packaged cubes
   - Better quality and value

2. **Duplicate Prevention**: Skip if pumpkin already in list
   - If "pumpkin", "butternut pumpkin cut", or "1/2 cut pumpkin" already exists → skip the cubes
   - Prevents buying both cut pumpkin and pre-packaged cubes
   - One 1/2 cut pumpkin typically provides 3-4 cups of cubes

## Architecture: AI-Driven Approach

This rule is implemented **ONLY in prompts.json** (the AI layer).

**Why?** We trust the AI completely to handle substitutions and duplicate detection during list generation.
The matcher just does simple product search - no business logic.

### Single Source of Truth: `prompts.json`

Added pumpkin cubes rule to the AI shopping list optimizer:
```
🎃 PUMPKIN CUBES SPECIAL RULE:
- If the list includes 'pumpkin cubes' or 'pre-cut pumpkin cubes':
  * SUBSTITUTE with: '1/2 cut pumpkin' or 'butternut pumpkin cut' (whole cut pumpkin, not pre-diced)
  * DO NOT add if '1/2 cut pumpkin', 'butternut pumpkin cut', or 'pumpkin' already exists in the list
  * Reason: Fresh cut pumpkin is better quality than pre-packaged cubes
  * When combining quantities: One 1/2 cut pumpkin typically provides 3-4 cups of cubes
```

### What About `shopping_list_matcher.py`?

**Simple product search only** - no special logic needed.
The AI has already done the substitution and duplicate detection when it created the list.

```
Recipe has "pumpkin cubes - 4 cups"
  ↓
AI reads prompt rules
  ↓
AI checks if pumpkin already in list
  ↓
If yes: AI skips it (no duplicate)
If no: AI writes "butternut pumpkin cut - 1/2 pumpkin"
  ↓
Matcher searches Woolworths for "butternut pumpkin cut"
  ↓
Done! ✅
```

## Benefits

✅ **Fresh Quality**: Cut pumpkin is fresher than pre-packaged cubes
✅ **Better Value**: Whole cut pumpkin is typically better value per weight
✅ **No Duplicates**: Won't buy both cut pumpkin and pre-packaged cubes
✅ **Consistent**: Works across both AI planning and product matching

## Quantity Guidelines

- **1/2 cut butternut pumpkin** ≈ 3-4 cups of cubes (600-800g)
- **Whole butternut pumpkin cut** ≈ 6-8 cups of cubes

## Example Scenarios

### Scenario 1: Pumpkin cubes in list
```
Input: "pumpkin cubes - 4 cups"
Output: Searches for "butternut pumpkin cut"
Result: Gets 1/2 cut butternut pumpkin
```

### Scenario 2: Both pumpkin and pumpkin cubes
```
Input:
  - "butternut pumpkin cut - 600g" (from Recipe 1)
  - "pumpkin cubes - 4 cups" (from Recipe 2)
  
Processing:
  1. Adds butternut pumpkin cut ✅
  2. Sees pumpkin cubes → checks if pumpkin exists
  3. Pumpkin already added → skips cubes 🎃
  
Result: Only 1 pumpkin item (no duplicate)
```

### Scenario 3: Only pumpkin cubes from one recipe
```
Input: "pumpkin cubes - 2 cups"
Output: Searches for "butternut pumpkin cut"
Result: Gets 1/2 cut butternut pumpkin
```

## Testing

To test this rule:
1. Create a recipe with "pumpkin cubes"
2. Generate a shopping list (AI will read the prompts)
3. Check the output - should say "butternut pumpkin cut" or "1/2 cut pumpkin"
4. Should never see "pumpkin cubes" in the final list

To test duplicate prevention:
1. Create two recipes: one with "pumpkin" and one with "pumpkin cubes"
2. Generate shopping list
3. Should only see ONE pumpkin item in the output (no duplicate)

## Date Created
November 26, 2025
