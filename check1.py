import json
from cloud import fetch_all_cloud_folders
from db import fetch_data_from_db
from addon import fetch_complete_data
import subprocess
import logging
import sys
from config import PLATFORMS  # Import the PLATFORMS configuration

sys.stdout.reconfigure(line_buffering=True)

# Set up logging configuration
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

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
    valid_clouds = list(PLATFORMS.keys())  # Fetch valid clouds from configuration

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

    updated_db_data = db_data_parsed.copy()

    # Validate and update cname and cid fields in the database
    for anime in db_data_parsed:
        cname_list = anime.get('cname', '').split(', ')
        cid_list = anime.get('cid', '').split(', ')

        # Filter out invalid clouds
        updated_cname_list = []
        updated_cid_list = []

        for cname, cid in zip(cname_list, cid_list):
            if cname in valid_clouds:
                updated_cname_list.append(cname)
                updated_cid_list.append(cid)
            else:
                logging.info(f"Removing invalid cloud: {cname} with cid: {cid}")

        # Check for new clouds in the cloud data
        anime_name = anime.get('name')
        cloud_anime = next((a for a in cloud_data if a.get('name') == anime_name), None)
        logging.debug(f"Cloud data for anime {anime_name}: {cloud_anime}")

        if cloud_anime:
            new_cnames = cloud_anime.get('cname', '').split(', ') if cloud_anime.get('cname') else []
            new_cids = cloud_anime.get('cid', '').split(', ') if cloud_anime.get('cid') else []

            for cname, cid in zip(new_cnames, new_cids):
                if cname and cid and cname not in updated_cname_list:
                    updated_cname_list.append(cname)
                    updated_cid_list.append(cid)
                    logging.info(f"Added new cloud: {cname} with cid: {cid} for anime: {anime_name}")

        # Update the anime's cname and cid fields
        anime['cname'] = ', '.join(updated_cname_list)
        anime['cid'] = ', '.join(updated_cid_list)

    # Log the final updated database after all modifications (removal of invalid clouds and adding new ones)
    logging.info("Final updated database data (cname and cid fields modified):")
    logging.info(json.dumps(updated_db_data, indent=4))

    # Extract anime names from cloud and DB
    cloud_anime_names = {anime.get('name') for anime in cloud_data if anime.get('name')}
    db_anime_dict = {anime.get('name'): anime for anime in db_data_parsed if anime.get('name')}
    db_anime_names = set(db_anime_dict.keys())

    # Determine new, unchanged, and deleted anime
    new_anime_names = cloud_anime_names - db_anime_names
    unchanged_anime_names = cloud_anime_names & db_anime_names
    deleted_anime_names = db_anime_names - cloud_anime_names

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

    # Handle deleted anime names
    if deleted_anime_names:
        print("\nDeleted Anime Names:")
        for name in deleted_anime_names:
            print(f" - {name}")
            updated_db_data = [anime for anime in updated_db_data if anime.get('name') != name]
            print(f" - {name} has been removed from the database.")

    # If changes were detected in cloud or db, we update the database
    if updated_db_data != db_data_parsed:
        try:
            print("\nChanges detected, updating database...")
            subprocess.run(['python', 'update.py'], input=json.dumps(updated_db_data), text=True, check=True)
            print("\nDatabase updated successfully!")
        except subprocess.CalledProcessError as e:
            print(f"Failed to update the database: {e}")
            print(f"Subprocess output: {e.output}")
            print(f"Subprocess errors: {e.stderr}")
    else:
        print("\nNOTHING NEW TO SEE BRO")
        try:
            print("\nNo changes detected, sending data to check2.py...")
            result = subprocess.run(['python', 'check2.py'], input=json.dumps(updated_db_data), text=True, capture_output=True, check=True)
            print("Subprocess output:", result.stdout)
            print("Subprocess errors:", result.stderr)
        except subprocess.CalledProcessError as e:
            print(f"Failed to send data to check2.py: {e}")
            print(f"Subprocess output: {e.output}")
            print(f"Subprocess errors: {e.stderr}")

if __name__ == "__main__":
    perform_check()
