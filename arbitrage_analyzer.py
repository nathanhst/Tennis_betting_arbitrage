import json
import os
from datetime import datetime, timezone

# Path to the data
RAW_FILE = r"D:\Quant\Python\sports_data\intercepted_raw_api.json"

def get_parsed_data():
    if not os.path.exists(RAW_FILE):
        print(f"Error: {RAW_FILE} not found.")
        return []

    with open(RAW_FILE, 'r', encoding='utf-8') as f:
        try:
            intercepts = json.load(f)
        except json.JSONDecodeError:
            print("Error: Could not decode JSON.")
            return []

    extracted_matches = []
    now = datetime.now()

    # 1. Parse Napoleon (Superbet) - Index 9
    if len(intercepts) > 9:
        superbet_data = intercepts[9].get("data", {}).get("data", [])
        for match in superbet_data:
            # Parse Date: '2026-06-24 13:30:00'
            try:
                match_dt = datetime.strptime(match.get('matchDate', ''), '%Y-%m-%d %H:%M:%S')
                if match_dt < now: continue
            except: continue # Skip if date is missing/invalid

            odds_list = match.get("odds") or []
            odds = {"1": None, "2": None}
            for odd in odds_list:
                if odd.get("marketName") == "Match Winner":
                    odds[odd.get("code")] = odd.get("price")

            # Split names: "Player1·Player2"
            full_name = match.get("matchName", "Unknown·Unknown")
            names = full_name.split("·")
            home = names[0].strip() if len(names) > 0 else "Unknown"
            away = names[1].strip() if len(names) > 1 else "Unknown"

            extracted_matches.append({
                "source": "Napoleon",
                "home": home,
                "away": away,
                "odds1": odds.get("1"),
                "odds2": odds.get("2")
            })

    # 2. Parse Bingoal (Kambi) - Index 22/25
    for idx in [22, 25]:
        if len(intercepts) > idx:
            kambi_data = intercepts[idx].get("data", {}).get("events", [])
            for entry in kambi_data:
                event = entry.get("event", {})
                # Parse Date: '2026-07-12T08:00:00Z'
                start_str = event.get('start', '').replace('Z', '')
                try:
                    match_dt = datetime.fromisoformat(start_str)
                    if match_dt.replace(tzinfo=None) < now: continue
                except: continue

                bet_offers = entry.get("betOffers", [])
                odds = {"1": None, "2": None}
                for offer in bet_offers:
                    if "Wedstrijdnotering" in offer.get("criterion", {}).get("label", ""):
                        for outcome in offer.get("outcomes", []):
                            price = outcome.get("odds", 0) / 1000
                            if outcome.get("label") == event.get("homeName"): odds["1"] = price
                            elif outcome.get("label") == event.get("awayName"): odds["2"] = price
                
                if event.get("homeName"):
                    extracted_matches.append({
                        "source": "Bingoal",
                        "home": event.get("homeName"),
                        "away": event.get("awayName"),
                        "odds1": odds["1"],
                        "odds2": odds["2"]
                    })

    return extracted_matches

def run_dashboard():
    matches = get_parsed_data()
    # Logic to compare matches and find Arb
    print(f"{'MATCH':<40} | {'NAPOLEON':<12} | {'BINGOAL':<12} | {'ARB %'}")
    print("-" * 80)
    
    # Simple grouping by match name
    grouped = {}
    for m in matches:
        key = f"{m['home']} vs {m['away']}"
        if key not in grouped: grouped[key] = {"Napoleon": {}, "Bingoal": {}}
        grouped[key][m['source']] = m

    for key, data in grouped.items():
        n = data.get("Napoleon", {})
        b = data.get("Bingoal", {})
        o1n, o2n = n.get("odds1"), n.get("odds2")
        o1b, o2b = b.get("odds1"), b.get("odds2")
        
        if o1n and o2b:
            arb = (1/float(o1n) + 1/float(o2b)) * 100
            print(f"{key[:38]:<40} | {str(o1n):<5}/{str(o2n):<5} | {str(o1b):<5}/{str(o2b):<5} | {arb:.2f}%")

if __name__ == "__main__":
    run_dashboard()