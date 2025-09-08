
# LeadGen AI Flow — Streamlit (Pure Python)

A pure Python Streamlit app that mirrors your n8n workflow:
**Webhook-style filters → mock insights → AI (Groq) or template email → tabular results + CSV download.**

## Features
- Filter by `industry`, `location`, `sizeMin`, `sizeMax`
- Adds the same **mock insights** logic
- Generates outreach emails via **Groq** (if `GROQ_API_KEY` is set) or a **deterministic template**
- Displays results in a table and allows **CSV export**
- Shows a **sample JSON** block similar to your webhook’s response

## Quickstart
```bash
pip install -r requirements.txt
export GROQ_API_KEY="YOUR_KEY_HERE"   # optional; for LLM generation
streamlit run app.py
```

Then open the Streamlit URL shown in your terminal (usually http://localhost:8501).

## Notes
- If no `GROQ_API_KEY` is set or the API call fails, the app uses a clean template to keep things reliable.
- You can swap in any other LLM provider by editing `generate_email_with_groq`.
