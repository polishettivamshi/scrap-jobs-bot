"""
Run this AFTER updating GITHUB_TOKEN in .env to verify write access works.
"""
from dotenv import load_dotenv
import os, requests

load_dotenv()
token = os.getenv("GITHUB_TOKEN")
repo  = os.getenv("GITHUB_REPO")
headers = {"Authorization": f"token {token}"}

# Check scopes
r = requests.get("https://api.github.com/user", headers=headers)
scopes = r.headers.get("X-OAuth-Scopes", "")
print(f"✅ Authenticated as: {r.json().get('login')}")
print(f"✅ Token scopes: '{scopes}'")

if "repo" in scopes or "public_repo" in scopes:
    print("✅ Token has WRITE access — push_to_github will work correctly!")
else:
    print("❌ Token is missing 'repo' or 'public_repo' scope — push will fail!")
    print("   Please regenerate the token and tick the 'repo' scope checkbox.")
