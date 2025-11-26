"""
Shopping List Chat Agent - Native Anthropic SDK
Uses Claude's native tool use (function calling) for better performance
No LangChain dependency needed!
"""

import anthropic
import json
import os
from typing import Dict, List, Optional
from prompt_manager import get_prompt_manager


class ShoppingListChatAgent:
    """AI Chat Agent using Claude's native tool use capabilities"""
    
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
        self.conversation_history = []
        
        # Define tools that Claude can use
        self.tools = [
            {
                "name": "add_items",
                "description": "Add one or more items to the shopping list",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "items": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string", "description": "Item name"},
                                    "quantity": {"type": "string", "description": "Quantity (e.g., '2', '500g', '1L')"},
                                    "category": {"type": "string", "description": "Category (Fresh Produce, Dairy & Eggs, Meat & Protein, Pantry Staples, Frozen, Bakery, Other)"}
                                },
                                "required": ["name", "quantity", "category"]
                            }
                        }
                    },
                    "required": ["items"]
                }
            },
            {
                "name": "remove_items",
                "description": "Remove items from the shopping list",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "item_names": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Names of items to remove"
                        }
                    },
                    "required": ["item_names"]
                }
            },
            {
                "name": "modify_quantity",
                "description": "Change the quantity of an item",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "item_name": {"type": "string", "description": "Name of the item"},
                        "new_quantity": {"type": "string", "description": "New quantity"}
                    },
                    "required": ["item_name", "new_quantity"]
                }
            },
            {
                "name": "search_woolworths",
                "description": "Search for products in Woolworths catalog",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search term"},
                        "category": {"type": "string", "description": "Optional category filter"}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "set_preferred_product",
                "description": "Set or update a preferred Woolworths product for an ingredient. Saves permanently to user preferences.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "ingredient": {"type": "string", "description": "Ingredient name (e.g., 'greek yogurt', 'bananas')"},
                        "stockcode": {"type": "integer", "description": "Woolworths stockcode"},
                        "fallback_stockcodes": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": "Optional list of fallback stockcodes if primary is unavailable"
                        }
                    },
                    "required": ["ingredient", "stockcode"]
                }
            },
            {
                "name": "get_preferred_products",
                "description": "Get all saved preferred products for the user",
                "input_schema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "remove_preferred_product",
                "description": "Remove a preferred product preference",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "ingredient": {"type": "string", "description": "Ingredient name to remove preference for"}
                    },
                    "required": ["ingredient"]
                }
            }
        ]
    
    def chat(self, user_message: str, current_shopping_list: Dict) -> Dict:
        """
        Process user message using Claude's native tool use
        
        Args:
            user_message: User's message
            current_shopping_list: Current shopping list by category
            
        Returns:
            Dict with response and any actions taken
        """
        
        # Build system message with current list context
        system_message = self._build_system_message(current_shopping_list)
        
        # Build messages array
        messages = self.conversation_history + [
            {"role": "user", "content": user_message}
        ]
        
        try:
            # Call Claude with tool use
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                system=system_message,
                tools=self.tools,
                messages=messages
            )
            
            # Process response
            result = self._process_response(response, current_shopping_list)
            
            # Update conversation history
            self.conversation_history.append({"role": "user", "content": user_message})
            self.conversation_history.append({
                "role": "assistant",
                "content": response.content
            })
            
            return result
            
        except Exception as e:
            print(f"Chat error: {e}")
            import traceback
            traceback.print_exc()
            return {
                "response": "I encountered an error. Could you please rephrase your request?",
                "action": "none",
                "changes_made": None
            }
    
    def _build_system_message(self, shopping_list: Dict) -> str:
        """Build system message with shopping list context"""
        list_text = self._format_shopping_list(shopping_list)
        
        # Load prompt from prompt manager
        pm = get_prompt_manager()
        return pm.get_prompt("shopping_chat_assistant.system_template", list_text=list_text)
    
    def _format_shopping_list(self, shopping_list: Dict) -> str:
        """Format shopping list for display"""
        if not shopping_list:
            return "Shopping list is empty."
        
        lines = []
        total_items = 0
        
        for category, items in shopping_list.items():
            if items:
                lines.append(f"\n{category}:")
                for item in items:
                    if isinstance(item, dict):
                        name = item.get('item', item.get('name', item.get('ingredient_name', 'Unknown')))
                        qty = item.get('quantity', '')
                        notes = item.get('notes', '')
                        item_text = f"  - {name}"
                        if qty:
                            item_text += f" ({qty})"
                        if notes:
                            item_text += f" - {notes}"
                        lines.append(item_text)
                        total_items += 1
                    else:
                        lines.append(f"  - {item}")
                        total_items += 1
        
        lines.insert(0, f"Total items: {total_items}")
        return "\n".join(lines)
    
    def _process_response(self, response, current_shopping_list: Dict) -> Dict:
        """Process Claude's response and execute any tool calls"""
        
        # Check if Claude wants to use tools
        tool_calls = []
        text_response = ""
        
        for block in response.content:
            if block.type == "text":
                text_response = block.text
            elif block.type == "tool_use":
                tool_calls.append(block)
        
        # If no tool calls, just return the text response
        if not tool_calls:
            return {
                "response": text_response or "I'm here to help with your shopping list!",
                "action": "none",
                "changes_made": None
            }
        
        # Execute tool calls
        changes = []
        updated_list = current_shopping_list.copy()
        action_type = "none"
        
        for tool_call in tool_calls:
            tool_name = tool_call.name
            tool_input = tool_call.input
            
            if tool_name == "add_items":
                action_type = "add"
                for item in tool_input.get("items", []):
                    category = item.get("category", "Other")
                    if category not in updated_list:
                        updated_list[category] = []
                    
                    updated_list[category].append({
                        "item": item["name"],
                        "quantity": item.get("quantity", ""),
                        "notes": ""
                    })
                    changes.append(f"Added {item['name']} to {category}")
            
            elif tool_name == "remove_items":
                action_type = "remove"
                for item_name in tool_input.get("item_names", []):
                    removed = False
                    for category, items in updated_list.items():
                        for i, item in enumerate(items):
                            if isinstance(item, dict):
                                name = item.get('item', item.get('name', '')).lower()
                            else:
                                name = str(item).lower()
                            
                            if item_name.lower() in name:
                                items.pop(i)
                                changes.append(f"Removed {item_name}")
                                removed = True
                                break
                        if removed:
                            break
            
            elif tool_name == "modify_quantity":
                action_type = "modify"
                item_name = tool_input.get("item_name")
                new_qty = tool_input.get("new_quantity")
                
                for category, items in updated_list.items():
                    for item in items:
                        if isinstance(item, dict):
                            name = item.get('item', item.get('name', '')).lower()
                            if item_name.lower() in name:
                                item['quantity'] = new_qty
                                changes.append(f"Changed {item_name} quantity to {new_qty}")
                                break
            
            elif tool_name == "search_woolworths":
                # This would integrate with your Woolworths MCP
                action_type = "search"
                query = tool_input.get("query")
                changes.append(f"Searching Woolworths for: {query}")
            
            elif tool_name == "set_preferred_product":
                action_type = "set_preferred"
                ingredient = tool_input.get("ingredient")
                stockcode = tool_input.get("stockcode")
                fallback_codes = tool_input.get("fallback_stockcodes", [])
                
                # Actually save to Firestore
                try:
                    from preferred_products_manager import get_preferred_products_manager
                    from shopping_list_matcher import ShoppingListMatcher
                    
                    manager = get_preferred_products_manager()
                    
                    # Get product details from Woolworths
                    matcher = ShoppingListMatcher(use_preferences=False)
                    product_details = matcher.get_product_details(str(stockcode))
                    
                    if product_details:
                        success = manager.set_preferred_product(
                            ingredient_name=ingredient,
                            stockcode=int(stockcode),
                            product_name=product_details.get('display_name', ''),
                            price=product_details.get('price', 0),
                            image_url=product_details.get('imageUrl', ''),
                            fallback_stockcodes=[int(code) for code in fallback_codes] if fallback_codes else []
                        )
                        
                        if success:
                            fallback_text = f" with {len(fallback_codes)} fallback(s)" if fallback_codes else ""
                            changes.append(f"✅ Saved preference: {ingredient} → {product_details.get('display_name', stockcode)}{fallback_text}")
                        else:
                            changes.append(f"❌ Failed to save preference for {ingredient}")
                    else:
                        changes.append(f"❌ Could not find product details for stockcode {stockcode}")
                        
                except Exception as e:
                    changes.append(f"❌ Error saving preference: {str(e)}")
            
            elif tool_name == "get_preferred_products":
                action_type = "get_preferred"
                try:
                    from preferred_products_manager import get_preferred_products_manager
                    manager = get_preferred_products_manager()
                    prefs = manager.list_all_preferences()
                    
                    if prefs:
                        pref_text = "\n".join([
                            f"  • {p['ingredient_name']} → {p['product_name']} ({p['stockcode']}) - used {p.get('use_count', 0)} times"
                            for p in prefs
                        ])
                        changes.append(f"📋 Your {len(prefs)} preferred products:\n{pref_text}")
                    else:
                        changes.append("No preferred products saved yet.")
                except Exception as e:
                    changes.append(f"❌ Error getting preferences: {str(e)}")
            
            elif tool_name == "remove_preferred_product":
                action_type = "remove_preferred"
                ingredient = tool_input.get("ingredient")
                try:
                    from preferred_products_manager import get_preferred_products_manager
                    manager = get_preferred_products_manager()
                    success = manager.remove_preferred_product(ingredient)
                    
                    if success:
                        changes.append(f"✅ Removed preference for {ingredient}")
                    else:
                        changes.append(f"⚠️ No preference found for {ingredient}")
                except Exception as e:
                    changes.append(f"❌ Error removing preference: {str(e)}")
        
        return {
            "response": text_response or "I've updated your shopping list!",
            "action": action_type,
            "updated_list": updated_list if action_type in ["add", "remove", "modify"] else None,
            "changes_made": "; ".join(changes) if changes else None,
            "tool_calls": [{"name": tc.name, "input": tc.input} for tc in tool_calls]
        }
    
    def reset_conversation(self):
        """Clear conversation history"""
        self.conversation_history = []


# Standalone function for simple optimization without tools
def optimize_shopping_list_simple(raw_ingredients: List[Dict], 
                                  organic_preferences: List[str],
                                  substitutions: List[Dict],
                                  staples: List[Dict]) -> Dict:
    """
    Simple shopping list optimization using Claude without LangChain
    """
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")
    
    client = anthropic.Anthropic(api_key=api_key)
    
    # Format ingredients
    ingredients_list = "\n".join([
        f"- {ing.get('name', ing.get('ingredient_name', 'Unknown'))} {ing.get('quantity', '')} {ing.get('unit', '')}".strip()
        for ing in raw_ingredients
    ])
    
    staples_list = "\n".join([
        f"- {s.get('name')} {s.get('quantity', '')} {s.get('unit', '')}".strip()
        for s in staples if not s.get('in_stock', False)
    ])
    
    organic_text = ", ".join(organic_preferences) if organic_preferences else "None"
    
    prompt = f"""Organize this shopping list intelligently by category.

INGREDIENTS:
{ingredients_list}

STAPLES TO ADD (not in stock):
{staples_list}

ORGANIC PREFERENCES: {organic_text}

Return a JSON object with this structure:
{{
  "categories": {{
    "Fresh Produce": [{{"item": "name", "quantity": "amount", "notes": ""}}],
    "Dairy & Eggs": [],
    "Meat & Protein": [],
    "Pantry Staples": [],
    "Frozen": [],
    "Bakery": [],
    "Other": []
  }},
  "shopping_tips": ["tip1", "tip2"],
  "cost_saving_suggestions": ["suggestion1"],
  "total_items": 0
}}

Rules:
- Combine duplicates (e.g., "2 cups milk" + "1 cup milk" = "3 cups milk")
- Apply organic preferences where specified
- Include ALL items - never skip any
- Return ONLY valid JSON"""
    
    try:
        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=4096,
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
        
        print(f"✅ AI Shopping List: {result.get('total_items', 0)} items organized")
        return result
        
    except Exception as e:
        print(f"Optimization error: {e}")
        # Return basic fallback
        return {
            "categories": {"Other": [
                {"item": ing.get('name', 'Unknown'), "quantity": ing.get('quantity', ''), "notes": ""}
                for ing in raw_ingredients
            ]},
            "shopping_tips": [],
            "cost_saving_suggestions": [],
            "total_items": len(raw_ingredients)
        }
