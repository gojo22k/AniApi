from addon import fetch_complete_data
import json
import subprocess
import sys
sys.stdout.reconfigure(line_buffering=True)

def fetch_and_update():
    """
    Fetch the complete anime data and forward it to update.py for processing and updating the database.
    """
    try:
        # Step 1: Fetch the complete anime data
        complete_data = fetch_complete_data()

        if not complete_data:
            print("No data fetched. Exiting the update process.")
            return

        # Debugging: Log the fetched data size
        print(f"Fetched {len(complete_data)} records.")

        # Step 2: Prepare the data to be sent to update.py
        data_to_send = json.dumps(complete_data)

        # Step 3: Run update.py with the fetched data as input
        result = subprocess.run(
            ['python', 'update.py'],
            input=data_to_send,
            text=True,
            capture_output=True,
        )

        # Step 4: Process the result
        if result.returncode == 0:
            print("Update completed successfully.")
            print(f"Output from update.py: {result.stdout.strip()}")
        else:
            print(f"Update failed with error code {result.returncode}.")
            print(f"Error details: {result.stderr.strip()}")

    except json.JSONDecodeError as e:
        print(f"JSON error during processing: {e}")
    except subprocess.SubprocessError as e:
        print(f"Error running update.py: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    fetch_and_update()
