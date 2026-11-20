import streamlit as st
import requests
import json
import re
import io
import zipfile

# ---------- PAGE SETUP ----------
st.set_page_config(page_title="AI IDE & Project Generator", page_icon="💻", layout="wide")

# ---------- API CONFIG ----------
API_KEY = st.secrets["GROQ_API_KEY"]

col1, col2 = st.columns([1, 1.5])

with col1:
    st.title("💻 AI Developer IDE")
    st.write("Build, Edit, and Preview your complete project.")
    
    with st.sidebar:
        st.header("Project Setup")
        project_type = st.selectbox("Tech Stack:", [
            "HTML + Tailwind CSS Website",
            "Python Flask API",
            "Python Automation Script",
            "Next.js (React) App",
            "Node.js Express Backend"
        ])
        
        if st.button("🗑️ Reset IDE"):
            st.session_state.messages = []
            st.session_state.project_files = {}
            st.rerun()

    # Session State
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "system", "content": f"You are a Senior Developer. The user wants to build/edit a {project_type} project. "
                                          "If updating an existing project, modify the necessary files. "
                                          "For EVERY file you create or modify, you MUST use this exact format:\n"
                                          "### FILENAME: path/to/filename.ext\n"
                                          "```language\n[code here]\n```\n"
                                          "Do not skip files. Do not add conversational text, ONLY the file outputs."}
        ]
    if "project_files" not in st.session_state:
        st.session_state.project_files = {}

    # Chat Area
    for msg in st.session_state.messages:
        if msg["role"] != "system":
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    if prompt := st.chat_input("Example: Ek login page banao..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
            
            # Agar pehle se files hain, toh AI ko existing code ka context do
            context_prompt = ""
            if st.session_state.project_files:
                context_prompt = "\n\nHere are the current files in the project:\n"
                for fname, code in st.session_state.project_files.items():
                    context_prompt += f"### FILENAME: {fname}\n```\n{code}\n```\n"

            api_messages = st.session_state.messages.copy()
            if context_prompt:
                api_messages[-1]["content"] += context_prompt

            data = {
                "model": "qwen/qwen3.8-27b", 
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
            st.session_state.messages.append({"role": "assistant", "content": full_response})

        # Parse and update files
        file_pattern = re.compile(r'### FILENAME:\s*(.*?)\n```[a-zA-Z0-9]*\n(.*?)```', re.DOTALL)
        matches = file_pattern.findall(full_response)
        
        if matches:
            for filename, code in matches:
                clean_name = filename.strip().replace('`', '')
                st.session_state.project_files[clean_name] = code.strip()
            st.rerun()

# ---------- RIGHT COLUMN: IDE & PREVIEW ----------
with col2:
    if st.session_state.project_files:
        # Top Bar for Download
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for fname, code in st.session_state.project_files.items():
                zip_file.writestr(fname, code)
        zip_buffer.seek(0)
        
        st.download_button(
            label="📦 Download Complete Project (.ZIP)",
            data=zip_buffer,
            file_name="ai_project.zip",
            mime="application/zip",
            type="primary"
        )
        
        # Create Tabs for Editing vs Live Preview
        tab_edit, tab_preview = st.tabs(["📝 Code Editor", "👁️ Live Preview"])
        
        with tab_edit:
            col_file, col_dummy = st.columns([1, 1])
            with col_file:
                selected_file = st.selectbox("Select file to edit:", list(st.session_state.project_files.keys()))
            
            if selected_file:
                # Code Editor
                edited_code = st.text_area(
                    f"Editing: {selected_file}", 
                    value=st.session_state.project_files[selected_file], 
                    height=400
                )
                
                if st.button("💾 Save Changes to File"):
                    st.session_state.project_files[selected_file] = edited_code
                    st.success("File updated successfully!")
                    st.rerun()
                    
        with tab_preview:
            # Find HTML file for preview
            html_file = next((f for f in st.session_state.project_files.keys() if f.endswith('.html')), None)
            if html_file:
                st.write(f"**Live Preview of `{html_file}`**")
                html_content = st.session_state.project_files[html_file]
                
                # If CSS/JS files exist, inject them into HTML for preview
                for fname, code in st.session_state.project_files.items():
                    if fname.endswith('.css'):
                        html_content = html_content.replace(f'<link rel="stylesheet" href="{fname}">', f'<style>{code}</style>')
                    if fname.endswith('.js'):
                        html_content = html_content.replace(f'<script src="{fname}"></script>', f'<script>{code}</script>')
                
                # Render Live
                st.components.v1.html(html_content, height=500, scrolling=True)
            else:
                st.info("Live preview sirf HTML projects ke liye available hai. Python/Node projects ko run karne ke liye ZIP download karein.")
                
    else:
        st.info("👈 Left side se project generate karein. Jaise hi code banega, yahan Editor aur Live Preview aayega!")