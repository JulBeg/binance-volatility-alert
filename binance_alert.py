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
TIME_DIFFERENCE = int(os.getenv('TIME_DIFFERENCE', '300'))  # Rolling window in seconds (5 minutes)
REFRESH_INTERVAL = int(os.getenv('REFRESH_INTERVAL', '60'))  # Price refresh interval in seconds (1 minute)
QUOTE_CURRENCY = os.getenv('QUOTE_CURRENCY', 'USDT')  # Default to USDT
ALERT_LOG_FILE = "price_alerts.txt"  # File to store price alerts
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'

# Setup logging
logging.basicConfig(
    level=logging.INFO if DEBUG else logging.WARNING,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# In-memory price history with timestamps
PRICE_HISTORY = {}  # {coin: [(price, timestamp), ...]}

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

def send_telegram_alert(message):
    """Send alert to Telegram."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram credentials not configured")
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, data=data)
        response.raise_for_status()
    except Exception as e:
        logger.error(f"Failed to send Telegram alert: {e}")

# Send startup configuration
startup_message = f"🚀 Binance Alert Bot Started\nRefresh Interval: {REFRESH_INTERVAL}s\nTime Window: {TIME_DIFFERENCE}s\nAlert Threshold: {ALERT_THRESHOLD}%"
logger.info(startup_message)
send_telegram_alert(startup_message)

while True:
    current_prices = get_all_prices()
    if current_prices is None:
        logger.warning("Waiting before retry...")
        time.sleep(60)
        continue

    current_time = int(time.time())

    for coin, current_price in current_prices.items():
        if coin.endswith(QUOTE_CURRENCY):
            if coin not in PRICE_HISTORY:
                PRICE_HISTORY[coin] = []
            
            # Add current price to history
            PRICE_HISTORY[coin].append((current_price, current_time))
            
            # Remove prices older than TIME_DIFFERENCE
            PRICE_HISTORY[coin] = [(p, t) for p, t in PRICE_HISTORY[coin] 
                                 if current_time - t <= TIME_DIFFERENCE]
            
            if len(PRICE_HISTORY[coin]) > 1:
                # Get the oldest price in our window
                old_price, old_timestamp = PRICE_HISTORY[coin][0]
                if old_price > 0 and current_price > 0:
                    time_diff = current_time - old_timestamp
                    # Only compare if we have a price that's TIME_DIFFERENCE old or close to it
                    if time_diff >= TIME_DIFFERENCE * 0.9:  # Allow 90% of intended window
                        change = ((current_price - old_price) / old_price) * 100
                        logger.info(f"Checking {coin} for price change: {change:.2f}% over {time_diff/60:.1f} minutes")
                        
                        if change > ALERT_THRESHOLD:
                            alert_message = f"🚀 ALERT: {coin} increased by {change:.2f}% in {time_diff/60:.1f} minutes!"
                            logger.warning(alert_message)
                            try:
                                # Store alert in file
                                current_time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                with open(ALERT_LOG_FILE, 'a') as f:
                                    f.write(f"\n=== {current_time_str} ===\n")
                                    f.write(f"{coin}: {change:.2f}% (Price: {current_price:.8f} {QUOTE_CURRENCY})\n")
                                
                                # Send Telegram alert
                                send_telegram_alert(alert_message)
                            except Exception as e:
                                logger.error(f"Failed to write to log or send alert: {e}")

    logger.info(f"Checked prices, waiting {REFRESH_INTERVAL} seconds...")
    time.sleep(REFRESH_INTERVAL)
