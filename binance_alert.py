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
TIME_DIFFERENCE = int(os.getenv('TIME_DIFFERENCE', '5'))  # Rolling window in minutes
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

# In-memory price history
PRICE_HISTORY = {}  # {coin: price}
LAST_CHECK_TIME = 0

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
startup_message = f"🚀 Binance Alert Bot Started\nCheck Interval: {TIME_DIFFERENCE} minutes\nAlert Threshold: {ALERT_THRESHOLD}%"
logger.info(startup_message)
send_telegram_alert(startup_message)

while True:
    current_time = int(time.time())
    
    # Check prices every TIME_DIFFERENCE minutes
    if current_time - LAST_CHECK_TIME >= TIME_DIFFERENCE * 60:
        current_prices = get_all_prices()
        if current_prices is None:
            logger.warning("Waiting before retry...")
            time.sleep(60)
            continue
        
        current_time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        for coin, current_price in current_prices.items():
            if coin.endswith(QUOTE_CURRENCY):
                if coin in PRICE_HISTORY:
                    old_price = PRICE_HISTORY[coin]
                    if old_price > 0 and current_price > 0:  # Skip if prices are zero
                        # Calculate change percentage
                        change = ((current_price - old_price) / old_price) * 100
                        logger.info(f"Checking {coin}: price change: {change:.2f}% over {TIME_DIFFERENCE} minutes")
                        
                        if change > ALERT_THRESHOLD:
                            alert_message = f"🚀 ALERT: {coin} increased by {change:.2f}% in {TIME_DIFFERENCE} minutes!"
                            logger.warning(alert_message)
                            try:
                                # Store alert in file
                                with open(ALERT_LOG_FILE, 'a') as f:
                                    f.write(f"\n=== {current_time_str} ===\n")
                                    f.write(f"{coin}: {change:.2f}% (Price: {current_price:.8f} {QUOTE_CURRENCY})\n")
                                
                                # Send Telegram alert
                                send_telegram_alert(alert_message)
                            except Exception as e:
                                logger.error(f"Failed to write to log or send alert: {e}")
                
                # Update price history
                PRICE_HISTORY[coin] = current_price
        
        LAST_CHECK_TIME = current_time
        logger.info(f"Checked prices, waiting {TIME_DIFFERENCE} minutes...")
    
    time.sleep(60)  # Sleep for 1 minute then check if it's time to check prices
