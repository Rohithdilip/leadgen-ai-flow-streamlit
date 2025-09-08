import os
import json
import re
from typing import List, Dict, Any
import requests
import streamlit as st
import pandas as pd

# Load environment variables 
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Read Groq API key and enforce one default model
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DEFAULT_MODEL = "moonshotai/kimi-k2-instruct"  # enforced everywhere

st.set_page_config(page_title="LeadGen AI Flow (Streamlit)", page_icon="📧", layout="wide")

# ---------------------------
# Seed data 
# ---------------------------
SEED_COMPANIES: List[Dict[str, Any]] = [
    {"companyName": "TechNova Solutions", "website": "https://technova.example", "employeeCount": 120, "industry": "Software", "location": "Bengaluru, IN"},
    {"companyName": "GreenMakers Manufacturing", "website": "https://greenmakers.example", "employeeCount": 80, "industry": "Manufacturing", "location": "Pune, IN"},
    {"companyName": "AeroLogix Systems", "website": "https://aerologix.example", "employeeCount": 210, "industry": "Logistics", "location": "Hyderabad, IN"},
]

# ---------------------------
# Helpers
# ---------------------------
def add_insights(j: Dict[str, Any]) -> List[str]:
    industry = (j.get("industry") or "").lower()
    employee_count = int(j.get("employeeCount", 0))
    location = j.get("location") or ""

    bullets = []
    if re.search(r"software", industry, re.I):
        bullets += [
            "SaaS roadmap includes AI/ML modules",
            "Active in developer ecosystem; likely uses CI/CD",
        ]
    elif re.search(r"manufact", industry, re.I):
        bullets += [
            "Sustainable, lean operations focus",
            "Potential need for shop-floor IoT/SCADA integrations",
        ]
    elif re.search(r"logistic", industry, re.I):
        bullets += [
            "Fleet optimization & real-time tracking",
            "Likely evaluating warehouse automation",
        ]
    else:
        bullets += ["Expanding digital footprint"]

    if employee_count > 150:
        bullets.append("Mid-market team with scaling pains")

    if re.search(r"\bIN\b|India", location, re.I):
        bullets.append("Operating in India with regional growth")

    return bullets[:3]

def filter_companies(items: List[Dict[str, Any]], industry_q: str, location_q: str, size_min: int, size_max: int):
    out = []
    industry_q = (industry_q or "").lower().strip()
    location_q = (location_q or "").lower().strip()

    for it in items:
        employee_count = int(it.get("employeeCount", 0))
        industry_val = str(it.get("industry", "")).lower()
        location_val = str(it.get("location", "")).lower()

        ok_size = (employee_count >= size_min) and (employee_count <= size_max)
        ok_ind = (industry_q in industry_val) if industry_q else True
        ok_loc = (location_q in location_val) if location_q else True

        if ok_size and ok_ind and ok_loc:
            out.append(it)
    return out

# ---------------------------
# LLM: Groq (or local template fallback)
# ---------------------------
def generate_email_with_groq(company: Dict[str, Any], insights: List[str]) -> Dict[str, Any]:
    """
    Uses Groq's OpenAI-compatible endpoint if GROQ_API_KEY is set.
    Returns dict with 'source' = 'groq' or 'template', and optional 'error'.
    """
    api_key = GROQ_API_KEY
    if not api_key:
        result = generate_email_template(company, insights)
        result["source"] = "template"
        result["error"] = "Missing GROQ_API_KEY"
        return result

    model = DEFAULT_MODEL  

    system_msg = (
        "You are a professional B2B sales assistant. "
        "Return output as strict JSON only (no prose, no backticks). "
        'Schema: {"company":"string","subject":"string","body":"string","tone":"string","wordCount":number} '
        "All fields must always be present. Ensure body has 80-120 words."
    )

    user_prompt = (
        f"Company: {company.get('companyName')}\n"
        f"Website: {company.get('website')}\n"
        f"Industry: {company.get('industry')}\n"
        f"Employees: {company.get('employeeCount')}\n"
        f"Insights:\n" + "\n".join(insights) + "\n\n"
        "Write a concise outreach email (80–120 words) in a consultative and professional tone. "
        "The email should naturally reference the provided insights and be structured as a clear, personalized message to the company. "
        "Conclude the email with the following signature block:\n\n"
        "Warm Regards,\nRohith Dilip\nWednesday Solutions"
    )

    try:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.4,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        content = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")

        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            cleaned_lines = cleaned.splitlines()
            if cleaned_lines and cleaned_lines[0].strip().lower() == "json":
                cleaned_lines = cleaned_lines[1:]
            cleaned = "\n".join(cleaned_lines)

        try:
            obj = json.loads(cleaned)
            result = {
                "company": obj.get("company") or company.get("companyName"),
                "subject": obj.get("subject") or "Exploring a tailored approach",
                "body": obj.get("body") or "",
                "tone": obj.get("tone") or "consultative",
                "wordCount": obj.get("wordCount") or None,
                "source": "groq",
            }
            return result
        except Exception as parse_err:
            result = generate_email_template(company, insights)
            result["source"] = "template"
            result["error"] = f"ParseError: {parse_err}; content={content[:300]}..."
            return result

    except Exception as req_err:
        result = generate_email_template(company, insights)
        result["source"] = "template"
        err_text = ""
        try:
            err_text = resp.text[:300]  # type: ignore
        except Exception:
            pass
        result["error"] = f"RequestError: {req_err}; response={err_text}"
        return result

def generate_email_template(company: Dict[str, Any], insights: List[str]) -> Dict[str, Any]:
    # Deterministic fallback ~100 words
    bullets = "; ".join(insights)
    body = (
        f"Hi {company.get('companyName')},\n\n"
        f"I came across your work at {company.get('companyName')} and noticed: {bullets}. "
        f"We help teams like yours turn these priorities into measurable outcomes with a lightweight rollout and clear ROI within a few weeks. "
        f"If it’s useful, I can share a brief walkthrough tailored to {company.get('industry')} and your current team size of {company.get('employeeCount')}.\n\n"
        "Warm Regards,\n"
        "Rohith Dilip\n"
        "Wednesday Solutions"
    )
    return {
        "company": company.get("companyName"),
        "subject": f"{company.get('companyName')}: quick idea to accelerate {company.get('industry').lower()} goals",
        "body": body,
        "tone": "consultative",
        "wordCount": len(body.split())
    }

# ---------------------------
# UI
# ---------------------------
st.title("📧 LeadGen AI Flow — Streamlit")


with st.sidebar:
    st.header("Filters")
    industry = st.text_input("Industry contains", value="")
    location = st.text_input("Location contains", value="")
    col1, col2 = st.columns(2)
    with col1:
        size_min = st.number_input("Min employees", min_value=0, value=0, step=10)
    with col2:
        size_max = st.number_input("Max employees", min_value=0, value=999999, step=10)
    st.markdown("---")
    st.header("Status")
    if GROQ_API_KEY:
        st.success("🔑 GROQ_API_KEY loaded")
    else:
        st.warning("⚠️ No GROQ_API_KEY found — template fallback will be used")
    run_btn = st.button("Run")

df_seed = pd.DataFrame(SEED_COMPANIES)
st.subheader("Seed Companies")
st.dataframe(df_seed, use_container_width=True)

results = []
if run_btn:
    filtered = filter_companies(SEED_COMPANIES, industry, location, size_min, size_max)
    if not filtered:
        st.warning("No companies matched your filters. Try loosening them.")
    for comp in filtered:
        ins = add_insights(comp)
        email = generate_email_with_groq(comp, ins)
        results.append({
            "Company Name": email.get("company"),
            "Subject": email.get("subject"),
            "Body For Email": email.get("body"),
            "Tone": email.get("tone"),
            "Word Count": email.get("wordCount"),
            "Source": email.get("source"),
            "LLM Error": email.get("error"),
            "Website": comp.get("website"),
            "Industry": comp.get("industry"),
            "Employees": comp.get("employeeCount"),
            "Location": comp.get("location"),
            "Insights": "\n".join(ins),
        })

if results:
    st.subheader("Results")
    df = pd.DataFrame(results)
    st.dataframe(df, use_container_width=True)

    # Download CSV
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Download CSV", data=csv, file_name="leadgen_results.csv", mime="text/csv")

    # Show JSON for first item to mimic webhook response
    st.markdown("**Sample JSON (first item)**")
    st.code(json.dumps(results[0], indent=2))


