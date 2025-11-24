"""
Firestore Database Manager for Google Cloud
Provides a compatible interface with the existing database structure
"""
import os
from datetime import datetime
from typing import List, Dict, Optional, Any

# Try to import Firestore (only available when deployed to GCP or with credentials)
try:
    from google.cloud import firestore
    from firebase_admin import credentials, firestore as admin_firestore, initialize_app
    FIRESTORE_AVAILABLE = True
except ImportError:
    FIRESTORE_AVAILABLE = False
    print("⚠️  Firestore not available - install google-cloud-firestore for GCP deployment")

class FirestoreManager:
    """Manages Firestore database operations with SQLite-like interface"""
    
    def __init__(self):
        """Initialize Firestore client"""
        if not FIRESTORE_AVAILABLE:
            raise ImportError("Firestore libraries not installed")
        
        self.db = None
        self._initialize_firestore()
    
    def _initialize_firestore(self):
        """Initialize Firestore client"""
        try:
            # On Google Cloud Run, credentials are automatic
            # For local testing, set GOOGLE_APPLICATION_CREDENTIALS environment variable
            self.db = firestore.Client()
            print("✅ Firestore initialized successfully")
        except Exception as e:
            print(f"⚠️  Firestore initialization error: {e}")
            print("   Set GOOGLE_APPLICATION_CREDENTIALS for local testing")
            raise
    
    def _collection_name(self, table_name: str) -> str:
        """Get Firestore collection name from SQL table name"""
        return table_name
    
    # ==================== Preferred Products ====================
    
    def get_preferred_product(self, ingredient: str) -> Optional[Dict]:
        """Get preferred product for an ingredient"""
        try:
            # Try exact match first
            docs = self.db.collection('preferred_products') \
                .where('ingredient', '==', ingredient) \
                .limit(1) \
                .stream()
            
            for doc in docs:
                data = doc.to_dict()
                data['id'] = doc.id
                return data
            
            # Try case-insensitive partial match
            all_docs = self.db.collection('preferred_products').stream()
            ingredient_lower = ingredient.lower()
            
            for doc in all_docs:
                data = doc.to_dict()
                if ingredient_lower in data.get('ingredient', '').lower():
                    data['id'] = doc.id
                    return data
            
            return None
        except Exception as e:
            print(f"Error getting preferred product: {e}")
            return None
    
    def set_preferred_product(self, data: Dict) -> bool:
        """Set preferred product for an ingredient"""
        try:
            ingredient = data['ingredient']
            
            # Check if exists
            existing = self.get_preferred_product(ingredient)
            
            # Prepare document data
            doc_data = {
                'ingredient': ingredient,
                'product_name': data['product_name'],
                'stockcode': data['stockcode'],
                'brand': data.get('brand'),
                'size': data.get('size'),
                'price': data.get('price'),
                'is_organic': data.get('is_organic', False),
                'image_url': data.get('image_url'),
                'created_at': firestore.SERVER_TIMESTAMP,
                'updated_at': firestore.SERVER_TIMESTAMP
            }
            
            if existing:
                # Update existing
                self.db.collection('preferred_products').document(existing['id']).update({
                    **doc_data,
                    'created_at': existing.get('created_at')  # Keep original
                })
            else:
                # Create new
                self.db.collection('preferred_products').add(doc_data)
            
            return True
        except Exception as e:
            print(f"Error setting preferred product: {e}")
            return False
    
    def remove_preferred_product(self, ingredient: str) -> bool:
        """Remove preferred product for an ingredient"""
        try:
            product = self.get_preferred_product(ingredient)
            if product:
                self.db.collection('preferred_products').document(product['id']).delete()
                return True
            return False
        except Exception as e:
            print(f"Error removing preferred product: {e}")
            return False
    
    def get_all_preferred_products(self) -> List[Dict]:
        """Get all preferred products"""
        try:
            docs = self.db.collection('preferred_products').stream()
            products = []
            for doc in docs:
                data = doc.to_dict()
                data['id'] = doc.id
                products.append(data)
            return products
        except Exception as e:
            print(f"Error getting all preferred products: {e}")
            return []
    
    # ==================== Substitutions ====================
    
    def get_substitution(self, original_ingredient: str) -> Optional[Dict]:
        """Get substitution for an ingredient"""
        try:
            docs = self.db.collection('substitutions') \
                .where('original_ingredient', '==', original_ingredient) \
                .where('active', '==', True) \
                .limit(1) \
                .stream()
            
            for doc in docs:
                data = doc.to_dict()
                data['id'] = doc.id
                return data
            
            return None
        except Exception as e:
            print(f"Error getting substitution: {e}")
            return None
    
    def set_substitution(self, original: str, substitute: str, reason: str = None) -> bool:
        """Set a substitution rule"""
        try:
            doc_data = {
                'original_ingredient': original,
                'substitute_ingredient': substitute,
                'reason': reason,
                'active': True,
                'created_at': firestore.SERVER_TIMESTAMP,
                'updated_at': firestore.SERVER_TIMESTAMP
            }
            
            # Check if exists
            existing = self.get_substitution(original)
            if existing:
                self.db.collection('substitutions').document(existing['id']).update(doc_data)
            else:
                self.db.collection('substitutions').add(doc_data)
            
            return True
        except Exception as e:
            print(f"Error setting substitution: {e}")
            return False
    
    # ==================== Organic Preferences ====================
    
    def get_organic_preference(self, ingredient: str) -> bool:
        """Check if ingredient should be organic"""
        try:
            docs = self.db.collection('organic_preferences') \
                .where('ingredient', '==', ingredient) \
                .limit(1) \
                .stream()
            
            for doc in docs:
                data = doc.to_dict()
                return data.get('prefer_organic', False)
            
            return False
        except Exception as e:
            print(f"Error getting organic preference: {e}")
            return False
    
    def set_organic_preference(self, ingredient: str, prefer_organic: bool = True) -> bool:
        """Set organic preference for an ingredient"""
        try:
            doc_data = {
                'ingredient': ingredient,
                'prefer_organic': prefer_organic,
                'created_at': firestore.SERVER_TIMESTAMP
            }
            
            # Use ingredient as document ID for easy updates
            doc_ref = self.db.collection('organic_preferences').document(ingredient)
            doc_ref.set(doc_data, merge=True)
            
            return True
        except Exception as e:
            print(f"Error setting organic preference: {e}")
            return False
    
    # ==================== Shopping History ====================
    
    def add_shopping_history(self, data: Dict) -> bool:
        """Add item to shopping history"""
        try:
            doc_data = {
                'ingredient': data['ingredient'],
                'product_name': data['product_name'],
                'stockcode': data['stockcode'],
                'price': data.get('price'),
                'brand': data.get('brand'),
                'was_organic': data.get('was_organic', False),
                'was_on_special': data.get('was_on_special', False),
                'purchased_at': firestore.SERVER_TIMESTAMP
            }
            
            self.db.collection('shopping_history').add(doc_data)
            return True
        except Exception as e:
            print(f"Error adding shopping history: {e}")
            return False
    
    def get_shopping_history(self, limit: int = 50) -> List[Dict]:
        """Get recent shopping history"""
        try:
            docs = self.db.collection('shopping_history') \
                .order_by('purchased_at', direction=firestore.Query.DESCENDING) \
                .limit(limit) \
                .stream()
            
            history = []
            for doc in docs:
                data = doc.to_dict()
                data['id'] = doc.id
                history.append(data)
            
            return history
        except Exception as e:
            print(f"Error getting shopping history: {e}")
            return []
    
    # ==================== Recipe Methods ====================
    
    def get_all_recipes(self) -> List[Dict]:
        """Get all recipes from Firestore"""
        try:
            docs = self.db.collection('recipes').stream()
            recipes = []
            for doc in docs:
                data = doc.to_dict()
                data['id'] = doc.id
                recipes.append(data)
            return recipes
        except Exception as e:
            print(f"Error getting recipes: {e}")
            return []
    
    def get_recipe_by_id(self, recipe_id: str) -> Optional[Dict]:
        """Get a single recipe by ID"""
        try:
            doc = self.db.collection('recipes').document(str(recipe_id)).get()
            if doc.exists:
                data = doc.to_dict()
                data['id'] = doc.id
                return data
            return None
        except Exception as e:
            print(f"Error getting recipe {recipe_id}: {e}")
            return None
    
    def add_recipe(self, recipe_data: Dict) -> Optional[str]:
        """Add a new recipe"""
        try:
            recipe_data['created_at'] = datetime.now().isoformat()
            doc_ref = self.db.collection('recipes').add(recipe_data)
            return doc_ref[1].id
        except Exception as e:
            print(f"Error adding recipe: {e}")
            return None
    
    def update_recipe(self, recipe_id: str, recipe_data: Dict) -> bool:
        """Update an existing recipe"""
        try:
            self.db.collection('recipes').document(str(recipe_id)).update(recipe_data)
            return True
        except Exception as e:
            print(f"Error updating recipe: {e}")
            return False
    
    def delete_recipe(self, recipe_id: str) -> bool:
        """Delete a recipe"""
        try:
            self.db.collection('recipes').document(str(recipe_id)).delete()
            return True
        except Exception as e:
            print(f"Error deleting recipe: {e}")
            return False
    
    # ==================== Generic Query Methods ====================
    
    def query(self, collection: str, filters: List[tuple] = None, limit: int = None) -> List[Dict]:
        """
        Generic query method
        filters: List of tuples (field, operator, value)
        Example: [('ingredient', '==', 'carrots'), ('price', '<', 5)]
        """
        try:
            query = self.db.collection(collection)
            
            if filters:
                for field, operator, value in filters:
                    query = query.where(field, operator, value)
            
            if limit:
                query = query.limit(limit)
            
            docs = query.stream()
            results = []
            for doc in docs:
                data = doc.to_dict()
                data['id'] = doc.id
                results.append(data)
            
            return results
        except Exception as e:
            print(f"Error querying {collection}: {e}")
            return []
    
    def add_document(self, collection: str, data: Dict) -> Optional[str]:
        """Add a document to a collection"""
        try:
            doc_ref = self.db.collection(collection).add(data)
            return doc_ref[1].id
        except Exception as e:
            print(f"Error adding document to {collection}: {e}")
            return None
    
    def update_document(self, collection: str, doc_id: str, data: Dict) -> bool:
        """Update a document"""
        try:
            self.db.collection(collection).document(doc_id).update(data)
            return True
        except Exception as e:
            print(f"Error updating document in {collection}: {e}")
            return False
    
    def delete_document(self, collection: str, doc_id: str) -> bool:
        """Delete a document"""
        try:
            self.db.collection(collection).document(doc_id).delete()
            return True
        except Exception as e:
            print(f"Error deleting document from {collection}: {e}")
            return False
    
    # ==================== Batch Operations ====================
    
    def batch_write(self, operations: List[Dict]) -> bool:
        """
        Perform batch write operations
        operations: List of dicts with 'action', 'collection', 'data', 'doc_id' (optional)
        """
        try:
            batch = self.db.batch()
            
            for op in operations:
                collection = op['collection']
                action = op['action']  # 'set', 'update', 'delete'
                
                if action == 'set':
                    doc_ref = self.db.collection(collection).document()
                    batch.set(doc_ref, op['data'])
                elif action == 'update':
                    doc_ref = self.db.collection(collection).document(op['doc_id'])
                    batch.update(doc_ref, op['data'])
                elif action == 'delete':
                    doc_ref = self.db.collection(collection).document(op['doc_id'])
                    batch.delete(doc_ref)
            
            batch.commit()
            return True
        except Exception as e:
            print(f"Error in batch write: {e}")
            return False
    
    # Meal Plan Methods
    def save_meal_plan(self, meal_plan_data: Dict) -> Optional[str]:
        """Save a meal plan to Firestore"""
        try:
            doc_ref = self.db.collection('meal_plans').document()
            meal_plan_data['id'] = doc_ref.id
            doc_ref.set(meal_plan_data)
            return doc_ref.id
        except Exception as e:
            print(f"Error saving meal plan: {e}")
            return None
    
    def get_all_meal_plans(self) -> List[Dict]:
        """Get all saved meal plans"""
        try:
            meal_plans = []
            docs = self.db.collection('meal_plans').order_by('created_at', direction=firestore.Query.DESCENDING).stream()
            for doc in docs:
                plan_data = doc.to_dict()
                plan_data['id'] = doc.id
                meal_plans.append(plan_data)
            return meal_plans
        except Exception as e:
            print(f"Error getting meal plans: {e}")
            return []
    
    def get_meal_plan_by_id(self, meal_plan_id: str) -> Optional[Dict]:
        """Get a specific meal plan by ID"""
        try:
            doc = self.db.collection('meal_plans').document(meal_plan_id).get()
            if doc.exists:
                plan_data = doc.to_dict()
                plan_data['id'] = doc.id
                return plan_data
            return None
        except Exception as e:
            print(f"Error getting meal plan: {e}")
            return None
    
    def delete_meal_plan(self, meal_plan_id: str) -> bool:
        """Delete a meal plan"""
        try:
            self.db.collection('meal_plans').document(meal_plan_id).delete()
            return True
        except Exception as e:
            print(f"Error deleting meal plan: {e}")
            return False
    
    def get_timestamp(self):
        """Get current timestamp for Firestore"""
        return firestore.SERVER_TIMESTAMP

# Singleton instance (initialized when needed)
_firestore_manager = None

def get_firestore_manager() -> FirestoreManager:
    """Get or create Firestore manager instance"""
    global _firestore_manager
    if _firestore_manager is None:
        _firestore_manager = FirestoreManager()
    return _firestore_manager
