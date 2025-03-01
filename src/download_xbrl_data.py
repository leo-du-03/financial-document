import os
import requests

def download_documents(xbrl_data, download_dir):
    """
    Downloads documents specified in xbrl_data to download_dir.
    
    Args:
    - xbrl_data (dict): XBRL facts
    - download_dir (str): Directory where documents will be saved.
    
    Returns:
    - str: Name of the folder where documents were downloaded (UUID4 format).
    """
    headers = {
        'User-Agent': 'FDAS'
    }
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)

    try:
        for document in xbrl_data['documents']:
            url = document['url']
            filename = document['filename']
            response = requests.get(url, headers=headers)
            response.raise_for_status()

            with open(os.path.join(download_dir, filename), 'wb') as file:
                file.write(response.content)
        
        return download_dir

    except requests.exceptions.RequestException as e:
        print(f"Error downloading documents: {e}")
        return None
