import requests

def upload_image_to_envs(image_url):
    # Define the endpoint URL for envs.sh
    endpoint = "https://envs.sh"
    
    # Prepare the data to send in the request (upload remote URL)
    data = {'url': image_url}
    
    try:
        # Send the POST request to upload the image
        response = requests.post(endpoint, data=data)
        
        # Check if the request was successful
        if response.status_code == 200:
            # Get the shortened URL from the response
            shortened_url = response.text
            return shortened_url
        else:
            return f"Error: Unable to upload the image. Status Code: {response.status_code}"
    
    except requests.RequestException as e:
        return f"Error: {str(e)}"

if __name__ == "__main__":
    # Get the image URL from the user
    image_url = input("Enter the image URL to upload: ")
    
    # Call the function to upload the image and get the shortened URL
    result = upload_image_to_envs(image_url)
    
    # Print the result (shortened URL or error message)
    print(f"Result: {result}")
