import os
from groq import Groq
from openai import OpenAI

# Initialize clients (ensure the API keys are loaded by dotenv at startup)
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Define models
LLM_MODEL = "llama-3.1-8b-instant" # Up-to-date active model on Groq
EMBEDDING_MODEL = "text-embedding-3-small"

def summarize_article_for_ssc(title: str, content: str) -> str:
    """
    Uses the LLM to summarize an article down to facts relevant for SSC/UPSC exams.
    """
    prompt = (
        f"You are an expert tutor for the SSC (Staff Selection Commission) Exam in India.\n"
        f"Read the following news article and summarize it in 3-4 bullet points, focusing ONLY "
        f"on facts that are important for competitive exams (e.g., Dates, Names, Ministries, "
        f"International Treaties, Statistics).\n\n"
        f"Title: {title}\n"
        f"Content: {content}\n\n"
        f"Summary format: '- Fact 1\\n- Fact 2...'"
    )
    
    try:
        response = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=LLM_MODEL,
            temperature=0.3,
            max_tokens=300
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Summarization error: {e}")
        return "Could not generate summary."

def get_embedding(text: str) -> list[float]:
    """
    Generates a dense vector embedding using OpenAI.
    """
    try:
        response = openai_client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=[text]
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"Embedding error: {e}")
        # Return a zero vector for 1536 dim (OpenAI standard) as a safe fallback for type checking
        return [0.0] * 1536

def generate_rag_answer(question: str, context: str) -> str:
    """
    Generates an answer using retrieved context from the Vector Database.
    """
    prompt = (
        "You are an AI teaching assistant for the SSC Exam. Answer the user's question "
        "based ONLY on the provided Context. If the answer is not in the context, say "
        "'I do not have enough daily news context to answer this'. Keep the answer clear and concise.\n\n"
        f"Context:\n{context}\n\n"
        f"Question:\n{question}"
    )
    
    try:
        response = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=LLM_MODEL,
            temperature=0.5
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"QA error: {e}")
        return "I encountered an error generating the answer."
