"""
Recipe URL Parser
Extracts recipe information from various sources including websites, Instagram, and Facebook
"""

import requests
from bs4 import BeautifulSoup
import re
import json
from typing import Dict, Optional, List
from urllib.parse import urlparse

class RecipeParser:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    def parse_url(self, url: str) -> Optional[Dict]:
        """Parse a recipe URL and extract recipe information"""
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()
        
        # Determine source type
        if 'instagram.com' in domain:
            return self._parse_instagram(url)
        elif 'facebook.com' in domain or 'fb.com' in domain:
            return self._parse_facebook(url)
        else:
            return self._parse_generic_website(url)
    
    def _parse_generic_website(self, url: str) -> Optional[Dict]:
        """Parse recipe from a standard recipe website using schema.org and heuristics"""
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            recipe_data = {
                'source_url': url,
                'source_type': 'website',
                'name': None,
                'description': None,
                'ingredients': [],
                'method': None,
                'prep_time': None,
                'cook_time': None,
                'total_time': None,
                'servings': 4,
                'image_url': None,
                'cuisine': None,
                'meal_type': None
            }
            
            # Try to find JSON-LD schema.org Recipe data
            json_ld = soup.find('script', type='application/ld+json')
            if json_ld:
                try:
                    data = json.loads(json_ld.string)
                    if isinstance(data, list):
                        data = data[0]
                    
                    if data.get('@type') == 'Recipe':
                        recipe_data['name'] = data.get('name')
                        recipe_data['description'] = data.get('description')
                        recipe_data['prep_time'] = data.get('prepTime')
                        recipe_data['cook_time'] = data.get('cookTime')
                        recipe_data['total_time'] = data.get('totalTime')
                        
                        if 'recipeYield' in data:
                            try:
                                recipe_data['servings'] = int(re.search(r'\d+', str(data['recipeYield'])).group())
                            except:
                                pass
                        
                        if 'image' in data:
                            if isinstance(data['image'], dict):
                                recipe_data['image_url'] = data['image'].get('url')
                            elif isinstance(data['image'], list):
                                recipe_data['image_url'] = data['image'][0] if data['image'] else None
                            else:
                                recipe_data['image_url'] = data['image']
                        
                        if 'recipeIngredient' in data:
                            recipe_data['ingredients'] = [
                                {'name': ing, 'quantity': '', 'unit': '', 'notes': ''}
                                for ing in data['recipeIngredient']
                            ]
                        
                        if 'recipeInstructions' in data:
                            instructions = data['recipeInstructions']
                            if isinstance(instructions, list):
                                method_steps = []
                                for step in instructions:
                                    if isinstance(step, dict):
                                        method_steps.append(step.get('text', ''))
                                    else:
                                        method_steps.append(str(step))
                                recipe_data['method'] = '\n'.join(method_steps)
                            else:
                                recipe_data['method'] = instructions
                        
                        if 'recipeCuisine' in data:
                            recipe_data['cuisine'] = data['recipeCuisine']
                        
                        if 'recipeCategory' in data:
                            recipe_data['meal_type'] = data['recipeCategory']
                        
                        return recipe_data
                except json.JSONDecodeError:
                    pass
            
            # Fallback: Extract using heuristics
            recipe_data['name'] = self._extract_title(soup)
            recipe_data['description'] = self._extract_description(soup)
            recipe_data['ingredients'] = self._extract_ingredients(soup)
            recipe_data['method'] = self._extract_method(soup)
            recipe_data['image_url'] = self._extract_image(soup)
            
            return recipe_data if recipe_data['name'] else None
            
        except Exception as e:
            print(f"Error parsing website: {e}")
            return None
    
    def _parse_instagram(self, url: str) -> Optional[Dict]:
        """Parse recipe from Instagram post"""
        # Note: Instagram scraping is challenging due to authentication requirements
        # This is a placeholder for future implementation with Instagram API or advanced scraping
        
        recipe_data = {
            'source_url': url,
            'source_type': 'instagram',
            'name': 'Instagram Recipe (Manual Entry Required)',
            'description': 'Please manually enter recipe details. Instagram requires authentication for automated scraping.',
            'ingredients': [],
            'method': '',
            'image_url': None
        }
        
        # TODO: Implement Instagram API integration or Selenium-based scraping
        # For now, return placeholder data
        return recipe_data
    
    def _parse_facebook(self, url: str) -> Optional[Dict]:
        """Parse recipe from Facebook post"""
        # Note: Facebook scraping is challenging due to authentication requirements
        # This is a placeholder for future implementation
        
        recipe_data = {
            'source_url': url,
            'source_type': 'facebook',
            'name': 'Facebook Recipe (Manual Entry Required)',
            'description': 'Please manually enter recipe details. Facebook requires authentication for automated scraping.',
            'ingredients': [],
            'method': '',
            'image_url': None
        }
        
        # TODO: Implement Facebook Graph API integration or Selenium-based scraping
        return recipe_data
    
    def _extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract recipe title using heuristics"""
        # Try h1 first
        h1 = soup.find('h1')
        if h1:
            return h1.get_text().strip()
        
        # Try title tag
        title = soup.find('title')
        if title:
            return title.get_text().strip()
        
        return None
    
    def _extract_description(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract recipe description"""
        # Try meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            return meta_desc['content'].strip()
        
        # Try first paragraph
        paragraphs = soup.find_all('p')
        if paragraphs:
            return paragraphs[0].get_text().strip()
        
        return None
    
    def _extract_ingredients(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract ingredients list"""
        ingredients = []
        
        # Common ingredient list selectors
        ingredient_containers = soup.find_all(['ul', 'ol'], class_=re.compile(r'ingredient', re.I))
        
        for container in ingredient_containers:
            items = container.find_all('li')
            for item in items:
                text = item.get_text().strip()
                if text:
                    # Try to parse quantity, unit, and ingredient name
                    parsed = self._parse_ingredient_line(text)
                    ingredients.append(parsed)
        
        return ingredients
    
    def _parse_ingredient_line(self, line: str) -> Dict:
        """Parse an ingredient line into components"""
        # Simple regex to extract quantity and unit
        # Example: "2 cups flour" -> quantity: 2, unit: cups, name: flour
        
        match = re.match(r'(\d+(?:\.\d+)?(?:/\d+)?)\s*([a-zA-Z]+)?\s+(.+)', line)
        
        if match:
            quantity, unit, name = match.groups()
            return {
                'quantity': quantity,
                'unit': unit or '',
                'name': name.strip(),
                'notes': ''
            }
        else:
            return {
                'quantity': '',
                'unit': '',
                'name': line,
                'notes': ''
            }
    
    def _extract_method(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract cooking method/instructions"""
        # Common method/instruction selectors
        method_containers = soup.find_all(['ol', 'div'], class_=re.compile(r'(instruction|method|direction|step)', re.I))
        
        steps = []
        for container in method_containers:
            items = container.find_all(['li', 'p'])
            for item in items:
                text = item.get_text().strip()
                if text and len(text) > 20:  # Filter out short text
                    steps.append(text)
        
        return '\n\n'.join(steps) if steps else None
    
    def _extract_image(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract recipe image URL"""
        # Try Open Graph image
        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            return og_image['content']
        
        # Try first large image
        images = soup.find_all('img')
        for img in images:
            src = img.get('src') or img.get('data-src')
            if src and 'recipe' in src.lower():
                return src
        
        # Return first image if nothing else found
        if images:
            return images[0].get('src') or images[0].get('data-src')
        
        return None
    
    def parse_manual_recipe(self, recipe_text: str) -> Dict:
        """Parse a manually pasted recipe text"""
        # Simple text-based parsing for copy-pasted recipes
        lines = recipe_text.strip().split('\n')
        
        recipe_data = {
            'source_url': None,
            'source_type': 'manual',
            'name': lines[0].strip() if lines else 'Untitled Recipe',
            'description': '',
            'ingredients': [],
            'method': '',
            'servings': 4
        }
        
        # Try to identify ingredients and method sections
        current_section = None
        ingredients_lines = []
        method_lines = []
        
        for line in lines[1:]:
            line = line.strip()
            if not line:
                continue
            
            lower_line = line.lower()
            if 'ingredient' in lower_line:
                current_section = 'ingredients'
                continue
            elif any(word in lower_line for word in ['method', 'instruction', 'direction', 'step']):
                current_section = 'method'
                continue
            
            if current_section == 'ingredients':
                ingredients_lines.append(line)
            elif current_section == 'method':
                method_lines.append(line)
        
        # Parse ingredients
        for line in ingredients_lines:
            recipe_data['ingredients'].append(self._parse_ingredient_line(line))
        
        # Join method lines
        recipe_data['method'] = '\n'.join(method_lines)
        
        return recipe_data
