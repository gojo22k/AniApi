import json
import subprocess
import sys
import time
import requests
from db import fetch_data_from_db

sys.stdout.reconfigure(line_buffering=True)

def fetch_jikan_stats(anime_name):
    """Fetch anime statistics from Jikan API"""
    try:
        response = requests.get(f"https://api.jikan.moe/v4/anime?q={anime_name}")
        response.raise_for_status()
        data = response.json()
        
        if data.get("data"):
            anime = data["data"][0]
            
            # Extract studios
            studios = ", ".join(studio["name"] for studio in anime.get("studios", [])) if anime.get("studios") else "N/A"
            
            # Extract producers
            producers = ", ".join(producer["name"] for producer in anime.get("producers", [])) if anime.get("producers") else "Aniflix"
            
            # Get status and airing info
            status = anime.get("status", "Unknown")
            airing = str(anime.get("airing", False)).lower()
            
            # Validate status-airing consistency
            if status.lower() == "finished airing" or status.lower() == "finished":
                airing = "false"
                status = "Finished"
            elif status.lower() == "currently airing":
                airing = "true"
                status = "Current"
            
            return {
                "type": anime.get("type", "N/A"),
                "status": status,
                "airing": airing,
                "studio": studios,
                "producers": producers,
                "total_episodes": anime.get("episodes", "N/A")
            }
    except Exception as e:
        print(f"Jikan error for {anime_name}: {e}")
    return None

def fetch_kitsu_stats(anime_name):
    """Fetch anime statistics from Kitsu API as fallback"""
    try:
        response = requests.get(f"https://kitsu.io/api/edge/anime?filter[text]={anime_name}")
        response.raise_for_status()
        data = response.json()
        
        if data.get("data"):
            anime = data["data"][0]
            attributes = anime["attributes"]
            
            status = attributes.get("status", "Unknown").capitalize()
            
            # Validate status-airing consistency
            if status.lower() == "finished":
                airing = "false"
            elif status.lower() == "current":
                airing = "true"
            else:
                airing = "false"
            
            return {
                "type": attributes.get("showType", "N/A"),
                "status": status,
                "airing": airing,
                "studio": "N/A",
                "producers": "Aniflix",
                "total_episodes": attributes.get("episodeCount", "N/A")
            }
    except Exception as e:
        print(f"Kitsu error for {anime_name}: {e}")
    return None

def needs_update(anime):
    """Check if anime needs statistics update"""
    fields_to_check = ['type', 'status', 'studio', 'producers', 'total_episodes']
    
    for field in fields_to_check:
        value = anime.get(field, 'N/A')
        if value == 'N/A' or value == '' or value is None:
            return True
    
    # Check status-airing consistency
    status = anime.get('status', '').lower()
    airing = anime.get('airing', '').lower()
    
    if (status == 'finished' and airing == 'true') or (status == 'current' and airing == 'false'):
        return True
    
    return False

def update_anime_stats():
    """
    Update anime statistics (type, status, airing, studio, producers, episodes)
    """
    print("Fetching database...")
    db_data, _ = fetch_data_from_db()
    
    if not db_data.strip():
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
        
        if needs_update(anime):
            print(f"Updating stats for: {anime_name}")
            
            # Try Jikan first
            stats = fetch_jikan_stats(anime_name)
            
            if not stats:
                # Try Kitsu as fallback
                time.sleep(1)
                stats = fetch_kitsu_stats(anime_name)
            
            if stats:
                # Update fields only if they are N/A or need correction
                if anime.get('type', 'N/A') == 'N/A':
                    anime['type'] = stats['type']
                
                if anime.get('status', 'N/A') == 'N/A' or needs_update(anime):
                    anime['status'] = stats['status']
                    anime['airing'] = stats['airing']
                
                if anime.get('studio', 'N/A') == 'N/A':
                    anime['studio'] = stats['studio']
                
                if anime.get('producers', 'N/A') == 'N/A':
                    anime['producers'] = stats['producers']
                
                if anime.get('total_episodes', 'N/A') == 'N/A':
                    anime['total_episodes'] = stats['total_episodes']
                
                updated_count += 1
                print(f"✅ Updated: Type={stats['type']}, Status={stats['status']}, Airing={stats['airing']}, Episodes={stats['total_episodes']}")
            else:
                print(f"❌ No stats found for {anime_name}")
            
            time.sleep(2)  # Rate limiting
    
    if updated_count > 0:
        print(f"\nTotal updated: {updated_count} anime")
        print("Saving to database...")
        
        try:
            subprocess.run(['python', 'update.py'], input=json.dumps(db_data_parsed), text=True, check=True)
            print("✅ Database updated successfully!")
        except subprocess.CalledProcessError as e:
            print(f"❌ Update failed: {e}")
    else:
        print("No updates needed. All statistics are up to date.")

if __name__ == "__main__":
    update_anime_stats()