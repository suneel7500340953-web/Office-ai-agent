import streamlit as st
import requests
import json
import re
import io
import zipfile

# ---------- PAGE SETUP ----------
st.set_page_config(page_title="Full-Stack AI Builder", page_icon="🏗️", layout="wide")

col1, col2 = st.columns([1, 1.2])

with col1:
    st.title("🏗️ AI App Builder")
    st.write("Koi bhi Website, App ya Software banwao!")
    
    with st.sidebar:
        st.header("Project Setup")
        project_type = st.selectbox("Kya banana hai?", [
            "Simple Website (HTML/CSS/JS)",
            "Python Backend / Script",
            "React / Next.js Web App",
            "Flutter Mobile App",
            "Data Science / ML Project"
        ])
        
        if st.button("🗑️ Naya Project"):
            st.session_state.messages = []
            st.session_state.project_files = {}
            st.rerun()

    API_KEY = st.secrets["GROQ_API_KEY"]

    # Initialize states
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "system", "content": f"You are a Senior Full-Stack Developer. The user wants to build: {project_type}. "
                                          "Write complete, production-ready code. "
                                          "If you create multiple files, format them clearly using: \n"
                                          "### FILENAME: filename.ext\n"
                                          "```language\ncode here\n```\n"
                                          "Always provide all necessary files to run the project."}
        ]
    if "project_files" not in st.session_state:
        st.session_state.project_files = {}

    # Display Chat
    for msg in st.session_state.messages:
        if msg["role"] != "system":
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    # Chat Input
    if prompt := st.chat_input("Example: Ek to-do list app banao with LocalStorage..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
            data = {
                "model": "qwen/qwen3.8-27b", 
                "messages": st.session_state.messages, 
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
            st.session_state.messages.append({"role": "assistant", "content": full_response})

        # --- SMART PARSER: Files aur Code nikalna ---
        # Regex se "### FILENAME: filename.ext" aur uske baad ka code dhoondhna
        file_pattern = re.compile(r'### FILENAME:\s*(.*?)\n```[a-zA-Z]*\n(.*?)```', re.DOTALL)
        matches = file_pattern.findall(full_response)
        
        if matches:
            for filename, code in matches:
                st.session_state.project_files[filename.strip()] = code.strip()
            st.rerun() # Files mil gayi, right side update karo

# ---------- RIGHT COLUMN: PREVIEW & DOWNLOAD ----------
with col2:
    st.subheader("📁 Project Files & Preview")
    
    if st.session_state.project_files:
        files = st.session_state.project_files
        
        # 1. Files ki list dikhana
        st.write("**Files Generated:**")
        for fname in files.keys():
            st.write(f"- `{fname}`")
            
        # 2. ZIP Download Button
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for fname, code in files.items():
                zip_file.writestr(fname, code)
        zip_buffer.seek(0)
        
        st.download_button(
            label="📦 Download Full Project (ZIP)",
            data=zip_buffer,
            file_name="my_ai_project.zip",
            mime="application/zip",
            type="primary"
        )
        
        st.divider()
        
        # 3. Live Preview (Agar HTML/CSS/JS hai)
        html_file = next((f for f in files.keys() if f.endswith('.html')), None)
        if html_file:
            st.write(f"**Live Preview (`{html_file}`):**")
            # CSS/JS ko HTML mein merge karke preview dikhana
            html_content = files[html_file]
            
            # Agar CSS/JS alag files mein hain, toh unko inline karo preview ke liye
            for fname, code in files.items():
                if fname.endswith('.css'):
                    html_content = html_content.replace(f'<link rel="stylesheet" href="{fname}">', f'<style>{code}</style>')
                if fname.endswith('.js'):
                    html_content = html_content.replace(f'<script src="{fname}"></script>', f'<script>{code}</script>')
            
            st.components.v1.html(html_content, height=500, scrolling=True)
        else:
            st.info("Ye backend/app code hai. Iska live preview yahan nahi dikhega. Aap ZIP download karke apne PC par run kar sakte hain.")
            
    else:
        st.info("AI aapse baat karke code generate karega aur yahan files dikhengi. Aap poora project ek ZIP file mein download kar sakte hain!")