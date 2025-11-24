"""
Woolworths API Service
REST API wrapper with Playwright authentication for cart management
"""

from flask import Flask, request, jsonify
import requests
import os
import json
import asyncio
from datetime import datetime, timedelta

app = Flask(__name__)

WOOLWORTHS_API_BASE = "https://www.woolworths.com.au/apis/ui"

# Store session cookies (in production, use Redis or similar)
user_sessions = {}

# Check if Playwright is available
PLAYWRIGHT_AVAILABLE = False
try:
    from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    print("⚠️  Playwright not available - authentication features disabled")


async def playwright_login(email: str, password: str):
    """Use Playwright to login and capture cookies"""
    if not PLAYWRIGHT_AVAILABLE:
        return {"success": False, "error": "Playwright not installed"}
    
    try:
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        print(f"🔐 Logging in to Woolworths as {email}...")
        
        # Navigate to login page
        await page.goto('https://www.woolworths.com.au/shop/securelogin', wait_until='networkidle')
        
        # Fill in login form
        await page.fill('input[name="username"]', email)
        await page.fill('input[name="password"]', password)
        
        # Click login button
        await page.click('button[type="submit"]')
        
        # Wait for login to complete (check for redirect or account page)
        try:
            await page.wait_for_url('**/shop/myaccount**', timeout=10000)
            print("✅ Login successful!")
        except PlaywrightTimeout:
            # Check if we're logged in anyway
            current_url = page.url
            if 'login' in current_url.lower():
                await browser.close()
                return {"success": False, "error": "Login failed - check credentials"}
        
        # Extract cookies
        cookies = await context.cookies()
        
        # Convert to requests-compatible format
        cookie_dict = {cookie['name']: cookie['value'] for cookie in cookies}
        
        # Close browser
        await browser.close()
        
        return {
            "success": True,
            "cookies": cookie_dict,
            "expires_at": (datetime.now() + timedelta(hours=24)).isoformat()
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "woolworths-api"})


@app.route('/api/search', methods=['POST'])
def search_products():
    """Search for products on Woolworths"""
    data = request.json or {}
    search_term = data.get('searchTerm') or data.get('search_term')
    page_size = data.get('pageSize', 20)
    
    if not search_term:
        return jsonify({"error": "searchTerm is required"}), 400
    
    try:
        # Call Woolworths API with proper headers
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(
            f"{WOOLWORTHS_API_BASE}/Search/products",
            params={
                "searchTerm": search_term,
                "pageSize": page_size
            },
            headers=headers,
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Extract and format products
            products = []
            for item in data.get('Products', [])[:page_size]:
                products.append({
                    'stockcode': item.get('Stockcode', ''),
                    'name': item.get('Name', ''),
                    'brand': item.get('Brand', ''),
                    'price': item.get('Price', 0),
                    'size': item.get('PackageSize', ''),
                    'image': item.get('MediumImageFile', ''),
                    'description': item.get('Description', ''),
                    'unit': item.get('Unit', ''),
                    'cupPrice': item.get('CupPrice', 0),
                    'cupMeasure': item.get('CupMeasure', ''),
                    'isAvailable': item.get('IsAvailable', True)
                })
            
            return jsonify({
                "success": True,
                "products": products,
                "count": len(products),
                "totalFound": data.get('TotalRecordCount', len(products))
            })
        else:
            return jsonify({
                "success": False,
                "error": f"API returned status {response.status_code}",
                "products": []
            }), response.status_code
            
    except requests.Timeout:
        return jsonify({
            "success": False,
            "error": "Request timed out",
            "products": []
        }), 504
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "products": []
        }), 500


@app.route('/api/product/<stockcode>', methods=['GET'])
def get_product_details(stockcode):
    """Get detailed product information"""
    try:
        response = requests.get(
            f"{WOOLWORTHS_API_BASE}/products/{stockcode}",
            timeout=10
        )
        
        if response.status_code == 200:
            return jsonify({
                "success": True,
                "product": response.json()
            })
        else:
            return jsonify({
                "success": False,
                "error": f"Product not found"
            }), 404
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/product-details', methods=['POST'])
def get_product_by_stockcode():
    """Get detailed product information via POST (accepts JSON)"""
    data = request.json or {}
    stockcode = data.get('stockcode')
    
    if not stockcode:
        return jsonify({"error": "stockcode is required"}), 400
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'application/json'
        }
        
        response = requests.get(
            f"{WOOLWORTHS_API_BASE}/products/{stockcode}",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            return jsonify({
                "success": True,
                "product": response.json()
            })
        else:
            return jsonify({
                "success": False,
                "error": f"Product not found for stockcode {stockcode}"
            }), 404
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/specials', methods=['GET'])
def get_specials():
    """Get current specials"""
    try:
        category = request.args.get('category', '')
        page_size = int(request.args.get('pageSize', 20))
        
        response = requests.get(
            f"{WOOLWORTHS_API_BASE}/specials",
            params={
                "category": category,
                "pageSize": page_size
            },
            timeout=10
        )
        
        if response.status_code == 200:
            return jsonify({
                "success": True,
                "specials": response.json()
            })
        else:
            return jsonify({
                "success": False,
                "error": "Could not fetch specials"
            }), response.status_code
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/auth/login', methods=['POST'])
def login():
    """Login to Woolworths and capture session cookies"""
    if not PLAYWRIGHT_AVAILABLE:
        return jsonify({
            "success": False,
            "error": "Playwright not available - authentication disabled"
        }), 503
    
    data = request.json or {}
    email = data.get('email')
    password = data.get('password')
    session_id = data.get('session_id', 'default')
    
    if not email or not password:
        return jsonify({
            "success": False,
            "error": "Email and password are required"
        }), 400
    
    # Run async login in event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(playwright_login(email, password))
    loop.close()
    
    if result.get('success'):
        # Store cookies for this session
        user_sessions[session_id] = {
            'cookies': result['cookies'],
            'expires_at': result['expires_at'],
            'email': email
        }
        
        return jsonify({
            "success": True,
            "session_id": session_id,
            "message": "Logged in successfully",
            "expires_at": result['expires_at']
        })
    else:
        return jsonify(result), 401


@app.route('/api/auth/status', methods=['GET'])
def auth_status():
    """Check if session is authenticated"""
    session_id = request.args.get('session_id', 'default')
    
    session = user_sessions.get(session_id)
    
    if not session:
        return jsonify({
            "authenticated": False,
            "message": "No session found"
        })
    
    # Check if session expired
    expires_at = datetime.fromisoformat(session['expires_at'])
    if datetime.now() > expires_at:
        # Remove expired session
        del user_sessions[session_id]
        return jsonify({
            "authenticated": False,
            "message": "Session expired"
        })
    
    return jsonify({
        "authenticated": True,
        "email": session['email'],
        "expires_at": session['expires_at']
    })


@app.route('/api/cart', methods=['GET'])
def get_cart():
    """Get cart contents (requires authentication)"""
    session_id = request.args.get('session_id', 'default')
    
    session = user_sessions.get(session_id)
    
    if not session:
        return jsonify({
            "success": False,
            "error": "Not authenticated. Please login first."
        }), 401
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'application/json'
        }
        
        response = requests.get(
            f"{WOOLWORTHS_API_BASE}/cart",
            cookies=session['cookies'],
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            return jsonify({
                "success": True,
                "cart": response.json()
            })
        elif response.status_code == 401:
            return jsonify({
                "success": False,
                "error": "Session expired. Please login again."
            }), 401
        else:
            return jsonify({
                "success": False,
                "error": f"Could not fetch cart (status {response.status_code})"
            }), response.status_code
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/cart/add', methods=['POST'])
def add_to_cart():
    """Add item to cart (requires authentication)"""
    data = request.json or {}
    session_id = data.get('session_id', 'default')
    stockcode = data.get('stockcode')
    quantity = data.get('quantity', 1)
    
    if not stockcode:
        return jsonify({
            "success": False,
            "error": "Stockcode is required"
        }), 400
    
    session = user_sessions.get(session_id)
    
    if not session:
        return jsonify({
            "success": False,
            "error": "Not authenticated. Please login first."
        }), 401
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        response = requests.post(
            f"{WOOLWORTHS_API_BASE}/cart/add",
            json={
                'stockcode': stockcode,
                'quantity': quantity
            },
            cookies=session['cookies'],
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            return jsonify({
                "success": True,
                "message": "Item added to cart",
                "stockcode": stockcode,
                "quantity": quantity
            })
        elif response.status_code == 401:
            return jsonify({
                "success": False,
                "error": "Session expired. Please login again."
            }), 401
        else:
            return jsonify({
                "success": False,
                "error": f"Could not add to cart (status {response.status_code})"
            }), response.status_code
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/cart/update', methods=['POST'])
def update_cart():
    """Update cart item quantity (requires authentication)"""
    data = request.json or {}
    session_id = data.get('session_id', 'default')
    stockcode = data.get('stockcode')
    quantity = data.get('quantity')
    
    if not stockcode or quantity is None:
        return jsonify({
            "success": False,
            "error": "Stockcode and quantity are required"
        }), 400
    
    session = user_sessions.get(session_id)
    
    if not session:
        return jsonify({
            "success": False,
            "error": "Not authenticated"
        }), 401
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        response = requests.put(
            f"{WOOLWORTHS_API_BASE}/cart/update",
            json={
                'stockcode': stockcode,
                'quantity': quantity
            },
            cookies=session['cookies'],
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            return jsonify({
                "success": True,
                "message": "Cart updated"
            })
        elif response.status_code == 401:
            return jsonify({
                "success": False,
                "error": "Session expired"
            }), 401
        else:
            return jsonify({
                "success": False,
                "error": f"Could not update cart (status {response.status_code})"
            }), response.status_code
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
