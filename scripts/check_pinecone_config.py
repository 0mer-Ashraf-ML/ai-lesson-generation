# scripts/check_pinecone_config.py
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from app.config import settings
import requests

print(f"Pinecone API Key (first 5 chars): {settings.pinecone_api_key[:5]}...")
print(f"Pinecone Environment: {settings.pinecone_environment}")
print(f"Pinecone Index Name: {settings.pinecone_index_name}")

# Try a simple API call to list indexes
try:
    headers = {
        "Api-Key": settings.pinecone_api_key,
    }
    response = requests.get(
        f"https://controller.{settings.pinecone_environment}.pinecone.io/databases",
        headers=headers
    )
    print(f"Pinecone API Response: {response.status_code}")
    if response.status_code == 200:
        print(f"Available indexes: {response.json()}")
    else:
        print(f"Error: {response.text}")
except Exception as e:
    print(f"Error connecting to Pinecone: {str(e)}")