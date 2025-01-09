import requests
from imdb import IMDb
from cloud import fetch_all_cloud_folders

def upload_image_to_envs(image_url):
    """
    Upload the image URL to envs.sh and return the shortened link.
    """
    endpoint = "https://envs.sh"
    data = {'url': image_url}
    
    try:
        response = requests.post(endpoint, data=data)
        
        if response.status_code == 200:
            return response.text  # Return the shortened URL
        else:
            print(f"Error: Unable to upload image. Status code: {response.status_code}")
            return image_url  # Return original URL if failed
    except requests.RequestException as e:
        print(f"Error uploading image: {str(e)}")
        return image_url  # Return original URL if error

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

            youtube_trailer = f"https://www.youtube.com/embed/{attributes.get('youtubeVideoId')}?enablejsapi=1&wmode=opaque&autoplay=1&loop=1" if attributes.get("youtubeVideoId") else None
            
            # Upload banner and poster to envs.sh and get shortened URLs
            banner_url = upload_image_to_envs(attributes["coverImage"]["original"]) if attributes.get("coverImage") else "N/A"
            poster_url = upload_image_to_envs(attributes["posterImage"]["original"]) if attributes.get("posterImage") else "N/A"
            
            return {
                "status": attributes.get("status", "Unknown").capitalize(),
                "total_episodes": attributes.get("episodeCount", "N/A"),
                "kposter": poster_url,
                "ktrailer": youtube_trailer or "N/A",
                "banner": banner_url,
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

            # Upload poster to envs.sh and get shortened URL
            iposter_url = upload_image_to_envs(movie.get("full-size cover url", "N/A"))
            
            return {
                "imdb_rating": movie.get("rating", "N/A"),
                "imdb_votes": movie.get("votes", "N/A"),
                "iposter": iposter_url,
                "itrailer": "N/A",  # IMDb API doesn't provide trailer links by default
            }
        return None
    except Exception as e:
        return None

def fetch_list_anime(mal_id):
    """
    Fetch related anime from Jikan using the provided mal_id.
    Returns a list of related anime names.
    """
    relations_url = f"https://api.jikan.moe/v4/anime/{mal_id}/relations"
    try:
        response = requests.get(relations_url)
        response.raise_for_status()
        data = response.json()
        
        listanime = []
        for relation in data.get("data", []):
            for entry in relation.get("entry", []):
                name = entry.get("name")
                if name:
                    listanime.append(name)
        return listanime if listanime else "N/A"  # Return "N/A" if no related anime
    except requests.RequestException:
        return "N/A"

import requests

def fetch_jikan_data(anime_name):
    """
    Fetch additional anime details using the Jikan v4 API, including studios, producers,
    trailers, banners, genres, and related anime.
    """
    jikan_url = f"https://api.jikan.moe/v4/anime?q={anime_name}&limit=1"
    try:
        response = requests.get(jikan_url)
        response.raise_for_status()
        data = response.json()

        if data.get("data"):
            anime = data["data"][0]
            mal_id = anime.get("mal_id")

            # Trailer from Jikan if available
            trailer = anime.get("trailer", {}).get("url")
            if trailer and "youtube.com" in trailer:
                trailer = f"https://www.youtube.com/embed/{trailer.split('?v=')[-1]}?enablejsapi=1&wmode=opaque&autoplay=1&loop=1"
                video_id = trailer.split("/embed/")[-1].split("?")[0]
                jbanner = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
            else:
                trailer = "N/A"
                jbanner = "N/A"

            # Upload banner and poster to envs.sh if applicable
            jposter_url = upload_image_to_envs(anime["images"]["jpg"]["large_image_url"]) if anime.get("images") else "N/A"
            jbanner_url = upload_image_to_envs(jbanner) if jbanner != "N/A" else "N/A"

            # Genres and related anime
            genres = ", ".join(genre["name"] for genre in anime.get("genres", []))
            listanime = fetch_list_anime(mal_id)  # Fetch related anime using the mal_id

            # Studios and producers
            studios = ", ".join(studio["name"] for studio in anime.get("studios", []))
            producers = ", ".join(producer["name"] for producer in anime.get("producers", []))

            return {
                "type": anime.get("type", "Unknown"),
                "jname": anime.get("title_japanese", "Unknown"),
                "airing": anime.get("airing", "False"),
                "pg_rating": anime.get("rating", "N/A"),
                "jposter": jposter_url,
                "jtrailer": trailer,
                "jbanner": jbanner_url,
                "genre": genres if genres else "N/A",
                "studios": studios if studios else "N/A",
                "producers": producers if producers else "N/A",
                "listanime": listanime,  # Store the list of related anime
                "sanime": fetch_similar_anime(mal_id) or "N/A",  # Similar anime
            }
        return None
    except requests.RequestException as e:
        print(f"Error fetching Jikan data for {anime_name}: {e}")
        return None

def fetch_complete_data(folders=None):
    """
    Fetches folder data and enriches it with details from Jikan, Kitsu, and IMDb.
    """
    enriched_data = []

    # Fetch folders from the cloud if none are provided
    if folders is None:
        folders = fetch_all_cloud_folders()

    for folder in folders:
        # Ensure folder is a dictionary
        if isinstance(folder, str):
            folder = {"name": folder}

        anime_name = folder["name"]
        aid = folder.get("AID") or folder.get("aid") or "N/A"
        let = folder.get("LET", "N/A")
        cname = folder.get("CNAME", "N/A")
        cids = folder.get("CIDs", "N/A")

        # Fetch data from all sources
        imdb_data = fetch_imdb_data(anime_name) or {}
        jikan_data = fetch_jikan_data(anime_name) or {}
        kitsu_data = fetch_kitsu_data(anime_name) or {}

        # Combine banners
        banners = ", ".join(filter(None, [kitsu_data.get("banner"), jikan_data.get("jbanner")]))

        # Combine posters
        posters = ", ".join(filter(None, [kitsu_data.get("kposter"), jikan_data.get("jposter"), imdb_data.get("iposter")]))
        trailers = ", ".join(filter(None, [kitsu_data.get("ktrailer"), jikan_data.get("jtrailer")]))

        # Combine all sources' data
        enriched_data.append({
            "AID": aid,
            "LET": let,
            "NAME": anime_name,
            "jname": jikan_data.get("jname", anime_name),
            "CNAME": cname,
            "CIDs": cids,
            "type": jikan_data.get("type", "N/A"),
            "kposter": kitsu_data.get("kposter", "N/A"),
            "jposter": jikan_data.get("jposter", "N/A"),
            "airing": jikan_data.get("airing", "false"),
            "producers": jikan_data.get("producers", "N/A"),
            "studios": jikan_data.get("studios", "N/A"),
            "iposter": imdb_data.get("iposter", "N/A"),
            "ktrailer": kitsu_data.get("ktrailer", "N/A"),
            "jtrailer": jikan_data.get("jtrailer", "N/A"),
            "itrailer": imdb_data.get("itrailer", "N/A"),
            "trailers": trailers,
            "posters": posters,
            "banners": banners,
            "listanime": jikan_data.get("listanime", "N/A"),
            "synopsis": kitsu_data.get("synopsis", "No synopsis available."),
            **jikan_data,
            **kitsu_data,
            **imdb_data,
        })

        # Log the success or failure of the data fetching
        print(f"Successfully fetched data for {anime_name}")

    return enriched_data


if __name__ == "__main__":
    complete_data = fetch_complete_data()
    for anime in complete_data:
        print(
            f"AID: {anime['AID']} LET: {anime['LET']} NAME: {anime['NAME']} "
            f"CNAME: {anime['CNAME']} CID: {anime['CIDs']}\n"
            f"jname: {anime.get('jname', 'N/A')}\n"
            f"Posters: {anime.get('posters', 'N/A')}\n"
            f"Banner: {anime.get('banners', 'N/A')}\n"
            f"Trailers: {anime.get('trailers', 'N/A')}\n"
            f"Genre: {anime.get('genre', 'N/A')}\n"
            f"Type: {anime.get('type', 'N/A')}\n"
            f"Status: {anime.get('status', 'N/A')}\n"
            f"Studio: {anime.get('studios', 'N/A')}\n"
            f"Producers: {anime.get('producers', 'N/A')}\n"
            f"Airing: {anime.get('airing', 'N/A')}\n"
            f"Total Episodes: {anime.get('total_episodes', 'N/A')}\n"
            f"PG Rating: {anime.get('pg_rating', 'N/A')}\n"
            f"Similar Anime: {anime.get('sanime', 'N/A')}\n"
            f"IMDb Rating: {anime.get('imdb_rating', 'N/A')}\n"
            f"IMDb Votes: {anime.get('imdb_votes', 'N/A')}\n"
            f"Synopsis: {anime.get('synopsis', 'No synopsis available.')}\n"
            f"ListAnime: {anime.get('listanime', 'N/A')}\n"
        )
