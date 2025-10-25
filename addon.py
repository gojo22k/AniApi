import json
import requests
from imdb import IMDb
from cloud import fetch_all_cloud_folders
from db import fetch_data_from_db

def shorten_image_url(image_url):
    """
    Shorten the image URL using freeimage.host API and convert extensions to .webp
    """
    api_key = "6d207e02198a847aa98d0a2a901485a5"  # Your API Key
    try:
        response = requests.post('https://freeimage.host/api/1/upload', data={
            'key': api_key,
            'action': 'upload',
            'source': image_url,
            'format': 'json'
        })
        response.raise_for_status()
        data = response.json()

        if "image" in data and "display_url" in data["image"]:
            url = data["image"]["display_url"]
            # If already a webp, return as is
            if url.lower().endswith('.webp'):
                return url
            # Find the last occurrence of a file extension
            extensions = ['md.jpg', 'md.png', 'th.jpg', 'th.png', 'jpg', 'jpeg', 'png']
            # Sort by length (longest first) to match longer patterns first
            extensions.sort(key=len, reverse=True)
            for ext in extensions:
                if url.lower().endswith(ext):
                    return url[:-(len(ext))] + 'webp'
            return url
    except requests.RequestException as e:
        pass
    return image_url  # Return original URL if shortening fails


def fetch_kitsu_data(anime_name):
    """
    Fetch additional anime details using the Kitsu API.
    """
    kitsu_url = f"https://kitsu.io/api/edge/anime?filter[text]={anime_name}"
    try:
        response = requests.get(kitsu_url)
        response.raise_for_status()
        data = response.json()

        if data.get("data"):
            anime = data["data"][0]
            attributes = anime["attributes"]

            # Shorten images
            kposter = shorten_image_url(attributes["posterImage"]["original"]) if attributes.get("posterImage") else "N/A"
            banner = shorten_image_url(attributes["coverImage"]["original"]) if attributes.get("coverImage") else "N/A"

            # Kitsu provides youtubeVideoId for trailer
            youtube_trailer = f"https://www.youtube.com/embed/{attributes.get('youtubeVideoId')}?enablejsapi=1&wmode=opaque&autoplay=1&loop=1" if attributes.get("youtubeVideoId") else None
            
            return {
                "status": attributes.get("status", "Unknown").capitalize(),
                "total_episodes": attributes.get("episodeCount", "N/A"),
                "kposter": kposter,
                "ktrailer": youtube_trailer or "N/A",
                "banner": banner,
                "synopsis": attributes.get("synopsis", "No synopsis available."),
            }
        return None
    except requests.RequestException as e:
        return None


def fetch_imdb_data(anime_name):
    """
    Fetch additional anime details using the IMDb API.
    """
    ia = IMDb()
    try:
        search_results = ia.search_movie(anime_name)
        if search_results:
            movie = search_results[0]
            ia.update(movie)

            iposter = movie.get("full-size cover url", "N/A")
            iposter = shorten_image_url(iposter) if iposter != "N/A" else "N/A"
            
            return {
                "imdb_rating": movie.get("rating", "N/A"),
                "imdb_votes": movie.get("votes", "N/A"),
                "iposter": iposter,
                "itrailer": "N/A",  # IMDb API doesn't provide trailer links by default
            }
        return None
    except Exception as e:
        return None

def fetch_similar_anime(mal_id):
    """
    Fetch similar anime using the Jikan v4 recommendations endpoint.
    """
    if not mal_id:
        return "N/A"
    recommendations_url = f"https://api.jikan.moe/v4/anime/{mal_id}/recommendations"
    try:
        response = requests.get(recommendations_url)
        response.raise_for_status()
        data = response.json()

        if data.get("data"):
            return ", ".join([rec["entry"]["title"] for rec in data["data"]])  # Fetch top 5 recommendations
        return "No similar anime found."
    except requests.RequestException as e:
        return "Error fetching similar anime."

def fetch_list_anime(mal_id):
    """
    Fetch related anime names from Jikan relations endpoint.
    """
    url = f"https://api.jikan.moe/v4/anime/{mal_id}/relations"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        # Extract only the anime names
        listanime = [entry.get("name", "Unknown") for relation in data.get("data", []) for entry in relation.get("entry", [])]

        return listanime
    except requests.RequestException:
        return []


def fetch_jikan_data(anime_name):
    """
    Fetch additional anime details using the Jikan v4 API and include related anime, trailers, banners, studios, and producers.
    """
    jikan_url = f"https://api.jikan.moe/v4/anime?q={anime_name}"
    try:
        response = requests.get(jikan_url)
        response.raise_for_status()
        data = response.json()

        if data.get("data"):
            anime = data["data"][0]
            mal_id = anime.get("mal_id")

            # Extract studios and producers
            studios = ", ".join(studio["name"] for studio in anime.get("studios", [])) if anime.get("studios") else "N/A"
            producers = ", ".join(producer["name"] for producer in anime.get("producers", [])) if anime.get("producers") else "N/A"

            # Get Japanese title and airing status
            jname = anime.get("title_japanese", "N/A")
            airing = str(anime.get("airing", False)).lower()
            
            # Fetch trailer from Jikan if available
            trailer = anime.get("trailer", {}).get("url")
            if trailer and "youtube.com" in trailer:
                trailer = f"https://www.youtube.com/embed/{trailer.split('?v=')[-1]}?enablejsapi=1&wmode=opaque&autoplay=1&loop=1"
                video_id = trailer.split("/embed/")[-1].split("?")[0]
                jbanner = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
                jbanner = shorten_image_url(jbanner)  # Shorten banner URL
            else:
                trailer = "N/A"
                jbanner = "N/A"

            # Shorten the poster
            jposter = shorten_image_url(anime["images"]["jpg"]["large_image_url"]) if anime.get("images") else "N/A"

            # Fetch genres and related anime
            genres = ", ".join(genre["name"] for genre in anime.get("genres", []))
            listanime = fetch_list_anime(mal_id)  # Fetch related series for the anime
            similar_anime = fetch_similar_anime(mal_id)

            return {
                "type": anime.get("type", "Unknown"),
                "pg_rating": anime.get("rating", "N/A"),
                "jposter": jposter,
                "jtrailer": trailer,
                "jbanner": jbanner,
                "genre": genres if genres else "N/A",
                "listanime": listanime,  # Store the list of related series
                "sanime": similar_anime or "N/A",
                "studio": studios,  # ✅ Added studio
                "producers": producers or "Aniflix",  # ✅ Added producers
                "jname": jname,
                "airing": airing
            }
        return None
    except requests.RequestException as e:
        return None

import json
from db import fetch_data_from_db

import json

# Global variable to store AID
getAid = None  # Will be initialized from the database

def fetch_last_aid_from_db():
    """Fetch the last AID from the database once and store it in `getAid`."""
    global getAid  # Use the global variable
    
    if getAid is not None:
        return getAid  # Use the stored AID if already initialized

    # Fetch data from the database
    db_data, _ = fetch_data_from_db()
    try:
        existing_db_data = json.loads(db_data)  # Parse JSON data
    except json.JSONDecodeError:
        getAid = 0  # If database is invalid, start from 0
        return getAid

    # Extract the highest AID from the database
    existing_aids = {anime.get('aid', 0) for anime in existing_db_data if isinstance(anime.get('aid', 0), int)}
    getAid = max(existing_aids, default=0)  # Set global AID
    return getAid


def fetch_complete_data(filtered_data=None):
    """
    Fetches all folder data or uses the provided filtered data and assigns unique AIDs.
    Uses a global variable (`getAid`) to track AID without updating the database repeatedly.
    """
    global getAid  # Use global AID variable

    enriched_data = []
    folders = filtered_data if filtered_data is not None else fetch_all_cloud_folders()

    # Initialize `getAid` from the database only once
    if getAid is None:
        getAid = fetch_last_aid_from_db()

    # Iterate over folders and assign a unique AID for each anime
    for folder in folders:
        anime_name = folder["name"]
        let = folder["LET"]
        cname = folder["CNAME"]
        cids = folder["CIDs"]

        # Increment AID locally
        getAid += 1  

        # Fetch data from all sources
        imdb_data = fetch_imdb_data(anime_name) or {}
        jikan_data = fetch_jikan_data(anime_name) or {}
        kitsu_data = fetch_kitsu_data(anime_name) or {}

        # Combine banners, posters, and trailers
        banners = ", ".join(filter(None, [kitsu_data.get("banner"), jikan_data.get("jbanner")]))
        posters = ", ".join(filter(None, [kitsu_data.get("kposter"), jikan_data.get("jposter"), imdb_data.get("iposter")]))
        trailers = ", ".join(filter(None, [kitsu_data.get("ktrailer"), jikan_data.get("jtrailer")]))

        # Add new anime with updated AID
        enriched_data.append({
            "AID": getAid,  # Now correctly incremented
            "LET": let,
            "NAME": anime_name,
            "CNAME": cname,
            "CIDs": cids,
            "posters": posters,
            "banners": banners,
            "trailers": trailers,
            "listanime": jikan_data.get("listanime", "N/A"),
            "synopsis": kitsu_data.get("synopsis", "No synopsis available."),
            **jikan_data,
            **kitsu_data,
            **imdb_data,
        })
        # Logging
        print(f"Successfully fetched data for {anime_name} with new AID: {getAid}")

    return enriched_data


if __name__ == "__main__":
    complete_data = fetch_complete_data()
    for anime in complete_data:
        print(
            f"AID: {anime['AID']} LET: {anime['LET']} NAME: {anime['NAME']} "
            f"CNAME: {anime['CNAME']} CID: {anime['CIDs']}\n"
            f"Posters: {anime.get('posters', 'N/A')}\n"
            f"Trailers: {anime.get('trailers', 'N/A')}\n"
            f"Genre: {anime.get('genre', 'N/A')}\n"
            f"Status: {anime.get('status', 'N/A')}\n"
            f"Total Episodes: {anime.get('total_episodes', 'N/A')}\n"
            f"PG Rating: {anime.get('pg_rating', 'N/A')}\n"
            f"Similar Anime: {anime.get('sanime', 'N/A')}\n"
            f"IMDb Rating: {anime.get('imdb_rating', 'N/A')}\n"
            f"IMDb Votes: {anime.get('imdb_votes', 'N/A')}\n"
            f"Synopsis: {anime.get('synopsis', 'No synopsis available.')}\n"
            f"ListAnime: {anime.get('listanime', 'N/A')}\n"
        )
