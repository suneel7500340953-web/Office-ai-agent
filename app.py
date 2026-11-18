import streamlit as st
import requests
import json
import io
from openpyxl import Workbook
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

# ---------- CONFIG (Streamlit Secrets se API key uthegi) ----------
API_KEY = st.secrets["GROQ_API_KEY"]
MODEL = "qwen/qwen3.8-27b"

# Page Setting
st.set_page_config(page_title="AI Office Assistant", page_icon="🤖", layout="wide")
st.title("🤖 AI Office Assistant (JARVIS)")
st.write("Mujhse koi bhi Word Document ya Excel Sheet banwao, main taiyar karke dunga!")

def call_ai(system_prompt, user_prompt):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    data = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    }
    res = requests.post(url, headers=headers, json=data)
    if res.status_code == 200:
        text = res.json()['choices'][0]['message']['content']
        return text.replace("```json", "").replace("```", "").strip()
    return None

# Chat History Save Karne Ke Liye
if "messages" not in st.session_state:
    st.session_state.messages = []

# Purani chat dikhana
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Main Chat Input
if user_req := st.chat_input("Kya banwana hai? (e.g., 'Rahul ka resume banao jisme Python skills ho')"):
    
    # User ka message screen par dikhao
    st.session_state.messages.append({"role": "user", "content": user_req})
    with st.chat_message("user"):
        st.markdown(user_req)

    # AI ka process
    with st.chat_message("assistant"):
        with st.spinner("Soch raha hoon..."):
            
            # 1. Boss (Supervisor) se poocho
            sup_prompt = 'You are a Supervisor. Decide if user needs "Excel" or "Word". Return ONLY valid JSON. Example: {"workers": ["Word"]}'
            decision_text = call_ai(sup_prompt, user_req)
            
            try:
                decision = json.loads(decision_text)
                workers = decision.get("workers", ["Word"])
            except:
                workers = ["Word"]

            # 2. Kaam karo
            if "Word" in workers:
                st.write("📝 **Word Document ban raha hai...**")
                sys_prompt = 'You are an Expert Resume Writer. Return ONLY a JSON array of instructions. Actions: {"action": "add_name", "text": "Name"}, {"action": "add_heading", "text": "Heading"}, {"action": "add_text", "text": "Para"}, {"action": "add_job", "role": "Role", "company": "Company", "dates": "Date", "bullets": ["Point"]}'
                response = call_ai(sys_prompt, user_req)
                
                try:
                    plan = json.loads(response)
                    doc = Document()
                    for section in doc.sections:
                        section.top_margin, section.bottom_margin = Inches(0.5), Inches(0.5)
                    
                    for step in plan:
                        action = step.get("action")
                        if action == "add_name":
                            h = doc.add_heading(step["text"].upper(), level=0)
                            h.alignment = WD_ALIGN_PARAGRAPH.CENTER
                        elif action == "add_heading":
                            doc.add_heading(step["text"].upper(), level=1)
                        elif action == "add_text":
                            doc.add_paragraph(step["text"])
                        elif action == "add_job":
                            p = doc.add_paragraph()
                            run_role = p.add_run(step["role"]); run_role.bold = True
                            run_company = p.add_run(f" | {step['company']} ({step['dates']})"); run_company.italic = True
                            for bullet in step["bullets"]:
                                doc.add_paragraph(bullet, style='List Bullet')
                    
                    # File ko memory mein save karo
                    doc_bytes = io.BytesIO()
                    doc.save(doc_bytes)
                    doc_bytes.seek(0)
                    
                    st.success("✅ Word File Taiyar Hai!")
                    st.download_button(
                        label="📥 Download Word File",
                        data=doc_bytes,
                        file_name="AI_Document.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
                except Exception as e:
                    st.error(f"Error: {e}")

            # 3. Excel ka kaam
            if "Excel" in workers:
                st.write("📊 **Excel File ban rahi hai...**")
                sys_prompt = 'You are a Data Generator. Return ONLY JSON array. Example: [{"Item": "A", "Value": 100}]'
                response = call_ai(sys_prompt, user_req)
                
                try:
                    data = json.loads(response)
                    wb = Workbook()
                    ws = wb.active
                    if data:
                        headers = list(data[0].keys())
                        ws.append(headers)
                        for row in data:
                            ws.append(list(row.values()))
                    
                    # File ko memory mein save karo
                    excel_bytes = io.BytesIO()
                    wb.save(excel_bytes)
                    excel_bytes.seek(0)
                    
                    st.success("✅ Excel File Taiyar Hai!")
                    st.download_button(
                        label="📥 Download Excel File",
                        data=excel_bytes,
                        file_name="AI_Data.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                except Exception as e:
                    st.error(f"Error: {e}")

            # AI ka final jawab
            final_msg = "Aapki file taiyar hai! Upar diye gaye button se download kar lein."
            st.session_state.messages.append({"role": "assistant", "content": final_msg})
            st.markdown(final_msg)