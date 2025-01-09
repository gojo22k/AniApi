import requests
import html
from collections import defaultdict
from config import PLATFORMS

def normalize_name(name):
    """
    Normalizes the anime name by converting it to lowercase and stripping leading/trailing spaces.
    """
    return name.strip().lower()

def fetch_folder_data(url, cloud_name):
    """
    Fetches folder data from a given API URL, decodes special characters in folder names,
    and returns a list of dictionaries containing folder ids and names, along with the cloud name.
    """
    try:
        response = requests.get(url)
        response.raise_for_status()

        data = response.json()
        if 'result' not in data or 'folders' not in data['result']:
            return []

        folder_data = []
        for platform in data['result']['folders']:
            if cloud_name == 'MixDrop':
                folder_name = platform.get('title', '')
                folder_id = platform.get('id', '')
            else:
                folder_name = platform.get('name', '')
                folder_id = platform.get('fld_id', '')

            decoded_name = html.unescape(folder_name)
            normalized_name = normalize_name(decoded_name)

            folder_data.append({
                'id': folder_id,
                'name': decoded_name,
                'normalized_name': normalized_name,
                'cloud_name': cloud_name
            })

        return folder_data
    except requests.RequestException:
        return []

def fetch_all_cloud_folders():
    """
    Fetch folder data from all cloud platforms, merge and sort the data by folder name,
    and generate unique AID, CID, and CNAMEs.
    """
    all_folders = defaultdict(lambda: {'CIDs': [], 'CNAMEs': []})

    for platform_name, url in PLATFORMS.items():
        platform_folders = fetch_folder_data(url, platform_name)
        if platform_folders:
            for folder in platform_folders:
                folder_name = folder['normalized_name']
                folder_id = folder['id']
                cloud_name = folder['cloud_name']

                all_folders[folder_name]['CIDs'].append(folder_id)
                all_folders[folder_name]['CNAMEs'].append(cloud_name)

    formatted_folders = []
    aid_counter = 1

    for anime_name, data in all_folders.items():
        AID = aid_counter
        aid_counter += 1

        CIDs = ', '.join(map(str, data['CIDs']))
        CNAMEs = ', '.join(data['CNAMEs'])
        formatted_anime_name = anime_name.title()
        first_letter = formatted_anime_name[0].upper() if formatted_anime_name else ''

        formatted_folders.append({
            'AID': AID,
            'LET': first_letter,
            'CIDs': CIDs,
            'name': formatted_anime_name,
            'CNAME': CNAMEs
        })

    formatted_folders.sort(key=lambda x: x['name'].lower())
    return formatted_folders
