import requests
from imdb import IMDb
from cloud import fetch_all_cloud_folders

# Function to shorten image URL using freeimage.host API
def shorten_image_url(image_url):
    """
    Shorten the image URL using freeimage.host.
    """
    try:
        response = requests.post('https://freeimage.host/api/1/upload', data={
            'image': image_url,
        })
        response.raise_for_status()
        data = response.json()
        
        if data.get('image') and data['image'].get('url'):
            return data['image']['url']
    except requests.RequestException as e:
        print(f"Error shortening image URL: {e}")
        return image_url  # Return the original URL if shortening fails


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
    Fetch additional anime details using the Jikan v4 API and include related anime, trailers, and banners.
    """
    jikan_url = f"https://api.jikan.moe/v4/anime?q={anime_name}"
    try:
        response = requests.get(jikan_url)
        response.raise_for_status()
        data = response.json()

        if data.get("data"):
            anime = data["data"][0]
            mal_id = anime.get("mal_id")

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
            }
        return None
    except requests.RequestException as e:
        return None


def fetch_complete_data():
    """
    Fetches all folder data, enriches it with details from Jikan, Kitsu, and IMDb, 
    and returns the complete dataset.
    """
    enriched_data = []
    folders = fetch_all_cloud_folders()

    for folder in folders:
        anime_name = folder["name"]
        aid = folder["AID"]
        let = folder["LET"]
        cname = folder["CNAME"]
        cids = folder["CIDs"]

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
            "CNAME": cname,
            "CIDs": cids,
            "kposter": kitsu_data.get("kposter", "N/A"),
            "jposter": jikan_data.get("jposter", "N/A"),
            "iposter": imdb_data.get("iposter", "N/A"),
            "ktrailer": kitsu_data.get("ktrailer", "N/A"),
            "jtrailer": jikan_data.get("jtrailer", "N/A"),
            "itrailer": imdb_data.get("itrailer", "N/A"),
            "trailers": trailers,
            "posters": posters,
            "banners": banners,
            "listanime": jikan_data.get("listanime", "N/A"),  # Include the list of similar anime
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
