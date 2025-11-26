"""
Extract Preferred Products from Current Woolworths Cart
Run this script after manually adding your preferred items to the cart
"""

import json
from preferred_products_manager import get_preferred_products_manager

# Mapping of ingredients to stockcodes (you'll update this manually first time)
MANUAL_PREFERENCES = {
    # Example format:
    # "greek yogurt": 571487,
    # "banana": 306510,
    # Add your preferences here after reviewing your cart
}

def extract_from_woolworths_cart():
    """
    Extract preferences from Woolworths cart API
    You'll need to get the cart data first
    """
    print("=" * 80)
    print("EXTRACT PREFERRED PRODUCTS FROM CART")
    print("=" * 80)
    print()
    
    # Get cart data (you'll need to implement cart retrieval)
    print("📋 Step 1: Get your current Woolworths cart")
    print("   - Go to woolworths.com.au and add your preferred items")
    print("   - Use the Woolworths MCP tools to get cart data")
    print()
    
    # For now, use manual mapping
    if MANUAL_PREFERENCES:
        print(f"📝 Found {len(MANUAL_PREFERENCES)} manual preferences")
        
        manager = get_preferred_products_manager()
        
        for ingredient, stockcode in MANUAL_PREFERENCES.items():
            print(f"\n🔍 Processing: {ingredient} → {stockcode}")
            
            # Get product details from Woolworths
            from shopping_list_matcher import ShoppingListMatcher
            matcher = ShoppingListMatcher(use_preferences=False)  # Don't use preferences when looking up
            
            product_details = matcher.get_product_details(str(stockcode))
            
            if product_details:
                success = manager.set_preferred_product(
                    ingredient_name=ingredient,
                    stockcode=stockcode,
                    product_name=product_details.get('display_name', ''),
                    price=product_details.get('price', 0),
                    image_url=product_details.get('imageUrl', '')
                )
                
                if success:
                    print(f"  ✅ Saved: {product_details.get('display_name', '')}")
                else:
                    print(f"  ❌ Failed to save")
            else:
                print(f"  ⚠️  Could not find product details for stockcode {stockcode}")
        
        print()
        print("=" * 80)
        print("✅ PREFERENCES SAVED!")
        print("=" * 80)
        
        # Show summary
        preferences = manager.list_all_preferences()
        print(f"\n📊 Total Preferences: {len(preferences)}")
        print("\nSaved preferences:")
        for pref in preferences:
            print(f"  • {pref['ingredient_name']} → {pref['product_name']} ({pref['stockcode']})")
    
    else:
        print("⚠️  No manual preferences defined yet")
        print()
        print("To add preferences:")
        print("1. Edit this file and add to MANUAL_PREFERENCES dict")
        print("2. Format: \"ingredient name\": stockcode")
        print("3. Example: \"greek yogurt\": 571487")
        print()
        print("Or use the Shopping Chat Assistant:")
        print('   "For greek yogurt, use stockcode 571487"')

def import_from_cart_json(cart_file: str = "cart_export.json"):
    """Import preferences from exported cart JSON"""
    try:
        with open(cart_file, 'r') as f:
            cart_data = json.load(f)
        
        manager = get_preferred_products_manager()
        
        # Assuming cart has Products array
        products = cart_data.get('Products', [])
        
        imported = manager.import_from_cart(products)
        print(f"✅ Imported {imported} preferences from cart")
        
    except FileNotFoundError:
        print(f"❌ Cart file not found: {cart_file}")
    except Exception as e:
        print(f"❌ Error importing from cart: {e}")

if __name__ == "__main__":
    print()
    print("PREFERRED PRODUCTS SETUP")
    print()
    print("Choose an option:")
    print("1. Manual setup (edit MANUAL_PREFERENCES in this file)")
    print("2. Import from cart JSON file")
    print()
    
    choice = input("Enter choice (1 or 2): ").strip()
    
    if choice == "1":
        extract_from_woolworths_cart()
    elif choice == "2":
        filename = input("Enter cart JSON filename (default: cart_export.json): ").strip()
        if not filename:
            filename = "cart_export.json"
        import_from_cart_json(filename)
    else:
        print("Invalid choice")
