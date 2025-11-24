"""
Unified Recipe Manager - Works with SQLite locally and Firestore on GCP
"""

from typing import List, Dict, Optional
from config import Config

class RecipeManager:
    """Unified interface for recipe database operations"""
    
    def __init__(self):
        """Initialize the appropriate database backend"""
        self.backend = None
        self.db_type = Config().database_type
        
        if self.db_type == 'firestore':
            try:
                from firestore_manager import get_firestore_manager
                self.backend = get_firestore_manager()
                print("✅ Using Firestore for recipes")
            except Exception as e:
                print(f"⚠️  Could not initialize Firestore: {e}")
                print("   Falling back to SQLite")
                self.db_type = 'sqlite'
        
        if self.db_type in ('sqlite', 'postgresql'):
            from recipe_database import RecipeDatabase
            self.backend = RecipeDatabase()
            print(f"✅ Using SQLite for recipes")
    
    def get_all_recipes(self) -> List[Dict]:
        """Get all recipes"""
        if self.db_type == 'firestore':
            # Firestore recipes already have ingredients embedded
            return self.backend.get_all_recipes()
        else:
            # SQLite recipes need ingredients fetched separately
            recipes = self.backend.get_all_recipes()
            # Add ingredients to each recipe if the method exists
            if hasattr(self.backend, 'get_recipe_ingredients'):
                for recipe in recipes:
                    recipe['ingredients'] = self.backend.get_recipe_ingredients(recipe['id'])
            return recipes
    
    def get_recipe(self, recipe_id: int) -> Optional[Dict]:
        """Get a single recipe by ID"""
        if self.db_type == 'firestore':
            # Firestore recipes already have ingredients embedded
            return self.backend.get_recipe_by_id(str(recipe_id))
        else:
            recipe = self.backend.get_recipe(recipe_id)
            if recipe and hasattr(self.backend, 'get_recipe_ingredients'):
                recipe['ingredients'] = self.backend.get_recipe_ingredients(recipe_id)
            return recipe
    
    def get_recipe_ingredients(self, recipe_id: int) -> List[Dict]:
        """Get ingredients for a recipe"""
        if self.db_type == 'firestore':
            recipe = self.backend.get_recipe_by_id(str(recipe_id))
            return recipe.get('ingredients', []) if recipe else []
        else:
            return self.backend.get_recipe_ingredients(recipe_id)
    
    def add_recipe(self, name_or_data, **kwargs) -> Optional[int]:
        """Add a new recipe - accepts either a dict or name with kwargs"""
        # Handle both dict input and legacy name+kwargs input
        if isinstance(name_or_data, dict):
            recipe_data = name_or_data
        else:
            # Legacy usage: add_recipe('name', description='...', etc.)
            recipe_data = {'name': name_or_data, **kwargs}
        
        if self.db_type == 'firestore':
            return self.backend.add_recipe(recipe_data)
        else:
            return self.backend.add_recipe(recipe_data['name'], **{k: v for k, v in recipe_data.items() if k != 'name'})
    
    def update_recipe(self, recipe_id: int, **kwargs) -> bool:
        """Update a recipe"""
        if self.db_type == 'firestore':
            return self.backend.update_recipe(str(recipe_id), kwargs)
        else:
            return self.backend.update_recipe(recipe_id, **kwargs)
    
    def delete_recipe(self, recipe_id: int) -> bool:
        """Delete a recipe"""
        if self.db_type == 'firestore':
            return self.backend.delete_recipe(str(recipe_id))
        else:
            return self.backend.delete_recipe(recipe_id)
    
    def add_recipe_ingredient(self, recipe_id: int, ingredient_name: str, quantity: str = "", unit: str = "", **kwargs) -> Optional[int]:
        """Add an ingredient to a recipe"""
        if self.db_type == 'firestore':
            # For Firestore, update the recipe's ingredients array
            recipe = self.backend.get_recipe_by_id(str(recipe_id))
            if recipe:
                ingredients = recipe.get('ingredients', [])
                ingredients.append({
                    'ingredient_name': ingredient_name,
                    'quantity': quantity,
                    'unit': unit,
                    **kwargs
                })
                return self.backend.update_recipe(str(recipe_id), {'ingredients': ingredients})
            return None
        else:
            return self.backend.add_recipe_ingredient(recipe_id, ingredient_name, quantity, unit, **kwargs)
    
    def search_recipes(self, search_term: str = "", filters: Dict = None) -> List[Dict]:
        """Search recipes"""
        if self.db_type == 'firestore':
            # Get all recipes and filter client-side (Firestore doesn't support complex text search)
            all_recipes = self.get_all_recipes()
            if not search_term and not filters:
                return all_recipes
            
            results = []
            for recipe in all_recipes:
                match = True
                
                # Text search
                if search_term:
                    search_lower = search_term.lower()
                    if search_lower not in recipe.get('name', '').lower():
                        match = False
                
                # Filters
                if filters and match:
                    for key, value in filters.items():
                        if recipe.get(key) != value:
                            match = False
                            break
                
                if match:
                    results.append(recipe)
            
            return results
        else:
            return self.backend.search_recipes(search_term, filters)
    
    def get_family_members(self) -> List[Dict]:
        """Get all family members"""
        if self.db_type == 'firestore':
            return self.backend.query('family_members') if hasattr(self.backend, 'query') else []
        else:
            return self.backend.get_family_members()
    
    def get_all_family_members(self) -> List[Dict]:
        """Get all family members (alias for get_family_members)"""
        return self.get_family_members()
    
    def update_times_cooked(self, recipe_id: int) -> bool:
        """Increment the times_cooked counter"""
        if self.db_type == 'firestore':
            recipe = self.backend.get_recipe_by_id(str(recipe_id))
            if recipe:
                times_cooked = recipe.get('times_cooked', 0) + 1
                return self.backend.update_recipe(str(recipe_id), {'times_cooked': times_cooked})
            return False
        else:
            return self.backend.update_times_cooked(recipe_id)
    
    def generate_shopping_list(self, recipe_ids: List[int], servings_multiplier: float = 1.0) -> List[Dict]:
        """Generate a shopping list from multiple recipes"""
        ingredients_map = {}
        
        for recipe_id in recipe_ids:
            # Get ingredients for this recipe
            if self.db_type == 'firestore':
                recipe = self.backend.get_recipe_by_id(str(recipe_id))
                if not recipe:
                    continue
                ingredients = recipe.get('ingredients', [])
            else:
                ingredients = self.backend.get_recipe_ingredients(recipe_id)
            
            # Aggregate ingredients
            for ingredient in ingredients:
                ingredient_name = ingredient.get('ingredient_name', '')
                unit = ingredient.get('unit', '')
                quantity = ingredient.get('quantity', '')
                is_optional = ingredient.get('is_optional', False)
                
                key = f"{ingredient_name}_{unit}"
                
                if key in ingredients_map:
                    # Try to combine quantities
                    try:
                        existing_qty = float(ingredients_map[key]['quantity']) if ingredients_map[key]['quantity'] else 0
                        new_qty = float(quantity) if quantity else 0
                        ingredients_map[key]['quantity'] = str(existing_qty + new_qty)
                    except (ValueError, TypeError):
                        # If quantities can't be combined, keep as is
                        pass
                else:
                    ingredients_map[key] = {
                        'ingredient_name': ingredient_name,
                        'quantity': quantity,
                        'unit': unit,
                        'is_optional': is_optional
                    }
        
        # Apply servings multiplier
        shopping_list = []
        for ingredient in ingredients_map.values():
            if ingredient['quantity']:
                try:
                    qty = float(ingredient['quantity']) * servings_multiplier
                    ingredient['quantity'] = str(qty)
                except (ValueError, TypeError):
                    pass
            
            shopping_list.append(ingredient)
        
        return sorted(shopping_list, key=lambda x: x['ingredient_name'])
    
    # Meal Plan Methods
    def save_meal_plan(self, name: str, start_date: str, end_date: str, meals: Dict, ai_strategy: str = None) -> Optional[str]:
        """Save a meal plan to database"""
        if self.db_type == 'firestore':
            meal_plan_data = {
                'name': name,
                'start_date': start_date,
                'end_date': end_date,
                'meals': meals,
                'ai_strategy': ai_strategy,
                'created_at': self.backend.get_timestamp()
            }
            return self.backend.save_meal_plan(meal_plan_data)
        else:
            return self.backend.save_meal_plan(name, start_date, end_date, meals)
    
    def get_all_meal_plans(self) -> List[Dict]:
        """Get all saved meal plans"""
        if self.db_type == 'firestore':
            return self.backend.get_all_meal_plans()
        else:
            return self.backend.get_all_meal_plans()
    
    def get_meal_plan(self, meal_plan_id: str) -> Optional[Dict]:
        """Get a specific meal plan by ID"""
        if self.db_type == 'firestore':
            return self.backend.get_meal_plan_by_id(meal_plan_id)
        else:
            return self.backend.get_meal_plan(int(meal_plan_id))
    
    def delete_meal_plan(self, meal_plan_id: str) -> bool:
        """Delete a meal plan"""
        if self.db_type == 'firestore':
            return self.backend.delete_meal_plan(meal_plan_id)
        else:
            return self.backend.delete_meal_plan(int(meal_plan_id))
