"""
recreate collection
"""

from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
import dotenv
import os


dotenv.load_dotenv()
QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY")
QDRANT_URL = os.environ.get("QDRANT_URL")
PROJECT_NAME = os.environ.get("PROJECT_NAME")
COLLECTION_NAME = os.environ.get("COLLECTION_NAME") or PROJECT_NAME
assert QDRANT_API_KEY and QDRANT_URL and PROJECT_NAME

def main():
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

    client.recreate_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=1536, distance=Distance.DOT),
    )
    print(f"OK, recreated COLLECTION_NAME:{COLLECTION_NAME}")

if __name__ == "__main__":
    main()
