"""
AI Agent for Intelligent Meal Planning
Uses LangChain for structured meal planning (Pydantic models)
Native Anthropic SDK for shopping list optimization (simpler, faster)
"""

from langchain_anthropic import ChatAnthropic
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
import anthropic
import json
import os
from prompt_manager import get_prompt_manager

# Set up the LLM
def get_llm():
    """Get the language model"""
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")
    # Using Claude 3 Haiku - fast, cost-effective (upgrade to Sonnet when available)
    return ChatAnthropic(
        model="claude-3-haiku-20240307", 
        temperature=0.7,
        timeout=60.0,  # 60 second timeout
        max_retries=2  # Retry on failures
    )

# Output schema for meal plan
class DayMealPlan(BaseModel):
    """Meal plan for a single day"""
    day: str = Field(description="Day of the week (Monday, Tuesday, Wednesday, Thursday, or Friday only - no weekends)")
    breakfast: Optional[str] = Field(description="Recipe name for general breakfast, or None")
    breakfast_maya: Optional[str] = Field(description="Recipe name for Maya's breakfast (should have 'maya' tag), or None")
    breakfast_ehren: Optional[str] = Field(description="Recipe name for Ehren's breakfast (should have 'ehren' tag), or None")
    lunch: Optional[str] = Field(description="Recipe name for general lunch, or None")
    lunch_ehren: Optional[str] = Field(description="Recipe name for Ehren's school lunch (should have 'ehren' tag), or None")
    dinner: Optional[str] = Field(description="Recipe name for dinner, or None")
    reasoning: str = Field(description="Brief explanation of why these recipes were chosen")

class WeeklyMealPlan(BaseModel):
    """Complete weekly meal plan"""
    week_plan: List[DayMealPlan] = Field(description="Meal plan for each day of the week")
    overall_strategy: Optional[str] = Field(default="Balanced weekly meal plan", description="Overall strategy and considerations for the meal plan")

class MealPlanAgent:
    """AI Agent for generating intelligent meal plans"""
    
    def __init__(self):
        self.llm = get_llm()
        self.parser = PydanticOutputParser(pydantic_object=WeeklyMealPlan)
        
    def generate_meal_plan(self, recipes: List[Dict], family_preferences: Dict, 
                          additional_context: str = "") -> WeeklyMealPlan:
        """
        Generate an intelligent meal plan using AI
        
        Args:
            recipes: List of available recipes with details
            family_preferences: Dictionary of family member preferences
            additional_context: Additional context or constraints for meal planning
            
        Returns:
            WeeklyMealPlan object with daily meal assignments
        """
        
        # Format recipes for the prompt
        recipes_text = self._format_recipes(recipes)
        family_prefs_text = self._format_family_preferences(family_preferences)
        
        # Load prompts from prompt manager
        pm = get_prompt_manager()
        system_prompt = pm.get_prompt("meal_plan_generation.system")
        user_prompt_template = pm.get_prompt("meal_plan_generation.user_template")
        
        # Create the prompt with format instructions
        system_with_format = system_prompt + "\n\n{format_instructions}"
        user_prompt = user_prompt_template.format(
            recipes_text=recipes_text,
            preferences_text=family_prefs_text,
            additional_context=additional_context or "No additional constraints"
        )
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_with_format),
            ("human", user_prompt)
        ])
        
        # Format the prompt
        formatted_prompt = prompt.format_messages(
            format_instructions=self.parser.get_format_instructions()
        )
        
        # Get response from LLM
        response = self.llm.invoke(formatted_prompt)
        
        # Parse the response
        try:
            meal_plan = self.parser.parse(response.content)
            return meal_plan
        except Exception as e:
            print(f"Error parsing response: {e}")
            print(f"Raw response: {response.content}")
            raise
    
    def _format_recipes(self, recipes: List[Dict]) -> str:
        """Format recipes for the prompt"""
        formatted = []
        
        for recipe in recipes:
            recipe_text = f"""
Recipe: {recipe.get('name', 'Unknown')}
- Meal Type: {recipe.get('meal_type', 'Any')}
- Cuisine: {recipe.get('cuisine', 'Not specified')}
- Difficulty: {recipe.get('difficulty', 'Medium')}
- Time: {recipe.get('total_time', 'Not specified')}
- Description: {recipe.get('description', 'No description')}
"""
            # Add tags (CRITICAL for filtering)
            tags = recipe.get('tags', [])
            if tags:
                recipe_text += f"- Tags: {', '.join(tags)}\n"
            else:
                recipe_text += "- Tags: none\n"
            
            # Add ingredient count if available
            if 'ingredients' in recipe and recipe['ingredients']:
                recipe_text += f"- Ingredients: {len(recipe['ingredients'])} items\n"
            
            formatted.append(recipe_text)
        
        return "\n".join(formatted)
    
    def _format_family_preferences(self, family_preferences: Dict) -> str:
        """Format family preferences for the prompt"""
        if not family_preferences:
            return "No specific family preferences provided."
        
        formatted = []
        
        for member, prefs in family_preferences.items():
            pref_text = f"\n{member.title()}:"
            
            if isinstance(prefs, dict):
                # Handle structured preferences
                if 'general_preferences' in prefs:
                    pref_text += f"\n  General: {', '.join(prefs['general_preferences'])}"
                if 'liked_recipes' in prefs:
                    pref_text += f"\n  Likes: {', '.join(prefs['liked_recipes'])}"
                if 'disliked_recipes' in prefs:
                    pref_text += f"\n  Dislikes: {', '.join(prefs['disliked_recipes'])}"
            elif isinstance(prefs, list):
                # Handle simple list of preferences
                pref_text += f"\n  Preferences: {', '.join(prefs)}"
            else:
                pref_text += f"\n  {prefs}"
            
            formatted.append(pref_text)
        
        return "\n".join(formatted)
    
    def suggest_alternative(self, current_plan: WeeklyMealPlan, day: str, 
                          meal_type: str, recipes: List[Dict]) -> str:
        """
        Suggest an alternative recipe for a specific meal
        
        Args:
            current_plan: Current meal plan
            day: Day to change (e.g., "Monday")
            meal_type: Meal to change (e.g., "dinner")
            recipes: Available recipes
            
        Returns:
            Suggested recipe name
        """
        
        # Get current meal plan context
        context = f"""Current meal plan for {day}:
"""
        for day_plan in current_plan.week_plan:
            if day_plan.day == day:
                context += f"Breakfast: {day_plan.breakfast}\n"
                context += f"Lunch: {day_plan.lunch}\n"
                context += f"Dinner: {day_plan.dinner}\n"
                context += f"Reasoning: {day_plan.reasoning}\n"
                break
        
        recipes_text = self._format_recipes(recipes)
        
        prompt = f"""Given this current meal plan:
{context}

Available recipes:
{recipes_text}

Suggest a better alternative for {meal_type} on {day}. 
Consider variety, balance, and family preferences.
Return ONLY the recipe name, nothing else."""
        
        response = self.llm.invoke(prompt)
        return response.content.strip()


def get_family_preferences_from_db(recipe_db):
    """
    Extract family preferences from database in format suitable for AI agent
    
    Args:
        recipe_db: RecipeDatabase instance
        
    Returns:
        Dictionary of family preferences
    """
    family_members = recipe_db.get_all_family_members()
    preferences = {}
    
    for member in family_members:
        member_name = member.get('display_name', member.get('name', 'Unknown'))
        
        prefs = {
            'general_preferences': member.get('preferences', []),
        }
        
        # Could add liked/disliked recipes here if we track them
        # For now, just use general preferences
        
        preferences[member_name] = prefs
    
    return preferences


class ShoppingListOptimizer:
    """AI Agent for optimizing and organizing shopping lists"""
    
    def __init__(self):
        self.llm = get_llm()
    
    def optimize_shopping_list(self, raw_ingredients: List[Dict], 
                               organic_preferences: List[str],
                               substitutions: List[Dict],
                               staples: List[Dict]) -> Dict:
        """
        Use AI to intelligently organize and optimize a shopping list
        
        Args:
            raw_ingredients: List of ingredients from recipes
            organic_preferences: List of ingredients to prefer organic
            substitutions: List of ingredient substitutions
            staples: List of staple items with in_stock status
            
        Returns:
            Dictionary with optimized categories and suggestions
        """
        
        # Format the raw data
        ingredients_text = self._format_ingredients(raw_ingredients)
        staples_text = self._format_staples(staples)
        organic_text = ", ".join(organic_preferences) if organic_preferences else "None specified"
        subs_text = self._format_substitutions(substitutions)
        
        # Log input counts for debugging
        print(f"🔍 AI Shopping List Input: {len(raw_ingredients)} ingredients + {len([s for s in staples if not s.get('in_stock')])} staples")
        
        prompt = f"""You are an expert grocery shopping assistant. Analyze this shopping list and organize it intelligently.

RAW INGREDIENTS FROM RECIPES:
{ingredients_text}

STAPLES (items to add if not in stock):
{staples_text}

ORGANIC PREFERENCES: {organic_text}

INGREDIENT SUBSTITUTIONS:
{subs_text}

CRITICAL: You MUST return ONLY valid JSON. No explanations, no markdown, just pure JSON.

⚠️ CRITICAL REQUIREMENT: Include EVERY SINGLE ingredient listed above. Do NOT drop any items.

Tasks:
1. Combine duplicate/similar ingredients (e.g., "2 cups milk" + "1 cup milk" = "3 cups milk")
2. Organize into store categories: Fresh Produce, Dairy & Eggs, Meat & Protein, Pantry Staples, Frozen, Bakery, Other
3. Apply organic preferences where specified
4. Apply any substitutions listed
5. Add staples that are not in stock
6. Provide helpful shopping tips
7. Suggest cost-saving opportunities
8. ⚠️ NEVER skip or omit any ingredient - if unsure about category, put it in "Other"

JSON Format (return EXACTLY this structure):
{{
  "categories": {{
    "Fresh Produce": [
      {{"item": "organic kale", "quantity": "2 bunches", "notes": "Organic preference"}},
      {{"item": "tomatoes", "quantity": "4", "notes": ""}}
    ],
    "Dairy & Eggs": [
      {{"item": "milk", "quantity": "2L", "notes": "Combined from recipes"}}
    ],
    "Pantry Staples": [],
    "Other": []
  }},
  "shopping_tips": [
    "Buy organic produce from organic section",
    "Consider larger quantities for cost savings"
  ],
  "cost_saving_suggestions": [
    "Buy family-size pasta instead of small boxes"
  ],
  "total_items": 15
}}

IMPORTANT: Return ONLY the JSON object above. No markdown, no ```json blocks, no extra text."""
        
        try:
            response = self.llm.invoke(prompt)
            
            # Clean the response content
            content = response.content.strip()
            
            # Remove markdown code blocks if present
            if content.startswith('```json'):
                content = content.replace('```json', '', 1).strip()
            if content.startswith('```'):
                content = content.replace('```', '', 1).strip()
            if content.endswith('```'):
                content = content.rsplit('```', 1)[0].strip()
            
            # Parse the JSON response
            result = json.loads(content)
            
            # CRITICAL: Validate that all ingredients are accounted for
            result = self._validate_and_fix_missing_items(result, raw_ingredients, staples)
            
            print(f"✅ AI Shopping List: {result.get('total_items', 0)} items organized into {len(result.get('categories', {}))} categories")
            return result
        except json.JSONDecodeError as e:
            print(f"Error parsing AI response: {e}")
            print(f"Raw response: {response.content[:500]}")  # Limit output
            # Return basic fallback
            return self._fallback_organization(raw_ingredients, staples)
        except Exception as e:
            print(f"Error in AI optimization: {e}")
            import traceback
            traceback.print_exc()
            return self._fallback_organization(raw_ingredients, staples)
    
    def _format_ingredients(self, ingredients: List[Dict]) -> str:
        """Format ingredients for prompt"""
        lines = []
        for ing in ingredients:
            name = ing.get('name', ing.get('ingredient_name', 'Unknown'))
            qty = ing.get('quantity', '')
            unit = ing.get('unit', '')
            lines.append(f"- {name} {qty} {unit}".strip())
        return "\n".join(lines) if lines else "No ingredients"
    
    def _format_staples(self, staples: List[Dict]) -> str:
        """Format staples for prompt"""
        lines = []
        for staple in staples:
            if not staple.get('in_stock', False):
                name = staple.get('name', 'Unknown')
                qty = staple.get('quantity', '')
                unit = staple.get('unit', '')
                lines.append(f"- {name} {qty} {unit}".strip())
        return "\n".join(lines) if lines else "All staples in stock"
    
    def _format_substitutions(self, substitutions: List[Dict]) -> str:
        """Format substitutions for prompt"""
        lines = []
        for sub in substitutions:
            orig = sub.get('original', '')
            subst = sub.get('substitute', '')
            reason = sub.get('reason', '')
            lines.append(f"- Replace '{orig}' with '{subst}' {f'({reason})' if reason else ''}")
        return "\n".join(lines) if lines else "No substitutions"
    
    def _validate_and_fix_missing_items(self, ai_result: Dict, raw_ingredients: List[Dict], staples: List[Dict]) -> Dict:
        """Validate AI result has all ingredients, add any missing ones"""
        categories = ai_result.get('categories', {})
        
        # Collect all items from AI result
        ai_items_lower = set()
        for category_items in categories.values():
            for item in category_items:
                item_name = item.get('item', '').lower().strip()
                ai_items_lower.add(item_name)
        
        # Check each raw ingredient
        missing_items = []
        for ing in raw_ingredients:
            name = ing.get('name', ing.get('ingredient_name', 'Unknown')).lower().strip()
            # Check if this ingredient or a variation exists in AI result
            found = False
            for ai_item in ai_items_lower:
                # Check if ingredient is in AI item or vice versa (handles combinations)
                if name in ai_item or ai_item in name:
                    found = True
                    break
            
            if not found:
                missing_items.append(ing)
        
        # Check staples that should be added
        for staple in staples:
            if not staple.get('in_stock', False):
                name = staple.get('name', '').lower().strip()
                found = any(name in ai_item or ai_item in name for ai_item in ai_items_lower)
                if not found:
                    missing_items.append({
                        'name': staple['name'],
                        'quantity': staple.get('quantity', ''),
                        'unit': staple.get('unit', ''),
                        'is_staple': True
                    })
        
        # Add missing items to Other category
        if missing_items:
            print(f"⚠️  AI dropped {len(missing_items)} items - adding them back to 'Other' category")
            if 'Other' not in categories:
                categories['Other'] = []
            
            for item in missing_items:
                name = item.get('name', item.get('ingredient_name', 'Unknown'))
                qty = item.get('quantity', '')
                unit = item.get('unit', '')
                categories['Other'].append({
                    'item': name,
                    'quantity': f"{qty} {unit}".strip() if qty or unit else '',
                    'notes': 'Added (missing from AI)' + (' - Staple' if item.get('is_staple') else '')
                })
            
            # Update total items
            ai_result['total_items'] = sum(len(items) for items in categories.values())
            ai_result['categories'] = categories
        
        return ai_result
    
    def _fallback_organization(self, ingredients: List[Dict], staples: List[Dict]) -> Dict:
        """Basic fallback if AI fails"""
        categories = {
            "Fresh Produce": [],
            "Dairy & Eggs": [],
            "Meat & Protein": [],
            "Pantry Staples": [],
            "Other": []
        }
        
        # Simple categorization
        for ing in ingredients:
            name = ing.get('name', ing.get('ingredient_name', 'Unknown'))
            qty = ing.get('quantity', '')
            unit = ing.get('unit', '')
            categories["Other"].append({
                "item": name,
                "quantity": f"{qty} {unit}".strip(),
                "notes": ""
            })
        
        # Add staples
        for staple in staples:
            if not staple.get('in_stock', False):
                name = staple.get('name', 'Unknown')
                qty = staple.get('quantity', '')
                unit = staple.get('unit', '')
                categories["Other"].append({
                    "item": name,
                    "quantity": f"{qty} {unit}".strip(),
                    "notes": "Staple item"
                })
        
        return {
            "categories": categories,
            "shopping_tips": ["AI optimization unavailable - using basic categorization"],
            "cost_saving_suggestions": [],
            "total_items": len(ingredients) + len([s for s in staples if not s.get('in_stock')])
        }


# Alternative: Native Anthropic SDK optimizer (no LangChain dependency)
class ShoppingListOptimizerNative:
    """Simple shopping list optimizer using native Anthropic SDK"""
    
    def __init__(self):
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        self.client = anthropic.Anthropic(
            api_key=api_key,
            timeout=60.0,  # 60 second timeout
            max_retries=2  # Retry on failures
        )
        self.model = "claude-3-haiku-20240307"
    
    def optimize_shopping_list(self, raw_ingredients: List[Dict], 
                               organic_preferences: List[str],
                               substitutions: List[Dict],
                               staples: List[Dict]) -> Dict:
        """
        Optimize shopping list using native Anthropic SDK (faster than LangChain)
        """
        
        # Format inputs
        ingredients_list = "\n".join([
            f"- {ing.get('name', ing.get('ingredient_name', 'Unknown'))} {ing.get('quantity', '')} {ing.get('unit', '')}".strip()
            for ing in raw_ingredients
        ])
        
        staples_list = "\n".join([
            f"- {s.get('name')} {s.get('quantity', '')} {s.get('unit', '')}".strip()
            for s in staples if not s.get('in_stock', False)
        ])
        
        organic_text = ", ".join(organic_preferences) if organic_preferences else "None"
        
        subs_text = "\n".join([
            f"- {s.get('original')} → {s.get('substitute')}"
            for s in substitutions
        ]) if substitutions else "None"
        
        print(f"🔍 AI Shopping List Input: {len(raw_ingredients)} ingredients + {len([s for s in staples if not s.get('in_stock')])} staples")
        
        # Debug: Log a few sample ingredients to verify
        if raw_ingredients:
            print(f"   Sample ingredients:")
            for i, ing in enumerate(raw_ingredients[:5]):
                print(f"   - {ing.get('name', ing.get('ingredient_name', 'Unknown'))} {ing.get('quantity', '')} {ing.get('unit', '')}".strip())
        
        # Load prompt from prompt manager
        pm = get_prompt_manager()
        prompt = pm.get_prompt(
            "shopping_list_optimization.user_template",
            ingredients_list=ingredients_list,
            staples_list=staples_list,
            organic_text=organic_text,
            subs_text=subs_text
        )
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,  # Maximum for Haiku (8192 would require Sonnet)
                temperature=0.3,  # Lower temperature for more consistent results
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Extract JSON from response
            content = response.content[0].text.strip()
            
            # Clean markdown if present
            if content.startswith('```json'):
                content = content.replace('```json', '').replace('```', '').strip()
            elif content.startswith('```'):
                content = content.replace('```', '').strip()
            
            result = json.loads(content)
            
            # Validate all items are present
            result = self._validate_items(result, raw_ingredients, staples)
            
            print(f"✅ AI Shopping List: {result.get('total_items', 0)} items organized into {len(result.get('categories', {}))} categories")
            return result
            
        except Exception as e:
            print(f"Native optimizer error: {e}")
            import traceback
            traceback.print_exc()
            # Fallback to basic organization
            return self._fallback_organization(raw_ingredients, staples)
    
    def _validate_items(self, result: Dict, raw_ingredients: List[Dict], staples: List[Dict]) -> Dict:
        """Ensure all items are in the result"""
        categories = result.get('categories', {})
        
        # Collect all AI items
        ai_items = set()
        for items in categories.values():
            for item in items:
                ai_items.add(item.get('item', '').lower().strip())
        
        # Check for missing items
        missing = []
        for ing in raw_ingredients:
            name = ing.get('name', ing.get('ingredient_name', '')).lower().strip()
            if not any(name in ai_item or ai_item in name for ai_item in ai_items):
                missing.append(ing)
        
        for staple in staples:
            if not staple.get('in_stock', False):
                name = staple.get('name', '').lower().strip()
                if not any(name in ai_item or ai_item in name for ai_item in ai_items):
                    missing.append({'name': staple['name'], 'quantity': staple.get('quantity', ''), 'unit': staple.get('unit', '')})
        
        # Add missing items
        if missing:
            print(f"⚠️  AI dropped {len(missing)} items - adding them back")
            if 'Other' not in categories:
                categories['Other'] = []
            for item in missing:
                name = item.get('name', item.get('ingredient_name', 'Unknown'))
                qty = item.get('quantity', '')
                unit = item.get('unit', '')
                categories['Other'].append({
                    'item': name,
                    'quantity': f"{qty} {unit}".strip(),
                    'notes': 'Added (missing from AI)'
                })
        
        result['total_items'] = sum(len(items) for items in categories.values())
        result['categories'] = categories
        return result
    
    def _fallback_organization(self, ingredients: List[Dict], staples: List[Dict]) -> Dict:
        """Basic fallback if AI fails"""
        items = []
        for ing in ingredients:
            name = ing.get('name', ing.get('ingredient_name', 'Unknown'))
            qty = ing.get('quantity', '')
            unit = ing.get('unit', '')
            items.append({"item": name, "quantity": f"{qty} {unit}".strip(), "notes": ""})
        
        for staple in staples:
            if not staple.get('in_stock', False):
                items.append({
                    "item": staple['name'],
                    "quantity": f"{staple.get('quantity', '')} {staple.get('unit', '')}".strip(),
                    "notes": "Staple"
                })
        
        return {
            "categories": {"Other": items},
            "shopping_tips": ["AI optimization unavailable"],
            "cost_saving_suggestions": [],
            "total_items": len(items)
        }
