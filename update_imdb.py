import json
import subprocess
import sys
import time
import requests
import re
from imdb import IMDb
from db import fetch_data_from_db

sys.stdout.reconfigure(line_buffering=True)

def clean_anime_name(name):
    """Clean anime name for better API matching"""
    name = re.sub(r'\s+Season\s+\d+', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s+S\d+', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s+Part\s+\d+', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s+\d+(st|nd|rd|th)\s+Season', '', name, flags=re.IGNORECASE)
    name = re.sub(r'[:\-\(\)\[\]]', ' ', name)
    name = ' '.join(name.split())
    return name.strip()

def get_rating_from_imdb(anime_name):
    """Fetch rating from IMDb with flexible search"""
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
            rating = movie.get("rating")
            votes = movie.get("votes")
            if rating:
                return round(float(rating), 2), votes if votes else "N/A"
    except Exception as e:
        print(f"IMDb error for {anime_name}: {e}")
    return None, None

def get_rating_from_kitsu(anime_name):
    """Fetch rating from Kitsu API and convert to /10 scale"""
    try:
        # Try original name
        response = requests.get(f"https://kitsu.io/api/edge/anime?filter[text]={anime_name}&page[limit]=5")
        response.raise_for_status()
        data = response.json()
        
        # If no results, try cleaned name
        if not data.get("data"):
            cleaned_name = clean_anime_name(anime_name)
            if cleaned_name != anime_name:
                print(f"Retrying Kitsu with: {cleaned_name}")
                time.sleep(1)
                response = requests.get(f"https://kitsu.io/api/edge/anime?filter[text]={cleaned_name}&page[limit]=5")
                response.raise_for_status()
                data = response.json()
        
        if data.get("data"):
            anime = data["data"][0]
            attributes = anime["attributes"]
            rating = attributes.get("averageRating")
            
            if rating:
                # Kitsu uses 0-100 scale, convert to 0-10
                converted_rating = round(float(rating) / 10, 2)
                return converted_rating, "N/A"
    except Exception as e:
        print(f"Kitsu error for {anime_name}: {e}")
    return None, None

def get_rating_from_jikan(anime_name):
    """Fetch rating from Jikan API with flexible search"""
    try:
        # Try original name
        response = requests.get(f"https://api.jikan.moe/v4/anime?q={anime_name}&limit=5")
        response.raise_for_status()
        data = response.json()
        
        # If no results, try cleaned name
        if not data.get("data"):
            cleaned_name = clean_anime_name(anime_name)
            if cleaned_name != anime_name:
                print(f"Retrying Jikan with: {cleaned_name}")
                time.sleep(1)
                response = requests.get(f"https://api.jikan.moe/v4/anime?q={cleaned_name}&limit=5")
                response.raise_for_status()
                data = response.json()
        
        if data.get("data"):
            anime = data["data"][0]
            rating = anime.get("score")
            scored_by = anime.get("scored_by")
            
            if rating:
                return round(float(rating), 2), scored_by if scored_by else "N/A"
    except Exception as e:
        print(f"Jikan error for {anime_name}: {e}")
    return None, None

def get_rating_from_anilist(anime_name):
    """Fetch rating from AniList GraphQL API"""
    query = '''
    query ($search: String) {
        Media(search: $search, type: ANIME) {
            averageScore
            popularity
        }
    }
    '''
    
    try:
        variables = {'search': anime_name}
        response = requests.post(
            'https://graphql.anilist.co',
            json={'query': query, 'variables': variables},
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        
        if data.get('data') and data['data'].get('Media'):
            media = data['data']['Media']
            score = media.get('averageScore')
            popularity = media.get('popularity', 'N/A')
            
            if score:
                # AniList uses 0-100 scale, convert to 0-10
                converted_score = round(float(score) / 10, 2)
                return converted_score, popularity
    except Exception as e:
        print(f"AniList error for {anime_name}: {e}")
    return None, None

def update_imdb_ratings():
    """
    Update IMDb ratings for anime with N/A or missing ratings
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
        current_rating = anime.get('imdb_rating', 'N/A')
        
        # Check if rating needs update
        if current_rating == 'N/A' or current_rating == '' or current_rating is None:
            print(f"Updating rating for: {anime_name}")
            
            rating, votes = None, None
            
            # Try Jikan first (fastest and most reliable for anime)
            rating, votes = get_rating_from_jikan(anime_name)
            
            if rating:
                anime['imdb_rating'] = rating
                anime['imdb_votes'] = votes
                updated_count += 1
                print(f"[SUCCESS] Jikan Rating: {rating}/10, Votes: {votes}")
            else:
                # Try AniList as second option
                time.sleep(1)
                rating, votes = get_rating_from_anilist(anime_name)
                
                if rating:
                    anime['imdb_rating'] = rating
                    anime['imdb_votes'] = votes
                    updated_count += 1
                    print(f"[SUCCESS] AniList Rating: {rating}/10, Popularity: {votes}")
                else:
                    # Try Kitsu
                    time.sleep(1)
                    rating, votes = get_rating_from_kitsu(anime_name)
                    
                    if rating:
                        anime['imdb_rating'] = rating
                        anime['imdb_votes'] = votes
                        updated_count += 1
                        print(f"[SUCCESS] Kitsu Rating: {rating}/10")
                    else:
                        # Try IMDb as last resort
                        time.sleep(1)
                        rating, votes = get_rating_from_imdb(anime_name)
                        
                        if rating:
                            anime['imdb_rating'] = rating
                            anime['imdb_votes'] = votes
                            updated_count += 1
                            print(f"[SUCCESS] IMDb Rating: {rating}/10, Votes: {votes}")
                        else:
                            print(f"[FAILED] No rating found for {anime_name}")
            
            time.sleep(2)  # Prevent API rate limiting
    
    if updated_count > 0:
        print(f"\nTotal updated: {updated_count} anime")
        print("Saving to database...")
        
        try:
            subprocess.run(['python', 'update.py'], input=json.dumps(db_data_parsed), text=True, check=True)
            print("[SUCCESS] Database updated successfully!")
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Update failed: {e}")
    else:
        print("No updates needed. All ratings are available.")

if __name__ == "__main__":
    update_imdb_ratings()