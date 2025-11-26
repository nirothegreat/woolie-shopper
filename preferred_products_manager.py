"""
Preferred Products Manager
Manages user's preferred product choices for shopping list ingredients
"""

from typing import Dict, List, Optional
from datetime import datetime
from google.cloud import firestore
import re

class PreferredProductsManager:
    """Manages preferred product mappings for ingredients"""
    
    def __init__(self, db=None):
        self.db = db or firestore.Client()
        self.collection_name = 'preferred_products'
    
    def _normalize_ingredient(self, ingredient: str) -> str:
        """Normalize ingredient name for consistent matching"""
        # Remove extra spaces, lowercase
        normalized = ingredient.lower().strip()
        # Remove common variations
        normalized = re.sub(r'\s+', ' ', normalized)
        # Remove quantity indicators
        normalized = re.sub(r'\b(organic|fresh|frozen|dried)\b', '', normalized).strip()
        return normalized
    
    def set_preferred_product(
        self, 
        ingredient_name: str, 
        stockcode: int,
        product_name: str = "",
        price: float = 0.0,
        image_url: str = "",
        fallback_stockcodes: List[int] = None,
        user_id: str = "default"
    ) -> bool:
        """
        Set or update preferred product for an ingredient
        
        Args:
            ingredient_name: The ingredient (e.g., "greek yogurt")
            stockcode: Primary Woolworths stockcode
            product_name: Full product name
            price: Product price
            image_url: Product image URL
            fallback_stockcodes: List of alternative stockcodes if primary is unavailable
            user_id: User identifier
            
        Returns:
            True if successful
        """
        try:
            normalized_name = self._normalize_ingredient(ingredient_name)
            
            # Check if preference already exists
            existing = self._get_preference_doc(normalized_name, user_id)
            
            data = {
                'user_id': user_id,
                'ingredient_name': normalized_name,
                'original_name': ingredient_name,
                'stockcode': stockcode,
                'product_name': product_name,
                'price': price,
                'image_url': image_url,
                'fallback_stockcodes': fallback_stockcodes or [],
                'last_updated': firestore.SERVER_TIMESTAMP
            }
            
            if existing:
                # Update existing preference
                existing['ref'].update(data)
                print(f"✅ Updated preference for '{ingredient_name}' → {stockcode}")
            else:
                # Create new preference
                data['added_date'] = firestore.SERVER_TIMESTAMP
                data['use_count'] = 0
                self.db.collection(self.collection_name).add(data)
                print(f"✅ Added preference for '{ingredient_name}' → {stockcode}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error setting preferred product: {e}")
            return False
    
    def get_preferred_product(
        self, 
        ingredient_name: str, 
        user_id: str = "default"
    ) -> Optional[Dict]:
        """
        Get preferred product for an ingredient
        
        Args:
            ingredient_name: The ingredient to look up
            user_id: User identifier
            
        Returns:
            Dict with stockcode and product info, or None
        """
        try:
            normalized_name = self._normalize_ingredient(ingredient_name)
            doc = self._get_preference_doc(normalized_name, user_id)
            
            if doc:
                # Update use count and last used
                doc['ref'].update({
                    'use_count': firestore.Increment(1),
                    'last_used': firestore.SERVER_TIMESTAMP
                })
                
                data = doc['data']
                return {
                    'ingredient_name': data.get('ingredient_name'),
                    'stockcode': data.get('stockcode'),
                    'product_name': data.get('product_name'),
                    'price': data.get('price'),
                    'image_url': data.get('image_url'),
                    'use_count': data.get('use_count', 0)
                }
            
            return None
            
        except Exception as e:
            print(f"❌ Error getting preferred product: {e}")
            return None
    
    def _get_preference_doc(self, normalized_name: str, user_id: str) -> Optional[Dict]:
        """Helper to get preference document"""
        docs = self.db.collection(self.collection_name)\
            .where('user_id', '==', user_id)\
            .where('ingredient_name', '==', normalized_name)\
            .limit(1)\
            .stream()
        
        for doc in docs:
            return {'ref': doc.reference, 'data': doc.to_dict()}
        
        return None
    
    def remove_preferred_product(
        self, 
        ingredient_name: str, 
        user_id: str = "default"
    ) -> bool:
        """Remove preferred product for an ingredient"""
        try:
            normalized_name = self._normalize_ingredient(ingredient_name)
            doc = self._get_preference_doc(normalized_name, user_id)
            
            if doc:
                doc['ref'].delete()
                print(f"✅ Removed preference for '{ingredient_name}'")
                return True
            else:
                print(f"⚠️ No preference found for '{ingredient_name}'")
                return False
                
        except Exception as e:
            print(f"❌ Error removing preferred product: {e}")
            return False
    
    def list_all_preferences(self, user_id: str = "default") -> List[Dict]:
        """Get all preferred products for a user"""
        try:
            docs = self.db.collection(self.collection_name)\
                .where('user_id', '==', user_id)\
                .order_by('ingredient_name')\
                .stream()
            
            preferences = []
            for doc in docs:
                data = doc.to_dict()
                preferences.append({
                    'ingredient_name': data.get('ingredient_name'),
                    'original_name': data.get('original_name'),
                    'stockcode': data.get('stockcode'),
                    'product_name': data.get('product_name'),
                    'price': data.get('price'),
                    'use_count': data.get('use_count', 0),
                    'last_used': data.get('last_used')
                })
            
            return preferences
            
        except Exception as e:
            print(f"❌ Error listing preferences: {e}")
            return []
    
    def import_from_cart(self, cart_items: List[Dict], user_id: str = "default") -> int:
        """
        Import preferred products from current shopping cart
        
        Args:
            cart_items: List of items from Woolworths cart
            user_id: User identifier
            
        Returns:
            Number of preferences imported
        """
        count = 0
        
        for item in cart_items:
            stockcode = item.get('Stockcode') or item.get('stockcode')
            display_name = item.get('DisplayName') or item.get('display_name')
            price = item.get('Price') or item.get('price', 0)
            
            if not stockcode or not display_name:
                continue
            
            # Try to extract ingredient name from product name
            # This is a heuristic - you can improve based on patterns
            ingredient = self._extract_ingredient_from_product(display_name)
            
            if ingredient:
                success = self.set_preferred_product(
                    ingredient_name=ingredient,
                    stockcode=stockcode,
                    product_name=display_name,
                    price=price,
                    user_id=user_id
                )
                
                if success:
                    count += 1
        
        print(f"✅ Imported {count} preferred products from cart")
        return count
    
    def _extract_ingredient_from_product(self, product_name: str) -> Optional[str]:
        """
        Extract ingredient name from full product name
        This is a heuristic - improve as needed
        """
        # Remove brand names and package sizes
        name = product_name.lower()
        
        # Common patterns to remove
        name = re.sub(r'\d+g|\d+kg|\d+ml|\d+l|\d+ pack', '', name)
        name = re.sub(r'woolworths|macro|essentials', '', name)
        name = re.sub(r'\b(organic|fresh|frozen|dried|sliced|diced|chopped)\b', '', name)
        name = re.sub(r'\s+', ' ', name).strip()
        
        # Take first 2-3 meaningful words
        words = [w for w in name.split() if len(w) > 2]
        if words:
            return ' '.join(words[:2])
        
        return None


# Global instance
_preferred_products_manager = None

def get_preferred_products_manager() -> PreferredProductsManager:
    """Get or create the global preferred products manager"""
    global _preferred_products_manager
    if _preferred_products_manager is None:
        _preferred_products_manager = PreferredProductsManager()
    return _preferred_products_manager
