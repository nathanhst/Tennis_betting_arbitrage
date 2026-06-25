# Tennis betting arbitrage

This project is a real-time arbitrage detection system for tennis, designed to identify price discrepancies between major bookmakers, specifically Bingoal and Napoleon Sports. By leveraging Playwright to intercept live network payloads and a Flask-based backend, the tool continuously monitors, parses, and compares odds to calculate the arbitrage percentage in real-time. The system provides an intuitive, color-coded web dashboard that instantly highlights profitable opportunities, simplifying the data extraction process into a fully automated pipeline for quantitative sports trading.

- live_arb_engine.py: The core application engine. It runs the dual-browser Playwright scraper in parallel, hosts the Flask web dashboard, and coordinates the real-time processing of incoming odds data.
- arbitrage_analyzer.py: A specialized utility module used for parsing raw API payloads, filtering matches, and performing the mathematical calculations to identify profitable arbitrage opportunities.
- local_bookies_scraper.py: Your initial diagnostic tool designed to sniff network traffic and verify API connectivity, serving as a baseline for testing and debugging new bookmaker integrations.
