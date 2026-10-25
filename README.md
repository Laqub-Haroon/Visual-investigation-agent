# UC04 – Visual Investigation Agent

An LLM-powered agent that analyzes images of monuments and produces a structured
investigation report: observed clues, inferred conclusions, probable location,
authenticity assessment, historical context and sources.

## How it works
Image → vision LLM (Gemini) → clue extraction (observed vs inferred) →
optional Google Search verification → structured report → chat with memory for follow-ups.

## Setup
1. Install Python 3.10+
2. `python -m venv venv` then `venv\Scripts\activate`
3. `pip install -r requirements.txt`
4. Copy `.env.example` to `.env` and add your Gemini API key
5. Put the dataset images in the `images/` folder

## Run
- Analyze the whole dataset: `python batch.py` (results in `outputs/`)
- Chatbot with follow-up questions: `streamlit run app.py`

