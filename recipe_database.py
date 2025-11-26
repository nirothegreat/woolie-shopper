"""
Recipe Database Manager
Handles recipe storage, family preferences, and grocery list generation
"""

import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional

class RecipeDatabase:
    def __init__(self, db_path: str = "recipes.db"):
        self.db_path = db_path
        self.conn = None
        self.init_database()
    
    def get_connection(self):
        """Get database connection"""
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
        return self.conn
    
    def init_database(self):
        """Initialize database with tables"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Family members table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS family_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                display_name TEXT NOT NULL,
                preferences TEXT,
                dietary_restrictions TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Recipes table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recipes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                source_url TEXT,
                source_type TEXT,
                description TEXT,
                servings INTEGER DEFAULT 4,
                prep_time TEXT,
                cook_time TEXT,
                total_time TEXT,
                difficulty TEXT,
                cuisine TEXT,
                meal_type TEXT,
                calories INTEGER,
                protein TEXT,
                carbs TEXT,
                fats TEXT,
                fiber TEXT,
                method TEXT,
                tips TEXT,
                image_url TEXT,
                is_favorite BOOLEAN DEFAULT 0,
                rating INTEGER,
                times_cooked INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_cooked TIMESTAMP
            )
        """)
        
        # Recipe ingredients table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recipe_ingredients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipe_id INTEGER NOT NULL,
                ingredient_name TEXT NOT NULL,
                quantity TEXT,
                unit TEXT,
                notes TEXT,
                is_optional BOOLEAN DEFAULT 0,
                FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
            )
        """)
        
        # Family recipe preferences (who likes what)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS family_recipe_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                family_member_id INTEGER NOT NULL,
                recipe_id INTEGER NOT NULL,
                preference_level INTEGER DEFAULT 3,
                notes TEXT,
                FOREIGN KEY (family_member_id) REFERENCES family_members(id) ON DELETE CASCADE,
                FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE,
                UNIQUE(family_member_id, recipe_id)
            )
        """)
        
        # Meal plans table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS meal_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                start_date DATE NOT NULL,
                end_date DATE NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Meal plan recipes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS meal_plan_recipes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                meal_plan_id INTEGER NOT NULL,
                recipe_id INTEGER NOT NULL,
                meal_date DATE NOT NULL,
                meal_type TEXT NOT NULL,
                servings INTEGER DEFAULT 4,
                FOREIGN KEY (meal_plan_id) REFERENCES meal_plans(id) ON DELETE CASCADE,
                FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
            )
        """)
        
        # Shopping lists table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS shopping_lists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                meal_plan_id INTEGER,
                status TEXT DEFAULT 'draft',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (meal_plan_id) REFERENCES meal_plans(id) ON DELETE SET NULL
            )
        """)
        
        # Shopping list items
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS shopping_list_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shopping_list_id INTEGER NOT NULL,
                ingredient_name TEXT NOT NULL,
                quantity TEXT,
                unit TEXT,
                category TEXT,
                is_organic_preferred BOOLEAN DEFAULT 0,
                is_purchased BOOLEAN DEFAULT 0,
                woolworths_stockcode INTEGER,
                price REAL,
                notes TEXT,
                FOREIGN KEY (shopping_list_id) REFERENCES shopping_lists(id) ON DELETE CASCADE
            )
        """)
        
        # Recipe tags
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recipe_tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipe_id INTEGER NOT NULL,
                tag TEXT NOT NULL,
                FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
            )
        """)
        
        conn.commit()
        self._insert_default_family_members()
    
    def _insert_default_family_members(self):
        """Insert default family members if they don't exist"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        family_members = [
            {
                "name": "ehren",
                "display_name": "Ehren",
                "preferences": json.dumps(["hotdogs", "pizza", "ramen noodles", "chicken nuggets", "mac and cheese"]),
                "dietary_restrictions": json.dumps([])
            },
            {
                "name": "maya",
                "display_name": "Maya",
                "preferences": json.dumps(["pasta", "rice", "Italian dishes", "pizza", "lasagna"]),
                "dietary_restrictions": json.dumps([])
            },
            {
                "name": "daddy",
                "display_name": "Daddy",
                "preferences": json.dumps(["steak", "chicken", "protein-rich dishes", "BBQ", "burgers"]),
                "dietary_restrictions": json.dumps([])
            },
            {
                "name": "mommy",
                "display_name": "Mommy",
                "preferences": json.dumps(["salads", "soups", "healthy options", "fish", "vegetables"]),
                "dietary_restrictions": json.dumps([])
            }
        ]
        
        for member in family_members:
            cursor.execute("""
                INSERT OR IGNORE INTO family_members (name, display_name, preferences, dietary_restrictions)
                VALUES (?, ?, ?, ?)
            """, (member["name"], member["display_name"], member["preferences"], member["dietary_restrictions"]))
        
        conn.commit()
    
    def add_recipe(self, recipe_data: Dict) -> int:
        """Add a new recipe to the database"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO recipes (
                name, source_url, source_type, description, servings,
                prep_time, cook_time, total_time, difficulty, cuisine,
                meal_type, calories, protein, carbs, fats, fiber,
                method, tips, image_url
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            recipe_data.get('name'),
            recipe_data.get('source_url'),
            recipe_data.get('source_type'),
            recipe_data.get('description'),
            recipe_data.get('servings', 4),
            recipe_data.get('prep_time'),
            recipe_data.get('cook_time'),
            recipe_data.get('total_time'),
            recipe_data.get('difficulty'),
            recipe_data.get('cuisine'),
            recipe_data.get('meal_type'),
            recipe_data.get('calories'),
            recipe_data.get('protein'),
            recipe_data.get('carbs'),
            recipe_data.get('fats'),
            recipe_data.get('fiber'),
            recipe_data.get('method'),
            recipe_data.get('tips'),
            recipe_data.get('image_url')
        ))
        
        recipe_id = cursor.lastrowid
        
        # Add ingredients
        if 'ingredients' in recipe_data:
            for ingredient in recipe_data['ingredients']:
                cursor.execute("""
                    INSERT INTO recipe_ingredients (recipe_id, ingredient_name, quantity, unit, notes, is_optional)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    recipe_id,
                    ingredient.get('name'),
                    ingredient.get('quantity'),
                    ingredient.get('unit'),
                    ingredient.get('notes'),
                    ingredient.get('is_optional', False)
                ))
        
        # Add tags
        if 'tags' in recipe_data:
            for tag in recipe_data['tags']:
                cursor.execute("""
                    INSERT INTO recipe_tags (recipe_id, tag)
                    VALUES (?, ?)
                """, (recipe_id, tag))
        
        conn.commit()
        return recipe_id
    
    def get_recipe(self, recipe_id: int) -> Optional[Dict]:
        """Get a recipe by ID with ingredients"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM recipes WHERE id = ?", (recipe_id,))
        recipe = cursor.fetchone()
        
        if not recipe:
            return None
        
        recipe_dict = dict(recipe)
        
        # Get ingredients
        cursor.execute("""
            SELECT * FROM recipe_ingredients WHERE recipe_id = ?
        """, (recipe_id,))
        ingredients = [dict(row) for row in cursor.fetchall()]
        
        # Map ingredient_name to name for consistency with other parts of the codebase
        for ing in ingredients:
            if 'ingredient_name' in ing and 'name' not in ing:
                ing['name'] = ing['ingredient_name']
        
        recipe_dict['ingredients'] = ingredients
        
        # Get tags
        cursor.execute("""
            SELECT tag FROM recipe_tags WHERE recipe_id = ?
        """, (recipe_id,))
        recipe_dict['tags'] = [row['tag'] for row in cursor.fetchall()]
        
        return recipe_dict
    
    def get_all_recipes(self, filters: Optional[Dict] = None) -> List[Dict]:
        """Get all recipes with optional filters"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM recipes WHERE 1=1"
        params = []
        
        if filters:
            if 'meal_type' in filters:
                query += " AND meal_type = ?"
                params.append(filters['meal_type'])
            if 'cuisine' in filters:
                query += " AND cuisine = ?"
                params.append(filters['cuisine'])
            if 'is_favorite' in filters:
                query += " AND is_favorite = ?"
                params.append(filters['is_favorite'])
        
        query += " ORDER BY name"
        
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def update_family_member_preferences(self, member_name: str, preferences: List[str]):
        """Update family member preferences"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE family_members 
            SET preferences = ?
            WHERE name = ?
        """, (json.dumps(preferences), member_name))
        
        conn.commit()
    
    def get_family_member(self, member_name: str) -> Optional[Dict]:
        """Get family member details"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM family_members WHERE name = ?", (member_name,))
        member = cursor.fetchone()
        
        if member:
            member_dict = dict(member)
            member_dict['preferences'] = json.loads(member_dict['preferences'])
            member_dict['dietary_restrictions'] = json.loads(member_dict['dietary_restrictions'])
            return member_dict
        
        return None
    
    def get_all_family_members(self) -> List[Dict]:
        """Get all family members"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM family_members ORDER BY id")
        members = []
        for row in cursor.fetchall():
            member = dict(row)
            member['preferences'] = json.loads(member['preferences'])
            member['dietary_restrictions'] = json.loads(member['dietary_restrictions'])
            members.append(member)
        
        return members
    
    def set_recipe_preference(self, family_member_id: int, recipe_id: int, preference_level: int, notes: str = ""):
        """Set a family member's preference for a recipe (1-5 scale)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO family_recipe_preferences 
            (family_member_id, recipe_id, preference_level, notes)
            VALUES (?, ?, ?, ?)
        """, (family_member_id, recipe_id, preference_level, notes))
        
        conn.commit()
    
    def generate_shopping_list(self, recipe_ids: List[int], servings_multiplier: float = 1.0) -> List[Dict]:
        """Generate a shopping list from multiple recipes"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Aggregate ingredients from all recipes
        ingredients_map = {}
        
        for recipe_id in recipe_ids:
            cursor.execute("""
                SELECT ingredient_name, quantity, unit, is_optional
                FROM recipe_ingredients
                WHERE recipe_id = ?
            """, (recipe_id,))
            
            for row in cursor.fetchall():
                ingredient = dict(row)
                key = f"{ingredient['ingredient_name']}_{ingredient['unit']}"
                
                if key in ingredients_map:
                    # Try to combine quantities (simple addition for now)
                    try:
                        existing_qty = float(ingredients_map[key]['quantity']) if ingredients_map[key]['quantity'] else 0
                        new_qty = float(ingredient['quantity']) if ingredient['quantity'] else 0
                        ingredients_map[key]['quantity'] = str(existing_qty + new_qty)
                    except (ValueError, TypeError):
                        # If quantities can't be combined, keep as is
                        pass
                else:
                    ingredients_map[key] = ingredient
        
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
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None
