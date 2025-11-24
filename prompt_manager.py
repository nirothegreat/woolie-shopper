"""
Prompt Manager for Woolies Shopper
Loads AI prompts from JSON file or Firestore for easy updates without redeployment
"""

import json
import os
from typing import Dict, Optional
from datetime import datetime, timedelta

class PromptManager:
    """Manages AI prompts with support for file and Firestore storage"""
    
    def __init__(self, prompts_file: str = "prompts.json"):
        self.prompts_file = prompts_file
        self._prompts_cache = None
        self._cache_timestamp = None
        self._cache_ttl = timedelta(minutes=5)  # Reload every 5 minutes
        self.use_firestore = os.getenv('USE_FIRESTORE_PROMPTS', 'false').lower() == 'true'
        self.db = None
        
        if self.use_firestore:
            try:
                from google.cloud import firestore
                self.db = firestore.Client()
                print("✅ Firestore prompt storage enabled")
            except Exception as e:
                print(f"⚠️ Firestore prompts disabled: {e}")
                self.use_firestore = False
    
    def _load_from_file(self) -> Dict:
        """Load prompts from JSON file"""
        try:
            with open(self.prompts_file, 'r') as f:
                prompts = json.load(f)
            print(f"✅ Loaded prompts from {self.prompts_file}")
            return prompts
        except Exception as e:
            print(f"❌ Error loading prompts from file: {e}")
            return self._get_default_prompts()
    
    def _load_from_firestore(self) -> Optional[Dict]:
        """Load prompts from Firestore (if available)"""
        if not self.use_firestore or not self.db:
            return None
        
        try:
            doc_ref = self.db.collection('config').document('prompts')
            doc = doc_ref.get()
            
            if doc.exists:
                prompts = doc.to_dict()
                print("✅ Loaded prompts from Firestore")
                return prompts
            else:
                print("⚠️ No prompts found in Firestore, using file")
                return None
        except Exception as e:
            print(f"⚠️ Error loading from Firestore: {e}")
            return None
    
    def get_prompts(self, force_reload: bool = False) -> Dict:
        """
        Get prompts with caching
        
        Args:
            force_reload: Force reload from source
            
        Returns:
            Dictionary of prompts
        """
        # Check if cache is still valid
        if not force_reload and self._prompts_cache and self._cache_timestamp:
            if datetime.now() - self._cache_timestamp < self._cache_ttl:
                return self._prompts_cache
        
        # Try Firestore first if enabled
        if self.use_firestore:
            prompts = self._load_from_firestore()
            if prompts:
                self._prompts_cache = prompts
                self._cache_timestamp = datetime.now()
                return prompts
        
        # Fall back to file
        prompts = self._load_from_file()
        self._prompts_cache = prompts
        self._cache_timestamp = datetime.now()
        return prompts
    
    def get_prompt(self, prompt_key: str, **kwargs) -> str:
        """
        Get a specific prompt with optional variable substitution
        
        Args:
            prompt_key: Key path like "meal_plan_generation.system" or "shopping_list_optimization.user_template"
            **kwargs: Variables to substitute in template
            
        Returns:
            Formatted prompt string
        """
        prompts = self.get_prompts()
        
        # Navigate nested keys
        keys = prompt_key.split('.')
        value = prompts
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                print(f"⚠️ Prompt key not found: {prompt_key}")
                return ""
        
        # If it's an array, join it into a string (for multi-line prompts)
        if isinstance(value, list):
            value = ''.join(value)
        
        # If it's a template, format it
        if isinstance(value, str) and kwargs:
            try:
                return value.format(**kwargs)
            except KeyError as e:
                print(f"⚠️ Missing template variable: {e}")
                return value
        
        return value
    
    def save_to_firestore(self, prompts: Dict) -> bool:
        """
        Save prompts to Firestore
        
        Args:
            prompts: Dictionary of prompts to save
            
        Returns:
            True if successful
        """
        if not self.use_firestore or not self.db:
            print("⚠️ Firestore not enabled")
            return False
        
        try:
            doc_ref = self.db.collection('config').document('prompts')
            prompts['_metadata']['last_updated'] = datetime.now().isoformat()
            doc_ref.set(prompts)
            print("✅ Prompts saved to Firestore")
            
            # Clear cache to force reload
            self._prompts_cache = None
            self._cache_timestamp = None
            
            return True
        except Exception as e:
            print(f"❌ Error saving to Firestore: {e}")
            return False
    
    def _get_default_prompts(self) -> Dict:
        """Fallback default prompts if file/Firestore unavailable"""
        return {
            "meal_plan_generation": {
                "system": "You are an expert meal planning assistant.",
                "user_template": "Create a meal plan based on available recipes."
            },
            "shopping_list_optimization": {
                "system": "You are a shopping list optimizer.",
                "user_template": "Organize and combine duplicate items in this shopping list."
            },
            "shopping_chat_assistant": {
                "system_template": "You are a helpful shopping assistant for Woolworths."
            },
            "_metadata": {
                "version": "1.0.0",
                "description": "Default fallback prompts"
            }
        }


# Global instance
_prompt_manager = None

def get_prompt_manager() -> PromptManager:
    """Get or create the global prompt manager instance"""
    global _prompt_manager
    if _prompt_manager is None:
        _prompt_manager = PromptManager()
    return _prompt_manager
