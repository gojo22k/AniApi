import base64
import requests
import os
import json
from config import *

def fetch_data_from_db():
    """
    Fetch the raw data from the anime_data.txt file in the GitHub repository.
    """
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/contents/{PATH}"
    headers = {
        "Authorization": f"token {GIT_TOKEN}"
    }

    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        # Check if the response is a list or a dictionary
        data = response.json()

        if isinstance(data, list):
            print("Error: Unexpected response format. List received instead of dictionary.")
            return None, None
        
        # Now handle the expected dictionary format
        file_content = data.get('content', None)
        if not file_content:
            print("Error: No content found in the file.")
            return None, None
        
        try:
            # Decode base64 content into the original string
            decoded_content = base64.b64decode(file_content).decode("utf-8")
        except Exception as e:
            print(f"Error decoding base64 content: {e}")
            return None, None

        sha = data.get('sha', None)  # Safely get the sha
        return decoded_content, sha  # Return decoded content and sha
    else:
        print("Error fetching data from GitHub:", response.status_code)
        return None, None

def update_data_in_db(new_json_data):
    """
    Overwrite the existing content of the anime_data.txt file in the GitHub repository with new JSON data.
    """
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/contents/{PATH}"
    headers = {
        "Authorization": f"token {GIT_TOKEN}"
    }

    # Step 1: Fetch the current file metadata (to get the 'sha')
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        sha = data.get('sha', None)  # Fetch the current sha

    else:
        print("Error fetching the existing file:", response.json())
        return False

    # Step 2: Validate and sort the new data
    try:
        anime_list = json.loads(new_json_data)  # Ensure new data is valid JSON
        if not isinstance(anime_list, list):
            print("Error: Data should be a list of anime entries.")
            return False
        # Sort the data by `aid` in ascending order
        anime_list_sorted = sorted(anime_list, key=lambda x: x.get('aid', 0))
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON data: {e}")
        return False

    # Step 3: Convert the sorted list back to JSON string
    sorted_json_data = json.dumps(anime_list_sorted, indent=4)

    # Step 4: Base64 encode the sorted content
    encoded_data = base64.b64encode(sorted_json_data.encode("utf-8")).decode("utf-8")

    # Step 5: Prepare the payload to overwrite the file
    update_payload = {
        "message": "♦️ DONE UPDATING ♦️",
        "sha": sha,  # Use the current sha to update the file
        "content": encoded_data  # Base64 encoded sorted content
    }

    # Step 6: Send the PUT request to update the file
    response = requests.put(url, headers=headers, json=update_payload)

    if response.status_code == 200:
        print("Successfully Updated the Database.")
        return True
    else:
        print("Error updating the Database:", response.json())
        return False
