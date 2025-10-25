import json
import time
import requests
import subprocess
import logging
import sys
from logging.handlers import RotatingFileHandler

# Define the Kitsu API URL for fetching anime data by name
KITSU_API_URL = "https://kitsu.io/api/edge/anime"

# Set up logging configuration
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
log_handler = RotatingFileHandler('app.log', maxBytes=2000, backupCount=5)
log_handler.setFormatter(log_formatter)
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(log_handler)

# Function to send logs to Telegram (Assuming you have a function for this)
def send_log_to_telegram(log_message):
    # Add logic to send log_message to Telegram
    pass

def log_message(message_type, message_content):
    """Log messages with different types for better organization."""
    log_functions = {
        'INFO': lambda msg: logger.info(msg),
        'ERROR': lambda msg: logger.error(msg),
        'WARNING': lambda msg: logger.warning(msg),
        'UPDATE': lambda msg: logger.info(msg),
        'DEBUG': lambda msg: logger.debug(msg),
        'SUCCESS': lambda msg: logger.info(msg),
    }
    
    # If the log type is valid, log the message
    if message_type in log_functions:
        log_functions[message_type](message_content)
        send_log_to_telegram(f"{message_type}: {message_content}")
    else:
        logger.info(f"[UNKNOWN] {message_content}")
        send_log_to_telegram(f"UNKNOWN: {message_content}")

def get_anime_status_from_kitsu(anime_name):
    """Fetch the anime status from Kitsu API based on the anime name."""
    try:
        response = requests.get(f"{KITSU_API_URL}?filter[text]={anime_name}")
        response.raise_for_status()  # Check if the request was successful
        data = response.json()
        
        if data['data']:
            # Extract the first match (if multiple matches exist)
            anime_data = data['data'][0]['attributes']
            status = anime_data.get('status').lower()  # Get the status in lowercase for comparison
            return status
        else:
            log_message('WARNING', f"No anime found for {anime_name}")
            return None

    except requests.RequestException as e:
        log_message('ERROR', f"Error fetching data from Kitsu API for {anime_name}: {e}")
        return None

def send_to_update_script(updated_db_data):
    """Send the updated anime data to the update.py script."""
    try:
        subprocess.run(['python', 'update.py'], input=json.dumps(updated_db_data), text=True, check=True)
        log_message('SUCCESS', "Database updated.")
    except subprocess.CalledProcessError:
        log_message('ERROR', "Error updating the database.")

def check_anime_status(data):
    """Check anime statuses, log changes, update the response, and handle airing status."""
    try:
        parsed_data = json.loads(data)
        changes_made = False
        updated_db_data = []

        for anime in parsed_data:
            name = anime.get('name')
            current_status = anime.get('status', '').lower()  # Existing status from DB data
            
            # Fetch the current status from Kitsu
            fetched_status = get_anime_status_from_kitsu(name)
            
            if fetched_status:
                # If the status from the DB is not 'finished', check for changes
                if current_status != 'finished':
                    time.sleep(2)  # Pause before recheck
                    
                    # Fetch the status again after recheck
                    rechecked_status = get_anime_status_from_kitsu(name)
                    
                    if rechecked_status and rechecked_status != current_status:
                        # Update the status in the DB response (capitalize the status field)
                        anime['status'] = rechecked_status.capitalize()  
                        
                        # If the status is finished, set 'airing' to False
                        if rechecked_status == 'finished':
                            anime['airing'] = False
                        
                        log_message('UPDATE', f"Status for {name} has changed from {current_status.capitalize()} to {rechecked_status.capitalize()}")
                        
                        changes_made = True  # Mark that a change was made
                
                # Add the updated anime data to the list
                updated_db_data.append(anime)

        if changes_made:
            send_to_update_script(updated_db_data)
        else:
            log_message('INFO', "NO CHANGES")

    except json.JSONDecodeError:
        log_message('ERROR', "Error decoding data.")

if __name__ == "__main__":
    # Assuming data is passed from subprocess as a string
    import sys
    data = sys.stdin.read()  # Read the input passed from the subprocess
    check_anime_status(data)
