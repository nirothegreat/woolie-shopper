"""
Shopping List Product Matcher
Searches Woolworths for each ingredient and matches to real products
"""

import requests
import os
from typing import List, Dict, Optional

class ShoppingListMatcher:
    """Matches shopping list ingredients to Woolworths products"""
    
    def __init__(self, mcp_url: str = None):
        self.mcp_url = mcp_url or os.getenv('WOOLWORTHS_MCP_URL', 'https://woolies-mcp-server-dk2j6ogx4a-uc.a.run.app')
    
    def get_product_details(self, stockcode: str) -> Optional[Dict]:
        """Get product details by stockcode from Woolworths using direct API"""
        try:
            # Call Woolworths API directly
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Accept': 'application/json'
            }
            
            response = requests.get(
                f'https://www.woolworths.com.au/apis/ui/products/{stockcode}',
                headers=headers,
                timeout=10
            )
            
            if response.status_code != 200:
                print(f"Failed to get product details for {stockcode}: {response.status_code}")
                return None
            
            product = response.json()
            
            if not product:
                print(f"No product data for stockcode {stockcode}")
                return None
            
            return {
                'name': product.get('Name', ''),
                'display_name': product.get('DisplayName', ''),
                'stockcode': product.get('Stockcode', stockcode),
                'price': product.get('Price') or 0,
                'brand': product.get('Brand', ''),
                'size': product.get('PackageSize', ''),
                'imageUrl': product.get('MediumImageFile', ''),
                'isOrganic': 'organic' in product.get('Name', '').lower(),
                'isAvailable': product.get('IsAvailable', True)
            }
            
        except Exception as e:
            print(f"Error getting product details for {stockcode}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def search_product(self, ingredient: str, quantity: str = "", unit: str = "") -> Optional[Dict]:
        """Search Woolworths for a product matching the ingredient"""
        try:
            search_query = ingredient.strip()
            
            response = requests.post(
                f'{self.mcp_url}/api/search',
                json={'searchTerm': search_query, 'pageSize': 3},
                timeout=10
            )
            
            if response.status_code != 200:
                return None
            
            data = response.json()
            if not data.get('success') or not data.get('products'):
                return None
            
            first_result = data['products'][0]
            if 'Products' in first_result and len(first_result['Products']) > 0:
                product = first_result['Products'][0]
                
                return {
                    'ingredient': ingredient,
                    'quantity': quantity,
                    'unit': unit,
                    'matched': True,
                    'product_name': product.get('Name', ''),
                    'display_name': product.get('DisplayName', ''),
                    'stockcode': product.get('Stockcode', 0),
                    'price': product.get('Price') or 0,
                    'cup_price': product.get('CupPrice') or 0,
                    'cup_string': product.get('CupString', ''),
                    'size': product.get('PackageSize', ''),
                    'image_url': product.get('MediumImageFile', ''),
                    'is_available': product.get('IsAvailable', True)
                }
            
            return None
            
        except Exception as e:
            print(f"Error searching for {ingredient}: {e}")
            return None
    
    def match_shopping_list(self, shopping_list_items: List[Dict]) -> Dict:
        """Match all items in shopping list to Woolworths products"""
        matched_items = []
        unmatched_items = []
        total_cost = 0.0
        
        for item in shopping_list_items:
            ingredient = item.get('ingredient_name') or item.get('name', '')
            quantity = item.get('quantity', '')
            unit = item.get('unit', '')
            category = item.get('category', 'Other')
            
            matched = self.search_product(ingredient, str(quantity), unit)
            
            if matched:
                matched['category'] = category
                matched['original_quantity'] = quantity
                matched['original_unit'] = unit
                matched_items.append(matched)
                # Handle None prices
                price = matched.get('price') or 0
                total_cost += price
            else:
                unmatched_items.append({
                    'ingredient': ingredient,
                    'quantity': quantity,
                    'unit': unit,
                    'category': category,
                    'matched': False
                })
        
        return {
            'matched_items': matched_items,
            'unmatched_items': unmatched_items,
            'total_matched': len(matched_items),
            'total_unmatched': len(unmatched_items),
            'total_items': len(shopping_list_items),
            'estimated_cost': total_cost,
            'match_rate': len(matched_items) / len(shopping_list_items) * 100 if shopping_list_items else 0
        }
    
    def export_to_local_format(self, match_results: Dict) -> str:
        """Export matched products to a simple text format"""
        output = []
        output.append("=" * 80)
        output.append("WOOLWORTHS SHOPPING LIST - MATCHED PRODUCTS")
        output.append("=" * 80)
        output.append(f"Match Rate: {match_results['match_rate']:.1f}%")
        output.append(f"Total Cost: ${match_results['estimated_cost']:.2f}")
        output.append("")
        
        categories = {}
        for item in match_results['matched_items']:
            cat = item['category']
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(item)
        
        for category, items in sorted(categories.items()):
            output.append(f"\n{'=' * 80}")
            output.append(f"{category.upper()}")
            output.append(f"{'=' * 80}")
            
            for item in items:
                output.append(f"\n✓ {item['ingredient']}")
                output.append(f"  Need: {item['original_quantity']} {item['original_unit']}")
                output.append(f"  Product: {item['display_name']}")
                output.append(f"  Price: ${item['price']:.2f}")
                output.append(f"  Stockcode: {item['stockcode']}")
                if item['cup_string']:
                    output.append(f"  Unit Price: {item['cup_string']}")
        
        if match_results['unmatched_items']:
            output.append(f"\n{'=' * 80}")
            output.append("UNMATCHED ITEMS (Manual Search Required)")
            output.append(f"{'=' * 80}")
            for item in match_results['unmatched_items']:
                output.append(f"\n✗ {item['ingredient']}")
                output.append(f"  Need: {item['quantity']} {item['unit']}")
        
        output.append(f"\n{'=' * 80}")
        output.append("END OF SHOPPING LIST")
        output.append(f"{'=' * 80}")
        
        return "\n".join(output)
    
    def export_to_json(self, match_results: Dict) -> Dict:
        """Export matched products to JSON format"""
        return {
            'summary': {
                'total_items': match_results['total_items'],
                'matched': match_results['total_matched'],
                'unmatched': match_results['total_unmatched'],
                'match_rate': f"{match_results['match_rate']:.1f}%",
                'estimated_cost': f"${match_results['estimated_cost']:.2f}"
            },
            'products': [
                {
                    'ingredient': item['ingredient'],
                    'quantity_needed': f"{item['original_quantity']} {item['original_unit']}",
                    'product': {
                        'name': item['display_name'],
                        'stockcode': item['stockcode'],
                        'price': item['price'],
                        'unit_price': item['cup_string'],
                        'image': item['image_url'],
                        'available': item['is_available']
                    },
                    'category': item['category']
                }
                for item in match_results['matched_items']
            ],
            'unmatched': [
                {
                    'ingredient': item['ingredient'],
                    'quantity_needed': f"{item['quantity']} {item['unit']}",
                    'category': item['category']
                }
                for item in match_results['unmatched_items']
            ]
        }
