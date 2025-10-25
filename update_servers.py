import json
import subprocess
import sys
from cloud import fetch_all_cloud_folders
from db import fetch_data_from_db

sys.stdout.reconfigure(line_buffering=True)

def update_server_info():
    """
    Update cname and cid fields for all anime by fetching latest cloud data
    """
    print("Fetching cloud data...")
    cloud_data = fetch_all_cloud_folders()
    
    print("Fetching database...")
    db_data, _ = fetch_data_from_db()
    
    if not cloud_data or not db_data.strip():
        print("Error: Unable to fetch data from cloud or database.")
        return
    
    try:
        db_data_parsed = json.loads(db_data)
    except json.JSONDecodeError:
        print("Error: Failed to decode database data.")
        return
    
    # Create a mapping of anime names to cloud data
    cloud_dict = {}
    for anime in cloud_data:
        name = anime['name'].lower().strip()
        cloud_dict[name] = {
            'cname': anime['CNAME'],
            'cid': anime['CIDs']
        }
    
    updated_count = 0
    
    # Update database entries
    for anime in db_data_parsed:
        anime_name = anime.get('name', '').lower().strip()
        
        if anime_name in cloud_dict:
            old_cname = anime.get('cname', 'N/A')
            old_cid = anime.get('cid', 'N/A')
            
            new_cname = cloud_dict[anime_name]['cname']
            new_cid = cloud_dict[anime_name]['cid']
            
            if old_cname != new_cname or old_cid != new_cid:
                anime['cname'] = new_cname
                anime['cid'] = new_cid
                updated_count += 1
                print(f"Updated: {anime.get('name')} - Servers: {new_cname}")
    
    if updated_count > 0:
        print(f"\nTotal updated: {updated_count} anime")
        print("Saving to database...")
        
        try:
            subprocess.run(['python', 'update.py'], input=json.dumps(db_data_parsed), text=True, check=True)
            print("✅ Database updated successfully!")
        except subprocess.CalledProcessError as e:
            print(f"❌ Update failed: {e}")
    else:
        print("No updates needed. All server information is up to date.")

if __name__ == "__main__":
    update_server_info()