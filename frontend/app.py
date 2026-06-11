import streamlit as st
import requests
import json
import os
import time

# 1. SETUP PAGE CONFIG & THEME
st.set_page_config(
    page_title="KarmaaFlow AI - Current Affairs Tutor",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded"
)

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
SESSIONS_FILE = "chat_sessions.json"

# Inject Custom Gemini-style CSS
st.markdown("""
<style>
    /* Dark theme overrides */
    .stApp {
        background-color: #070913;
        color: #e2e8f0;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Main container width */
    .block-container {
        max-width: 55rem;
        padding-top: 3rem;
        padding-bottom: 5rem;
        margin: auto;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #0c0e1a !important;
        border-right: 1px solid #1e293b;
    }
    
    /* Custom welcome title gradient */
    .gemini-title {
        font-size: 3rem;
        font-weight: 800;
        background: linear-gradient(90deg, #60a5fa, #818cf8, #c084fc);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    
    .gemini-subtitle {
        font-size: 2.2rem;
        font-weight: 700;
        color: #64748b;
        margin-bottom: 1.5rem;
    }
    
    .gemini-desc {
        color: #94a3b8;
        font-size: 0.95rem;
        line-height: 1.6;
        margin-bottom: 2rem;
        max-width: 38rem;
    }
    
    /* Suggestion cards styling */
    .suggestion-card {
        background-color: #0c0e1a;
        border: 1px solid #1e293b;
        border-radius: 1rem;
        padding: 1.25rem;
        cursor: pointer;
        transition: all 0.3s ease;
        margin-bottom: 1rem;
        min-height: 7rem;
    }
    
    .suggestion-card:hover {
        background-color: #13172a;
        border-color: #4f46e5;
        box-shadow: 0 4px 20px rgba(79, 70, 229, 0.15);
    }
    
    .suggestion-title {
        font-weight: 600;
        color: #f1f5f9;
        font-size: 0.95rem;
        margin-bottom: 0.4rem;
    }
    
    .suggestion-desc {
        color: #64748b;
        font-size: 0.8rem;
        line-height: 1.4;
    }
    
    /* Disclaimer footer */
    .disclaimer-text {
        text-align: center;
        color: #475569;
        font-size: 0.75rem;
        margin-top: 1.5rem;
    }
</style>
""", unsafe_allow_html=True)

# 2. SESSION PERSISTENCE (SERVER-SIDE FILE STORAGE)
def load_sessions() -> dict:
    if os.path.exists(SESSIONS_FILE):
        try:
            with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_sessions(sessions: dict):
    try:
        with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(sessions, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"Error saving chat sessions: {e}")

# Initialize session state variables
if "sessions" not in st.session_state:
    st.session_state.sessions = load_sessions()

if "current_session_id" not in st.session_state:
    # Set default or create new
    if st.session_state.sessions:
        st.session_state.current_session_id = list(st.session_state.sessions.keys())[0]
    else:
        new_id = str(int(time.time()))
        st.session_state.sessions[new_id] = {
            "title": "New Chat",
            "messages": []
        }
        st.session_state.current_session_id = new_id
        save_sessions(st.session_state.sessions)

# 3. SIDEBAR NAVIGATION
st.sidebar.markdown("<h3 style='color: #818cf8; margin-bottom: 1rem;'>✨ Options</h3>", unsafe_allow_html=True)

# Create a new session button
if st.sidebar.button("➕ New Chat", use_container_width=True):
    new_id = str(int(time.time()))
    st.session_state.sessions[new_id] = {
        "title": "New Chat",
        "messages": []
    }
    st.session_state.current_session_id = new_id
    save_sessions(st.session_state.sessions)
    st.rerun()

st.sidebar.markdown("<hr style='margin: 1rem 0; border-color: #1e293b;' />", unsafe_allow_html=True)
st.sidebar.markdown("<p style='color: #475569; font-size: 0.8rem; font-weight: 600; margin-bottom: 0.5rem;'>RECENT CHATS</p>", unsafe_allow_html=True)

# List recent chat sessions
for sess_id, sess_info in list(st.session_state.sessions.items()):
    col1, col2 = st.sidebar.columns([8, 2])
    
    # Session switch button
    active_style = "color: #818cf8; font-weight: 600;" if sess_id == st.session_state.current_session_id else "color: #94a3b8;"
    if col1.button(f"💬 {sess_info['title']}", key=f"select_{sess_id}", use_container_width=True, type="secondary"):
        st.session_state.current_session_id = sess_id
        st.rerun()
        
    # Delete button
    if col2.button("🗑️", key=f"del_{sess_id}", help="Delete chat"):
        del st.session_state.sessions[sess_id]
        save_sessions(st.session_state.sessions)
        
        # If deleted active, reset
        if st.session_state.current_session_id == sess_id:
            if st.session_state.sessions:
                st.session_state.current_session_id = list(st.session_state.sessions.keys())[0]
            else:
                new_id = str(int(time.time()))
                st.session_state.sessions[new_id] = {"title": "New Chat", "messages": []}
                st.session_state.current_session_id = new_id
                save_sessions(st.session_state.sessions)
        st.rerun()

# Operations segment at the bottom of the sidebar
st.sidebar.markdown("<hr style='margin: 1.5rem 0; border-color: #1e293b;' />", unsafe_allow_html=True)

# Ingest refresh trigger
if st.sidebar.button("🔄 Refresh News", use_container_width=True):
    with st.sidebar.status("Scraping news in background..."):
        try:
            res = requests.post(f"{BACKEND_URL}/api/ingest/trigger")
            if res.status_code == 200:
                st.sidebar.success("Ingestion triggered!")
            else:
                st.sidebar.error("Failed to trigger ingestion.")
        except Exception as e:
            st.sidebar.error(f"Connection error: {e}")

# Download daily PDF
try:
    pdf_res = requests.get(f"{BACKEND_URL}/api/media/pdf", timeout=2)
    if pdf_res.status_code == 200:
        st.sidebar.download_button(
            label="📥 Download Daily PDF",
            data=pdf_res.content,
            file_name="SSC_Daily_Notes.pdf",
            mime="application/pdf",
            use_container_width=True
        )
except Exception:
    pass

# 4. CHAT INTERACTIVE LOGIC
active_session = st.session_state.sessions[st.session_state.current_session_id]
messages = active_session["messages"]

# RAG question handler
def send_chat_message(prompt_text: str):
    # Append user message
    messages.append({"role": "user", "content": prompt_text})
    
    # Update title from first prompt
    if active_session["title"] == "New Chat":
        active_session["title"] = prompt_text[:25] + "..." if len(prompt_text) > 25 else prompt_text
        
    save_sessions(st.session_state.sessions)
    st.rerun()

# Landing page if session has 0 messages
if not messages:
    st.markdown('<h1 class="gemini-title">Hello, Scholar</h1>', unsafe_allow_html=True)
    st.markdown('<h2 class="gemini-subtitle">How can I assist your prep today?</h2>', unsafe_allow_html=True)
    st.markdown(
        '<p class="gemini-desc">I am your AI Current Affairs Tutor for the SSC Exam. '
        'I retrieve the latest news facts from our Vector Database and execute SQLite queries '
        'to help you learn and evaluate your knowledge dynamically.</p>',
        unsafe_allow_html=True
    )
    
    # 2x2 Suggestion Starters Grid
    cols = st.columns(2)
    
    starters = [
        ("Summarize News", "Get a factual bullet-point summary of today's key updates.", "Summarize today's major news and current affairs."),
        ("Daily Quiz", "Evaluate your readiness with a 5-question multiple choice test.", "Generate a 5-question current affairs quiz based on the latest news."),
        ("Economic Reforms", "Explain policy changes, budget points, and reforms.", "Explain the key economic reforms and policy changes from today's news."),
        ("SSC CGL Strategy", "Get a study roadmap and tips for current affairs.", "Provide a study plan and strategy to prepare current affairs for the SSC CGL exam.")
    ]
    
    for i, (title, desc, prompt) in enumerate(starters):
        col_idx = i % 2
        with cols[col_idx]:
            # Renders card container + trigger button
            st.markdown(f"""
            <div class="suggestion-card">
                <div class="suggestion-title">✨ {title}</div>
                <div class="suggestion-desc">{desc}</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button(f"Try: \"{title}\"", key=f"starter_btn_{i}", use_container_width=True):
                send_chat_message(prompt)

else:
    # Render existing conversation logs
    for idx, msg in enumerate(messages):
        with st.chat_message(msg["role"], avatar="✨" if msg["role"] == "assistant" else None):
            st.markdown(msg["content"])
            
            # Helper actions for assistant responses
            if msg["role"] == "assistant":
                col1, col2 = st.columns([2, 8])
                
                # Audio TTS trigger
                if col1.button("🔊 Listen", key=f"tts_{idx}"):
                    with st.spinner("Synthesizing audio..."):
                        try:
                            audio_res = requests.post(f"{BACKEND_URL}/api/media/tts", json={"text": msg["content"]})
                            if audio_res.status_code == 200:
                                st.audio(audio_res.content, format="audio/mp3")
                            else:
                                st.error("Failed to generate voice output.")
                        except Exception as e:
                            st.error(f"TTS error: {e}")

# 5. CHAT INPUT
user_input = st.chat_input("Ask about today's current affairs...")

if user_input:
    # If starting message, write immediately and rerun
    messages.append({"role": "user", "content": user_input})
    
    # Update title
    if active_session["title"] == "New Chat":
        active_session["title"] = user_input[:25] + "..." if len(user_input) > 25 else user_input
        
    save_sessions(st.session_state.sessions)
    
    # Display the new message immediately
    with st.chat_message("user"):
        st.markdown(user_input)
        
    # Query backend via API
    with st.chat_message("assistant", avatar="✨"):
        response_placeholder = st.empty()
        with st.spinner("Analyzing data inputs..."):
            try:
                res = requests.post(f"{BACKEND_URL}/api/chat/", json={"question": user_input})
                if res.status_code == 200:
                    data = res.json()
                    answer = data.get("answer", "I could not compile a response.")
                else:
                    answer = "Connection error while reaching the AI."
            except Exception as e:
                answer = f"Backend communication error: {e}"
                
        # Write assistant response
        response_placeholder.markdown(answer)
        
    # Sync states
    messages.append({"role": "assistant", "content": answer})
    save_sessions(st.session_state.sessions)
    st.rerun()

st.markdown('<div class="disclaimer-text">KarmaaFlow AI can make mistakes. Verify important info.</div>', unsafe_allow_html=True)
