from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import hashlib
import json

# ---------------- CONFIG ----------------
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL = "gemma3:4b"
# ----------------------------------------

app = FastAPI()

# Create session with connection pooling and retry strategy
session = requests.Session()
retry_strategy = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["POST"]
)
adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=1, pool_maxsize=1)
session.mount("http://", adapter)
session.mount("https://", adapter)

# Serve static files (index.html)
app.mount("/static", StaticFiles(directory="."), name="static")

@app.get("/")
def root():
    return FileResponse("index.html")

# ---------- API ----------

class ScanRequest(BaseModel):
    text: str

CACHE = {}  # Cleared cache due to format change from indices to text strings

def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def analyze_bias(text: str):
    prompt = f"""You are a bias detection expert. Analyze the following text for biased or loaded language.

IMPORTANT: Return ONLY a valid JSON array. Do not include any text before or after the JSON.

If you find biased language, return JSON in this exact format:
[
  {{
    "text": "problematic words or phrase",
    "severity": 0.5,
    "type": "political",
    "reason": "explanation",
    "suggestion": "neutral version"
  }}
]

If no bias is found, return: []

Rules:
- Extract the exact problematic words or phrases from the original text, including any surrounding punctuation like quotation marks, apostrophes, parentheses, etc.
- Include the complete biased expression as it appears in the text
- severity: 0.0 (no bias) to 1.0 (strong bias)
- type: one of "political", "emotional", "framing", "assumption", "loaded language"
- Be conservative - only flag obvious bias

Text to analyze:
{text}

Return only JSON:"""

    try:
        response = session.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "prompt": prompt,
                "stream": False
            },
            timeout=60
        )
        response.raise_for_status()
        
        raw = response.json().get("response", "").strip()
        print(f"Raw response: {raw}")

        try:
            # Try to parse as JSON
            return json.loads(raw)
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            # Try to extract JSON from response if it contains extra text
            try:
                start = raw.find('[')
                end = raw.rfind(']') + 1
                if start >= 0 and end > start:
                    json_str = raw[start:end]
                    return json.loads(json_str)
            except:
                pass
            return []
    except (requests.ConnectionError, requests.Timeout, requests.RequestException) as e:
        print(f"Error connecting to Ollama: {e}")
        return []

@app.post("/scan")
def scan(req: ScanRequest):
    if not req.text.strip():
        return {"results": []}

    key = hash_text(req.text)

    if key in CACHE:
        return {"results": CACHE[key]}

    results = analyze_bias(req.text)
    CACHE[key] = results
    return {"results": results}
