# Mushroom Quantity Rule

## Overview
Special handling for mushroom quantities to use decimal kilograms format for proper ordering at Woolworths.

## Rule Implementation

### When the shopping list contains "mushrooms":

**Always express quantity in decimal kilograms** (e.g., 0.5kg, 0.2kg, 1.0kg)

### Conversions

Common conversions the AI should apply:

| Recipe Says | AI Converts To |
|-------------|----------------|
| 200g mushrooms | 0.2kg |
| 500g mushrooms | 0.5kg |
| 1 cup mushrooms | 0.2kg |
| 2 cups mushrooms | 0.4kg |
| 250g mushrooms | 0.25kg |
| 1kg mushrooms | 1.0kg |

### Why This Rule?

- Woolworths sells loose mushrooms by weight
- Decimal kg format (0.5kg) is clearer than fractions or grams
- Pre-packaged mushrooms often come in kg increments (0.2kg, 0.5kg, etc.)
- Easier to order the right amount

## Architecture: AI-Driven

This rule is implemented **ONLY in prompts.json** (the AI layer).

### Single Source of Truth: `prompts.json`

```
🍄 MUSHROOM QUANTITY RULE:
- When the list includes 'mushrooms':
  * ALWAYS express quantity in DECIMAL kilograms (e.g., 0.5kg, 0.2kg, 1.0kg)
  * DO NOT use cups, grams for small amounts, or fractions
  * Examples: '200g' → '0.2kg', '1 cup' → '0.2kg', '500g' → '0.5kg'
  * Reason: Woolworths sells mushrooms by weight in decimal kg format
```

### What About the Matcher?

**No changes needed.** The AI has already converted to decimal kg format when it created the list.

```
Recipe has "mushrooms - 1 cup"
  ↓
AI reads prompt rules
  ↓
AI converts: 1 cup ≈ 200g ≈ 0.2kg
  ↓
AI writes "mushrooms - 0.2kg"
  ↓
Matcher searches Woolworths for "mushrooms"
  ↓
Done! ✅
```

## Example Scenarios

### Scenario 1: Small amount
```
Input: "mushrooms - 1 cup"
AI Output: "mushrooms - 0.2kg"
Result: Clear decimal format
```

### Scenario 2: Weight in grams
```
Input: "mushrooms - 250g"
AI Output: "mushrooms - 0.25kg"
Result: Converted to decimal kg
```

### Scenario 3: Multiple recipes
```
Input:
  - "mushrooms - 200g" (Recipe 1)
  - "mushrooms - 1 cup" (Recipe 2)
  
AI Processing:
  1. Convert: 200g → 0.2kg
  2. Convert: 1 cup → 0.2kg
  3. Combine: 0.2kg + 0.2kg = 0.4kg
  
AI Output: "mushrooms - 0.4kg"
```

## Benefits

✅ **Clear Format**: Decimal kg is easy to understand
✅ **Matches Store**: How Woolworths sells mushrooms
✅ **Easy Combining**: Simple to add up (0.2 + 0.3 = 0.5)
✅ **No Confusion**: Avoids mixing units (g, cups, kg)

## Approximate Conversions

For reference:
- **1 cup sliced mushrooms** ≈ 70-80g ≈ 0.075kg → round to **0.1kg**
- **1 cup whole mushrooms** ≈ 100g ≈ 0.1kg → use **0.1kg**
- **Standard punnet** = 200g = **0.2kg**
- **Large pack** = 400-500g = **0.5kg**

The AI should use these guidelines when converting from cups to kg.

## Testing

To test this rule:
1. Create a recipe with "mushrooms - 1 cup"
2. Generate a shopping list (AI will read the prompts)
3. Check the output - should say "mushrooms - 0.2kg" (not "1 cup" or "200g")
4. Test with multiple recipes - should combine in decimal kg format

## Date Created
November 26, 2025
