import os
import json
import uuid
import re
from pinecone import Pinecone, ServerlessSpec
from rank_bm25 import BM25Okapi

# Initialize Pinecone
pinecone_client = None
index = None
INDEX_NAME = "current-affairs"

ARTICLES_JSON_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "articles_db.json")

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

def save_document_locally(url: str, title: str, summary: str):
    """
    Saves article details to a local JSON file to enable BM25 sparse search.
    """
    os.makedirs(os.path.dirname(ARTICLES_JSON_PATH), exist_ok=True)
    
    data = []
    if os.path.exists(ARTICLES_JSON_PATH):
        try:
            with open(ARTICLES_JSON_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"Error reading local articles database: {e}")
            
    # Check if article already exists by URL
    if not any(article.get("url") == url for article in data):
        data.append({
            "url": url,
            "title": title,
            "summary": summary
        })
        try:
            with open(ARTICLES_JSON_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error writing to local articles database: {e}")

def upsert_summary(url: str, title: str, summary: str, embedding: list[float]):
    """
    Saves the embedded summary to Pinecone and caches locally for BM25.
    """
    # 1. Save locally for sparse indexing
    save_document_locally(url, title, summary)

    # 2. Save to Pinecone
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

def tokenize(text: str) -> list[str]:
    """Simple alphanumeric tokenizer."""
    return re.findall(r'\w+', text.lower())

def query_context(embedding: list[float], top_k: int = 3) -> str:
    """
    Fallback standard dense search query.
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

def query_hybrid_rrf(query_text: str, query_embedding: list[float], top_k: int = 3) -> str:
    """
    Performs Hybrid Search (Dense vectors from Pinecone + Sparse keywords from local BM25)
    and merges rankings using Reciprocal Rank Fusion (RRF).
    """
    # 1. Retrieve Dense Matches from Pinecone
    dense_matches = []
    if index:
        try:
            results = index.query(
                vector=query_embedding,
                top_k=10, # Retrieve more to allow rank fusion
                include_metadata=True
            )
            for idx, match in enumerate(results.get('matches', [])):
                meta = match.get('metadata', {})
                dense_matches.append({
                    "id": match.get("id"),
                    "title": meta.get("title", ""),
                    "summary": meta.get("summary", ""),
                    "url": meta.get("url", ""),
                    "rank": idx + 1
                })
        except Exception as e:
            print(f"Dense search error: {e}")

    # 2. Retrieve Sparse Matches from local BM25
    sparse_matches = []
    articles = []
    if os.path.exists(ARTICLES_JSON_PATH):
        try:
            with open(ARTICLES_JSON_PATH, "r", encoding="utf-8") as f:
                articles = json.load(f)
        except Exception as e:
            print(f"Error loading local articles for BM25: {e}")

    if articles:
        # Build BM25 index on the fly for latest documents
        corpus_tokenized = [tokenize(art["summary"]) for art in articles]
        bm25 = BM25Okapi(corpus_tokenized)
        
        query_tokenized = tokenize(query_text)
        scores = bm25.get_scores(query_tokenized)
        
        # Rank based on BM25 scores
        ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        
        rank_counter = 1
        for idx in ranked_indices:
            if scores[idx] <= 0:  # Skip zero relevance
                continue
            art = articles[idx]
            doc_id = str(uuid.uuid5(uuid.NAMESPACE_URL, art["url"]))
            sparse_matches.append({
                "id": doc_id,
                "title": art["title"],
                "summary": art["summary"],
                "url": art["url"],
                "rank": rank_counter
            })
            rank_counter += 1

    # If no local articles exist, fall back to pure Pinecone dense search
    if not sparse_matches:
        return query_context(query_embedding, top_k)

    # 3. Reciprocal Rank Fusion (RRF)
    K = 60
    rrf_scores = {}
    doc_lookup = {}

    def track_doc(doc, rank):
        doc_id = doc["id"]
        if doc_id not in doc_lookup:
            doc_lookup[doc_id] = {
                "title": doc["title"],
                "summary": doc["summary"],
                "url": doc["url"]
            }
        if doc_id not in rrf_scores:
            rrf_scores[doc_id] = 0.0
        rrf_scores[doc_id] += 1.0 / (K + rank)

    for doc in dense_matches:
        track_doc(doc, doc["rank"])
    for doc in sparse_matches:
        track_doc(doc, doc["rank"])

    # Sort documents by RRF score
    sorted_doc_ids = sorted(rrf_scores.keys(), key=lambda d: rrf_scores[d], reverse=True)

    # 4. Extract top_k context chunks
    context_chunks = []
    for doc_id in sorted_doc_ids[:top_k]:
        doc = doc_lookup[doc_id]
        context_chunks.append(f"Source: {doc['title']}\nSummary: {doc['summary']}")

    return "\n\n".join(context_chunks)
