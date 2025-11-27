"""
Flask Web Application for Woolworths Recipe Shopping
Replaces the Streamlit app with a proper web framework
"""

from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash
from recipe_manager import RecipeManager
from recipe_parser import RecipeParser
from database import PreferencesDB
from meal_plan_agent import MealPlanAgent, ShoppingListOptimizerNative, get_family_preferences_from_db
from shopping_chat_agent_native import ShoppingListChatAgent  # Using native Anthropic SDK (faster, simpler)
from shopping_list_matcher import ShoppingListMatcher
from config import config
from db_manager import db
import os
from datetime import datetime, timedelta
import json
import sqlite3
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Verify API key is loaded
anthropic_key = os.getenv('ANTHROPIC_API_KEY')
if anthropic_key:
    print(f"✅ ANTHROPIC_API_KEY loaded (starts with: {anthropic_key[:15]}...)")
else:
    print("⚠️  ANTHROPIC_API_KEY not found - AI features will be unavailable")

app = Flask(__name__)
app.secret_key = config.SECRET_KEY
app.config.from_object(config)

# Initialize database schema on startup
try:
    db.init_schema()
    print(f"✅ Using {db.db_type} database")
except Exception as e:
    print(f"⚠️  Database initialization warning: {e}")

# Initialize databases and AI agents
recipe_db = RecipeManager()  # Now uses Firestore on GCP, SQLite locally
prefs_db = PreferencesDB()

# Initialize AI agents (will be created on first use to avoid startup errors if no API key)
meal_plan_ai = None
shopping_optimizer = None
shopping_chat_agents = {}  # Store chat agents per session
shopping_list_matcher = None  # Shopping list matcher for Woolworths products

def get_shopping_list_matcher():
    """Get or create the shopping list matcher"""
    global shopping_list_matcher
    if shopping_list_matcher is None:
        try:
            shopping_list_matcher = ShoppingListMatcher()
        except Exception as e:
            print(f"Warning: Could not initialize shopping list matcher: {e}")
            return None
    return shopping_list_matcher

def get_meal_plan_agent():
    """Get or create the meal planning AI agent"""
    global meal_plan_ai
    if meal_plan_ai is None:
        try:
            meal_plan_ai = MealPlanAgent()
        except ValueError as e:
            print(f"Warning: Could not initialize AI agent: {e}")
            return None
    return meal_plan_ai

def get_shopping_optimizer():
    """Get or create the shopping list optimizer AI agent"""
    global shopping_optimizer
    if shopping_optimizer is None:
        try:
            shopping_optimizer = ShoppingListOptimizerNative()
        except ValueError as e:
            print(f"Warning: Could not initialize shopping optimizer: {e}")
            return None
    return shopping_optimizer

def get_shopping_chat_agent(session_id):
    """Get or create a shopping chat agent for this session"""
    global shopping_chat_agents
    if session_id not in shopping_chat_agents:
        try:
            shopping_chat_agents[session_id] = ShoppingListChatAgent()
        except ValueError as e:
            print(f"Warning: Could not initialize chat agent: {e}")
            return None
    return shopping_chat_agents[session_id]

# Helper function to apply preferences (from original app)
def apply_preferences(ingredients):
    """Apply user preferences to ingredient list"""
    result = []
    
    for item in ingredients:
        item_copy = item.copy()
        ingredient_name = item.get('name', item.get('ingredient_name', '')).lower()
        
        # Get substitutions - FIXED: use correct method name
        substitutions = prefs_db.get_all_substitutions()
        for sub in substitutions:
            if sub['original'].lower() in ingredient_name:
                item_copy['original_name'] = item_copy.get('name', item_copy.get('ingredient_name', ''))
                item_copy['name'] = sub['substitute']
                if 'notes' not in item_copy:
                    item_copy['notes'] = []
                item_copy['notes'].append(f"Substituted from {sub['original']}")
        
        # Apply organic preferences - FIXED: returns List[str], not List[Dict]
        organic_items = prefs_db.get_all_organic_preferences()
        for org_item_name in organic_items:
            if org_item_name.lower() in ingredient_name:
                search_term = f"organic {item_copy.get('name', item_copy.get('ingredient_name', ''))}"
                item_copy['search_term'] = search_term
                if 'notes' not in item_copy:
                    item_copy['notes'] = []
                item_copy['notes'].append("Organic preferred")
        
        result.append(item_copy)
    
    return result

# Routes

@app.route('/')
def index():
    """Home page with dashboard"""
    recipes = recipe_db.get_all_recipes()
    family_members = recipe_db.get_all_family_members()
    
    # Get stats
    total_recipes = len(recipes)
    breakfast_count = len([r for r in recipes if r.get('meal_type') == 'Breakfast'])
    dinner_count = len([r for r in recipes if r.get('meal_type') == 'Dinner'])
    
    return render_template('index.html', 
                         total_recipes=total_recipes,
                         breakfast_count=breakfast_count,
                         dinner_count=dinner_count,
                         family_count=len(family_members))

@app.route('/recipes')
def recipes():
    """Recipe library page"""
    all_recipes = recipe_db.get_all_recipes()
    
    # Filter by meal type if requested
    meal_type = request.args.get('meal_type')
    if meal_type and meal_type != 'All':
        all_recipes = [r for r in all_recipes if r.get('meal_type') == meal_type]
    
    # Search
    search = request.args.get('search', '')
    if search:
        all_recipes = [r for r in all_recipes if search.lower() in r['name'].lower()]
    
    return render_template('recipes.html', recipes=all_recipes, search=search, meal_type=meal_type)

@app.route('/recipes/<recipe_id>')
def recipe_detail(recipe_id):
    """View single recipe details"""
    recipe = recipe_db.get_recipe(recipe_id)
    
    print(f"DEBUG recipe_detail: recipe_id={recipe_id}")
    print(f"DEBUG recipe_detail: recipe type={type(recipe)}")
    print(f"DEBUG recipe_detail: recipe={recipe}")
    
    if not recipe:
        flash('Recipe not found', 'error')
        return redirect(url_for('recipes'))
    
    # Ensure recipe is a dictionary
    if isinstance(recipe, str):
        print(f"ERROR: Recipe is a string, not a dict!")
        flash('Error loading recipe', 'error')
        return redirect(url_for('recipes'))
    
    return render_template('recipe_detail.html', recipe=recipe)

@app.route('/recipes/add', methods=['GET', 'POST'])
def add_recipe():
    """Add new recipe from URL or manual entry"""
    if request.method == 'POST':
        recipe_url = request.form.get('recipe_url')
        
        if recipe_url:
            # Parse recipe from URL
            parser = RecipeParser()
            recipe_data = parser.parse_url(recipe_url)
            
            if recipe_data:
                # Add to database
                recipe_id = recipe_db.add_recipe(recipe_data)
                flash(f'Recipe "{recipe_data["name"]}" added successfully!', 'success')
                return redirect(url_for('recipe_detail', recipe_id=recipe_id))
            else:
                flash('Could not parse recipe from URL. Please try manual entry.', 'error')
        else:
            # Manual entry
            # Parse ingredients from textarea using the unified measurement parser
            ingredients_text = request.form.get('ingredients', '')
            ingredients = []
            
            if ingredients_text:
                from measurement_parser import MeasurementParser
                parser = MeasurementParser()
                
                for line in ingredients_text.strip().split('\n'):
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Use measurement parser for consistent parsing
                    parsed = parser.parse_ingredient(line)
                    ingredients.append(parsed)
            
            recipe_data = {
                'name': request.form.get('name'),
                'description': request.form.get('description', ''),
                'servings': int(request.form.get('servings', 4)),
                'prep_time': request.form.get('prep_time'),
                'cook_time': request.form.get('cook_time'),
                'difficulty': request.form.get('difficulty', 'Medium'),
                'cuisine': request.form.get('cuisine', ''),
                'meal_type': request.form.get('meal_type', 'Dinner'),
                'method': request.form.get('method', ''),
                'ingredients': ingredients,
                'source_type': 'manual',
                'tags': []
            }
            
            recipe_id = recipe_db.add_recipe(recipe_data)
            flash(f'Recipe "{recipe_data["name"]}" added successfully with {len(ingredients)} ingredients!', 'success')
            return redirect(url_for('recipe_detail', recipe_id=recipe_id))
    
    return render_template('add_recipe.html')

@app.route('/recipes/<recipe_id>/delete', methods=['POST'])
def delete_recipe(recipe_id):
    """Delete a recipe"""
    recipe = recipe_db.get_recipe(recipe_id)
    if recipe:
        recipe_name = recipe["name"]
        success = recipe_db.delete_recipe(recipe_id)
        if success:
            flash(f'Recipe "{recipe_name}" deleted successfully!', 'success')
        else:
            flash(f'Failed to delete recipe "{recipe_name}"', 'error')
    else:
        flash('Recipe not found', 'error')
    return redirect(url_for('recipes'))

@app.route('/recipes/<recipe_id>/meal-type', methods=['POST'])
def update_recipe_meal_type(recipe_id):
    """Update the meal type of a recipe"""
    try:
        data = request.json
        meal_type = data.get('meal_type', '').strip()
        
        # Validate meal type
        valid_meal_types = ['Breakfast', 'Lunch', 'Dinner', 'Snack', 'Dessert']
        if meal_type not in valid_meal_types:
            return jsonify({'success': False, 'error': 'Invalid meal type'}), 400
        
        recipe = recipe_db.get_recipe(recipe_id)
        if not recipe:
            return jsonify({'success': False, 'error': 'Recipe not found'}), 404
        
        # Update recipe
        success = recipe_db.update_recipe(recipe_id, meal_type=meal_type)
        
        if success:
            return jsonify({'success': True, 'meal_type': meal_type})
        else:
            return jsonify({'success': False, 'error': 'Failed to update recipe'}), 500
            
    except Exception as e:
        print(f"Error updating meal type: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/recipes/<recipe_id>/tags', methods=['POST'])
def add_recipe_tag(recipe_id):
    """Add a tag to a recipe"""
    try:
        data = request.json
        tag = data.get('tag', '').strip().lower()
        
        if not tag:
            return jsonify({'success': False, 'error': 'Tag cannot be empty'}), 400
        
        recipe = recipe_db.get_recipe(recipe_id)
        if not recipe:
            return jsonify({'success': False, 'error': 'Recipe not found'}), 404
        
        # Get current tags
        tags = recipe.get('tags', [])
        
        # Check if tag already exists
        if tag in tags:
            return jsonify({'success': False, 'error': 'Tag already exists'}), 400
        
        # Add new tag
        tags.append(tag)
        
        # Update recipe
        success = recipe_db.update_recipe(recipe_id, tags=tags)
        
        if success:
            return jsonify({'success': True, 'tag': tag})
        else:
            return jsonify({'success': False, 'error': 'Failed to update recipe'}), 500
            
    except Exception as e:
        print(f"Error adding tag: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/recipes/<recipe_id>/tags/<tag>', methods=['DELETE'])
def remove_recipe_tag(recipe_id, tag):
    """Remove a tag from a recipe"""
    try:
        recipe = recipe_db.get_recipe(recipe_id)
        if not recipe:
            return jsonify({'success': False, 'error': 'Recipe not found'}), 404
        
        # Get current tags
        tags = recipe.get('tags', [])
        
        # Remove tag if it exists
        if tag in tags:
            tags.remove(tag)
            
            # Update recipe
            success = recipe_db.update_recipe(recipe_id, tags=tags)
            
            if success:
                return jsonify({'success': True})
            else:
                return jsonify({'success': False, 'error': 'Failed to update recipe'}), 500
        else:
            return jsonify({'success': False, 'error': 'Tag not found'}), 404
            
    except Exception as e:
        print(f"Error removing tag: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/family')
def family_preferences():
    """Family preferences management"""
    family_members = recipe_db.get_all_family_members()
    all_recipes = recipe_db.get_all_recipes()
    
    return render_template('family_preferences.html', 
                         family_members=family_members,
                         recipes=all_recipes)

@app.route('/family/<int:member_id>/preferences', methods=['POST'])
def update_family_preferences(member_id):
    """Update family member preferences"""
    member = recipe_db.get_family_member(member_id)
    if not member:
        flash('Family member not found', 'error')
        return redirect(url_for('family_preferences'))
    
    # Get preferences from form (one per line)
    prefs_text = request.form.get('preferences', '')
    prefs_list = [p.strip() for p in prefs_text.split('\n') if p.strip()]
    
    recipe_db.update_family_member_preferences(member['name'], prefs_list)
    flash(f'Preferences updated for {member["display_name"]}', 'success')
    
    return redirect(url_for('family_preferences'))

@app.route('/meal-plan')
def meal_plan():
    """Meal planning page"""
    # Get or create current week's meal plan
    if 'meal_plan' not in session:
        # Initialize empty meal plan for current week
        today = datetime.now()
        week_start = today - timedelta(days=today.weekday())
        
        session['meal_plan'] = {
            'start_date': week_start.strftime('%Y-%m-%d'),
            'end_date': (week_start + timedelta(days=6)).strftime('%Y-%m-%d'),
            'meals': {}
        }
    
    all_recipes = recipe_db.get_all_recipes()
    meal_plan = session.get('meal_plan', {})
    
    return render_template('meal_plan.html', 
                         recipes=all_recipes,
                         meal_plan=meal_plan)

@app.route('/meal-plan/update', methods=['POST'])
def update_meal_plan():
    """Update meal plan"""
    data = request.json
    
    if 'meal_plan' not in session:
        session['meal_plan'] = {'meals': {}}
    
    # Update the meal plan
    date = data.get('date')
    meal_type = data.get('meal_type')
    recipe_name = data.get('recipe_name')
    
    if date not in session['meal_plan']['meals']:
        session['meal_plan']['meals'][date] = {}
    
    session['meal_plan']['meals'][date][meal_type] = recipe_name
    session.modified = True
    
    return jsonify({'success': True})

@app.route('/meal-plan/save', methods=['POST'])
def save_meal_plan():
    """Save the current meal plan to database"""
    data = request.json
    plan_name = data.get('name', f"Meal Plan {datetime.now().strftime('%Y-%m-%d')}")
    
    meal_plan = session.get('meal_plan', {})
    if not meal_plan.get('meals'):
        return jsonify({'success': False, 'error': 'No meal plan to save'}), 400
    
    try:
        meal_plan_id = recipe_db.save_meal_plan(
            name=plan_name,
            start_date=meal_plan.get('start_date', ''),
            end_date=meal_plan.get('end_date', ''),
            meals=meal_plan.get('meals', {}),
            ai_strategy=meal_plan.get('ai_strategy')
        )
        
        if meal_plan_id:
            return jsonify({'success': True, 'id': meal_plan_id, 'message': 'Meal plan saved successfully!'})
        else:
            return jsonify({'success': False, 'error': 'Failed to save meal plan'}), 500
    except Exception as e:
        print(f"Error saving meal plan: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/meal-plan/export', methods=['POST'])
def export_meal_plan():
    """Export the current meal plan as HTML with recipe links"""
    from flask import make_response
    
    meal_plan = session.get('meal_plan', {})
    if not meal_plan.get('meals'):
        return jsonify({'success': False, 'error': 'No meal plan to export'}), 400
    
    try:
        # Get all recipes to build recipe URL mapping
        all_recipes = recipe_db.get_all_recipes()
        recipe_lookup = {r['name']: r for r in all_recipes}
        
        # Build HTML export
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Meal Plan - Week of {meal_plan.get('start_date', '')}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
            background: #f8f9fa;
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #007bff;
            padding-bottom: 0.5rem;
        }}
        .info {{
            background: #e3f2fd;
            padding: 1rem;
            border-radius: 8px;
            margin-bottom: 2rem;
        }}
        .day-section {{
            background: white;
            border-radius: 8px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .day-header {{
            font-size: 1.5rem;
            font-weight: bold;
            color: #007bff;
            margin-bottom: 0.5rem;
        }}
        .date {{
            color: #6c757d;
            font-size: 0.9rem;
            margin-bottom: 1rem;
        }}
        .reasoning {{
            background: #f0f9ff;
            border-left: 4px solid #2c7a4d;
            padding: 0.75rem;
            margin-bottom: 1rem;
            font-style: italic;
            color: #2c7a4d;
        }}
        .meal-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1rem;
        }}
        .meal-card {{
            background: #f8f9fa;
            padding: 1rem;
            border-radius: 6px;
            border-left: 4px solid #007bff;
        }}
        .meal-type {{
            font-weight: 600;
            color: #495057;
            margin-bottom: 0.5rem;
            text-transform: uppercase;
            font-size: 0.85rem;
        }}
        .recipe-name {{
            font-size: 1.1rem;
            margin-bottom: 0.5rem;
        }}
        .recipe-link {{
            color: #007bff;
            text-decoration: none;
            font-weight: 500;
        }}
        .recipe-link:hover {{
            text-decoration: underline;
        }}
        .no-meal {{
            color: #6c757d;
            font-style: italic;
        }}
        .strategy {{
            background: #d4edda;
            border: 1px solid #c3e6cb;
            color: #155724;
            padding: 1rem;
            border-radius: 8px;
            margin-bottom: 2rem;
        }}
        @media print {{
            body {{
                background: white;
            }}
            .day-section {{
                box-shadow: none;
                border: 1px solid #ddd;
            }}
        }}
    </style>
</head>
<body>
    <h1>📅 Meal Plan</h1>
    <div class="info">
        <strong>Week:</strong> {meal_plan.get('start_date', '')} to {meal_plan.get('end_date', '')}<br>
        <strong>Exported:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M')}
    </div>
"""
        
        # Add AI strategy if present
        if meal_plan.get('ai_strategy'):
            html += f"""
    <div class="strategy">
        <strong>🧠 AI Strategy:</strong> {meal_plan.get('ai_strategy', '')}
    </div>
"""
        
        # Add meal days
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        sorted_dates = sorted(meal_plan.get('meals', {}).keys())
        
        for i, day in enumerate(days):
            if i < len(sorted_dates):
                date = sorted_dates[i]
                day_meals = meal_plan['meals'].get(date, {})
                reasoning = day_meals.get('reasoning', '')
                
                html += f"""
    <div class="day-section">
        <div class="day-header">{day}</div>
        <div class="date">{date}</div>
"""
                
                if reasoning:
                    html += f"""
        <div class="reasoning">💡 {reasoning}</div>
"""
                
                html += """
        <div class="meal-grid">
"""
                
                # Define meal types with emojis
                meal_types = [
                    ('breakfast', '🌅 Breakfast'),
                    ('breakfast_maya', '👧 Maya Breakfast'),
                    ('breakfast_ehren', '👦 Ehren Breakfast'),
                    ('lunch', '🥪 Lunch'),
                    ('lunch_ehren', '🎒 Ehren School Lunch'),
                    ('dinner', '🍽️ Dinner'),
                ]
                
                for meal_key, meal_label in meal_types:
                    recipe_name = day_meals.get(meal_key)
                    if recipe_name:
                        recipe = recipe_lookup.get(recipe_name)
                        recipe_url = recipe.get('source_url') if recipe and recipe.get('source_url') else None
                        
                        html += f"""
            <div class="meal-card">
                <div class="meal-type">{meal_label}</div>
                <div class="recipe-name">
"""
                        
                        if recipe_url:
                            html += f"""                    <a href="{recipe_url}" class="recipe-link" target="_blank">{recipe_name}</a>
"""
                        else:
                            html += f"""                    <span>{recipe_name}</span>
"""
                        
                        html += """                </div>
            </div>
"""
                
                html += """
        </div>
    </div>
"""
        
        html += """
</body>
</html>
"""
        
        # Create response
        response = make_response(html)
        response.headers['Content-Type'] = 'text/html'
        response.headers['Content-Disposition'] = f'attachment; filename=meal-plan-{meal_plan.get("start_date", "export")}.html'
        
        return response
        
    except Exception as e:
        print(f"Error exporting meal plan: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/meal-plan/list')
def list_meal_plans():
    """Show all saved meal plans"""
    saved_plans = recipe_db.get_all_meal_plans()
    return render_template('meal_plan_list.html', meal_plans=saved_plans)

@app.route('/meal-plan/load/<plan_id>', methods=['POST'])
def load_meal_plan(plan_id):
    """Load a saved meal plan"""
    try:
        meal_plan = recipe_db.get_meal_plan(plan_id)
        if meal_plan:
            session['meal_plan'] = {
                'start_date': meal_plan.get('start_date', ''),
                'end_date': meal_plan.get('end_date', ''),
                'meals': meal_plan.get('meals', {}),
                'ai_strategy': meal_plan.get('ai_strategy')
            }
            session.modified = True
            flash(f"Loaded meal plan: {meal_plan.get('name', 'Unnamed')}", 'success')
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Meal plan not found'}), 404
    except Exception as e:
        print(f"Error loading meal plan: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/meal-plan/delete/<plan_id>', methods=['POST'])
def delete_saved_meal_plan(plan_id):
    """Delete a saved meal plan"""
    try:
        success = recipe_db.delete_meal_plan(plan_id)
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Failed to delete meal plan'}), 500
    except Exception as e:
        print(f"Error deleting meal plan: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/meal-plan/auto-generate', methods=['POST'])
def auto_generate_meal_plan():
    """Automatically generate a meal plan based on recipes and preferences"""
    import random
    
    all_recipes = recipe_db.get_all_recipes()
    
    # Categorize recipes by meal type
    breakfast_recipes = [r for r in all_recipes if r.get('meal_type') == 'Breakfast']
    lunch_recipes = [r for r in all_recipes if r.get('meal_type') in ['Lunch', 'Dinner']]
    dinner_recipes = [r for r in all_recipes if r.get('meal_type') == 'Dinner']
    
    # Filter recipes by tags for kids
    maya_breakfast = [r for r in breakfast_recipes if 'maya' in [t.lower() for t in r.get('tags', [])]]
    ehren_breakfast = [r for r in breakfast_recipes if 'ehren' in [t.lower() for t in r.get('tags', [])]]
    ehren_lunch = [r for r in lunch_recipes if 'ehren' in [t.lower() for t in r.get('tags', [])]]
    
    # If no lunch recipes, use dinner recipes for lunch too
    if not lunch_recipes:
        lunch_recipes = dinner_recipes.copy()
    
    if not breakfast_recipes or not dinner_recipes:
        flash('Need at least some breakfast and dinner recipes to auto-generate!', 'error')
        return redirect(url_for('meal_plan'))
    
    # Initialize meal plan
    today = datetime.now()
    week_start = today - timedelta(days=today.weekday())
    
    session['meal_plan'] = {
        'start_date': week_start.strftime('%Y-%m-%d'),
        'end_date': (week_start + timedelta(days=4)).strftime('%Y-%m-%d'),  # End on Friday
        'meals': {}
    }
    
    # Generate meal plan with repeating lunch/dinner
    used_breakfast = []
    current_lunch = None
    lunch_days_left = 0
    current_dinner = None
    dinner_days_left = 0
    
    # Only generate for weekdays (Monday-Friday)
    for day_num in range(5):  # Changed from 7 to 5
        day_date = (week_start + timedelta(days=day_num)).strftime('%Y-%m-%d')
        session['meal_plan']['meals'][day_date] = {}
        
        # Breakfast 1 - General (always different)
        available_breakfast = [r for r in breakfast_recipes if r['name'] not in used_breakfast]
        if not available_breakfast:
            used_breakfast = []
            available_breakfast = breakfast_recipes
        
        breakfast = random.choice(available_breakfast)
        used_breakfast.append(breakfast['name'])
        session['meal_plan']['meals'][day_date]['breakfast'] = breakfast['name']
        
        # Breakfast 2 - Maya's breakfast
        if maya_breakfast:
            maya_bfast = random.choice(maya_breakfast)
            session['meal_plan']['meals'][day_date]['breakfast_maya'] = maya_bfast['name']
        else:
            # Fallback to general breakfast if no Maya-tagged recipes
            maya_bfast = random.choice(breakfast_recipes)
            session['meal_plan']['meals'][day_date]['breakfast_maya'] = maya_bfast['name']
        
        # Breakfast 3 - Ehren's breakfast
        if ehren_breakfast:
            ehren_bfast = random.choice(ehren_breakfast)
            session['meal_plan']['meals'][day_date]['breakfast_ehren'] = ehren_bfast['name']
        else:
            # Fallback to general breakfast if no Ehren-tagged recipes
            ehren_bfast = random.choice(breakfast_recipes)
            session['meal_plan']['meals'][day_date]['breakfast_ehren'] = ehren_bfast['name']
        
        # Lunch 1 - General (can repeat for 2-3 days - leftovers!)
        if lunch_days_left <= 0:
            current_lunch = random.choice(lunch_recipes)
            lunch_days_left = random.randint(2, 3)
        
        session['meal_plan']['meals'][day_date]['lunch'] = current_lunch['name']
        lunch_days_left -= 1
        
        # Lunch 2 - Ehren's school lunch (different each day)
        if ehren_lunch:
            ehren_lunch_choice = random.choice(ehren_lunch)
            session['meal_plan']['meals'][day_date]['lunch_ehren'] = ehren_lunch_choice['name']
        else:
            # Fallback to general lunch if no Ehren-tagged recipes
            ehren_lunch_choice = random.choice(lunch_recipes)
            session['meal_plan']['meals'][day_date]['lunch_ehren'] = ehren_lunch_choice['name']
        
        # Dinner - can repeat for 2-3 days (leftovers!)
        if dinner_days_left <= 0:
            current_dinner = random.choice(dinner_recipes)
            dinner_days_left = random.randint(2, 3)
        
        session['meal_plan']['meals'][day_date]['dinner'] = current_dinner['name']
        dinner_days_left -= 1
    
    session.modified = True
    flash('✅ Meal plan auto-generated for weekdays! Includes breakfast for Maya & Ehren, and Ehren\'s school lunch.', 'success')
    
    return redirect(url_for('meal_plan'))

@app.route('/meal-plan/ai-generate', methods=['POST'])
def ai_generate_meal_plan():
    """AI-powered meal plan generation using LangChain"""
    agent = get_meal_plan_agent()
    
    if agent is None:
        flash('❌ AI agent not configured. Please set OPENAI_API_KEY environment variable.', 'error')
        return redirect(url_for('meal_plan'))
    
    try:
        # Get all recipes
        all_recipes = recipe_db.get_all_recipes()
        
        if not all_recipes:
            flash('❌ No recipes available. Please add some recipes first!', 'error')
            return redirect(url_for('meal_plan'))
        
        # Get family preferences
        family_preferences = get_family_preferences_from_db(recipe_db)
        
        # Get additional context from form (if any)
        additional_context = request.form.get('context', '')
        
        flash('🤖 AI is generating your meal plan... This may take a moment.', 'info')
        
        # Generate meal plan using AI
        print(f"🤖 Generating AI meal plan with {len(all_recipes)} recipes...")
        ai_meal_plan = agent.generate_meal_plan(
            recipes=all_recipes,
            family_preferences=family_preferences,
            additional_context=additional_context
        )
        
        print(f"✅ AI generated {len(ai_meal_plan.week_plan)} days")
        
        # Convert AI meal plan to session format
        today = datetime.now()
        week_start = today - timedelta(days=today.weekday())
        
        session['meal_plan'] = {
            'start_date': week_start.strftime('%Y-%m-%d'),
            'end_date': (week_start + timedelta(days=6)).strftime('%Y-%m-%d'),
            'meals': {},
            'ai_strategy': ai_meal_plan.overall_strategy
        }
        
        # Map AI recommendations to dates
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        for idx, day_plan in enumerate(ai_meal_plan.week_plan):
            day_date = (week_start + timedelta(days=idx)).strftime('%Y-%m-%d')
            
            # Debug logging
            print(f"Day {idx} ({day_plan.day}): B={day_plan.breakfast}, BM={day_plan.breakfast_maya}, BE={day_plan.breakfast_ehren}, L={day_plan.lunch}, LE={day_plan.lunch_ehren}, D={day_plan.dinner}")
            
            session['meal_plan']['meals'][day_date] = {
                'breakfast': day_plan.breakfast or '',
                'breakfast_maya': day_plan.breakfast_maya or '',
                'breakfast_ehren': day_plan.breakfast_ehren or '',
                'lunch': day_plan.lunch or '',
                'lunch_ehren': day_plan.lunch_ehren or '',
                'dinner': day_plan.dinner or '',
                'reasoning': day_plan.reasoning
            }
        
        session.modified = True
        flash(f'✅ AI meal plan generated! Strategy: {ai_meal_plan.overall_strategy}', 'success')
        
        return redirect(url_for('meal_plan'))
        
    except Exception as e:
        error_msg = str(e)
        # Extract useful info from validation errors
        if 'ValidationError' in error_msg or 'Field required' in error_msg:
            flash('❌ AI response format error - this is a temporary issue. Try again or use Random meal plan.', 'error')
        else:
            flash(f'❌ Error generating AI meal plan: {error_msg[:200]}', 'error')
        
        print(f"❌ AI meal plan error: {e}")
        import traceback
        traceback.print_exc()
        return redirect(url_for('meal_plan'))

@app.route('/shopping-list')
def shopping_list():
    """Generate and display shopping list"""
    # Check if we should use existing list from session (unless force_refresh is requested)
    force_refresh = request.args.get('force_refresh', 'false').lower() == 'true'
    servings_multiplier = float(request.args.get('multiplier', 1.0))
    
    # If shopping list already exists in session and not forcing refresh, use it
    if not force_refresh and 'shopping_list_categories' in session:
        print("✅ Using existing shopping list from session (modified by chat or previous generation)")
        categories = session.get('shopping_list_categories', {})
        staples = session.get('staples', get_default_staples())
        
        return render_template('shopping_list.html',
                             categories=categories,
                             staples=staples,
                             servings_multiplier=servings_multiplier,
                             ai_optimized=True,
                             shopping_tips=session.get('shopping_tips', []),
                             cost_saving=session.get('cost_saving', []),
                             from_session=True)
    
    # Generate fresh shopping list from meal plan
    print("🔄 Generating fresh shopping list from meal plan")
    
    # Get meal plan from session
    meal_plan = session.get('meal_plan', {})
    
    if not meal_plan.get('meals'):
        flash('Create a meal plan first!', 'warning')
        return redirect(url_for('meal_plan'))
    
    # Get selected recipes
    selected_recipe_names = set()
    for day_meals in meal_plan.get('meals', {}).values():
        for meal in day_meals.values():
            if meal and meal != 'None':
                # Handle both string and dict formats (defensive coding)
                if isinstance(meal, dict):
                    meal_name = meal.get('name', '')
                else:
                    meal_name = meal
                
                if meal_name:
                    selected_recipe_names.add(meal_name)
    
    # Get recipe IDs
    all_recipes = recipe_db.get_all_recipes()
    selected_recipe_ids = []
    for r in all_recipes:
        # Handle both string and dict formats for recipe names
        recipe_name = r.get('name', '')
        if isinstance(recipe_name, dict):
            recipe_name = recipe_name.get('name', '') if isinstance(recipe_name, dict) else str(recipe_name)
        
        if recipe_name in selected_recipe_names:
            selected_recipe_ids.append(r['id'])
    
    # Generate shopping list
    shopping_list_items = recipe_db.generate_shopping_list(selected_recipe_ids, servings_multiplier)
    
    # Get staples from session
    staples = session.get('staples', get_default_staples())
    
    # Add unchecked staples to shopping list
    for staple in staples:
        if not staple.get('in_stock', False):
            shopping_list_items.append({
                'ingredient_name': staple['name'],
                'name': staple['name'],
                'quantity': staple['quantity'],
                'unit': staple['unit'],
                'is_optional': False,
                'category_staple': staple['category']
            })
    
    # Try AI optimization first
    optimizer = get_shopping_optimizer()
    if optimizer:
        try:
            print(f"🤖 Starting AI shopping list optimization...")
            print(f"   Input: {len(shopping_list_items)} ingredients")
            
            # Get preferences for AI
            organic_prefs = prefs_db.get_all_organic_preferences()
            substitutions = prefs_db.get_all_substitutions()
            
            # Use AI to optimize
            ai_result = optimizer.optimize_shopping_list(
                raw_ingredients=shopping_list_items,
                organic_preferences=organic_prefs,
                substitutions=substitutions,
                staples=staples
            )
            
            print(f"✅ AI optimization complete!")
            
            # Convert AI result to our format
            categories = ai_result.get('categories', {})
            shopping_tips = ai_result.get('shopping_tips', [])
            cost_saving = ai_result.get('cost_saving_suggestions', [])
            
            # Store in session for chat agent and to preserve across page reloads
            session['shopping_list_categories'] = categories
            session['shopping_tips'] = shopping_tips
            session['cost_saving'] = cost_saving
            session.modified = True
            
            return render_template('shopping_list.html', 
                                 categories=categories,
                                 staples=staples,
                                 servings_multiplier=servings_multiplier,
                                 ai_optimized=True,
                                 shopping_tips=shopping_tips,
                                 cost_saving=cost_saving)
        except Exception as e:
            flash(f'⚠️ AI optimization failed, using standard list: {str(e)}', 'warning')
            print(f"❌ AI shopping list error: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("⚠️ Shopping optimizer not available (API key missing?)")
    
    # Standard processing (no AI or AI failed)
    # Apply preferences
    shopping_list_with_prefs = apply_preferences(shopping_list_items)
    
    # Categorize items
    categories = categorize_items(shopping_list_with_prefs)
    
    # Store categories in session for chat agent
    session['shopping_list_categories'] = categories
    session.modified = True
    
    return render_template('shopping_list.html', 
                         categories=categories,
                         staples=staples,
                         servings_multiplier=servings_multiplier,
                         ai_optimized=False,
                         shopping_tips=[],
                         cost_saving=[])

@app.route('/api/match-products', methods=['POST'])
def match_products():
    """Match shopping list items to actual Woolworths products"""
    try:
        data = request.json
        shopping_list_items = data.get('items', [])
        
        if not shopping_list_items:
            return jsonify({'success': False, 'error': 'No items provided'}), 400
        
        # Get matcher
        matcher = get_shopping_list_matcher()
        if not matcher:
            return jsonify({'success': False, 'error': 'Shopping list matcher not available'}), 503
        
        # Match all products
        match_results = matcher.match_shopping_list(shopping_list_items)
        
        # Store in session for download
        session['matched_products'] = match_results
        session.modified = True
        
        return jsonify({
            'success': True,
            'results': match_results
        })
    
    except Exception as e:
        print(f"Error in match_products: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/download-shopping-list')
def download_shopping_list():
    """Download matched shopping list as text or JSON file"""
    match_results = session.get('matched_products')
    
    print(f"Download requested - Session has matched_products: {match_results is not None}")
    
    if not match_results:
        print("No matched products in session")
        flash('No matched products found. Click "Match with Woolworths Products" first!', 'warning')
        return redirect(url_for('shopping_list'))
    
    try:
        # Get matcher to export
        matcher = get_shopping_list_matcher()
        if not matcher:
            flash('Shopping list matcher not available', 'error')
            return redirect(url_for('shopping_list'))
        
        # Get format (text or json)
        format_type = request.args.get('format', 'text')
        print(f"Download format: {format_type}")
        print(f"Matched items count: {match_results.get('total_matched', 0)}")
        
        from flask import Response
        
        if format_type == 'json':
            output = matcher.export_to_json(match_results)
            print(f"Generated JSON output with {len(output.get('products', []))} products")
            return Response(
                json.dumps(output, indent=2),
                mimetype='application/json',
                headers={'Content-Disposition': 'attachment; filename=woolworths_shopping_list.json'}
            )
        else:
            output = matcher.export_to_local_format(match_results)
            print(f"Generated TXT output, {len(output)} characters")
            return Response(
                output,
                mimetype='text/plain',
                headers={'Content-Disposition': 'attachment; filename=woolworths_shopping_list.txt'}
            )
    except Exception as e:
        print(f"Error generating download: {e}")
        flash(f'Error generating download: {str(e)}', 'error')
        return redirect(url_for('shopping_list'))

@app.route('/staples/update', methods=['POST'])
def update_staples():
    """Update staples list"""
    data = request.json
    session['staples'] = data.get('staples', [])
    session.modified = True
    return jsonify({'success': True})

@app.route('/preferences')
def preferences():
    """Shopping preferences management"""
    substitutions = prefs_db.get_all_substitutions()
    organic_prefs = prefs_db.get_all_organic_preferences()
    defaults = prefs_db.get_all_defaults()
    
    return render_template('preferences.html',
                         substitutions=substitutions,
                         organic_prefs=organic_prefs,
                         defaults=defaults)

@app.route('/api/shopping-chat', methods=['POST'])
def shopping_chat():
    """Chat with AI agent about shopping list"""
    data = request.json
    user_message = data.get('message', '')
    
    if not user_message:
        return jsonify({'success': False, 'error': 'No message provided'}), 400
    
    # Get or create chat agent for this session
    session_id = session.get('session_id')
    if not session_id:
        import uuid
        session_id = str(uuid.uuid4())
        session['session_id'] = session_id
    
    agent = get_shopping_chat_agent(session_id)
    if not agent:
        return jsonify({
            'success': False,
            'error': 'Chat agent not available. Please set OPENAI_API_KEY.'
        }), 503
    
    try:
        # Get current shopping list from session (stored as categories)
        shopping_list_categories = session.get('shopping_list_categories', {})
        
        # Debug: Log what we're sending to the agent
        print(f"DEBUG: Shopping list categories in session: {shopping_list_categories}")
        print(f"DEBUG: Number of categories: {len(shopping_list_categories)}")
        
        # Chat with agent (removed staples parameter)
        result = agent.chat(user_message, shopping_list_categories)
        
        # If the agent wants to set a preferred product
        if result.get('action') == 'set_preferred':
            stockcode = result.get('stockcode')
            ingredient = result.get('ingredient')
            
            if stockcode and ingredient:
                # Get product details from Woolworths
                try:
                    matcher = get_shopping_list_matcher()
                    if not matcher:
                        result['response'] = "❌ Shopping list matcher not available"
                        return jsonify({
                            'success': True,
                            'response': result['response'],
                            'action': result.get('action', 'none')
                        })
                    
                    product_details = matcher.get_product_details(stockcode)
                    
                    if product_details:
                        # Save as preferred product
                        if db.db_type == 'postgresql':
                            query = """
                                INSERT INTO preferred_products 
                                (ingredient, product_name, stockcode, brand, size, price, is_organic, image_url)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (ingredient) DO UPDATE SET
                                    product_name = EXCLUDED.product_name,
                                    stockcode = EXCLUDED.stockcode,
                                    brand = EXCLUDED.brand,
                                    size = EXCLUDED.size,
                                    price = EXCLUDED.price,
                                    is_organic = EXCLUDED.is_organic,
                                    image_url = EXCLUDED.image_url
                            """
                        else:
                            query = """
                                INSERT OR REPLACE INTO preferred_products 
                                (ingredient, product_name, stockcode, brand, size, price, is_organic, image_url)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """
                        
                        db.execute_query(query, (
                            ingredient,
                            product_details.get('name', product_details.get('Name', '')),
                            stockcode,
                            product_details.get('brand', product_details.get('Brand')),
                            product_details.get('size', product_details.get('Size')),
                            product_details.get('price', product_details.get('Price')),
                            1 if product_details.get('isOrganic') else 0,
                            product_details.get('imageUrl', product_details.get('ImageUrl'))
                        ))
                        
                        result['response'] = f"✅ Set preferred product for '{ingredient}': {product_details.get('name', 'Product')} (${product_details.get('price', 'N/A')})"
                        result['preferred_product_set'] = True
                    else:
                        result['response'] = f"❌ Could not find product details for stockcode {stockcode}"
                        
                except Exception as e:
                    print(f"Error setting preferred product: {e}")
                    result['response'] = f"❌ Error setting preferred product: {str(e)}"
        
        # If the agent modified the list, update session
        elif result.get('action') != 'none' and 'updated_list' in result:
            session['shopping_list_categories'] = result['updated_list']
            session.modified = True
        
        return jsonify({
            'success': True,
            'response': result.get('response', 'No response'),
            'action': result.get('action', 'none'),
            'changes_made': result.get('changes_made'),
            'updated_list': result.get('updated_list') if result.get('action') != 'none' else None,
            'preferred_product_set': result.get('preferred_product_set', False)
        })
        
    except Exception as e:
        print(f"Chat error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/reset-chat', methods=['POST'])
def reset_chat():
    """Reset chat conversation"""
    session_id = session.get('session_id')
    if session_id and session_id in shopping_chat_agents:
        shopping_chat_agents[session_id].reset_conversation()
    return jsonify({'success': True})

@app.route('/api/woolworths/search', methods=['POST'])
def woolworths_search():
    """
    Search Woolworths products
    Note: This endpoint requires manual MCP tool invocation through Cascade
    """
    data = request.json
    search_term = data.get('searchTerm', '')
    page_size = data.get('pageSize', 20)
    
    if not search_term:
        return jsonify({'success': False, 'error': 'Search term required'}), 400
    
    # Store search request in session for manual processing
    session['pending_search'] = {
        'term': search_term,
        'pageSize': page_size
    }
    session.modified = True
    
    return jsonify({
        'success': True,
        'message': 'Search request received. Results will be processed.',
        'searchTerm': search_term
    })

@app.route('/api/woolworths/product/<stockcode>')
def get_product(stockcode):
    """Get product details by stockcode"""
    session['pending_product_lookup'] = stockcode
    session.modified = True
    
    return jsonify({
        'success': True,
        'message': 'Product lookup requested',
        'stockcode': stockcode
    })

# Helper functions

def get_default_staples():
    """Get default staples list"""
    return [
        {'name': 'Milk', 'quantity': '2', 'unit': 'L', 'in_stock': False, 'category': 'Dairy'},
        {'name': 'Eggs', 'quantity': '1', 'unit': 'dozen', 'in_stock': False, 'category': 'Proteins'},
        {'name': 'Bread', 'quantity': '1', 'unit': 'loaf', 'in_stock': False, 'category': 'Bakery'},
        {'name': 'Strawberries', 'quantity': '1', 'unit': 'punnet', 'in_stock': False, 'category': 'Fresh Produce'},
        {'name': 'Blueberries', 'quantity': '1', 'unit': 'punnet', 'in_stock': False, 'category': 'Fresh Produce'},
        {'name': 'Butter', 'quantity': '250', 'unit': 'g', 'in_stock': False, 'category': 'Dairy'},
        {'name': 'Cheese', 'quantity': '500', 'unit': 'g', 'in_stock': False, 'category': 'Dairy'},
        {'name': 'Bananas', 'quantity': '1', 'unit': 'bunch', 'in_stock': False, 'category': 'Fresh Produce'},
        {'name': 'Apples', 'quantity': '1', 'unit': 'kg', 'in_stock': False, 'category': 'Fresh Produce'},
        {'name': 'Carrots', 'quantity': '1', 'unit': 'kg', 'in_stock': False, 'category': 'Fresh Produce'},
    ]

def categorize_items(items):
    """Categorize shopping list items"""
    categories = {}
    
    for item in items:
        # Check if it's a staple with predefined category
        if 'category_staple' in item:
            cat_name = item['category_staple']
            category_map = {
                'Dairy': '🥛 Dairy',
                'Proteins': '🍗 Proteins',
                'Fresh Produce': '🥬 Fresh Produce',
                'Bakery': '🍞 Bakery',
                'Pantry': '🏺 Pantry Staples',
                'Other': '📦 Other'
            }
            cat = category_map.get(cat_name, '📦 Other')
        else:
            # Categorize based on keywords
            ing_name = item.get('name', '').lower()
            
            if any(k in ing_name for k in ['chicken', 'beef', 'pork', 'fish', 'tofu', 'egg']):
                cat = "🍗 Proteins"
            elif any(k in ing_name for k in ['apple', 'banana', 'berry', 'tomato', 'lettuce', 'spinach', 'onion', 'garlic', 'strawberr', 'blueberr', 'carrot', 'pumpkin']):
                cat = "🥬 Fresh Produce"
            elif any(k in ing_name for k in ['milk', 'cheese', 'yogurt', 'butter']):
                cat = "🥛 Dairy"
            elif any(k in ing_name for k in ['bread', 'loaf']):
                cat = "🍞 Bakery"
            elif any(k in ing_name for k in ['flour', 'sugar', 'salt', 'pepper', 'oil', 'vinegar', 'rice']):
                cat = "🏺 Pantry Staples"
            else:
                cat = "📦 Other"
        
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(item)
    
    return categories

@app.route('/api/preferred-product/<ingredient>')
def get_preferred_product(ingredient):
    """Get preferred product for an ingredient"""
    try:
        # Use parameterized query that works for both SQLite and PostgreSQL
        query = """
            SELECT * FROM preferred_products 
            WHERE ingredient = %s OR ingredient LIKE %s
        """ if db.db_type == 'postgresql' else """
            SELECT * FROM preferred_products 
            WHERE ingredient = ? OR ingredient LIKE ?
        """
        
        product = db.execute_query(query, (ingredient, f"%{ingredient}%"), fetch_one=True)
        
        if product:
            return jsonify({
                'found': True,
                'product': product
            })
        return jsonify({'found': False})
    except Exception as e:
        return jsonify({'found': False, 'error': str(e)})

@app.route('/api/set-preferred-product', methods=['POST'])
def set_preferred_product():
    """Set preferred product for an ingredient"""
    try:
        data = request.json
        
        # Use appropriate SQL for database type
        if db.db_type == 'postgresql':
            query = """
                INSERT INTO preferred_products 
                (ingredient, product_name, stockcode, brand, size, price, is_organic, image_url)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (ingredient) DO UPDATE SET
                    product_name = EXCLUDED.product_name,
                    stockcode = EXCLUDED.stockcode,
                    brand = EXCLUDED.brand,
                    size = EXCLUDED.size,
                    price = EXCLUDED.price,
                    is_organic = EXCLUDED.is_organic,
                    image_url = EXCLUDED.image_url
            """
        else:
            query = """
                INSERT OR REPLACE INTO preferred_products 
                (ingredient, product_name, stockcode, brand, size, price, is_organic, image_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
        
        db.execute_query(query, (
            data['ingredient'],
            data['product_name'],
            data['stockcode'],
            data.get('brand'),
            data.get('size'),
            data.get('price'),
            1 if data.get('is_organic') else 0,
            data.get('image_url')
        ))
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/remove-preferred-product', methods=['POST'])
def remove_preferred_product():
    """Remove preferred product for an ingredient"""
    try:
        data = request.json
        
        # Use appropriate placeholder for database type
        query = "DELETE FROM preferred_products WHERE ingredient = %s" if db.db_type == 'postgresql' else "DELETE FROM preferred_products WHERE ingredient = ?"
        
        db.execute_query(query, (data['ingredient'],))
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/search-product', methods=['POST'])
def search_product():
    """Search for products on Woolworths via API service"""
    try:
        import requests as req
        
        data = request.json
        search_term = data.get('search_term') or data.get('searchTerm')
        page_size = data.get('pageSize', 20)
        
        if not search_term:
            return jsonify({'success': False, 'error': 'search_term is required'}), 400
        
        # Call Woolworths API service
        woolworths_api_url = os.environ.get('WOOLWORTHS_API_URL', 'https://woolies-api-120379231414.us-central1.run.app')
        
        response = req.post(
            f"{woolworths_api_url}/api/search",
            json={'searchTerm': search_term, 'pageSize': page_size},
            timeout=15
        )
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({'success': False, 'error': 'Search failed', 'products': []}), response.status_code
            
    except req.Timeout:
        return jsonify({'success': False, 'error': 'Request timed out', 'products': []}), 504
    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'products': []}), 500


if __name__ == '__main__':
    # For local development only - production uses gunicorn
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=os.environ.get('FLASK_DEBUG', 'False').lower() == 'true')
