from playwright.sync_api import sync_playwright
import json
import os

SAVE_DIR = r"D:\Quant\Python\sports_data"
RAW_FILE = os.path.join(SAVE_DIR, "intercepted_raw_api.json")

def handle_response(response):
    # Only capture XHR/Fetch responses
    if response.request.resource_type == "fetch" or response.request.resource_type == "xhr":
        url = response.url
        # Look for any JSON response that might contain match data
        if "events" in url or "matches" in url or "offer" in url:
            try:
                data = response.json()
                print(f"[WIRETAP] 🎯 CAPTURED DATA: {url}")
                
                # Save to list
                existing = []
                if os.path.exists(RAW_FILE):
                    try:
                        with open(RAW_FILE, 'r', encoding='utf-8') as f:
                            existing = json.load(f)
                    except: pass
                
                existing.append({"url": url, "data": data})
                with open(RAW_FILE, 'w', encoding='utf-8') as f:
                    json.dump(existing, f, indent=4)
            except:
                pass

def main():
    if not os.path.exists(SAVE_DIR): os.makedirs(SAVE_DIR)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.on("response", handle_response)
        
        # Napoleon
        print("\n[Napoleon] Navigating...")
        page.goto("https://napoleonsports.be/fr-be/sport-bets/tennis", wait_until="domcontentloaded")
        page.wait_for_timeout(15000) # Give extra time for dynamic loading
        
        # Bingoal
        print("\n[Bingoal] Navigating...")
        page.goto("https://www.bingoal.nl/nl/Sport/sports-hub/tennis", wait_until="domcontentloaded")
        page.wait_for_timeout(15000)
        
        browser.close()

if __name__ == "__main__":
    main()