import os
import requests
import base64
from dotenv import load_dotenv

load_dotenv()

def push_to_github(file_path):
    token = os.getenv("GITHUB_TOKEN")
    repo = os.getenv("GITHUB_REPO")
    url = f"https://api.github.com/repos/{repo}/contents/{file_path}"
    
    headers = {"Authorization": f"token {token}"}
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        sha = response.json().get('sha')
        with open(file_path, "r") as f:
            content = f.read()
        payload = {
            "message": f"chore: update {file_path} from Render",
            "content": base64.b64encode(content.encode()).decode(),
            "sha": sha
        }
        requests.put(url, headers=headers, json=payload)