import json
import subprocess
import sys
import time
import requests
from db import fetch_data_from_db

sys.stdout.reconfigure(line_buffering=True)

def fetch_mal_id(anime_name):
    """Fetch MAL ID from Jikan API"""
    try:
        response = requests.get(f"https://api.jikan.moe/v4/anime?q={anime_name}&limit=1", timeout=10)
        response.raise_for_status()
        data = response.json()
        if data.get("data"):
            return str(data["data"][0].get("mal_id", "N/A"))
    except Exception as e:
        print(f"Jikan error for {anime_name}: {e}")
    return "N/A"

def fetch_kitsu_id(anime_name):
    """Fetch Kitsu ID from Kitsu API"""
    try:
        response = requests.get(f"https://kitsu.io/api/edge/anime?filter[text]={anime_name}&page[limit]=1", timeout=10)
        response.raise_for_status()
        data = response.json()
        if data.get("data"):
            return str(data["data"][0].get("id", "N/A"))
    except Exception as e:
        print(f"Kitsu error for {anime_name}: {e}")
    return "N/A"

def fetch_anilist_id(anime_name):
    """Fetch AniList ID from AniList GraphQL API"""
    query = '''
    query ($search: String) {
        Media(search: $search, type: ANIME) {
            id
        }
    }
    '''
    try:
        response = requests.post(
            'https://graphql.anilist.co',
            json={'query': query, 'variables': {'search': anime_name}},
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        if data.get('data') and data['data'].get('Media'):
            return str(data['data']['Media']['id'])
    except Exception as e:
        print(f"AniList error for {anime_name}: {e}")
    return "N/A"

def needs_id_update(anime):
    """Check if any ID field is missing"""
    for field in ['mal_id', 'kitsu_id', 'anilist_id']:
        val = anime.get(field, 'N/A')
        if val == 'N/A' or val == '' or val is None:
            return True
    return False

def update_anime_ids():
    """Update MAL, Kitsu, and AniList IDs for all anime missing them"""
    print("Fetching database...")
    db_data, _ = fetch_data_from_db()

    if not db_data or not db_data.strip():
        print("Error: Unable to fetch database.")
        return

    try:
        db_data_parsed = json.loads(db_data)
    except json.JSONDecodeError:
        print("Error: Failed to decode database data.")
        return

    updated_count = 0

    for anime in db_data_parsed:
        anime_name = anime.get('name', 'Unknown')

        if needs_id_update(anime):
            print(f"Updating IDs for: {anime_name}")

            if anime.get('mal_id', 'N/A') in ('N/A', '', None):
                mal_id = fetch_mal_id(anime_name)
                anime['mal_id'] = mal_id
                print(f"  MAL ID: {mal_id}")
                time.sleep(1)

            if anime.get('kitsu_id', 'N/A') in ('N/A', '', None):
                kitsu_id = fetch_kitsu_id(anime_name)
                anime['kitsu_id'] = kitsu_id
                print(f"  Kitsu ID: {kitsu_id}")
                time.sleep(1)

            if anime.get('anilist_id', 'N/A') in ('N/A', '', None):
                anilist_id = fetch_anilist_id(anime_name)
                anime['anilist_id'] = anilist_id
                print(f"  AniList ID: {anilist_id}")
                time.sleep(1)

            updated_count += 1
            time.sleep(1)  # Rate limiting between anime

    if updated_count > 0:
        print(f"\nTotal updated: {updated_count} anime")
        print("Saving to database...")
        try:
            subprocess.run(['python', 'update.py'], input=json.dumps(db_data_parsed), text=True, check=True)
            print("[SUCCESS] Database updated successfully!")
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Update failed: {e}")
    else:
        print("No updates needed. All IDs are already present.")

if __name__ == "__main__":
    update_anime_ids()
