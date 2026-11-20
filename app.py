import streamlit as st
import requests
import json
import re
import io
import zipfile

# ---------- PAGE SETUP ----------
st.set_page_config(page_title="AI Project Generator", page_icon="🏗️", layout="wide")

# ---------- API CONFIG ----------
API_KEY = st.secrets["GROQ_API_KEY"]

# Layout: Left (Chat), Right (Project Files)
col1, col2 = st.columns([1, 1.2])

with col1:
    st.title("🏗️ AI Project Architect")
    st.write("Select a tech stack and describe your app. I'll generate the complete project code for you!")
    
    with st.sidebar:
        st.header("Project Settings")
        project_type = st.selectbox("Choose Tech Stack:", [
            "Next.js (React) App",
            "Python Flask API",
            "HTML + Tailwind CSS Website",
            "Node.js Express Backend",
            "Python Automation Script"
        ])
        
        if st.button("🗑️ Reset Project"):
            st.session_state.messages = []
            st.session_state.project_files = {}
            st.rerun()

    # Session State for Chat and Files
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "system", "content": f"You are a Senior Software Architect. The user wants to build a {project_type}. "
                                          "Generate the COMPLETE boilerplate code. "
                                          "For EVERY file, you MUST use this exact format:\n"
                                          "### FILENAME: path/to/filename.ext\n"
                                          "```language\n[code here]\n```\n"
                                          "Do not skip essential files (like package.json, requirements.txt, README.md, config files). "
                                          "Keep the code clean, functional, and well-commented. Do not add any conversational text, ONLY file outputs."}
        ]
    if "project_files" not in st.session_state:
        st.session_state.project_files = {}

    # Display Chat
    for msg in st.session_state.messages:
        if msg["role"] != "system":
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    # Chat Input
    if prompt := st.chat_input("Example: Ek login system banao with JWT auth..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
            data = {
                "model": "qwen/qwen3.8-27b", # Qwen coding mein best hai
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

        # --- SMART PARSER (Extracting Files & Folders) ---
        # Regex to find "### FILENAME: name.ext" followed by a code block
        file_pattern = re.compile(r'### FILENAME:\s*(.*?)\n```[a-zA-Z0-9]*\n(.*?)```', re.DOTALL)
        matches = file_pattern.findall(full_response)
        
        if matches:
            for filename, code in matches:
                # Clean up filename (remove spaces or backticks if AI added them)
                clean_name = filename.strip().replace('`', '')
                st.session_state.project_files[clean_name] = code.strip()
            st.rerun()

# ---------- RIGHT COLUMN: PROJECT FILES & DOWNLOAD ----------
with col2:
    st.subheader("📁 Generated Project Files")
    
    if st.session_state.project_files:
        st.success(f"✅ Project successfully generated with {len(st.session_state.project_files)} files!")
        
        # Show File Tree
        st.write("**File Structure:**")
        for fname in st.session_state.project_files.keys():
            st.code(fname, language="bash")
            
        # ZIP Creation
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for fname, code in st.session_state.project_files.items():
                # Folders create karke file likhna
                zip_file.writestr(fname, code)
        zip_buffer.seek(0)
        
        # Download Button
        st.download_button(
            label="📦 Download Complete Project (.ZIP)",
            data=zip_buffer,
            file_name=f"my_ai_project.zip",
            mime="application/zip",
            type="primary",
            use_container_width=True
        )
        
        st.divider()
        
        # Code Viewer (Dropdown to view any file's code)
        st.write("**Preview Code:**")
        selected_file = st.selectbox("Select a file to view:", list(st.session_state.project_files.keys()))
        if selected_file:
            st.code(st.session_state.project_files[selected_file], language="python")
            
    else:
        st.info("Yahan aapke project ki files dikhengi. Left side se AI ko prompt do!")