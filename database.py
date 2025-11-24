import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

DB_PATH = Path("woolies_preferences.db")

class PreferencesDB:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.init_db()
    
    def get_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)
    
    def init_db(self):
        """Initialize database with all tables"""
        conn = self.get_connection()
        c = conn.cursor()
        
        # Substitutions table
        c.execute('''
            CREATE TABLE IF NOT EXISTS substitutions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_ingredient TEXT NOT NULL,
                substitute_ingredient TEXT NOT NULL,
                reason TEXT,
                active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(original_ingredient)
            )
        ''')
        
        # Organic preferences table
        c.execute('''
            CREATE TABLE IF NOT EXISTS organic_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ingredient TEXT NOT NULL UNIQUE,
                prefer_organic BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Brand preferences table
        c.execute('''
            CREATE TABLE IF NOT EXISTS brand_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                preferred_brand TEXT,
                avoid_brand TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(category, preferred_brand)
            )
        ''')
        
        # Shopping defaults table
        c.execute('''
            CREATE TABLE IF NOT EXISTS shopping_defaults (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                setting_key TEXT NOT NULL UNIQUE,
                setting_value TEXT NOT NULL,
                setting_type TEXT DEFAULT 'string',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Dietary restrictions table
        c.execute('''
            CREATE TABLE IF NOT EXISTS dietary_restrictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                restriction_name TEXT NOT NULL UNIQUE,
                active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Shopping history table (for learning preferences)
        c.execute('''
            CREATE TABLE IF NOT EXISTS shopping_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ingredient TEXT NOT NULL,
                product_name TEXT NOT NULL,
                stockcode INTEGER NOT NULL,
                price REAL,
                brand TEXT,
                was_organic BOOLEAN,
                was_on_special BOOLEAN,
                purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Preferred products table (Woolworths product mapping)
        c.execute('''
            CREATE TABLE IF NOT EXISTS preferred_products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ingredient TEXT NOT NULL UNIQUE,
                product_name TEXT NOT NULL,
                stockcode INTEGER NOT NULL,
                brand TEXT,
                size TEXT,
                price REAL,
                is_organic BOOLEAN DEFAULT 0,
                image_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Avoided ingredients table
        c.execute('''
            CREATE TABLE IF NOT EXISTS avoided_ingredients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ingredient TEXT NOT NULL UNIQUE,
                reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create indexes for better performance
        c.execute('CREATE INDEX IF NOT EXISTS idx_substitutions_original ON substitutions(original_ingredient)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_organic_ingredient ON organic_preferences(ingredient)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_history_ingredient ON shopping_history(ingredient)')
        
        # Insert default settings if not exist
        self._insert_default_settings(c)
        
        # Insert default organic preferences
        self._insert_default_organic_preferences(c)
        
        conn.commit()
        conn.close()
    
    def _insert_default_settings(self, cursor):
        """Insert default shopping settings"""
        defaults = [
            ('prefer_australian_grown', 'true', 'boolean'),
            ('prefer_specials', 'true', 'boolean'),
            ('max_price_per_item', 'null', 'number'),
            ('prefer_smaller_packages', 'false', 'boolean'),
            ('avoid_palm_oil', 'true', 'boolean'),
            ('always_organic_produce', 'true', 'boolean'),
            ('highlight_expensive_items', '15', 'number'),
        ]
        
        for key, value, setting_type in defaults:
            cursor.execute('''
                INSERT OR IGNORE INTO shopping_defaults (setting_key, setting_value, setting_type)
                VALUES (?, ?, ?)
            ''', (key, value, setting_type))
    
    def _insert_default_organic_preferences(self, cursor):
        """Insert default organic preferences"""
        default_organic = [
            'pumpkin',
            'butternut',
            'strawberries',
            'blueberries',
            'spinach',
            'kale',
            'apples',
            'tomatoes'
        ]
        
        for ingredient in default_organic:
            cursor.execute('''
                INSERT OR IGNORE INTO organic_preferences (ingredient, prefer_organic)
                VALUES (?, 1)
            ''', (ingredient.lower(),))
    
    # ============ SUBSTITUTIONS ============
    
    def add_substitution(self, original: str, substitute: str, reason: str = None):
        """Add or update a substitution"""
        conn = self.get_connection()
        c = conn.cursor()
        
        c.execute('''
            INSERT INTO substitutions (original_ingredient, substitute_ingredient, reason)
            VALUES (?, ?, ?)
            ON CONFLICT(original_ingredient) DO UPDATE SET
                substitute_ingredient = excluded.substitute_ingredient,
                reason = excluded.reason,
                updated_at = CURRENT_TIMESTAMP
        ''', (original.lower(), substitute.lower(), reason))
        
        conn.commit()
        conn.close()
    
    def get_substitution(self, ingredient: str) -> Optional[str]:
        """Get substitution for an ingredient"""
        conn = self.get_connection()
        c = conn.cursor()
        
        c.execute('''
            SELECT substitute_ingredient FROM substitutions
            WHERE original_ingredient = ? AND active = 1
        ''', (ingredient.lower(),))
        
        result = c.fetchone()
        conn.close()
        
        return result[0] if result else None
    
    def get_all_substitutions(self) -> List[Dict]:
        """Get all active substitutions"""
        conn = self.get_connection()
        c = conn.cursor()
        
        c.execute('''
            SELECT original_ingredient, substitute_ingredient, reason, created_at
            FROM substitutions WHERE active = 1
            ORDER BY original_ingredient
        ''')
        
        results = [
            {
                'original': row[0],
                'substitute': row[1],
                'reason': row[2],
                'created_at': row[3]
            }
            for row in c.fetchall()
        ]
        
        conn.close()
        return results
    
    def delete_substitution(self, original: str):
        """Soft delete a substitution"""
        conn = self.get_connection()
        c = conn.cursor()
        
        c.execute('''
            UPDATE substitutions SET active = 0
            WHERE original_ingredient = ?
        ''', (original.lower(),))
        
        conn.commit()
        conn.close()
    
    # ============ ORGANIC PREFERENCES ============
    
    def add_organic_preference(self, ingredient: str):
        """Mark ingredient as preferring organic"""
        conn = self.get_connection()
        c = conn.cursor()
        
        c.execute('''
            INSERT OR REPLACE INTO organic_preferences (ingredient, prefer_organic)
            VALUES (?, 1)
        ''', (ingredient.lower(),))
        
        conn.commit()
        conn.close()
    
    def remove_organic_preference(self, ingredient: str):
        """Remove organic preference for ingredient"""
        conn = self.get_connection()
        c = conn.cursor()
        
        c.execute('DELETE FROM organic_preferences WHERE ingredient = ?', (ingredient.lower(),))
        
        conn.commit()
        conn.close()
    
    def should_prefer_organic(self, ingredient: str) -> bool:
        """Check if ingredient should be organic"""
        conn = self.get_connection()
        c = conn.cursor()
        
        c.execute('''
            SELECT prefer_organic FROM organic_preferences
            WHERE ingredient = ?
        ''', (ingredient.lower(),))
        
        result = c.fetchone()
        conn.close()
        
        return bool(result[0]) if result else False
    
    def get_all_organic_preferences(self) -> List[str]:
        """Get all ingredients marked for organic"""
        conn = self.get_connection()
        c = conn.cursor()
        
        c.execute('SELECT ingredient FROM organic_preferences WHERE prefer_organic = 1')
        results = [row[0] for row in c.fetchall()]
        
        conn.close()
        return results
    
    # ============ BRAND PREFERENCES ============
    
    def add_brand_preference(self, category: str, preferred_brand: str = None, 
                            avoid_brand: str = None, notes: str = None):
        """Add brand preference for a category"""
        conn = self.get_connection()
        c = conn.cursor()
        
        c.execute('''
            INSERT INTO brand_preferences (category, preferred_brand, avoid_brand, notes)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(category, preferred_brand) DO UPDATE SET
                avoid_brand = excluded.avoid_brand,
                notes = excluded.notes
        ''', (category.lower(), preferred_brand, avoid_brand, notes))
        
        conn.commit()
        conn.close()
    
    def get_brand_preference(self, category: str) -> Optional[Dict]:
        """Get brand preference for a category"""
        conn = self.get_connection()
        c = conn.cursor()
        
        c.execute('''
            SELECT preferred_brand, avoid_brand, notes
            FROM brand_preferences WHERE category = ?
        ''', (category.lower(),))
        
        result = c.fetchone()
        conn.close()
        
        if result:
            return {
                'preferred': result[0],
                'avoid': result[1],
                'notes': result[2]
            }
        return None
    
    # ============ SHOPPING DEFAULTS ============
    
    def set_default(self, key: str, value: any):
        """Set a shopping default"""
        conn = self.get_connection()
        c = conn.cursor()
        
        # Convert value to string
        if isinstance(value, bool):
            str_value = 'true' if value else 'false'
            setting_type = 'boolean'
        elif isinstance(value, (int, float)):
            str_value = str(value)
            setting_type = 'number'
        else:
            str_value = str(value)
            setting_type = 'string'
        
        c.execute('''
            INSERT INTO shopping_defaults (setting_key, setting_value, setting_type)
            VALUES (?, ?, ?)
            ON CONFLICT(setting_key) DO UPDATE SET
                setting_value = excluded.setting_value,
                updated_at = CURRENT_TIMESTAMP
        ''', (key, str_value, setting_type))
        
        conn.commit()
        conn.close()
    
    def get_default(self, key: str, default=None):
        """Get a shopping default"""
        conn = self.get_connection()
        c = conn.cursor()
        
        c.execute('''
            SELECT setting_value, setting_type FROM shopping_defaults
            WHERE setting_key = ?
        ''', (key,))
        
        result = c.fetchone()
        conn.close()
        
        if not result:
            return default
        
        value, setting_type = result
        
        # Convert back to appropriate type
        if setting_type == 'boolean':
            return value.lower() == 'true'
        elif setting_type == 'number':
            return float(value) if '.' in value else int(value)
        elif value == 'null':
            return None
        return value
    
    def get_all_defaults(self) -> Dict:
        """Get all shopping defaults"""
        conn = self.get_connection()
        c = conn.cursor()
        
        c.execute('SELECT setting_key, setting_value, setting_type FROM shopping_defaults')
        
        defaults = {}
        for row in c.fetchall():
            key, value, setting_type = row
            if setting_type == 'boolean':
                defaults[key] = value.lower() == 'true'
            elif setting_type == 'number':
                defaults[key] = float(value) if '.' in value else int(value)
            elif value == 'null':
                defaults[key] = None
            else:
                defaults[key] = value
        
        conn.close()
        return defaults
    
    # ============ SHOPPING HISTORY ============
    
    def log_purchase(self, ingredient: str, product_name: str, stockcode: int,
                     price: float = None, brand: str = None, 
                     was_organic: bool = False, was_on_special: bool = False):
        """Log a purchase to history"""
        conn = self.get_connection()
        c = conn.cursor()
        
        c.execute('''
            INSERT INTO shopping_history 
            (ingredient, product_name, stockcode, price, brand, was_organic, was_on_special)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (ingredient.lower(), product_name, stockcode, price, brand, 
              was_organic, was_on_special))
        
        conn.commit()
        conn.close()
    
    def get_purchase_history(self, ingredient: str = None, limit: int = 50) -> List[Dict]:
        """Get purchase history"""
        conn = self.get_connection()
        c = conn.cursor()
        
        if ingredient:
            c.execute('''
                SELECT ingredient, product_name, stockcode, price, brand, 
                       was_organic, was_on_special, purchased_at
                FROM shopping_history
                WHERE ingredient = ?
                ORDER BY purchased_at DESC
                LIMIT ?
            ''', (ingredient.lower(), limit))
        else:
            c.execute('''
                SELECT ingredient, product_name, stockcode, price, brand,
                       was_organic, was_on_special, purchased_at
                FROM shopping_history
                ORDER BY purchased_at DESC
                LIMIT ?
            ''', (limit,))
        
        results = [
            {
                'ingredient': row[0],
                'product': row[1],
                'stockcode': row[2],
                'price': row[3],
                'brand': row[4],
                'organic': bool(row[5]),
                'special': bool(row[6]),
                'date': row[7]
            }
            for row in c.fetchall()
        ]
        
        conn.close()
        return results
    
    def get_most_purchased_product(self, ingredient: str) -> Optional[Dict]:
        """Get the most frequently purchased product for an ingredient"""
        conn = self.get_connection()
        c = conn.cursor()
        
        c.execute('''
            SELECT product_name, stockcode, brand, COUNT(*) as purchase_count
            FROM shopping_history
            WHERE ingredient = ?
            GROUP BY stockcode
            ORDER BY purchase_count DESC
            LIMIT 1
        ''', (ingredient.lower(),))
        
        result = c.fetchone()
        conn.close()
        
        if result:
            return {
                'product': result[0],
                'stockcode': result[1],
                'brand': result[2],
                'times_purchased': result[3]
            }
        return None
    
    # ============ DIETARY RESTRICTIONS ============
    
    def add_dietary_restriction(self, restriction: str):
        """Add a dietary restriction"""
        conn = self.get_connection()
        c = conn.cursor()
        
        c.execute('''
            INSERT OR IGNORE INTO dietary_restrictions (restriction_name)
            VALUES (?)
        ''', (restriction.lower(),))
        
        conn.commit()
        conn.close()
    
    def remove_dietary_restriction(self, restriction: str):
        """Remove a dietary restriction"""
        conn = self.get_connection()
        c = conn.cursor()
        
        c.execute('''
            UPDATE dietary_restrictions SET active = 0
            WHERE restriction_name = ?
        ''', (restriction.lower(),))
        
        conn.commit()
        conn.close()
    
    def get_dietary_restrictions(self) -> List[str]:
        """Get all active dietary restrictions"""
        conn = self.get_connection()
        c = conn.cursor()
        
        c.execute('SELECT restriction_name FROM dietary_restrictions WHERE active = 1')
        results = [row[0] for row in c.fetchall()]
        
        conn.close()
        return results
    
    # ============ EXPORT/IMPORT ============
    
    def export_to_json(self) -> Dict:
        """Export all preferences to JSON"""
        return {
            'substitutions': self.get_all_substitutions(),
            'organic_preferences': self.get_all_organic_preferences(),
            'shopping_defaults': self.get_all_defaults(),
            'dietary_restrictions': self.get_dietary_restrictions(),
        }
    
    def import_from_json(self, data: Dict):
        """Import preferences from JSON"""
        # Import substitutions
        for sub in data.get('substitutions', []):
            self.add_substitution(sub['original'], sub['substitute'], sub.get('reason'))
        
        # Import organic preferences
        for ingredient in data.get('organic_preferences', []):
            self.add_organic_preference(ingredient)
        
        # Import shopping defaults
        for key, value in data.get('shopping_defaults', {}).items():
            self.set_default(key, value)
        
        # Import dietary restrictions
        for restriction in data.get('dietary_restrictions', []):
            self.add_dietary_restriction(restriction)
