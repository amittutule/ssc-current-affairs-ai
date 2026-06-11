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

# Custom KarmaaFlow Gradient "K" Logo (Base64 SVG)
ASSISTANT_AVATAR = "data:image/svg+xml;base64,PHN2ZyB2aWV3Qm94PSIwIDAgMjQgMjQiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PGNpcmNsZSBjeD0iMTIiIGN5PSIxMiIgcj0iMTAiIGZpbGw9InVybCgja2YtZ3JhZCkiLz48cGF0aCBkPSJNOCA3VjE3TTggMTJIMTAuNUwxNC41IDdNMTAuNSAxMkwxNSAxNyIgc3Ryb2tlPSJ3aGl0ZSIgc3Ryb2tlLXdpZHRoPSIyLjUiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCIvPjxkZWZzPjxsaW5lYXJHcmFkaWVudCBpZD0ia2YtZ3JhZCIgeDE9IjAiIHkxPSIwIiB4Mj0iMjQiIHkyPSIyNCIgZ3JhZGllbnRVbml0cz0idXNlclNwYWNlT25Vc2UiPjxzdG9wIG9mZnNldD0iMCUiIHN0b3AtY29sb3I9IiM2MzY2ZjEiLz48c3RvcCBvZmZzZXQ9IjEwMCUiIHN0b3AtY29sb3I9IiMwNmI2ZDQiLz48L2xpbmVhckdyYWRpZW50PjwvZGVmcz48L3N2Zz4="
USER_AVATAR = "data:image/svg+xml;base64,PHN2ZyB2aWV3Qm94PSIwIDAgMjQgMjQiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PGNpcmNsZSBjeD0iMTIiIGN5PSI4IiByPSI0IiBmaWxsPSIjODA4NjhiIi8+PHBhdGggZD0iTTIwIDE5QzIwIDE1LjY4NjMgMTYuNDE4MyAxMyAxMiAxM0M3LjU4MTcyIDEzIDQgMTUuNjg2MyA0IDE5IiBzdHJva2U9IiM4MDg2OGIiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIi8+PC9zdmc+"

# Inject Custom-branded Premium Layout Overrides
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap');
    
    /* Global font and background */
    html, body, [class*="css"], .stApp {
        font-family: 'Outfit', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
        background-color: #131314 !important;
        color: #e3e3e3 !important;
    }
    
    /* Style header and keep sidebar toggle button visible, but hide deploy and main menu */
    header[data-testid="stHeader"] {
        background-color: transparent !important;
    }
    [data-testid="stHeader"] [data-testid="stHeaderActionElements"] {
        display: none !important;
    }
    #MainMenu {
        display: none !important;
    }
    footer {visibility: hidden;}
    
    /* Center main content and give it modern layout width */
    .block-container {
        max-width: 820px !important;
        padding-top: 1rem !important;
        padding-bottom: 7rem !important;
        margin: auto !important;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #1e1f20 !important;
        border-right: 1px solid #2d2f31 !important;
    }
    
    /* Welcome Title layout */
    .kf-welcome-title {
        font-size: 3.5rem !important;
        font-weight: 700 !important;
        background: linear-gradient(135deg, #6366f1, #8b5cf6, #06b6d4) !important;
        -webkit-background-clip: text !important;
        -webkit-text-fill-color: transparent !important;
        margin-bottom: 0.1rem !important;
        margin-top: 3.5rem !important;
        letter-spacing: -0.02em !important;
        line-height: 1.2 !important;
    }
    
    .kf-welcome-subtitle {
        font-size: 2.6rem !important;
        font-weight: 600 !important;
        color: #444746 !important;
        margin-bottom: 2.5rem !important;
        letter-spacing: -0.01em !important;
        line-height: 1.2 !important;
    }
    
    .kf-desc {
        color: #80868b !important;
        font-size: 0.95rem !important;
        line-height: 1.6 !important;
        margin-bottom: 3.5rem !important;
        max-width: 600px !important;
    }
    
    /* Custom Suggestion Cards (Buttons inside columns in main body) */
    .block-container div[data-testid="column"] button {
        background-color: #1e1f20 !important;
        border: none !important;
        color: #e3e3e3 !important;
        border-radius: 16px !important;
        padding: 16px !important;
        height: 140px !important;
        text-align: left !important;
        white-space: pre-line !important;
        word-wrap: break-word !important;
        display: flex !important;
        flex-direction: column !important;
        justify-content: space-between !important;
        transition: all 0.25s ease !important;
        font-size: 0.85rem !important;
        font-weight: 500 !important;
        box-shadow: none !important;
        line-height: 1.45 !important;
        width: 100% !important;
    }
    
    .block-container div[data-testid="column"] button:hover {
        background-color: #2e3032 !important;
        transform: translateY(-2px) !important;
        border-left: 3px solid #6366f1 !important;
    }
    
    /* Hide default borders in layout columns */
    [data-testid="column"] {
        border: none !important;
    }
    
    /* Chat Input design */
    div[data-testid="stChatInput"] {
        background-color: #1e1f20 !important;
        border: 1px solid #2e3032 !important;
        border-radius: 32px !important;
        padding: 6px 16px !important;
        box-shadow: 0 4px 24px rgba(0, 0, 0, 0.4) !important;
        max-width: 768px !important;
        margin: 0 auto !important;
        transition: border-color 0.2s ease !important;
    }
    
    div[data-testid="stChatInput"]:focus-within {
        border-color: #6366f1 !important;
    }
    
    div[data-testid="stChatInput"] textarea {
        background-color: transparent !important;
        color: #e3e3e3 !important;
        border: none !important;
        font-size: 1.05rem !important;
        line-height: 1.45 !important;
        caret-color: #6366f1 !important;
    }
    
    /* Message timeline borders & backgrounds */
    div[data-testid="stChatMessage"] {
        background-color: transparent !important;
        border: none !important;
        padding: 1.5rem 0 !important;
        border-bottom: 1px solid #2e3032 !important;
    }
    
    div[data-testid="stChatMessage"] div.stMarkdown {
        color: #e3e3e3 !important;
        font-size: 1rem !important;
        line-height: 1.65 !important;
    }
    
    /* Custom TTS Pill button (Buttons inside chat messages) */
    div[data-testid="stChatMessage"] button {
        background-color: #1e1f20 !important;
        border: 1px solid #2d2f31 !important;
        color: #c4c7c5 !important;
        border-radius: 20px !important;
        padding: 4px 14px !important;
        font-size: 0.78rem !important;
        font-weight: 500 !important;
        width: auto !important;
        margin-top: 10px !important;
        display: inline-flex !important;
        align-items: center !important;
        gap: 6px !important;
        box-shadow: none !important;
        transition: all 0.2s ease !important;
    }
    
    div[data-testid="stChatMessage"] button:hover {
        background-color: #2e3032 !important;
        color: #e3e3e3 !important;
        border-color: #6366f1 !important;
    }
    
    /* Sidebar default button styling */
    [data-testid="stSidebar"] button {
        background-color: #1a1a1c !important;
        border: 1px solid #2d2f31 !important;
        color: #e3e3e3 !important;
        border-radius: 24px !important;
        padding: 10px 18px !important;
        font-weight: 500 !important;
        font-size: 0.9rem !important;
        display: flex !important;
        align-items: center !important;
        justify-content: flex-start !important;
        gap: 8px !important;
        text-align: left !important;
        width: 100% !important;
        box-shadow: none !important;
        transition: all 0.2s ease !important;
    }
    
    [data-testid="stSidebar"] button:hover {
        background-color: #2b2c2e !important;
        border-color: #6366f1 !important;
    }
    
    /* Recent chat list items (Buttons in the first column of sidebar rows) */
    [data-testid="stSidebar"] div[data-testid="column"]:first-child button {
        background-color: transparent !important;
        border: none !important;
        color: #c4c7c5 !important;
        text-align: left !important;
        padding: 8px 12px !important;
        border-radius: 8px !important;
        font-size: 0.85rem !important;
        display: block !important;
        width: 100% !important;
        text-overflow: ellipsis !important;
        overflow: hidden !important;
        white-space: nowrap !important;
        font-weight: 400 !important;
        box-shadow: none !important;
    }
    
    [data-testid="stSidebar"] div[data-testid="column"]:first-child button:hover {
        background-color: #2d2f31 !important;
        color: #e3e3e3 !important;
    }
    
    /* active chat highlight */
    [data-testid="stSidebar"] .recent-chat-item-active button {
        background-color: #2d2f31 !important;
        color: #e3e3e3 !important;
        font-weight: 600 !important;
        border-left: 2px solid #6366f1 !important;
    }
    
    /* Trash delete icon button (Buttons in the second column of sidebar rows) */
    [data-testid="stSidebar"] div[data-testid="column"]:last-child button {
        background-color: transparent !important;
        border: none !important;
        color: #80868b !important;
        border-radius: 50% !important;
        padding: 4px !important;
        width: 32px !important;
        height: 32px !important;
        min-width: 32px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        font-size: 0.85rem !important;
        box-shadow: none !important;
    }
    
    [data-testid="stSidebar"] div[data-testid="column"]:last-child button:hover {
        background-color: #2d2f31 !important;
        color: #ea4335 !important;
    }
    
    /* Sidebar utility buttons (Refresh, Download) */
    [data-testid="stSidebar"] .sidebar-utility-button button {
        background-color: transparent !important;
        border: 1px solid #2d2f31 !important;
        color: #c4c7c5 !important;
        border-radius: 20px !important;
        padding: 8px 16px !important;
        font-size: 0.85rem !important;
        font-weight: 500 !important;
        width: 100% !important;
        box-shadow: none !important;
        transition: all 0.2s ease !important;
    }
    
    [data-testid="stSidebar"] .sidebar-utility-button button:hover {
        background-color: #2d2f31 !important;
        border-color: #6366f1 !important;
        color: #e3e3e3 !important;
    }
    
    /* Info box in sidebar */
    .sidebar-info-box {
        background-color: #1a1a1c !important;
        border: 1px solid #2d2f31 !important;
        border-radius: 16px !important;
        padding: 14px !important;
        margin-top: 20px !important;
    }
    
    .info-title {
        font-weight: 600 !important;
        color: #6366f1 !important;
        font-size: 0.85rem !important;
        margin-bottom: 6px !important;
    }
    
    .info-text {
        color: #c4c7c5 !important;
        font-size: 0.78rem !important;
        line-height: 1.45 !important;
    }
    
    /* Disclaimer and footnotes */
    .disclaimer-text {
        text-align: center !important;
        color: #444746 !important;
        font-size: 0.75rem !important;
        margin-top: 3rem !important;
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
st.sidebar.markdown("<h2 style='color: #e3e3e3; font-size: 1.3rem; font-weight: 700; margin-bottom: 1.5rem;'>✨ KarmaaFlow AI</h2>", unsafe_allow_html=True)

# Create a new session button
st.sidebar.markdown('<div class="new-chat-btn-container">', unsafe_allow_html=True)
if st.sidebar.button("➕ New Chat", use_container_width=True):
    new_id = str(int(time.time()))
    st.session_state.sessions[new_id] = {
        "title": "New Chat",
        "messages": []
    }
    st.session_state.current_session_id = new_id
    save_sessions(st.session_state.sessions)
    st.rerun()
st.sidebar.markdown('</div>', unsafe_allow_html=True)

# Voice Search STT Widget
st.sidebar.markdown("<p style='color: #80868b; font-size: 0.75rem; font-weight: 600; margin-top: 1.25rem; margin-bottom: 0.5rem; letter-spacing: 0.05em;'>VOICE ASSIST</p>", unsafe_allow_html=True)
with st.sidebar:
    st.components.v1.html("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap');

    .mic-container {
        display: flex;
        align-items: center;
        background: #1a1a1c;
        border: 1px solid #2d2f31;
        border-radius: 20px;
        padding: 8px 14px;
        cursor: pointer;
        transition: all 0.2s ease;
        width: 100%;
        box-sizing: border-box;
    }
    .mic-container:hover {
        background: #2b2c2e;
        border-color: #6366f1;
    }
    .mic-container.listening {
        background: #ef4444;
        border-color: #ef4444;
        animation: pulse 1.5s infinite;
    }
    .mic-icon {
        font-size: 16px;
        margin-right: 8px;
        color: #e3e3e3;
    }
    .mic-text {
        color: #c4c7c5;
        font-size: 0.85rem;
        font-family: 'Outfit', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        font-weight: 500;
        user-select: none;
    }
    .mic-container.listening .mic-text {
        color: white;
    }
    @keyframes pulse {
        0% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.4); }
        70% { box-shadow: 0 0 0 8px rgba(239, 68, 68, 0); }
        100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
    }
</style>

<div class="mic-container" id="mic-container" onclick="toggleListening()">
    <span class="mic-icon" id="mic-icon">🎙️</span>
    <span class="mic-text" id="mic-text">Voice Input</span>
</div>

<script>
let recognition = null;
let isListening = false;

function initSpeech() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        return;
    }
    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    
    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        try {
            const textareas = window.parent.document.querySelectorAll('div[data-testid="stChatInput"] textarea');
            if (textareas.length > 0) {
                const ta = textareas[0];
                
                // Force React state synchronization
                const nativeValueSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value").set;
                nativeValueSetter.call(ta, transcript);
                ta.dispatchEvent(new Event('input', { bubbles: true }));
                ta.focus();
                
                // Wait 100ms for React state sync, then trigger the submit click
                setTimeout(() => {
                    const sendBtns = window.parent.document.querySelectorAll('div[data-testid="stChatInput"] button');
                    if (sendBtns.length > 0) {
                        sendBtns[0].click();
                    }
                }, 100);
            }
        } catch (e) {
            console.error("Failed to write and submit transcript", e);
        }
        stopListening();
    };
    
    recognition.onerror = (e) => {
        console.error(e);
        stopListening();
    };
    
    recognition.onend = () => {
        stopListening();
    };
}

function toggleListening() {
    if (!recognition) {
        initSpeech();
    }
    if (!recognition) {
        alert("Voice recognition is not supported in this browser. Please use Chrome or Safari.");
        return;
    }
    
    const container = document.getElementById("mic-container");
    const icon = document.getElementById("mic-icon");
    const text = document.getElementById("mic-text");
    
    if (isListening) {
        recognition.stop();
        stopListening();
    } else {
        try {
            recognition.start();
            isListening = true;
            container.classList.add("listening");
            icon.innerText = "🛑";
            text.innerText = "Listening...";
        } catch (e) {
            console.error(e);
        }
    }
}

function stopListening() {
    isListening = false;
    const container = document.getElementById("mic-container");
    const icon = document.getElementById("mic-icon");
    const text = document.getElementById("mic-text");
    if (container) container.classList.remove("listening");
    if (icon) icon.innerText = "🎙️";
    if (text) text.innerText = "Voice Input";
}
</script>
""", height=44)

st.sidebar.markdown("<hr style='margin: 1.25rem 0; border-color: #2d2f31;' />", unsafe_allow_html=True)
st.sidebar.markdown("<p style='color: #80868b; font-size: 0.75rem; font-weight: 600; margin-bottom: 0.75rem; letter-spacing: 0.05em;'>RECENT CHATS</p>", unsafe_allow_html=True)

# List recent chat sessions
for sess_id, sess_info in list(st.session_state.sessions.items()):
    col1, col2 = st.sidebar.columns([8, 2])
    
    # Active state check
    is_active = (sess_id == st.session_state.current_session_id)
    active_class = "recent-chat-item-active" if is_active else "recent-chat-item"
    btn_label = f"💬 {sess_info['title']}"
    
    with col1:
        st.markdown(f'<div class="{active_class}">', unsafe_allow_html=True)
        if st.button(btn_label, key=f"select_{sess_id}", use_container_width=True):
            st.session_state.current_session_id = sess_id
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col2:
        st.markdown('<div class="recent-chat-delete">', unsafe_allow_html=True)
        if st.button("🗑️", key=f"del_{sess_id}", help="Delete chat"):
            del st.session_state.sessions[sess_id]
            save_sessions(st.session_state.sessions)
            
            if st.session_state.current_session_id == sess_id:
                if st.session_state.sessions:
                    st.session_state.current_session_id = list(st.session_state.sessions.keys())[0]
                else:
                    new_id = str(int(time.time()))
                    st.session_state.sessions[new_id] = {"title": "New Chat", "messages": []}
                    st.session_state.current_session_id = new_id
                    save_sessions(st.session_state.sessions)
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# Controls at the bottom
st.sidebar.markdown("<hr style='margin: 1.5rem 0; border-color: #2d2f31;' />", unsafe_allow_html=True)

# Ingest refresh trigger
st.sidebar.markdown('<div class="sidebar-utility-button">', unsafe_allow_html=True)
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
st.sidebar.markdown('</div>', unsafe_allow_html=True)

# Download daily PDF
try:
    pdf_res = requests.get(f"{BACKEND_URL}/api/media/pdf", timeout=2)
    if pdf_res.status_code == 200:
        st.sidebar.markdown('<div class="sidebar-utility-button" style="margin-top: 10px;">', unsafe_allow_html=True)
        st.sidebar.download_button(
            label="📥 Download Daily PDF",
            data=pdf_res.content,
            file_name="SSC_Daily_Notes.pdf",
            mime="application/pdf",
            use_container_width=True
        )
        st.sidebar.markdown('</div>', unsafe_allow_html=True)
except Exception:
    pass

# Helper info box to explain the "No context" behavior
st.sidebar.markdown("""
<div class="sidebar-info-box">
    <div class="info-title">💡 Ingest Tip</div>
    <div class="info-text">
        If the AI reports missing news context, click <b>Refresh News</b> to fetch today's current affairs and sync the database!
    </div>
</div>
""", unsafe_allow_html=True)


# 4. CHAT INTERACTIVE LOGIC
active_session = st.session_state.sessions[st.session_state.current_session_id]
messages = active_session["messages"]

def send_chat_message(prompt_text: str):
    messages.append({"role": "user", "content": prompt_text})
    if active_session["title"] == "New Chat":
        active_session["title"] = prompt_text[:25] + "..." if len(prompt_text) > 25 else prompt_text
    save_sessions(st.session_state.sessions)
    st.rerun()

# Landing page if session has 0 messages
if not messages:
    st.markdown('<h1 class="kf-welcome-title">Hello, Scholar</h1>', unsafe_allow_html=True)
    st.markdown('<h2 class="kf-welcome-subtitle">How can I assist your prep today?</h2>', unsafe_allow_html=True)
    st.markdown(
        '<p class="kf-desc">I am your AI Current Affairs Tutor for the SSC Exam. '
        'I retrieve the latest news facts from our Vector Database and execute SQLite queries '
        'to help you learn and evaluate your knowledge dynamically.</p>',
        unsafe_allow_html=True
    )
    
    # 4-column Suggestion Starters Grid
    cols = st.columns(4)
    
    starters = [
        ("Summarize News", "Get a factual bullet-point summary of today's key updates.", "Summarize today's major news and current affairs."),
        ("Daily Quiz", "Evaluate your readiness with a 5-question multiple choice test.", "Generate a 5-question current affairs quiz based on the latest news."),
        ("Economic Reforms", "Explain policy changes, budget points, and reforms.", "Explain the key economic reforms and policy changes from today's news."),
        ("SSC CGL Strategy", "Get a study roadmap and preparation tips.", "Provide a study plan and strategy to prepare current affairs for the SSC CGL exam.")
    ]
    
    for i, (title, desc, prompt) in enumerate(starters):
        with cols[i]:
            if st.button(f"✨ {title}\n{desc}", key=f"starter_{i}", use_container_width=True):
                send_chat_message(prompt)

else:
    # Render existing conversation logs
    for idx, msg in enumerate(messages):
        avatar_img = ASSISTANT_AVATAR if msg["role"] == "assistant" else USER_AVATAR
        with st.chat_message(msg["role"], avatar=avatar_img):
            st.markdown(msg["content"])
            
            # Helper actions for assistant responses
            if msg["role"] == "assistant":
                # Audio TTS trigger
                if st.button("🔊 Listen", key=f"tts_{idx}"):
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
    
    if active_session["title"] == "New Chat":
        active_session["title"] = user_input[:25] + "..." if len(user_input) > 25 else user_input
        
    save_sessions(st.session_state.sessions)
    
    with st.chat_message("user", avatar=USER_AVATAR):
        st.markdown(user_input)
        
    with st.chat_message("assistant", avatar=ASSISTANT_AVATAR):
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
