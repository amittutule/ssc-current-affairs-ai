import os
import hashlib
from diskcache import Cache

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

# 5-Tier Disk Cache
cache = Cache(CACHE_DIR)

# TTL values in seconds
TTL_EMBEDDING = 7 * 24 * 3600      # 7 days
TTL_INTENT = 24 * 3600             # 24 hours
TTL_SQL_GEN = 24 * 3600            # 24 hours
TTL_SQL_RESULT = 15 * 60           # 15 minutes
TTL_RAG_ANSWER = 1 * 3600          # 1 hour

def _get_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def get_cached_embedding(text: str):
    """Tier 1: Embedding Cache (7d TTL)"""
    key = f"embed:{_get_hash(text)}"
    return cache.get(key)

def set_cached_embedding(text: str, embedding: list[float]):
    key = f"embed:{_get_hash(text)}"
    cache.set(key, embedding, expire=TTL_EMBEDDING)

def get_cached_intent(query: str):
    """Tier 2: Intent Router Cache (24h TTL)"""
    key = f"intent:{_get_hash(query)}"
    return cache.get(key)

def set_cached_intent(query: str, intent: str):
    key = f"intent:{_get_hash(query)}"
    cache.set(key, intent, expire=TTL_INTENT)

def get_cached_sql_gen(query: str):
    """Tier 3: SQL Gen Cache (24h TTL)"""
    key = f"sql_gen:{_get_hash(query)}"
    return cache.get(key)

def set_cached_sql_gen(query: str, sql: str):
    key = f"sql_gen:{_get_hash(query)}"
    cache.set(key, sql, expire=TTL_SQL_GEN)

def get_cached_sql_result(sql: str):
    """Tier 4: SQL Result Cache (15m TTL)"""
    key = f"sql_res:{_get_hash(sql)}"
    return cache.get(key)

def set_cached_sql_result(sql: str, result):
    key = f"sql_res:{_get_hash(sql)}"
    cache.set(key, result, expire=TTL_SQL_RESULT)

def get_cached_rag_answer(query: str, context: str):
    """Tier 5: RAG Answer Cache (1h TTL)"""
    combined = f"{query}|||{context}"
    key = f"rag_ans:{_get_hash(combined)}"
    return cache.get(key)

def set_cached_rag_answer(query: str, context: str, answer: str):
    combined = f"{query}|||{context}"
    key = f"rag_ans:{_get_hash(combined)}"
    cache.set(key, answer, expire=TTL_RAG_ANSWER)
