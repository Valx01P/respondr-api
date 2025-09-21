cd server


Mac/Linux
    python3 -m venv venv
    source venv/bin/activate


Windows
    python -m venv venv
    .\venv\Scripts\activate


pip install -r requirements.txt


uvicorn main:app --reload --port 8000


Example .env
```bash
GEMINI_API_KEY=
TAVILY_API_KEY=
```