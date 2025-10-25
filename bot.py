from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
import subprocess
import requests
import asyncio
import time
from pyrogram.filters import user, command
from pyrogram import Client, filters
from pyrogram.types import Message
from config import *
from db import fetch_data_from_db
import json

# Initialize the Pyrogram client with the necessary parameters
app = Client("anime_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b'OK - Bot is alive!')
    
    def log_message(self, format, *args):
        pass

def run_health_check_server():
    server_address = ('', HEALTH_CHECK_PORT)
    httpd = HTTPServer(server_address, HealthCheckHandler)
    print(f"Health check server started on port {HEALTH_CHECK_PORT}")
    httpd.serve_forever()

def keep_alive_pinger():
    """Ping the health check endpoint to prevent sleep"""
    time.sleep(30)  # Initial delay
    
    app_url = os.getenv('APP_URL', f'http://localhost:{HEALTH_CHECK_PORT}')
    
    while True:
        try:
            response = requests.get(app_url, timeout=10)
            print(f"[Keep-Alive] Pinged at {time.strftime('%Y-%m-%d %H:%M:%S')} - Status: {response.status_code}")
        except Exception as e:
            print(f"[Keep-Alive] Ping failed: {str(e)}")
        
        time.sleep(KEEP_ALIVE_INTERVAL)

def external_pinger():
    """Additional external ping using a free uptime monitoring service"""
    time.sleep(60)
    
    while True:
        try:
            # Ping multiple external services to ensure activity
            urls = [
                os.getenv('APP_URL', 'http://localhost:8000'),
                'https://www.google.com',  # Fallback
            ]
            
            for url in urls:
                try:
                    requests.head(url, timeout=5)
                except:
                    pass
                    
        except Exception as e:
            print(f"[External-Ping] Error: {str(e)}")
        
        time.sleep(150)  # Ping every 2.5 minutes

# Custom decorator to restrict commands to admins
def admin_only():
    def wrapper(_, __, message: Message):
        return message.from_user.id in ADMINS
    return filters.create(wrapper)

# Handler for authorized commands
@app.on_message(filters.command(["fast_update", "update_all", "check", "aniflix_api", "server", "imdb", "c_stats", "image"]) & admin_only())
async def authorized_handler(client, message: Message):
    """Authorized commands for admins."""
    command = message.command[0]
    
    if command == "fast_update":
        await message.reply("[RUNNING] Fast update...")
        await stream_script_output('check1.py', message)
        await message.reply("[COMPLETED] Fast update process finished.")
    elif command == "update_all":
        await message.reply("[RUNNING] Full update...")
        await stream_script_output('update_all.py', message)
        await message.reply("[COMPLETED] Full update process finished.")
    elif command == "check":
        await check(client, message)
    elif command == "aniflix_api":
        await aniflix_api(client, message)
    elif command == "server":
        await update_servers(client, message)
    elif command == "imdb":
        await update_imdb(client, message)
    elif command == "c_stats":
        await update_stats(client, message)
    elif command == "image":
        await update_images(client, message)

# Fallback for non-admins
@app.on_message(filters.command(["start", "fast_update", "update_all", "check", "aniflix_api", "server", "imdb", "c_stats", "image"]) & ~admin_only())
async def unauthorized_handler(client, message: Message):
    """Notify unauthorized users."""
    await message.reply("⛔ You are not authorized to use this command.")

@app.on_message(filters.command("start") & admin_only())
async def start(client, message: Message):
    """Send a welcome message with an image on /start"""
    start_image_url = "https://iili.io/3fLTdfn.jpg"
    
    await message.reply_photo(
        start_image_url,
        caption=(
            "👋 **Welcome to the Anime Bot!**\n\n"
            "This bot helps you manage anime data efficiently.\n"
            "Here are some commands you can use:\n"
            "🔹 `/fast_update` - Quickly update anime records\n"
            "🔹 `/update_all` - Perform a full database update\n"
            "🔹 `/check` - Check platform and API statuses\n"
            "🔹 `/aniflix_api` - Fetch anime list from the database\n"
            "🔹 `/server` - Update server information (cname, cid)\n"
            "🔹 `/imdb` - Update IMDb ratings\n"
            "🔹 `/c_stats` - Update anime statistics (type, status, episodes, etc.)\n"
            "🔹 `/image` - Update poster and banner images\n\n"
            "✅ **Admin Access Required for Certain Commands**\n"
            "Use the bot responsibly and enjoy your anime tracking! 🎉"
        )
    )

async def stream_script_output(script_name, message: Message):
    """
    Runs a script and streams its output line by line to the user as Telegram messages.
    """
    try:
        process = subprocess.Popen(
            ['python', script_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        
        output_lines = []

        for stdout_line in iter(process.stdout.readline, ""):
            if stdout_line.strip():
                await message.reply(stdout_line.strip())
                output_lines.append(stdout_line.strip())
        
        process.stdout.close()
        process.wait()

        if process.returncode != 0:
            stderr_output = process.stderr.read()
            if stderr_output.strip():
                await message.reply(f"Error: {stderr_output.strip()}")
            else:
                await message.reply("Error: Script exited with a non-zero status but no error message.")
        
        process.stderr.close()

        if not output_lines:
            await message.reply("The script did not produce any output.")

    except Exception as e:
        await message.reply(f"Error running script: {str(e)}")

@app.on_message(filters.command("check"))
async def check(client, message: Message):
    """Check the status of Git token, DB, Cloud URLs, and APIs"""
    try:
        status_report = "Checking platform and API statuses...\n\n"
        
        for platform, url in PLATFORMS.items():
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    status_report += f"[OK] {platform}: Online\n"
                else:
                    status_report += f"[ERROR] {platform}: Error - {response.status_code}\n"
            except Exception as e:
                status_report += f"[ERROR] {platform}: Error - {str(e)}\n"
        
        try:
            git_response = requests.get("https://api.github.com", headers={"Authorization": f"token {GIT_TOKEN}"})
            if git_response.status_code == 200:
                status_report += "[OK] Git Token: Valid\n"
            else:
                status_report += f"[ERROR] Git Token: Invalid - {git_response.status_code}\n"
        except Exception as e:
            status_report += f"[ERROR] Git Token: Error - {str(e)}\n"
        
        try:
            kitsu_response = requests.get(API_URLS['Kitsu'])
            if kitsu_response.status_code == 200:
                status_report += "[OK] Kitsu API: Online\n"
            else:
                status_report += f"[ERROR] Kitsu API: Error - {kitsu_response.status_code}\n"
        except Exception as e:
            status_report += f"[ERROR] Kitsu API: Error - {str(e)}\n"
        
        try:
            jikan_response = requests.get(API_URLS['JikanV4'])
            if jikan_response.status_code == 200:
                status_report += "[OK] Jikan API: Online\n"
            else:
                status_report += f"[ERROR] JikanV4 API: Error - {jikan_response.status_code}\n"
        except Exception as e:
            status_report += f"[ERROR] JikanV4 API: Error - {str(e)}\n"
        
        await message.reply(status_report)

    except Exception as e:
        await message.reply(f"Error checking statuses: {str(e)}")

@app.on_message(filters.command("aniflix_api"))
async def aniflix_api(client, message: Message):
    """Fetch all AIDs and names from the database in chunks to avoid long messages."""
    await message.reply("Fetching anime data...")
    try:
        data, _ = fetch_data_from_db()
        
        if data is None:
            await message.reply("Error fetching anime data.")
            return
        
        anime_data = json.loads(data)
        anime_list = [f"{anime['name']} - AID: {anime['aid']}" for anime in anime_data]
        
        if anime_list:
            chunk_size = 30
            for i in range(0, len(anime_list), chunk_size):
                chunk = anime_list[i:i + chunk_size]
                await message.reply("\n".join(chunk))
        else:
            await message.reply("No anime data found.")
        
    except Exception as e:
        await message.reply(f"Error fetching anime data: {str(e)}")

@app.on_message(filters.command("server"))
async def update_servers(client, message: Message):
    """Update server information (cname and cid) for all anime"""
    await message.reply("[RUNNING] Updating server information...")
    await stream_script_output('update_servers.py', message)
    await message.reply("[COMPLETED] Server update finished.")

@app.on_message(filters.command("imdb"))
async def update_imdb(client, message: Message):
    """Update IMDb ratings for anime with N/A ratings"""
    await message.reply("[RUNNING] Updating IMDb ratings...")
    await stream_script_output('update_imdb.py', message)
    await message.reply("[COMPLETED] IMDb update finished.")

@app.on_message(filters.command("c_stats"))
async def update_stats(client, message: Message):
    """Update anime statistics (type, status, episodes, etc.)"""
    await message.reply("[RUNNING] Updating anime statistics...")
    await stream_script_output('update_stats.py', message)
    await message.reply("[COMPLETED] Statistics update finished.")

@app.on_message(filters.command("image"))
async def update_images(client, message: Message):
    """Update poster and banner images with N/A values"""
    await message.reply("[RUNNING] Updating images...")
    await stream_script_output('update_images.py', message)
    await message.reply("[COMPLETED] Image update finished.")


if __name__ == "__main__":
    # Start health check server in a separate thread
    health_check_thread = threading.Thread(target=run_health_check_server)
    health_check_thread.daemon = True
    health_check_thread.start()
    
    # Start keep-alive pinger in a separate thread
    keep_alive_thread = threading.Thread(target=keep_alive_pinger)
    keep_alive_thread.daemon = True
    keep_alive_thread.start()
    
    # Start external pinger in a separate thread
    external_ping_thread = threading.Thread(target=external_pinger)
    external_ping_thread.daemon = True
    external_ping_thread.start()
    
    print("Bot is starting...")
    print("Health check server and keep-alive pingers are running")
    
    # Start the bot
    app.run()