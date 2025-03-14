import requests
import time
import os
import logging
import signal
import sys
from datetime import datetime

# Configuration
BINANCE_API_URL = "https://api.binance.com/api/v3/ticker/price"
ALERT_THRESHOLD = float(os.getenv('ALERT_THRESHOLD', '3.0'))  # Percentage
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', '300'))  # 5 minutes in seconds
QUOTE_CURRENCY = os.getenv('QUOTE_CURRENCY', 'USDT')  # Default to USDT
ALERT_LOG_FILE = "price_alerts.txt"  # File to store price alerts

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# In-memory price history
PRICE_HISTORY = {}

def get_all_prices():
    """Fetch all Binance coin prices."""
    try:
        response = requests.get(BINANCE_API_URL)
        response.raise_for_status()
        return {item["symbol"]: float(item["price"]) for item in response.json()}
    except requests.RequestException as e:
        logger.error(f"Failed to fetch prices: {e}")
        return None

def signal_handler(signum, frame):
    """Handle graceful shutdown."""
    logger.info("Shutting down...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

while True:
    current_prices = get_all_prices()
    if current_prices is None:
        logger.warning("Waiting before retry...")
        time.sleep(60)
        continue

    timestamp = time.time()
    alert_played = False  # Flag to track if alert was played in this interval

    for coin, current_price in current_prices.items():
        if coin.endswith(QUOTE_CURRENCY):
            if coin in PRICE_HISTORY:
                old_price = PRICE_HISTORY[coin]
                if old_price > 0 and current_price > 0:  # Skip if prices are zero
                    change = ((current_price - old_price) / old_price) * 100
                    
                    if change > ALERT_THRESHOLD:
                        logger.warning(f"🚀 ALERT: {coin} increased by {change:.2f}% in {CHECK_INTERVAL/60} minutes!")
                        if not alert_played:
                            print('\a', end='', flush=True)  # Terminal bell
                            alert_played = True
                        try:
                            # Store alert in file
                            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            with open(ALERT_LOG_FILE, 'a') as f:
                                f.write(f"\n=== {current_time} ===\n")
                                f.write(f"{coin}: {change:.2f}% (Price: {current_price:.8f} {QUOTE_CURRENCY})\n")
                        except Exception as e:
                            logger.error(f"Failed to write to log: {e}")

            PRICE_HISTORY[coin] = current_price

    logger.info(f"Checked prices, waiting {CHECK_INTERVAL/60} minutes...")
    time.sleep(CHECK_INTERVAL)
