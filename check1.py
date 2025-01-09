import json 
from cloud import fetch_all_cloud_folders
from db import fetch_data_from_db
from addon import fetch_complete_data 
import subprocess 
import logging
import sys
sys.stdout.reconfigure(line_buffering=True)
# Set up logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def generate_new_aid(existing_db_data):
    """Generate the next available AID based on the highest existing AID in the DB, ensuring uniqueness."""
    if not existing_db_data:
        logging.info("Database is empty. Starting with AID 1.")
        return 1  # If the database is empty, start with AID 1

    # Extract existing AIDs and ensure they are integers
    existing_aids = {anime.get('aid', 0) for anime in existing_db_data if isinstance(anime.get('aid', 0), int)}
    
    # Find the maximum AID value
    max_aid = max(existing_aids)

    # Generate the next unique AID
    new_aid = max_aid + 1
    while new_aid in existing_aids:
        new_aid += 1

    logging.info(f"Maximum AID found in database: {max_aid}. Using {new_aid} for the next anime entry.")
    return new_aid

def perform_check():
    # Fetch cloud and DB data
    cloud_data = fetch_all_cloud_folders()
    db_data, _ = fetch_data_from_db()

    if not cloud_data or not db_data:
        print("Error: Unable to fetch data from cloud or database.")
        return

    if db_data.strip() == "":
        print("Error: The database data is empty.")
        return

    try:
        db_data_parsed = json.loads(db_data)
    except json.JSONDecodeError:
        print("Error: Failed to decode the database data.")
        return

    # Extract anime names from cloud and DB
    cloud_anime_names = {anime.get('name') for anime in cloud_data if anime.get('name')}
    db_anime_dict = {anime.get('name'): anime for anime in db_data_parsed if anime.get('name')}
    db_anime_names = set(db_anime_dict.keys())

    # Determine new, unchanged, and deleted anime
    new_anime_names = cloud_anime_names - db_anime_names
    unchanged_anime_names = cloud_anime_names & db_anime_names
    deleted_anime_names = db_anime_names - cloud_anime_names

    updated_db_data = db_data_parsed.copy()

    # Handle new anime names
    if new_anime_names:
        print("\nNew Anime Names:")
        for name in new_anime_names:
            print(f" - {name}")
            new_anime_data = fetch_complete_data([anime for anime in cloud_data if anime.get('name') == name])
            if new_anime_data:
                new_aid = generate_new_aid(updated_db_data)
                for anime in new_anime_data:
                    anime['aid'] = new_aid
                    updated_db_data.append(anime)
            else:
                print(f"Failed to fetch data for {name}")

    if deleted_anime_names:
        print("\nDeleted Anime Names:")
        for name in deleted_anime_names:
            print(f" - {name}")
            updated_db_data = [anime for anime in updated_db_data if anime.get('name') != name]
            print(f" - {name} has been removed from the database.")

    if unchanged_anime_names:
        print("\nUnchanged Anime Names:")
        for name in unchanged_anime_names:
            print(f" - {name} data is unchanged in the database.")
            for anime in updated_db_data:
                if anime.get('name') == name:
                    continue

    if updated_db_data == db_data_parsed:
        print("\nNOTHING NEW TO SEE BRO")
        try:
            print("\nNo changes detected, sending data to check2.py...")
            subprocess.run(['python', 'check2.py'], input=json.dumps(updated_db_data), text=True, check=True)
        except Exception as e:
            print(f"Failed to send data to check2.py: {e}")
        return

    try:
        subprocess.run(['python', 'update.py'], input=json.dumps(updated_db_data), text=True, check=True)
        print("\nDatabase updated successfully!")
    except Exception as e:
        print(f"Failed to update the database: {e}")

if __name__ == "__main__":
    perform_check()