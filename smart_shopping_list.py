"""
Smart Shopping List Generator - Rule-based approach (no AI needed!)
Combines ingredients, applies preferences, and categorizes intelligently
"""

from typing import List, Dict
import re
from collections import defaultdict

class SmartShoppingListGenerator:
    """Intelligent rule-based shopping list generator"""
    
    def __init__(self):
        # Category mappings with extensive keywords
        self.category_map = {
            'Fresh Produce': [
                'lettuce', 'spinach', 'kale', 'arugula', 'salad', 'greens',
                'tomato', 'cucumber', 'carrot', 'celery', 'onion', 'garlic', 'ginger',
                'potato', 'sweet potato', 'pumpkin', 'squash', 'zucchini', 'eggplant',
                'capsicum', 'pepper', 'chili', 'jalapeno',
                'broccoli', 'cauliflower', 'cabbage', 'brussels sprout',
                'apple', 'banana', 'orange', 'lemon', 'lime', 'avocado',
                'strawberry', 'strawberries', 'blueberry', 'blueberries', 'raspberry', 'raspberries',
                'grape', 'mango', 'pineapple', 'berry', 'berries',
                'melon', 'watermelon', 'peach', 'pear', 'plum', 'cherry', 'cherries',
                'mushroom', 'corn', 'peas', 'bean', 'beans', 'asparagus', 'beetroot',
                'parsley', 'cilantro', 'coriander', 'basil', 'mint', 'dill', 'thyme', 'rosemary',
                'oregano', 'sage', 'tarragon', 'chives',
                'produce', 'vegetable', 'fruit', 'herb', 'fresh', 'zest'
            ],
            'Dairy & Eggs': [
                'milk', 'cream', 'yogurt', 'yoghurt', 'cheese', 'butter', 'egg',
                'sour cream', 'cottage cheese', 'ricotta', 'mozzarella', 'parmesan',
                'cheddar', 'feta', 'brie', 'cream cheese', 'whipped cream'
            ],
            'Meat & Seafood': [
                'chicken', 'beef', 'pork', 'lamb', 'turkey', 'duck',
                'bacon', 'ham', 'sausage', 'salami', 'prosciutto',
                'fish', 'salmon', 'tuna', 'cod', 'prawns', 'shrimp', 'seafood',
                'mince', 'steak', 'chop', 'roast', 'fillet', 'breast', 'thigh', 'wing',
                'meat', 'protein'
            ],
            'Pantry Staples': [
                'flour', 'sugar', 'salt', 'pepper', 'oil', 'vinegar',
                'rice', 'pasta', 'noodle', 'macaroni', 'couscous', 'quinoa',
                'sauce', 'paste', 'stock', 'broth', 'bouillon',
                'spice', 'seasoning', 'cumin', 'paprika', 'turmeric', 'curry',
                'cinnamon', 'nutmeg', 'vanilla', 'extract',
                'honey', 'syrup', 'jam', 'peanut butter', 'tahini',
                'canned', 'tin', 'chickpea', 'lentil', 'kidney bean', 'black bean',
                'coconut milk', 'condensed milk', 'evaporated milk', 'almond milk',
                'baking powder', 'baking soda', 'yeast', 'cornstarch', 'cornflour',
                'breadcrumb', 'panko', 'chia seed', 'chia', 'flax', 'sesame',
                'clove', 'cloves', 'mustard', 'chili powder', 'garlic powder', 'onion powder',
                'italian herb', 'dried herb', 'chili flakes', 'stevia'
            ],
            'Bakery': [
                'bread', 'roll', 'bun', 'bagel', 'croissant', 'muffin',
                'tortilla', 'wrap', 'pita', 'naan', 'flatbread',
                'cake', 'pastry', 'cookie', 'biscuit'
            ],
            'Frozen': [
                'frozen', 'ice cream', 'sorbet', 'gelato',
                'frozen vegetables', 'frozen fruit', 'frozen meal'
            ],
            'Beverages': [
                'water', 'juice', 'soda', 'soft drink', 'tea', 'coffee',
                'wine', 'beer', 'spirits', 'alcohol', 'drink', 'beverage'
            ],
            'Snacks': [
                'chip', 'crisp', 'cracker', 'popcorn', 'pretzel',
                'chocolate', 'candy', 'lolly', 'snack', 'nut', 'almond', 'cashew'
            ]
        }
    
    def generate_optimized_list(self, 
                               raw_ingredients: List[Dict],
                               organic_preferences: List[str] = None,
                               substitutions: List[Dict] = None,
                               staples: List[Dict] = None) -> Dict:
        """
        Generate an optimized shopping list with smart categorization
        
        Args:
            raw_ingredients: List of ingredients from recipes
            organic_preferences: List of items to prefer organic
            substitutions: List of ingredient substitutions
            staples: List of staple items to check
            
        Returns:
            Dict with categories, shopping_tips, and cost_saving_suggestions
        """
        
        organic_preferences = organic_preferences or []
        substitutions = substitutions or []
        staples = staples or []
        
        # Step 1: Normalize and combine duplicates
        combined = self._combine_duplicates(raw_ingredients)
        
        # Step 2: Apply substitutions
        combined = self._apply_substitutions(combined, substitutions)
        
        # Step 3: Apply organic preferences
        combined = self._apply_organic_preferences(combined, organic_preferences)
        
        # Step 4: Add unchecked staples
        for staple in staples:
            if not staple.get('in_stock', False):
                combined.append({
                    'name': staple['name'],
                    'quantity': staple['quantity'],
                    'unit': staple.get('unit', ''),
                    'notes': 'Staple item'
                })
        
        # Step 5: Categorize intelligently
        categories = self._categorize_items(combined)
        
        # Step 6: Generate helpful tips
        tips = self._generate_tips(combined, organic_preferences)
        cost_saving = self._generate_cost_saving_tips(combined)
        
        return {
            'categories': categories,
            'shopping_tips': tips,
            'cost_saving_suggestions': cost_saving,
            'total_items': len(combined)
        }
    
    def _combine_duplicates(self, ingredients: List[Dict]) -> List[Dict]:
        """Combine duplicate ingredients intelligently"""
        
        # Group by normalized name
        groups = defaultdict(list)
        
        for item in ingredients:
            name = item.get('name', item.get('ingredient_name', '')).lower().strip()
            # Normalize name (remove extra spaces, etc)
            name = ' '.join(name.split())
            groups[name].append(item)
        
        combined = []
        for name, items in groups.items():
            if len(items) == 1:
                combined.append(items[0])
            else:
                # Multiple items with same name - combine quantities if possible
                total_qty = 0
                unit = items[0].get('unit', '')
                notes = []
                
                # Try to sum numeric quantities
                can_sum = True
                for item in items:
                    qty_str = str(item.get('quantity', '1'))
                    # Extract number from quantity
                    match = re.search(r'(\d+\.?\d*)', qty_str)
                    if match:
                        total_qty += float(match.group(1))
                    else:
                        can_sum = False
                        break
                
                if can_sum and total_qty > 0:
                    # Successfully combined
                    combined.append({
                        'name': name,
                        'quantity': f"{total_qty:.1f}".rstrip('0').rstrip('.'),
                        'unit': unit,
                        'notes': f'Combined from {len(items)} recipes'
                    })
                else:
                    # Can't combine - keep separate
                    for idx, item in enumerate(items, 1):
                        item_copy = item.copy()
                        item_copy['notes'] = f'From recipe {idx}'
                        combined.append(item_copy)
        
        return combined
    
    def _apply_substitutions(self, ingredients: List[Dict], substitutions: List[Dict]) -> List[Dict]:
        """Apply ingredient substitutions"""
        
        if not substitutions:
            return ingredients
        
        # Build substitution map
        sub_map = {}
        for sub in substitutions:
            original = sub.get('original_ingredient', '').lower()
            replacement = sub.get('replacement', '')
            if original and replacement:
                sub_map[original] = replacement
        
        # Apply substitutions
        result = []
        for item in ingredients:
            name = item.get('name', item.get('ingredient_name', '')).lower()
            
            if name in sub_map:
                item_copy = item.copy()
                item_copy['name'] = sub_map[name]
                item_copy['notes'] = item_copy.get('notes', '') + f' (Substituted from {name})'
                result.append(item_copy)
            else:
                result.append(item)
        
        return result
    
    def _apply_organic_preferences(self, ingredients: List[Dict], organic_prefs: List[str]) -> List[Dict]:
        """Add organic prefix to preferred items"""
        
        if not organic_prefs:
            return ingredients
        
        organic_set = {pref.lower() for pref in organic_prefs}
        
        result = []
        for item in ingredients:
            name = item.get('name', item.get('ingredient_name', ''))
            name_lower = name.lower()
            
            # Check if any organic preference matches
            should_be_organic = any(pref in name_lower for pref in organic_set)
            
            if should_be_organic and 'organic' not in name_lower:
                item_copy = item.copy()
                item_copy['name'] = f'organic {name}'
                item_copy['notes'] = item_copy.get('notes', '') + ' 🌱'
                result.append(item_copy)
            else:
                result.append(item)
        
        return result
    
    def _categorize_items(self, ingredients: List[Dict]) -> Dict[str, List[Dict]]:
        """Categorize items into shopping categories"""
        
        categories = defaultdict(list)
        
        for item in ingredients:
            name = item.get('name', item.get('ingredient_name', '')).lower()
            category = self._get_category(name)
            
            # Format item for display
            formatted_item = {
                'item': item.get('name', item.get('ingredient_name', '')),
                'quantity': item.get('quantity', '1'),
                'unit': item.get('unit', ''),
                'notes': item.get('notes', '')
            }
            
            categories[category].append(formatted_item)
        
        # Sort items within each category
        for category in categories:
            categories[category].sort(key=lambda x: x['item'].lower())
        
        # Convert to regular dict and sort by category importance
        category_order = [
            'Fresh Produce',
            'Dairy & Eggs',
            'Meat & Seafood',
            'Bakery',
            'Pantry Staples',
            'Frozen',
            'Beverages',
            'Snacks',
            'Other'
        ]
        
        sorted_categories = {}
        for cat in category_order:
            if cat in categories:
                sorted_categories[cat] = categories[cat]
        
        # Add any remaining categories
        for cat, items in categories.items():
            if cat not in sorted_categories:
                sorted_categories[cat] = items
        
        return sorted_categories
    
    def _get_category(self, item_name: str) -> str:
        """Determine the category for an item"""
        
        item_name = item_name.lower()
        
        # Check each category's keywords
        for category, keywords in self.category_map.items():
            for keyword in keywords:
                if keyword in item_name:
                    return category
        
        return 'Other'
    
    def _generate_tips(self, ingredients: List[Dict], organic_prefs: List[str]) -> List[str]:
        """Generate helpful shopping tips"""
        
        tips = []
        
        # Count categories
        categories = set()
        for item in ingredients:
            name = item.get('name', item.get('ingredient_name', '')).lower()
            categories.add(self._get_category(name))
        
        # Tip about produce section
        if 'Fresh Produce' in [self._get_category(item.get('name', '').lower()) for item in ingredients]:
            tips.append("🥬 Start with fresh produce to ensure best quality")
        
        # Organic tip
        organic_count = sum(1 for item in ingredients if 'organic' in item.get('name', '').lower())
        if organic_count > 0:
            tips.append(f"🌱 {organic_count} organic items marked with preference")
        
        # Shopping efficiency
        if len(ingredients) > 20:
            tips.append(f"📝 {len(ingredients)} items total - consider shopping online or using a list app")
        
        return tips
    
    def _generate_cost_saving_tips(self, ingredients: List[Dict]) -> List[str]:
        """Generate cost-saving suggestions"""
        
        tips = []
        
        # Check for expensive items
        expensive_keywords = ['beef', 'lamb', 'salmon', 'prawns', 'shrimp', 'organic']
        expensive_items = [
            item for item in ingredients
            if any(kw in item.get('name', '').lower() for kw in expensive_keywords)
        ]
        
        if len(expensive_items) > 3:
            tips.append("💰 Consider buying meat/seafood on special or in bulk")
        
        # Seasonal produce tip
        tips.append("🌿 Buy seasonal produce for better prices and quality")
        
        # Bulk buying
        pantry_count = sum(1 for item in ingredients 
                          if self._get_category(item.get('name', '').lower()) == 'Pantry Staples')
        if pantry_count > 5:
            tips.append("📦 Pantry staples often cheaper in bulk")
        
        return tips


# Helper function for Flask app
def generate_smart_shopping_list(raw_ingredients, organic_preferences=None, 
                                 substitutions=None, staples=None):
    """Convenience function for Flask app"""
    generator = SmartShoppingListGenerator()
    return generator.generate_optimized_list(
        raw_ingredients, 
        organic_preferences, 
        substitutions, 
        staples
    )
