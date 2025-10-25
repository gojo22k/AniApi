import json
import subprocess
import sys
import time
import requests
import re
from db import fetch_data_from_db
from addon import shorten_image_url

sys.stdout.reconfigure(line_buffering=True)

def clean_anime_name(name):
    """Clean anime name for better API matching"""
    # Remove season numbers and extra text
    name = re.sub(r'\s+Season\s+\d+', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s+S\d+', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s+Part\s+\d+', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s+\d+(st|nd|rd|th)\s+Season', '', name, flags=re.IGNORECASE)
    # Remove special characters and extra spaces
    name = re.sub(r'[:\-\(\)\[\]]', ' ', name)
    name = ' '.join(name.split())
    return name.strip()

def get_alternative_names_from_jikan(anime_name):
    """Get alternative names (Japanese, romanized) from Jikan to use for other APIs"""
    try:
        response = requests.get(f"https://api.jikan.moe/v4/anime?q={anime_name}&limit=1")
        response.raise_for_status()
        data = response.json()
        
        if data.get("data"):
            anime = data["data"][0]
            alternatives = []
            
            # Get Japanese title
            if anime.get("title_japanese"):
                alternatives.append(anime["title_japanese"])
            
            # Get English title
            if anime.get("title_english"):
                alternatives.append(anime["title_english"])
            
            # Get synonyms
            if anime.get("title_synonyms"):
                alternatives.extend(anime["title_synonyms"])
            
            return alternatives
    except Exception as e:
        pass
    return []

def fetch_images_from_jikan(anime_name):
    """Fetch poster and banner from Jikan API with flexible search"""
    try:
        # Try with original name first
        response = requests.get(f"https://api.jikan.moe/v4/anime?q={anime_name}&limit=5")
        response.raise_for_status()
        data = response.json()
        
        # If no results, try with cleaned name
        if not data.get("data"):
            cleaned_name = clean_anime_name(anime_name)
            if cleaned_name != anime_name:
                print(f"Retrying with cleaned name: {cleaned_name}")
                time.sleep(1)
                response = requests.get(f"https://api.jikan.moe/v4/anime?q={cleaned_name}&limit=5")
                response.raise_for_status()
                data = response.json()
        
        if data.get("data"):
            # Use first result
            anime = data["data"][0]
            
            # Get poster
            poster = anime["images"]["jpg"]["large_image_url"] if anime.get("images") else None
            
            # Get banner from trailer
            banner = None
            trailer = anime.get("trailer", {}).get("url")
            if trailer and "youtube.com" in trailer:
                video_id = trailer.split('?v=')[-1].split('&')[0]
                banner = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
            
            # Shorten URLs
            if poster:
                poster = shorten_image_url(poster)
            if banner:
                banner = shorten_image_url(banner)
            
            return poster, banner
    except Exception as e:
        print(f"Jikan error for {anime_name}: {e}")
    return None, None

def fetch_images_from_kitsu(anime_name):
    """Fetch poster and banner from Kitsu API with flexible search"""
    try:
        # Try with original name
        response = requests.get(f"https://kitsu.io/api/edge/anime?filter[text]={anime_name}&page[limit]=5")
        response.raise_for_status()
        data = response.json()
        
        # If no results, try with cleaned name
        if not data.get("data"):
            cleaned_name = clean_anime_name(anime_name)
            if cleaned_name != anime_name:
                print(f"Retrying with cleaned name: {cleaned_name}")
                time.sleep(1)
                response = requests.get(f"https://kitsu.io/api/edge/anime?filter[text]={cleaned_name}&page[limit]=5")
                response.raise_for_status()
                data = response.json()
        
        if data.get("data"):
            anime = data["data"][0]
            attributes = anime["attributes"]
            
            poster = attributes["posterImage"]["original"] if attributes.get("posterImage") else None
            banner = attributes["coverImage"]["original"] if attributes.get("coverImage") else None
            
            # Shorten URLs
            if poster:
                poster = shorten_image_url(poster)
            if banner:
                banner = shorten_image_url(banner)
            
            return poster, banner
    except Exception as e:
        print(f"Kitsu error for {anime_name}: {e}")
    return None, None

def fetch_images_from_anilist(anime_name, alternative_names=None):
    """Fetch poster and banner from AniList GraphQL API with multiple name attempts"""
    query = '''
    query ($search: String) {
        Media(search: $search, type: ANIME) {
            coverImage {
                extraLarge
                large
            }
            bannerImage
            title {
                romaji
                english
                native
            }
        }
    }
    '''
    
    # Create list of names to try
    names_to_try = [anime_name]
    if alternative_names:
        names_to_try.extend(alternative_names)
    
    # Also try cleaned version
    cleaned = clean_anime_name(anime_name)
    if cleaned not in names_to_try:
        names_to_try.append(cleaned)
    
    for search_name in names_to_try:
        try:
            variables = {'search': search_name}
            response = requests.post(
                'https://graphql.anilist.co',
                json={'query': query, 'variables': variables},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get('data') and data['data'].get('Media'):
                media = data['data']['Media']
                poster = media['coverImage'].get('extraLarge') or media['coverImage'].get('large')
                banner = media.get('bannerImage')
                
                # Log which name worked (safe ASCII only)
                found_title = media['title'].get('english') or media['title'].get('romaji') or 'Found'
                if search_name != anime_name:
                    # Only print ASCII-safe characters
                    try:
                        safe_title = found_title.encode('ascii', 'ignore').decode('ascii')
                        if safe_title:
                            print(f"Found on AniList as: {safe_title}")
                        else:
                            print("Found on AniList (non-Latin title)")
                    except:
                        print("Found on AniList")
                
                # Shorten URLs
                if poster:
                    poster = shorten_image_url(poster)
                if banner:
                    banner = shorten_image_url(banner)
                
                return poster, banner
            
            time.sleep(0.5)  # Small delay between attempts
            
        except Exception as e:
            if search_name == names_to_try[-1]:  # Only log error on last attempt
                print(f"AniList error for {anime_name}: {e}")
            continue
    
    return None, None

def fetch_images_from_imdb(anime_name):
    """Fetch poster from IMDb"""
    from imdb import IMDb
    ia = IMDb()
    try:
        # Try original name
        search_results = ia.search_movie(anime_name)
        
        # If no results, try cleaned name
        if not search_results:
            cleaned_name = clean_anime_name(anime_name)
            if cleaned_name != anime_name:
                print(f"Retrying IMDb with: {cleaned_name}")
                search_results = ia.search_movie(cleaned_name)
        
        if search_results:
            movie = search_results[0]
            ia.update(movie)
            poster = movie.get("full-size cover url")
            
            if poster:
                poster = shorten_image_url(poster)
                return poster, None  # IMDb doesn't provide banners
    except Exception as e:
        print(f"IMDb error for {anime_name}: {e}")
    return None, None

def update_anime_images():
    """
    Update poster and banner images for anime with N/A values
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
        current_poster = anime.get('poster', 'N/A')
        current_banner = anime.get('banner', 'N/A')
        
        # Check if images need update
        needs_poster = current_poster == 'N/A' or current_poster == '' or current_poster is None
        needs_banner = current_banner == 'N/A' or current_banner == '' or current_banner is None
        
        if needs_poster or needs_banner:
            print(f"Updating images for: {anime_name}")
            
            poster, banner = None, None
            
            # Step 1: Get alternative names from Jikan (Japanese, romanized, etc.)
            print("Getting alternative names from Jikan...")
            alternative_names = get_alternative_names_from_jikan(anime_name)
            if alternative_names:
                # Filter out non-ASCII names for display to avoid encoding errors
                displayable_names = [name for name in alternative_names[:3] if all(ord(c) < 128 for c in name)]
                if displayable_names:
                    print(f"Found alternatives: {', '.join(displayable_names)}")
                else:
                    print(f"Found {len(alternative_names)} alternative names (including non-Latin characters)")
            time.sleep(1)
            
            # Step 2: Try AniList with all name variations (Priority 1)
            if needs_poster or needs_banner:
                print("Trying AniList with multiple names...")
                poster, banner = fetch_images_from_anilist(anime_name, alternative_names)
                time.sleep(1)
            
            # Step 3: Try Jikan if still missing (Priority 2)
            if (not poster and needs_poster) or (not banner and needs_banner):
                print("Trying Jikan...")
                jikan_poster, jikan_banner = fetch_images_from_jikan(anime_name)
                if not poster and jikan_poster:
                    poster = jikan_poster
                if not banner and jikan_banner:
                    banner = jikan_banner
                time.sleep(1)
            
            # Step 4: Try Kitsu if still missing (Priority 3)
            if (not poster and needs_poster) or (not banner and needs_banner):
                print("Trying Kitsu...")
                kitsu_poster, kitsu_banner = fetch_images_from_kitsu(anime_name)
                if not poster and kitsu_poster:
                    poster = kitsu_poster
                if not banner and kitsu_banner:
                    banner = kitsu_banner
                time.sleep(1)
            
            # Step 5: Try IMDb as last resort (Priority 4) - Only for posters
            if not poster and needs_poster:
                print("Trying IMDb...")
                imdb_poster, _ = fetch_images_from_imdb(anime_name)
                if imdb_poster:
                    poster = imdb_poster
                time.sleep(1)
            
            # Update if we found new images
            updated_this = False
            if poster and needs_poster:
                anime['poster'] = poster
                updated_this = True
                print(f"[SUCCESS] Updated poster from API")
            
            if banner and needs_banner:
                anime['banner'] = banner
                updated_this = True
                print(f"[SUCCESS] Updated banner from API")
            
            if updated_this:
                updated_count += 1
            else:
                print(f"[FAILED] No images found for {anime_name}")
            
            time.sleep(2)  # Rate limiting
    
    if updated_count > 0:
        print(f"\nTotal updated: {updated_count} anime")
        print("Saving to database...")
        
        try:
            subprocess.run(['python', 'update.py'], input=json.dumps(db_data_parsed), text=True, check=True)
            print("[SUCCESS] Database updated successfully!")
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Update failed: {e}")
    else:
        print("No updates needed. All images are available.")

if __name__ == "__main__":
    update_anime_images()