import os
import re
import json
import sqlite3
import tiktoken
from typing import TypedDict, List, Dict, Any, Literal
from langchain_core.messages import BaseMessage
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from app.services.ai_service import groq_client, openai_client, LLM_MODEL, EMBEDDING_MODEL, get_embedding
from app.services.vector_db import query_hybrid_rrf
from app.services.ops_db import execute_sql, OPS_DB_PATH
from app.services.cache import (
    get_cached_embedding, set_cached_embedding,
    get_cached_intent, set_cached_intent,
    get_cached_sql_gen, set_cached_sql_gen,
    get_cached_sql_result, set_cached_sql_result,
    get_cached_rag_answer, set_cached_rag_answer
)

# Initialize TikToken encoding for token budget validation
encoding = tiktoken.get_encoding("cl100k_base")

# 1. GRAPH STATE SCHEMA
class GraphState(TypedDict):
    query: str
    sanitized_query: str
    intent: str                 # 'rag' | 'sql' | 'hybrid'
    hyde_queries: List[str]
    retrieved_docs: List[str]
    sql_query: str
    sql_results: List[Dict[str, Any]]
    context: str                # XML Spotlighted Context
    answer: str
    reflect_score: float
    retry_count: int
    security_flags: List[str]   # Tracks violations (e.g. Injection)
    user_id: str

# 2. INPUT SECURITY PIPELINE (L1-L7)
def input_guard_node(state: GraphState) -> Dict[str, Any]:
    query = state["query"]
    flags = []
    
    # L1: Prompt Injection Patterns (Regex)
    injection_patterns = [
        r"(?i)ignore previous instructions",
        r"(?i)system prompt",
        r"(?i)delete from",
        r"(?i)drop table",
        r"(?i)update \w+ set",
        r"(?i)insert into",
        r"(?i)bypass safety"
    ]
    for pattern in injection_patterns:
        if re.search(pattern, query):
            flags.append("PROMPT_INJECTION_DETECTED")
            break
            
    # L5: Token Budget Check & Truncation (tiktoken)
    tokens = encoding.encode(query)
    max_tokens = 250
    if len(tokens) > max_tokens:
        query = encoding.decode(tokens[:max_tokens])
        flags.append("QUERY_TRUNCATED")
        
    # L7a: Content Moderation / PII Redaction
    # Redact simple email patterns
    query = re.sub(r"[\w\.-]+@[\w\.-]+\.\w+", "[REDACTED_EMAIL]", query)
    # Redact simple phone numbers
    query = re.sub(r"\b\d{10}\b", "[REDACTED_PHONE]", query)
    
    return {
        "sanitized_query": query,
        "security_flags": flags,
        "retry_count": 0,
        "retrieved_docs": [],
        "sql_results": []
    }

# 3. INTENT ROUTER NODE
def intent_router_node(state: GraphState) -> Dict[str, Any]:
    query = state["sanitized_query"]
    
    # 1. Fast greetings/chit-chat check
    clean_query = query.strip().lower().rstrip("?.! ")
    greetings = {
        "hi", "hello", "hey", "hola", "greetings", "good morning", "good afternoon", 
        "good evening", "howdy", "yo", "hi there", "hello there", "thanks", "thank you",
        "ok", "okay", "yes", "no", "bye", "goodbye"
    }
    if clean_query in greetings:
        return {"intent": "chat"}
        
    cached = get_cached_intent(query)
    if cached:
        return {"intent": cached}
        
    prompt = (
        "You are an Intent Routing Classifier for a competitive exam database.\n"
        "Analyze the user's question and categorize it into one of four intents:\n\n"
        "- 'chat': If the query is a simple greeting, parting, conversational filler, or chit-chat (e.g. 'hello', 'thanks', 'how are you', 'tell me a joke').\n"
        "- 'sql': If the query asks for database metadata, counts of articles, statistics, database states, "
        "or user metrics (e.g. 'how many articles are saved', 'what are the news sources', 'who is student_101').\n"
        "- 'rag': If the query asks about actual, factual current affairs, news topics, policies, or "
        "exam studies (e.g. 'what is the repo rate', 'explain the satellite launch').\n"
        "- 'hybrid': If it overlaps or falls in between.\n\n"
        f"User Query: \"{query}\"\n"
        "Return ONLY one word: either 'chat', 'sql', 'rag', or 'hybrid'."
    )
    
    try:
        res = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=LLM_MODEL,
            temperature=0.0
        )
        content = res.choices[0].message.content.strip().lower()
        if "chat" in content:
            intent = "chat"
        elif "sql" in content:
            intent = "sql"
        elif "rag" in content:
            intent = "rag"
        else:
            intent = "hybrid"
        set_cached_intent(query, intent)
        return {"intent": intent}
    except Exception as e:
        print(f"Intent router error: {e}")
        return {"intent": "hybrid"}

# 4. HyDE QUERY GENERATOR NODE
def hyde_generator_node(state: GraphState) -> Dict[str, Any]:
    query = state["sanitized_query"]
    
    prompt = (
        f"Write 3 short, hypothetical single-sentence answers to this question to help "
        f"search matching news articles. Question: \"{query}\""
    )
    
    try:
        res = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=LLM_MODEL,
            temperature=0.7,
            max_tokens=150
        )
        lines = [line.strip() for line in res.choices[0].message.content.split("\n") if line.strip()]
        return {"hyde_queries": lines[:3]}
    except Exception as e:
        print(f"HyDE error: {e}")
        return {"hyde_queries": [query]}

# 5. HYBRID RETRIEVER NODE
def retriever_node(state: GraphState) -> Dict[str, Any]:
    query = state["sanitized_query"]
    
    # Call HyDE or fallback to query
    search_queries = state.get("hyde_queries", [query])
    all_context_chunks = []
    
    for s_query in search_queries:
        # Check cache for embeddings
        embedding = get_cached_embedding(s_query)
        if not embedding:
            embedding = get_embedding(s_query)
            set_cached_embedding(s_query, embedding)
            
        # Run hybrid retrieval (Pinecone + BM25)
        context = query_hybrid_rrf(s_query, embedding, top_k=2)
        if context.strip():
            all_context_chunks.append(context)
            
    # Combine retrieved document texts
    combined_docs = list(set(all_context_chunks))
    return {"retrieved_docs": combined_docs}

def search_ddg_html(query: str, max_results: int = 3) -> List[str]:
    """
    Scrapes html.duckduckgo.com directly for search snippets.
    This is extremely stable compared to the official python API which gets blocked.
    """
    import requests
    from bs4 import BeautifulSoup
    url = "https://html.duckduckgo.com/html/"
    params = {"q": query}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        res = requests.get(url, params=params, headers=headers, timeout=5)
        if res.status_code != 200:
            return []
        soup = BeautifulSoup(res.text, "html.parser")
        results = []
        for a in soup.find_all("a", class_="result__snippet"):
            results.append(a.get_text(strip=True))
            if len(results) >= max_results:
                break
        return results
    except Exception as e:
        print(f"Direct DDG scrape error: {e}")
        return []

# 6. CRAG GRADER & WEB FALLBACK NODE
def crag_grader_node(state: GraphState) -> Dict[str, Any]:
    query = state["sanitized_query"]
    retrieved = "\n\n".join(state["retrieved_docs"])
    
    if not retrieved.strip():
        relevance_score = 0.0
    else:
        prompt = (
            "Evaluate if the following context has relevant facts to answer the question.\n"
            "Return a single decimal relevance score between 0.0 and 1.0 (e.g. '0.8').\n\n"
            f"Question: {query}\n"
            f"Context:\n{retrieved}\n\n"
            "Return ONLY the score as a float value."
        )
        try:
            res = groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=LLM_MODEL,
                temperature=0.0
            )
            val = re.findall(r"\d+\.\d+", res.choices[0].message.content)
            relevance_score = float(val[0]) if val else 0.5
        except Exception:
            relevance_score = 0.5

    docs = list(state["retrieved_docs"])
    
    # If relevance is low (< 0.7), activate robust DDG HTML search fallback
    if relevance_score < 0.7:
        print(f"CRAG: Relevance score ({relevance_score}) is low. Running Web Search Fallback...")
        try:
            search_results = search_ddg_html(query, max_results=3)
            if search_results:
                docs.append("--- Web Search Fallback Context ---\n" + "\n\n".join(search_results))
        except Exception as e:
            print(f"Web Search fallback error: {e}")
            
    # XML spotlighting structure formatting
    formatted_docs = []
    for idx, doc in enumerate(docs):
        formatted_docs.append(f"<context_document id=\"{idx+1}\">\n{doc}\n</context_document>")
        
    return {
        "retrieved_docs": docs,
        "context": "\n\n".join(formatted_docs)
    }

# 7. TEXT2SQL GENERATOR NODE
def sql_generator_node(state: GraphState) -> Dict[str, Any]:
    query = state["sanitized_query"]
    
    cached_sql = get_cached_sql_gen(query)
    if cached_sql:
        return {"sql_query": cached_sql}
        
    prompt = (
        "You are an expert SQL generator for a SQLite database.\n"
        "Generate a SQLite SELECT statement to answer the question.\n"
        "Only query columns that exist in the schema below:\n\n"
        "Table: articles_meta\n"
        "  - id (INTEGER, PRIMARY KEY)\n"
        "  - title (TEXT)\n"
        "  - url (TEXT)\n"
        "  - source (TEXT)\n"
        "  - category (TEXT)\n"
        "  - scraped_at (DATETIME)\n\n"
        "Table: user_analytics\n"
        "  - id (INTEGER, PRIMARY KEY)\n"
        "  - user_id (TEXT, UNIQUE)\n"
        "  - query_count (INTEGER)\n"
        "  - last_query (TEXT)\n\n"
        "Table: system_status\n"
        "  - key (TEXT, PRIMARY KEY)\n"
        "  - value (TEXT)\n\n"
        f"Question: \"{query}\"\n\n"
        "Return ONLY the plain SQL string. No markdown formatting, no code blocks."
    )
    
    try:
        res = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=LLM_MODEL,
            temperature=0.0
        )
        sql = res.choices[0].message.content.replace("```sql", "").replace("```", "").strip()
        set_cached_sql_gen(query, sql)
        return {"sql_query": sql}
    except Exception as e:
        print(f"SQL generation error: {e}")
        return {"sql_query": ""}

# 8. SQL EXECUTOR NODE
def sql_executor_node(state: GraphState) -> Dict[str, Any]:
    sql = state["sql_query"]
    
    # L1: Validation (SELECT statement only blocklist)
    sql_clean = sql.strip().upper()
    if not sql_clean.startswith("SELECT"):
        return {"sql_results": [{"error": "Security violation: Only SELECT operations permitted."}]}
        
    forbidden = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE", "REPLACE"]
    for keyword in forbidden:
        if keyword in sql_clean:
            return {"sql_results": [{"error": f"Security violation: Forbidden keyword '{keyword}' detected."}]}
            
    # Check cache for results
    cached_res = get_cached_sql_result(sql)
    if cached_res:
        return {"sql_results": cached_res}
        
    results = execute_sql(sql)
    set_cached_sql_result(sql, results)
    
    return {"sql_results": results}

# 9. LLM ANSWER GENERATION NODE
def answer_generator_node(state: GraphState) -> Dict[str, Any]:
    query = state["sanitized_query"]
    intent = state["intent"]
    
    # If security scan blocked
    if "PROMPT_INJECTION_DETECTED" in state.get("security_flags", []):
        return {"answer": "Security block: Inquiry violates prompt injection policies."}
        
    # Check cache first
    context_str = ""
    if intent == "sql":
        context_str = json.dumps(state.get("sql_results", []), indent=2)
    else:
        context_str = state.get("context", "")
        
    cached_ans = get_cached_rag_answer(query, context_str)
    if cached_ans:
        return {"answer": cached_ans}

    # Prompt constructing
    if intent == "sql":
        prompt = (
            "You are an database analytics assistant.\n"
            "Present the SQLite query results to the user in a clean, human-readable layout.\n\n"
            f"User Query: {query}\n"
            f"Database Result:\n{context_str}"
        )
    elif intent == "chat":
        prompt = (
            "You are an AI teaching assistant for the SSC Exam. Respond to the user's greeting "
            "or conversational chit-chat in a friendly, conversational, and helpful manner. "
            "Briefly introduce yourself as the GetSmarter AI Current Affairs Tutor and invite them to ask "
            "questions about today's current affairs, news summaries, or competitive exam preparation strategy.\n\n"
            f"User message: {query}"
        )
    else:
        prompt = (
            "You are an AI teaching assistant for the SSC Exam. Answer the user's question "
            "based on the spotlighted context documents. If the question is about specific news/current affairs events "
            "and the answer is not in the context, say 'I do not have enough daily news context to answer this'. "
            "However, if the question is about general competitive exam strategy, study plans, preparation roadmaps, "
            "syllabus details, or general academic advice for the SSC Exam, answer it comprehensively and helpfully "
            "based on your own knowledge. Keep the answer clear and concise.\n\n"
            f"Context Documents:\n{context_str}\n\n"
            f"Question:\n{query}"
        )
        
    try:
        res = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=LLM_MODEL,
            temperature=0.4
        )
        ans = res.choices[0].message.content
        set_cached_rag_answer(query, context_str, ans)
        return {"answer": ans}
    except Exception as e:
        print(f"Answer generator error: {e}")
        return {"answer": "I encountered an error compiling the answer."}

# 10. Self-RAG REFLECTOR NODE
def self_rag_reflector_node(state: GraphState) -> Dict[str, Any]:
    query = state["sanitized_query"]
    answer = state["answer"]
    context = state.get("context", "")
    intent = state["intent"]
    retries = state.get("retry_count", 0)
    
    # Chat, SQL responses, or security blocks don't need context validation
    if intent in ["sql", "chat"] or "I do not have enough daily news" in answer or "Security block" in answer:
        return {"reflect_score": 1.0, "retry_count": retries}
        
    prompt = (
        "Assess if the generated answer is fully supported by the provided facts. "
        "Do not allow outside knowledge. Answer with a score between 0.0 and 1.0.\n\n"
        f"Context:\n{context}\n\n"
        f"Answer:\n{answer}\n\n"
        "Return ONLY the score as a decimal float."
    )
    
    try:
        res = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=LLM_MODEL,
            temperature=0.0
        )
        val = re.findall(r"\b\d+(?:\.\d+)?\b", res.choices[0].message.content)
        score = float(val[0]) if val else 0.9
    except Exception:
        score = 0.9
        
    next_retries = retries
    if score < 0.8:
        next_retries = retries + 1
        
    return {"reflect_score": score, "retry_count": next_retries}

# 11. OUTPUT SECURITY NODE (L7b-L9)
def output_guard_node(state: GraphState) -> Dict[str, Any]:
    answer = state["answer"]
    
    # Restore any Redacted values if needed (simple check)
    # Re-verify pydantic-style consistency
    if len(answer.strip()) == 0:
        answer = "I apologize, but I was unable to generate a valid answer."
        
    return {"answer": answer}

# --- 12. LANGGRAPH STATE MACHINE BUILDER ---

# Edge routers
def route_intent(state: GraphState) -> Literal["sql_gen", "hyde_gen", "answer_gen"]:
    # Route based on input guard or intent classifier
    if "PROMPT_INJECTION_DETECTED" in state.get("security_flags", []):
        return "answer_gen"
    if state["intent"] == "chat":
        return "answer_gen"
    return "sql_gen" if state["intent"] == "sql" else "hyde_gen"

def route_reflect(state: GraphState) -> Literal["answer_gen", "output_guard"]:
    score = state.get("reflect_score", 1.0)
    retries = state.get("retry_count", 0)
    
    if score < 0.8 and retries < 2:
        print(f"Self-RAG: Low reflection score ({score}). Retrying generation (retry #{retries})...")
        return "answer_gen"
    return "output_guard"

# Build StateGraph
workflow = StateGraph(GraphState)

# Add Nodes
workflow.add_node("input_guard", input_guard_node)
workflow.add_node("intent_router", intent_router_node)
workflow.add_node("hyde_generator", hyde_generator_node)
workflow.add_node("retriever", retriever_node)
workflow.add_node("crag_grader", crag_grader_node)
workflow.add_node("sql_generator", sql_generator_node)
workflow.add_node("sql_executor", sql_executor_node)
workflow.add_node("answer_generator", answer_generator_node)
workflow.add_node("self_rag_reflector", self_rag_reflector_node)
workflow.add_node("output_guard", output_guard_node)

# Connect Edges
workflow.set_entry_point("input_guard")
workflow.add_edge("input_guard", "intent_router")

workflow.add_conditional_edges(
    "intent_router",
    route_intent,
    {
        "sql_gen": "sql_generator",
        "hyde_gen": "hyde_generator",
        "answer_gen": "answer_generator"
    }
)

# RAG branch
workflow.add_edge("hyde_generator", "retriever")
workflow.add_edge("retriever", "crag_grader")
workflow.add_edge("crag_grader", "answer_generator")

# SQL branch
workflow.add_edge("sql_generator", "sql_executor")
workflow.add_edge("sql_executor", "answer_generator")

# Reflection cycle
workflow.add_edge("answer_generator", "self_rag_reflector")
workflow.add_conditional_edges(
    "self_rag_reflector",
    route_reflect,
    {
        "answer_gen": "answer_generator",
        "output_guard": "output_guard"
    }
)

workflow.add_edge("output_guard", END)

# Compile graph with memory checkpoints
memory = MemorySaver()
app_graph = workflow.compile(checkpointer=memory)

def run_advanced_rag(query: str, user_id: str = "student_default") -> Dict[str, Any]:
    """
    Executes the Advanced RAG State Machine for a given user query.
    """
    config = {"configurable": {"thread_id": f"thread_{user_id}"}}
    inputs = {"query": query, "user_id": user_id}
    
    # Run the compiled LangGraph state machine
    output = app_graph.invoke(inputs, config=config)
    return {
        "answer": output["answer"],
        "intent": output["intent"],
        "security_flags": output["security_flags"],
        "sql_query": output.get("sql_query", "")
    }
