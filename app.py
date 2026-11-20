import streamlit as st
import requests
import json
import uuid
import pandas as pd
from gtts import gTTS
import io
from pypdf import PdfReader
from duckduckgo_search import DDGS
from bs4 import BeautifulSoup

# ---------- PAGE SETUP ----------
st.set_page_config(page_title="Ultimate GPT Clone", page_icon="🤖", layout="wide")
API_KEY = st.secrets["GROQ_API_KEY"]

# ---------- CONNECTOR FUNCTIONS ----------
def web_search(query):
    try:
        results = DDGS().text(query, max_results=3)
        return "\n".join([f"- {r['title']}: {r['body']}" for r in results])
    except Exception as e:
        return "Search failed."

def read_website(url):
    try:
        res = requests.get(url, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        text = ' '.join(soup.stripped_strings)
        return text[:3000] # Pehle 3000 characters (Context limit ke liye)
    except:
        return "Website read failed."

# ---------- SESSION STATE ----------
if "chats" not in st.session_state:
    st.session_state.chats = {}
if "current_chat_id" not in st.session_state:
    new_id = str(uuid.uuid4())
    st.session_state.current_chat_id = new_id
    st.session_state.chats[new_id] = []

# ---------- SIDEBAR ----------
with st.sidebar:
    st.title("🤖 Ultimate GPT")
    
    if st.button("➕ New Chat", use_container_width=True):
        new_id = str(uuid.uuid4())
        st.session_state.current_chat_id = new_id
        st.session_state.chats[new_id] = []
        st.rerun()
        
    st.divider()
    
    # --- CONNECTORS TOGGLE ---
    st.subheader("🔌 Connectors (Plugins)")
    use_web_search = st.toggle("🌐 Enable Web Search", value=False, help="AI ko live internet search ki permission do.")
    use_url_reader = st.toggle("🔗 Enable URL Reader", value=False, help="Kisi bhi website ka link dekar usko padhwao.")
    
    st.divider()
    
    st.subheader("Recent Chats")
    for chat_id in reversed(list(st.session_state.chats.keys())):
        msgs = st.session_state.chats[chat_id]
        title = "New Chat"
        for m in msgs:
            if m["role"] == "user":
                title = m["content"][:20] + "..."
                break
        if chat_id == st.session_state.current_chat_id:
            st.button(f"👉 {title}", key=chat_id, disabled=True, use_container_width=True)
        else:
            if st.button(f"💬 {title}", key=chat_id, use_container_width=True):
                st.session_state.current_chat_id = chat_id
                st.rerun()

# ---------- MAIN CHAT AREA ----------
st.title("🤖 AI Assistant with Connectors")
current_messages = st.session_state.chats[st.session_state.current_chat_id]

for msg in current_messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ---------- CHAT INPUT ----------
if prompt := st.chat_input("Message AI..."):
    
    with st.chat_message("user"):
        st.markdown(prompt)
    current_messages.append({"role": "user", "content": prompt})

    # ---------- CONNECTOR LOGIC EXECUTION ----------
    context_data = ""
    
    # 1. Web Search Connector
    if use_web_search:
        with st.spinner("🌐 Internet par search kar raha hoon..."):
            search_results = web_search(prompt)
            context_data += f"\n\n[Web Search Results]:\n{search_results}\n"
            
    # 2. URL Reader Connector (Agar prompt mein http ya www hai)
    if use_url_reader and ("http" in prompt or "www." in prompt):
        # Link extract karna (bahut basic logic)
        words = prompt.split()
        url = next((w for w in words if "http" in w or "www." in w), None)
        if url:
            with st.spinner(f"🔗 Website padh raha hoon: {url}"):
                site_content = read_website(url)
                context_data += f"\n\n[Website Content from {url}]:\n{site_content}\n"

    # 3. API Call (Context ke saath)
    with st.chat_message("assistant"):
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
        
        # Agar connector ne data laaya hai, toh usko prompt mein add karo
        final_prompt = prompt
        if context_data:
            final_prompt = f"{prompt}\n\nHere is the extra context from tools:\n{context_data}\n\nPlease answer based on this context."
            
        api_messages = current_messages[:-1] + [{"role": "user", "content": final_prompt}]
        
        data = {
            "model": "llama-3.3-70b-versatile",
            "messages": api_messages, 
            "stream": True
        }
        
        def generate_response():
            response = requests.post(url, headers=headers, json=data, stream=True)
            for line in response.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8')
                    if decoded_line.startswith("data: "):
                        json_str = decoded_line[6:]
                        if json_str.strip() != "[DONE]":
                            try:
                                chunk = json.loads(json_str)
                                delta = chunk['choices'][0]['delta']
                                if 'content' in delta:
                                    yield delta['content']
                            except:
                                pass

        full_response = st.write_stream(generate_response())
        
        # History mein original prompt save karo, context nahi (taaki chat lamba na ho)
        current_messages.append({"role": "assistant", "content": full_response})