import json
from db import update_data_in_db
import sys

def process_input_data(input_data):
    """
    Process the input data (complete anime data) into the required JSON structure.
    Allows flexibility for keys in uppercase or lowercase.
    """
    try:
        formatted_data = [
            {
                "aid": anime.get("AID") or anime.get("aid", "N/A"),
                "name": anime.get("NAME") or anime.get("name", "Unknown Anime"),
                "jname": anime.get("jname", "Dattebayo!!!"),
                "poster": anime.get("posters") or anime.get("poster", "N/A"),
                "banner": anime.get("banners") or anime.get("banner", "N/A"),
                "cname": anime.get("CNAME") or anime.get("cname", "N/A"),
                "cid": anime.get("CIDs") or anime.get("cid", "N/A"),
                "let": anime.get("LET") or anime.get("let", "N/A"),
                "trailer": anime.get("trailers") or anime.get("trailer", "N/A"),
                "genre": anime.get("genre") or anime.get("GENRE", "N/A"),
                "type": anime.get("type") or anime.get("type", "N/A"),
                "status": anime.get("status") or anime.get("STATUS", "N/A"),
                "airing": anime.get("airing") or anime.get("AIRING", "false"),
                "studio": anime.get("studio") or anime.get("studios", "N/A"),
                "producers": anime.get("producers") or anime.get("PRODUCERS", "N/A"),
                "total_episodes": anime.get("total_episodes") or anime.get("TOTAL_EPISODES", "N/A"),
                "pg_rating": anime.get("pg_rating") or anime.get("PG_RATING", "N/A"),
                "sanime": anime.get("sanime") or anime.get("SANIME", "N/A"),
                "imdb_rating": anime.get("imdb_rating") or anime.get("IMDB_RATING", "N/A"),
                "imdb_votes": anime.get("imdb_votes") or anime.get("IMDB_VOTES", "N/A"),
                "synopsis": anime.get("synopsis") or anime.get("SYNOPSIS", "No synopsis available."),
                "ranime": anime.get("listanime") or anime.get("ranime", "N/A"),
            }
            for anime in input_data
        ]
    except Exception as e:
        print(f"Error processing input data: {e}")
        return None

    return formatted_data


def update_database(formatted_data):
    """
    Update the database or GitHub repository with the formatted data.
    """
    # Ensure formatted_data is valid
    if not formatted_data:
        print("No data provided for update.")
        return

    # Convert formatted data to JSON string
    json_data = json.dumps(formatted_data, indent=4)  # Use compact format if size is an issue

    # Update the GitHub repository or database
    update_successful = update_data_in_db(json_data)

    if update_successful:
        print("✅ Done updating the data.")
    else:
        print("❌ Failed to update the data.")

def run(input_data):
    """
    Main function to process input and update database.
    """
    # Process the input data
    formatted_data = process_input_data(input_data)

    # Update the database or GitHub repository
    if formatted_data:
        update_database(formatted_data)
    else:
        print("No valid data to process.")

if __name__ == "__main__":
    try:
        # Get the input data from stdin (as passed by update_all.py)
        input_data = json.loads(sys.stdin.read())
        run(input_data)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON input: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
