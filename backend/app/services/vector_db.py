import os
from pinecone import Pinecone, ServerlessSpec
import uuid

# Initialize Pinecone
pinecone_client = None
index = None
INDEX_NAME = "current-affairs"

def init_pinecone():
    """
    Initializes the Pinecone connection and creates the index if it doesn't exist.
    Called once during startup.
    """
    global pinecone_client, index
    api_key = os.getenv("PINECONE_API_KEY")
    if not api_key:
        print("PINECONE_API_KEY is not set.")
        return

    pinecone_client = Pinecone(api_key=api_key)
    
    # Check if index exists
    existing_indexes = [idx_info["name"] for idx_info in pinecone_client.list_indexes()]
    
    if INDEX_NAME not in existing_indexes:
        print(f"Creating Pinecone index: {INDEX_NAME}...")
        pinecone_client.create_index(
            name=INDEX_NAME,
            dimension=1536, # Dimension for OpenAI text-embedding-3-small
            metric="cosine",
            spec=ServerlessSpec(
                cloud="aws",
                region="us-east-1" # Usually the free tier region
            )
        )
        print("Index created.")
    
    index = pinecone_client.Index(INDEX_NAME)

def upsert_summary(url: str, title: str, summary: str, embedding: list[float]):
    """
    Saves the embedded summary to Pinecone.
    """
    if not index:
        print("Pinecone index not initialized.")
        return
        
    doc_id = str(uuid.uuid5(uuid.NAMESPACE_URL, url)) # Unique deterministic ID based on URL
    
    index.upsert(
        vectors=[
            {
                "id": doc_id,
                "values": embedding,
                "metadata": {
                    "title": title,
                    "summary": summary,
                    "url": url
                }
            }
        ]
    )

def query_context(embedding: list[float], top_k: int = 3) -> str:
    """
    Searches Pinecone for the top_k most similar daily news summaries.
    Returns a concatenated string of the found context.
    """
    if not index:
        return ""
        
    results = index.query(
        vector=embedding,
        top_k=top_k,
        include_metadata=True
    )
    
    context_chunks = []
    for match in results.get('matches', []):
        meta = match.get('metadata', {})
        summary = meta.get('summary', '')
        title = meta.get('title', '')
        context_chunks.append(f"Source: {title}\nSummary: {summary}")
        
    return "\n\n".join(context_chunks)
