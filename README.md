# Tennis betting arbitrage

This project is a real-time arbitrage detection system for tennis, designed to identify price discrepancies between major bookmakers, specifically Bingoal and Napoleon Sports. By leveraging Playwright to intercept live network payloads and a Flask-based backend, the tool continuously monitors, parses, and compares odds to calculate the arbitrage percentage in real-time. The system provides an intuitive, color-coded web dashboard that instantly highlights profitable opportunities, simplifying the data extraction process into a fully automated pipeline for quantitative sports trading.

Engine for live matches:
- live_arb_engine.py:  Runs parallel scrapers specifically to pull live in-play odds. It hosts the Flask web dashboard and coordinates the low-latency processing required for active tennis matches.

Engine for future matches
- arbitrage_analyzer.py: The logic module for pre-match events. It handles deep-dive parsing of raw API payloads, performs historical filtering, and runs the complex math required to find arbitrage opportunities before the match even begins.
- local_bookies_scraper.py: Pulls the upcoming tennis schedule and current odds data directly from the bookmaker sites, feeding the raw match info into the future engine.
