"""
Woolworths MCP Client
Connects to the remote MCP service for product search and cart management
"""

import requests
import os
from typing import List, Dict, Optional
from functools import lru_cache

class WoolworthsClient:
    """Client for interacting with Woolworths MCP service"""
    
    def __init__(self, service_url: str = None):
        """Initialize client with MCP service URL"""
        self.service_url = service_url or os.environ.get('MCP_SERVICE_URL', 'http://localhost:8080')
        self.timeout = 30
        
    def _request(self, endpoint: str, method: str = 'GET', data: dict = None) -> dict:
        """Make HTTP request to MCP service"""
        url = f"{self.service_url}{endpoint}"
        
        try:
            if method == 'GET':
                response = requests.get(url, params=data, timeout=self.timeout)
            else:
                response = requests.post(url, json=data, timeout=self.timeout)
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e), "success": False}
    
    def health_check(self) -> bool:
        """Check if MCP service is healthy"""
        try:
            result = self._request('/health', 'GET')
            return result.get('status') == 'healthy'
        except:
            return False
    
    def search_products(self, search_term: str, page_size: int = 20) -> dict:
        """
        Search for products
        
        Args:
            search_term: Product search query
            page_size: Number of results to return
            
        Returns:
            dict with products array and metadata
        """
        return self._request('/api/search', 'POST', {
            'searchTerm': search_term,
            'pageSize': page_size
        })
    
    def get_product_details(self, stockcode: str) -> dict:
        """
        Get detailed product information
        
        Args:
            stockcode: Product stockcode/ID
            
        Returns:
            dict with product details
        """
        return self._request(f'/api/product/{stockcode}', 'GET')
    
    def get_categories(self) -> dict:
        """Get all product categories"""
        return self._request('/api/categories', 'GET')
    
    def get_specials(self, category: str = None, page_size: int = 20) -> dict:
        """
        Get current specials
        
        Args:
            category: Optional category filter
            page_size: Number of results
            
        Returns:
            dict with specials array
        """
        params = {'pageSize': page_size}
        if category:
            params['category'] = category
        
        return self._request('/api/specials', 'GET', params)
    
    def open_browser(self, headless: bool = True) -> dict:
        """Open browser session"""
        return self._request('/api/browser/open', 'POST', {'headless': headless})
    
    def close_browser(self) -> dict:
        """Close browser session"""
        return self._request('/api/browser/close', 'POST')
    
    def get_cart(self) -> dict:
        """Get current cart contents"""
        return self._request('/api/cart', 'GET')
    
    def add_to_cart(self, stockcode: int, quantity: int = 1) -> dict:
        """
        Add item to cart
        
        Args:
            stockcode: Product stockcode
            quantity: Quantity to add
            
        Returns:
            dict with success status
        """
        return self._request('/api/cart/add', 'POST', {
            'stockcode': stockcode,
            'quantity': quantity
        })
    
    def remove_from_cart(self, stockcode: int) -> dict:
        """
        Remove item from cart
        
        Args:
            stockcode: Product stockcode
            
        Returns:
            dict with success status
        """
        return self._request('/api/cart/remove', 'POST', {
            'stockcode': stockcode
        })
    
    def update_cart_quantity(self, stockcode: int, quantity: int) -> dict:
        """
        Update cart item quantity
        
        Args:
            stockcode: Product stockcode
            quantity: New quantity
            
        Returns:
            dict with success status
        """
        return self._request('/api/cart/update', 'POST', {
            'stockcode': stockcode,
            'quantity': quantity
        })
    
    def get_cookies(self) -> dict:
        """Get session cookies"""
        return self._request('/api/cookies/get', 'POST')


# Singleton instance
_woolworths_client = None

def get_woolworths_client() -> WoolworthsClient:
    """Get or create Woolworths client singleton"""
    global _woolworths_client
    if _woolworths_client is None:
        _woolworths_client = WoolworthsClient()
    return _woolworths_client
