import json
import subprocess
import logging
import sys
from cloud import fetch_all_cloud_folders
from db import fetch_data_from_db
from addon import fetch_complete_data
from config import PLATFORMS

sys.stdout.reconfigure(line_buffering=True)

# Set up minimal logging configuration
logging.basicConfig(level=logging.INFO, format='%(message)s')

def perform_check():
    cloud_data = fetch_all_cloud_folders()
    db_data, _ = fetch_data_from_db()
    valid_clouds = set(PLATFORMS.keys())

    if not cloud_data or not db_data.strip():
        print("Error: Unable to fetch data from cloud or database.")
        return

    try:
        db_data_parsed = json.loads(db_data)
    except json.JSONDecodeError:
        print("Error: Failed to decode database data.")
        return

    updated_db_data = db_data_parsed.copy()

    for anime in db_data_parsed:
        cname_list = anime.get('cname', '').split(', ')
        cid_list = anime.get('cid', '').split(', ')
        anime_name = anime.get('name')

        # Filter out invalid clouds
        updated_cname_list, updated_cid_list = zip(*[(c, i) for c, i in zip(cname_list, cid_list) if c in valid_clouds]) if cname_list else ([], [])
        cloud_anime = next((a for a in cloud_data if a.get('name') == anime_name), None)

        if cloud_anime:
            new_cnames, new_cids = cloud_anime.get('cname', '').split(', '), cloud_anime.get('cid', '').split(', ')
            for cname, cid in zip(new_cnames, new_cids):
                if cname and cid and cname not in updated_cname_list:
                    updated_cname_list += (cname,)
                    updated_cid_list += (cid,)

        anime['cname'], anime['cid'] = ', '.join(updated_cname_list), ', '.join(updated_cid_list)

    cloud_anime_names = {anime.get('name') for anime in cloud_data if anime.get('name')}
    db_anime_dict = {anime.get('name'): anime for anime in db_data_parsed if anime.get('name')}
    db_anime_names = set(db_anime_dict.keys())

    new_anime_names = cloud_anime_names - db_anime_names
    deleted_anime_names = db_anime_names - cloud_anime_names

    if new_anime_names:
        print("New Anime:")
        for name in new_anime_names:
            print(f" - {name}")
            new_anime_data = fetch_complete_data([a for a in cloud_data if a.get('name') == name])
            if new_anime_data:
                for anime in new_anime_data:
                    updated_db_data.append(anime)

    if deleted_anime_names:
        print("Deleted Anime:")
        for name in deleted_anime_names:
            print(f" - {name} removed")
            updated_db_data = [a for a in updated_db_data if a.get('name') != name]

    if updated_db_data != db_data_parsed:
        try:
            print("Updating database...")
            subprocess.run(['python', 'update.py'], input=json.dumps(updated_db_data), text=True, check=True)
            print("Database updated!")
        except subprocess.CalledProcessError as e:
            print(f"Update failed: {e}")
    else:
        print("No changes detected. Running check2.py...")
        try:
            result = subprocess.run(['python', 'check2.py'], input=json.dumps(updated_db_data), text=True, capture_output=True, check=True)
            print(result.stdout)
        except subprocess.CalledProcessError as e:
            print(f"check2.py failed: {e}")

if __name__ == "__main__":
    perform_check()
