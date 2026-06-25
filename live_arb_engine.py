from flask import Flask, jsonify
import threading
import time
from playwright.sync_api import sync_playwright

app = Flask(__name__)

GLOBAL_ARB_DATA = []
RAW_PAYLOADS = {"Napoleon": [], "Bingoal": []}

def extract_last_name(full_name):
    """Finds the most distinctive part of the name (longest word) to match across bookmakers."""
    if not full_name or full_name == "Unknown": return "Unknown"
    # Remove punctuation
    clean_name = full_name.replace(',', ' ').replace('/', ' ').replace('.', ' ')
    words = clean_name.split()
    
    # Filter out 1-letter initials (like 'J' or 'M')
    valid_words = [w.lower() for w in words if len(w) > 1]
    
    if valid_words:
        # Assume the longest word is the last name or most distinct identifier
        return sorted(valid_words, key=len)[-1]
    
    return words[-1].lower() if words else "unknown"

def process_raw_data():
    """Parses the intercepted JSON payloads and calculates arbitrage."""
    global GLOBAL_ARB_DATA
    extracted = []
    
    nap_count = 0
    bin_count = 0

    print(f"\n[SYSTEM] Processing {len(RAW_PAYLOADS['Napoleon'])} Napoleon and {len(RAW_PAYLOADS['Bingoal'])} Bingoal payloads...")

    # 1. Parse Napoleon (from dynamic memory)
    for data in RAW_PAYLOADS["Napoleon"]:
        try:
            if not isinstance(data, dict): continue
            matches = data.get("data", {}).get("data", []) if isinstance(data.get("data"), dict) else data.get("data", [])
            if not isinstance(matches, list): continue
            
            for match in matches:
                try:
                    full_name = match.get("matchName", "Unknown·Unknown")
                    names = full_name.split("·")
                    home = names[0].strip() if len(names) > 0 else "Unknown"
                    away = names[1].strip() if len(names) > 1 else "Unknown"
                    
                    o1, o2 = None, None
                    odds_list = match.get("odds") or []
                    for odd in odds_list:
                        market = str(odd.get("marketName", "")).lower()
                        if "match winner" in market or "winner" in market:
                            code = str(odd.get("code", ""))
                            if code == "1": o1 = odd.get("price")
                            if code == "2": o2 = odd.get("price")
                            
                    if o1 and o2:
                        extracted.append({"src": "Napoleon", "home": home, "away": away, "o1": o1, "o2": o2})
                    nap_count += 1
                except Exception:
                    pass
        except Exception as e:
            print(f"[ERROR] Napoleon Parser Issue: {e}")

    # 2. Parse Bingoal (from dynamic memory)
    for data in RAW_PAYLOADS["Bingoal"]:
        try:
            bingoal_events = []
            def find_events(d):
                if isinstance(d, dict):
                    if "events" in d and isinstance(d["events"], list):
                        bingoal_events.extend(d["events"])
                    for k, v in d.items():
                        find_events(v)
                elif isinstance(d, list):
                    for item in d:
                        find_events(item)
            
            find_events(data)

            for entry in bingoal_events:
                try:
                    if not isinstance(entry, dict): continue
                    event = entry.get("event", {})
                    if not event: continue
                    
                    home_name = event.get("homeName")
                    away_name = event.get("awayName")
                    if not home_name or not away_name: continue
                    
                    o1, o2 = None, None
                    offers_list = []
                    if "mainBetOffer" in entry and isinstance(entry["mainBetOffer"], dict):
                        offers_list.append(entry["mainBetOffer"])
                    offers_list.extend(entry.get("betOffers", []))
                        
                    for offer in offers_list:
                        if not isinstance(offer, dict): continue
                        outcomes = offer.get("outcomes", [])
                        
                        temp_o1, temp_o2 = None, None
                        for outcome in outcomes:
                            out_label = outcome.get("label", "")
                            price = outcome.get("odds", 0) / 1000
                            if out_label == home_name and price > 0: temp_o1 = price
                            elif out_label == away_name and price > 0: temp_o2 = price
                        
                        if temp_o1 and temp_o2:
                            o1 = temp_o1
                            o2 = temp_o2
                            break
                    
                    if o1 and o2:
                        extracted.append({"src": "Bingoal", "home": home_name, "away": away_name, "o1": o1, "o2": o2})
                        bin_count += 1
                except Exception:
                    pass
        except Exception as e:
            print(f"[ERROR] Bingoal Parser Issue: {e}")

    print(f"[SYSTEM] Extracted {nap_count} Napoleon matches and {bin_count} Bingoal matches.")

    grouped = {}
    for m in extracted:
        h_name = extract_last_name(m['home'])
        a_name = extract_last_name(m['away'])
        key = f"{h_name} vs {a_name}"
        
        if key not in grouped:
            grouped[key] = {"display_name": f"{m['home']} vs {m['away']}", "Napoleon": {}, "Bingoal": {}}
        grouped[key][m['src']] = m

    temp_arb_list = []
    for key, data in grouped.items():
        n = data.get("Napoleon", {})
        b = data.get("Bingoal", {})
        
        if n and b:
            try:
                o1n, o2n = float(n['o1']), float(n['o2'])
                o1b, o2b = float(b['o1']), float(b['o2'])
                
                if o1n > 0 and o2b > 0 and o1b > 0 and o2n > 0:
                    arb1 = (1/o1n + 1/o2b) * 100
                    arb2 = (1/o1b + 1/o2n) * 100
                    best_arb = min(arb1, arb2)
                    
                    temp_arb_list.append({
                        "match": data["display_name"],
                        "nap_o1": o1n, "nap_o2": o2n,
                        "bin_o1": o1b, "bin_o2": o2b,
                        "arb": best_arb
                    })
            except Exception:
                pass

    GLOBAL_ARB_DATA = sorted(temp_arb_list, key=lambda x: x['arb'])
    print(f"[SYSTEM] Successfully paired {len(GLOBAL_ARB_DATA)} overlapping matches!\n")

def run_playwright_scraper():
    """Background thread that navigates, clicks, and intercepts traffic."""
    print("[SYSTEM] Starting Interactive Scraper...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        
        def handle_response(response):
            if response.request.resource_type in ["fetch", "xhr"]:
                url = response.url.lower()
                # Debug logging to show we are looking for the 'listView'
                if "kambi" in url and "listview" in url:
                    print(f"[NETWORK] 🏆 FOUND MATCH API: {url}")
                    try:
                        data = response.json()
                        RAW_PAYLOADS["Bingoal"].append(data)
                    except: pass
                elif "superbet" in url or "napoleon" in url:
                    try:
                        data = response.json()
                        RAW_PAYLOADS["Napoleon"].append(data)
                    except: pass

        page_nap = context.new_page()
        page_nap.on("response", handle_response)
        
        page_bin = context.new_page()
        page_bin.on("response", handle_response)

        print("[SYSTEM] Navigating...")
        page_nap.goto("https://napoleonsports.be/fr-be/sport-bets/tennis", wait_until="domcontentloaded")
        page_bin.goto("https://www.bingoalsport.be/fr/Sports/sports-hub/tennis", wait_until="domcontentloaded")
        
        # INTERACTIVE STEP: Click a tournament link to trigger the listView API
        # We look for links containing 'tennis'
        try:
            print("[SYSTEM] Attempting to click Tennis tournament...")
            page_bin.wait_for_selector("a[href*='/tennis']", timeout=10000)
            page_bin.click("a[href*='/tennis']", timeout=5000)
        except:
            print("[SYSTEM] Could not auto-click tournament link. Please click a tournament in the Bingoal browser window manually.")

        # Continuous Refresh Loop
        while True:
            page_bin.wait_for_timeout(20000) # Wait 20 seconds for API data
            print("\n[SYSTEM] Processing captured network traffic...")
            process_raw_data()
            RAW_PAYLOADS["Napoleon"] = [] 
            RAW_PAYLOADS["Bingoal"] = []
            
            # Reload to restart the capture cycle
            page_nap.reload()
            page_bin.reload()
            # Wait for data again
            page_bin.wait_for_selector("a[href*='/tennis']", timeout=10000)
            page_bin.click("a[href*='/tennis']", timeout=5000)

@app.route('/')
def index():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Live Tennis Arbitrage</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gray-900 text-white min-h-screen p-8">
        <div class="max-w-6xl mx-auto">
            <h1 class="text-3xl font-bold text-blue-400 mb-6">🟢 Live Tennis Arbitrage Dashboard</h1>
            <div class="bg-gray-800 rounded-lg shadow-xl overflow-hidden">
                <table class="w-full text-left">
                    <thead class="bg-gray-700 text-gray-300">
                        <tr><th class="p-4">Match</th><th class="p-4">Napoleon</th><th class="p-4">Bingoal</th><th class="p-4">Arb %</th></tr>
                    </thead>
                    <tbody id="table-body" class="divide-y divide-gray-700">
                        <tr><td colspan="4" class="p-4 text-center text-gray-400">Initializing...</td></tr>
                    </tbody>
                </table>
            </div>
        </div>
        <script>
            async function updateTable() {
                try {
                    const res = await fetch('/data');
                    const data = await res.json();
                    const body = document.getElementById('table-body');
                    if (data.length === 0) return;
                    body.innerHTML = data.map(m => `
                        <tr class="${m.arb < 100 ? 'bg-green-900/40 border-l-4 border-green-500' : ''}">
                            <td class="p-4">${m.match}</td>
                            <td class="p-4">${m.nap_o1}/${m.nap_o2}</td>
                            <td class="p-4">${m.bin_o1}/${m.bin_o2}</td>
                            <td class="p-4 font-bold ${m.arb < 100 ? 'text-green-400' : 'text-gray-300'}">${m.arb.toFixed(2)}%</td>
                        </tr>
                    `).join('');
                } catch(e) {}
            }
            setInterval(updateTable, 3000);
        </script>
    </body>
    </html>
    """

@app.route('/data')
def get_data():
    return jsonify(GLOBAL_ARB_DATA)

if __name__ == "__main__":
    scraper_thread = threading.Thread(target=run_playwright_scraper, daemon=True)
    scraper_thread.start()
    app.run(port=5000, debug=False, use_reloader=False)