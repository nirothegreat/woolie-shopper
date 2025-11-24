# Woolworths MCP Server

A Model Context Protocol (MCP) server for interacting with Woolworths Australia's online shopping platform. This server provides tools for browsing products, searching items, viewing specials, managing shopping cart, and more.

## Features

- **Browser Automation**: Uses Puppeteer to open a browser, navigate to Woolworths, and capture session cookies
- **Session Management**: Maintains session cookies for authenticated API requests
- **Product Search**: Search for products across the Woolworths catalog with filtering and sorting
- **Product Details**: Get detailed information about specific products
- **Specials & Deals**: Browse current specials and promotional offers
- **Category Browsing**: Explore product categories
- **Shopping Cart**: Add items to cart, view cart contents, update quantities, and remove items

## Installation

1. Install dependencies:

```bash
npm install
```

2. Build the TypeScript code:

```bash
npm run build
```

## Usage

### Running the Server

The MCP server runs on stdio and is designed to be used with MCP-compatible clients (like Claude Desktop, Cline, or other AI assistants).

```bash
npm start
```

### Configuration for Windsurf

In Windsurf, go to **Settings** → **MCP Servers** and add the Woolworths MCP server, or create a configuration file in the project root.

Alternatively, add this to Windsurf's MCP configuration:

```json
{
  "mcpServers": {
    "woolworths": {
      "command": "node",
      "args": ["/Users/niro/woolies-shopper/dist/index.js"]
    }
  }
}
```

### Configuration for Claude Desktop

Add this to your Claude Desktop configuration file:

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "woolworths": {
      "command": "node",
      "args": ["/Users/niro/woolies-shopper/dist/index.js"]
    }
  }
}
```

Make sure to update the path to match your installation directory.

## Available Tools

### 1. woolworths_open_browser

Opens a browser and navigates to the Woolworths website. This is typically the first step to establish a session.

**Parameters:**
- `headless` (boolean, optional): Whether to run in headless mode (default: false)

**Example:**
```json
{ "headless": false }
```

### 2. woolworths_navigate

Navigate to a specific URL on the Woolworths website.

**Parameters:**
- `url` (string, required): The URL to navigate to

### 3. woolworths_get_cookies

Retrieves and stores session cookies from the current browser session. Run this after logging in or when you have an active session.

**Parameters:** None

### 4. woolworths_close_browser

Closes the browser instance while preserving the captured session cookies.

**Parameters:** None

### 5. woolworths_search_products

Search for products on Woolworths.

**Parameters:**
- `searchTerm` (string, required): The product search term
- `pageSize` (number, optional): Number of results to return (default: 20)

**Example:**
```json
{ "searchTerm": "milk", "pageSize": 20 }
```

### 6. woolworths_get_product_details

Get detailed information about a specific product by its stockcode.

**Parameters:**
- `stockcode` (string, required): The product stockcode/ID

### 7. woolworths_get_specials

Get current specials and deals from Woolworths.

**Parameters:**
- `category` (string, optional): Category filter (e.g., 'fruit-veg', 'meat-seafood')
- `pageSize` (number, optional): Number of results to return (default: 20)

### 8. woolworths_get_categories

Get the list of available product categories.

**Parameters:** None

### 9. woolworths_add_to_cart

Add a product to the shopping cart/trolley.

**Parameters:**
- `stockcode` (number, required): The product stockcode/ID
- `quantity` (number, optional): Quantity to add (default: 1)

**Example:**
```json
{ "stockcode": 123456, "quantity": 2 }
```

### 10. woolworths_get_cart

Get the current contents of the shopping cart/trolley.

**Parameters:** None

### 11. woolworths_remove_from_cart

Remove a product from the shopping cart/trolley.

**Parameters:**
- `stockcode` (number, required): The product stockcode/ID to remove

### 12. woolworths_update_cart_quantity

Update the quantity of a product in the shopping cart/trolley.

**Parameters:**
- `stockcode` (number, required): The product stockcode/ID
- `quantity` (number, required): New quantity

## Typical Workflow

1. **Open Browser**: Call `woolworths_open_browser` to launch a browser instance
2. **Login** (if needed): The browser window allows you to manually log in to your Woolworths account
3. **Capture Cookies**: Call `woolworths_get_cookies` to capture your session
4. **Close Browser**: Call `woolworths_close_browser` (cookies are preserved)
5. **Use API Tools**: Now you can use all the other tools (search, cart operations, etc.) with the authenticated session

## Example Usage Scenario

```
User: "Find milk products on Woolworths"
Assistant: 
1. Opens browser (woolworths_open_browser)
2. Waits for user to login if needed
3. Captures cookies (woolworths_get_cookies)
4. Closes browser (woolworths_close_browser)
5. Searches for milk (woolworths_search_products)
6. Shows results to user

User: "Add the first one to my cart"
Assistant:
1. Gets product details (woolworths_get_product_details)
2. Adds to cart (woolworths_add_to_cart)
3. Confirms addition
```

## Technical Details

### Browser Automation

The server uses Puppeteer to:
- Launch a Chromium browser instance
- Navigate to Woolworths website
- Capture cookies from the browser session
- Maintain user agent and browser fingerprint

### API Integration

Once cookies are captured, the server makes authenticated requests to Woolworths' internal APIs:
- Search API: `/apis/ui/Search/products` (POST)
- Product Detail API: `/apis/ui/product/detail/{stockcode}`
- Browse/Category API: `/apis/ui/browse/category`
- Categories API: `/apis/ui/PiesCategoriesWithSpecials`
- Shopping Cart API: `/apis/ui/Trolley/*` (AddItem, RemoveItem, UpdateItem, Get)

### Session Management

Session cookies are stored in memory for the duration of the server process. If the server restarts, you'll need to recapture cookies by opening the browser again.

## Development

### Watch Mode

For development with auto-recompilation:

```bash
npm run dev
```

### Building

```bash
npm run build
```

## Requirements

- Node.js 18 or higher
- npm or yarn
- Internet connection
- Chromium (downloaded automatically by Puppeteer)

## Notes

- The server maintains cookies in memory only - they are lost when the server restarts
- You may need to log in through the browser window for full functionality
- API endpoints may change as Woolworths updates their platform
- Respect Woolworths' terms of service when using this tool

## Troubleshooting

### Browser won't open
- Make sure Puppeteer is properly installed: `npm install puppeteer`
- Try running with `headless: false` to see what's happening

### API requests fail
- Ensure you've captured cookies after visiting the Woolworths site
- You may need to log in to your Woolworths account
- Cookies may have expired - try reopening browser and recapturing

### Connection issues
- Check your internet connection
- Woolworths' website or APIs may be temporarily unavailable
- Your IP may be rate-limited if making too many requests

## License

MIT

## Disclaimer

This tool is for educational and personal use only. It is not officially affiliated with or endorsed by Woolworths. Please use responsibly and in accordance with Woolworths' terms of service.
