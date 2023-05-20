import os
import time

from binance.client import Client
from telegram import Bot
import asyncio
import numpy as np
import pandas as pd

# Binance setup
binance_api_key = os.environ.get('BINANCE_API_KEY')
binance_api_secret = os.environ.get('BINANCE_API_SECRET')
binance_client = Client(binance_api_key, binance_api_secret)

# Telegram bot setup
telegram_bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
telegram_chat_id = os.environ.get('TELEGRAM_CHAT_ID')

# Time interval to check the volume
TIME_INTERVAL = Client.KLINE_INTERVAL_1HOUR

# Get all trading pairs
exchange_info = binance_client.get_exchange_info()
symbols = [s['symbol'] for s in exchange_info['symbols'] if s['symbol'].endswith('USDT')]

# For each symbol, get the historical kline data and calculate volume changes
volume_changes = {}
for symbol in symbols:
    klines = binance_client.get_historical_klines(symbol, TIME_INTERVAL, "7 days ago UTC")

    volumes = [float(kline[5]) for kline in klines]
    volume_changes[symbol] = pd.Series(volumes).pct_change().dropna()

# Now we can calculate a threshold for each symbol
thresholds = {symbol: (np.mean(changes) + 2 * np.std(changes)) for symbol, changes in volume_changes.items()}


async def send_message(message):
    bot = Bot(token=telegram_bot_token)
    await bot.send_message(chat_id=telegram_chat_id, text=message, parse_mode='HTML')


async def main():
    while True:
        notification_messages = []  # List to store individual notification messages

        for symbol in symbols:
            # Get the klines for the symbol
            klines = binance_client.get_klines(symbol=symbol, interval=TIME_INTERVAL, limit=2)

            # Calculate volume change
            previous_volume = float(klines[0][5])  # Volume is the 6th item in the list
            current_volume = float(klines[1][5])
            volume_change = ((current_volume - previous_volume) / previous_volume) * 100

            # Calculate price change
            previous_close = float(klines[0][4])  # Close price is the 5th item in the list
            current_close = float(klines[1][4])
            price_change = ((current_close - previous_close) / previous_close) * 100

            print(symbol, volume_change, thresholds[symbol])
            # If the volume has increased by more than the threshold, add to the notification messages list
            if volume_change > thresholds[symbol]:
                symbol_notification = f"<b>Symbol:</b> {symbol}\n" \
                                      f"<b>Volume change:</b> {volume_change:.2f}%\n" \
                                      f"<b>Price change:</b> {price_change:.2f}%\n"
                notification_messages.append(symbol_notification)

        # Create a formatted message with all the notification messages in a table-like structure
        if notification_messages:
            table_header = "<b>Volume and price change notifications:</b>\n\n"
            table_rows = '\n'.join(notification_messages)
            consolidated_message = f"{table_header}<pre>{table_rows}</pre>"

            # Send the consolidated message if there are any updates
            print(consolidated_message)
            await send_message(consolidated_message)

        # Sleep for an hour before checking again
        print(time.time(), "Sleeping for the next time..")
        await asyncio.sleep(3600)


asyncio.run(main())
