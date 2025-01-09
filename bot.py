from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
import subprocess
import requests
import asyncio
# import logging
from pyrogram.filters import user, command
from pyrogram import Client, filters
from pyrogram.types import Message
from config import *
from db import fetch_data_from_db
import json

# # Set up logging
# logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#                     level=logging.INFO)
# logger = logging.getLogger(__name__)

# Initialize the Pyrogram client with the necessary parameters
app = Client("anime_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b'OK')

def run_health_check_server():
    server_address = ('', 8000)
    httpd = HTTPServer(server_address, HealthCheckHandler)
    httpd.serve_forever()

# Custom decorator to restrict commands to admins
def admin_only():
    def wrapper(_, __, message: Message):
        return message.from_user.id in ADMINS
    return filters.create(wrapper)

# Handler for authorized commands
@app.on_message(filters.command(["start", "fast_update", "update_all", "check", "aniflix_api"]) & admin_only())
async def authorized_handler(client, message: Message):
    """Authorized commands for admins."""
    command = message.command[0]
    if command == "start":
        await message.reply("😊 Welcome to the Anime Bot! Use the available commands to interact.")
    elif command == "fast_update":
        await message.reply("⚠️ Running fast update...")
        await stream_script_output('check1.py', message)
        await message.reply("✅ Fast update process finished.")
    elif command == "update_all":
        await message.reply("⚠️ Running full update...")
        await stream_script_output('update_all.py', message)
        await message.reply("✅ Full update process finished.")
    elif command == "check":
        await check(client, message)
    elif command == "aniflix_api":
        await aniflix_api(client, message)

# Fallback for non-admins
@app.on_message(filters.command(["start", "fast_update", "update_all", "check", "aniflix_api"]) & ~admin_only())
async def unauthorized_handler(client, message: Message):
    """Notify unauthorized users."""
    await message.reply("⛔ You are not authorized to use this command.")

@app.on_message(filters.command("start"))
async def start(client, message: Message):
    """Send a welcome message on /start"""
    await message.reply("Welcome to the Anime Bot! Use the available commands to interact.")

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
            bufsize=1  # Line-buffered output
        )
        
        output_lines = []

        # Stream stdout in real-time
        for stdout_line in iter(process.stdout.readline, ""):
            if stdout_line.strip():  # If there's any non-empty line to send, send it immediately
                await message.reply(stdout_line.strip())
                output_lines.append(stdout_line.strip())
        
        # Wait for process to complete
        process.stdout.close()
        process.wait()

        # Check if there are any errors
        if process.returncode != 0:
            stderr_output = process.stderr.read()
            if stderr_output.strip():
                await message.reply(f"Error: {stderr_output.strip()}")
            else:
                await message.reply("Error: Script exited with a non-zero status but no error message.")
        
        process.stderr.close()

        # Handle case where no output was produced
        if not output_lines:
            await message.reply("The script did not produce any output.")

    except Exception as e:
        await message.reply(f"Error running script: {str(e)}")
        
@app.on_message(filters.command("fast_update"))
async def fast_update(client, message: Message):
    """Trigger the check1.py script and stream output live."""
    await message.reply("Running fast update...")
    await stream_script_output('check1.py', message)
    await message.reply("Fast update process finished.")

@app.on_message(filters.command("update_all"))
async def update_all(client, message: Message):
    """Trigger the update_all.py script and stream output live."""
    await message.reply("Running full update...")
    await stream_script_output('update_all.py', message)
    await message.reply("Full update process finished.")


@app.on_message(filters.command("check"))
async def check(client, message: Message):
    """Check the status of Git token, DB, Cloud URLs, and APIs"""
    try:
        status_report = "Checking platform and API statuses...\n\n"
        
        # Checking platform status
        for platform, url in PLATFORMS.items():
            try:
                response = requests.get(url)
                if response.status_code == 200:
                    status_report += f"✅ {platform}: Online\n"
                else:
                    status_report += f"❌ {platform}: Error - {response.status_code}\n"
            except Exception as e:
                status_report += f"❌ {platform}: Error - {str(e)}\n"
        
        # Checking Git Token (using GitHub API as an example)
        try:
            git_response = requests.get("https://api.github.com", headers={"Authorization": f"token {GIT_TOKEN}"})
            if git_response.status_code == 200:
                status_report += "✅ Git Token: Valid\n"
            else:
                status_report += f"❌ Git Token: Invalid - {git_response.status_code}, {GIT_TOKEN}\n"
        except Exception as e:
            status_report += f"❌ Git Token: Error - {str(e)}\n"
        
        # Checking Kitsu API
        try:
            kitsu_response = requests.get(API_URLS['Kitsu'])
            if kitsu_response.status_code == 200:
                status_report += "✅ Kitsu API: Online\n"
            else:
                status_report += f"❌ Kitsu API: Error - {kitsu_response.status_code}\n"
        except Exception as e:
            status_report += f"❌ Kitsu API: Error - {str(e)}\n"
        
        # Checking JikanV4 API
        try:
            jikan_response = requests.get(API_URLS['JikanV4'])
            if jikan_response.status_code == 200:
                status_report += "✅ Jikan API: Online\n"
            else:
                status_report += f"❌JikanV4 API: Error - {jikan_response.status_code}\n"
        except Exception as e:
            status_report += f"❌ JikanV4 API: Error - {str(e)}\n"
        
        # Send the status report
        await message.reply(status_report)

    except Exception as e:
        await message.reply(f"Error checking statuses: {str(e)}")

@app.on_message(filters.command("aniflix_api"))
async def aniflix_api(client, message: Message):
    """Fetch all AIDs and names from the database in chunks to avoid long messages."""
    await message.reply("Fetching anime data...")
    try:
        # Fetch the raw data from the database (GitHub)
        data, _ = fetch_data_from_db()
        
        if data is None:
            await message.reply("Error fetching anime data.")
            return
        
        # Parse the fetched data (assuming it's a JSON formatted string)
        anime_data = json.loads(data)
        
        # Prepare a list of anime names and AIDs
        anime_list = [f"{anime['name']} - AID: {anime['aid']}" for anime in anime_data]
        
        if anime_list:
            # Break the list into chunks of 30 items (or suitable size to fit Telegram limits)
            chunk_size = 30
            for i in range(0, len(anime_list), chunk_size):
                chunk = anime_list[i:i + chunk_size]
                await message.reply("\n".join(chunk))
        else:
            await message.reply("No anime data found.")
        
    except Exception as e:
        await message.reply(f"Error fetching anime data: {str(e)}")


if __name__ == "__main__":
    # Start health check server in a separate thread
    health_check_thread = threading.Thread(target=run_health_check_server)
    health_check_thread.daemon = True
    health_check_thread.start()
    
    # Start the bot
    app.run()

