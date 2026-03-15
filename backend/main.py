import json
import os
from datetime import datetime
from urllib.parse import urlparse
from pathlib import Path
from contextlib import asynccontextmanager

import requests
from dotenv import load_dotenv
from google import genai
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from google.cloud import firestore

# Load environment variables
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

PROJECT_ID = os.getenv('PROJECT_ID', 'aegis-live-guardian')
LOCATION = os.getenv('LOCATION', 'us-central1')

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Aegis-Live Backend starting...")
    yield
    # Shutdown
    print("Aegis-Live Backend shutting down...")

app = FastAPI(lifespan=lifespan)

class AnalysisRequest(BaseModel):
    url: str
    text: str

class ScoutReportRequest(BaseModel):
    url: str
    reason: str
    source: str = "user_report"

# Firestore Client
try:
    db = firestore.Client(project=PROJECT_ID)
except Exception:
    db = None

# Vertex AI Client
try:
    client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)
except Exception:
    client = None

SECURITY_SCOUT_PROMPT = (
    "You are a 'Security Scout' for Aegis-Live, a cybersecurity guardian. "
    "Your mission is to analyze web page text content and its URL to identify potential phishing scams targeting Indian users. "
    "You have access to two CRITICAL threat signals that are definitive markers of modern phishing attacks:\n\n"
    "1. PUNYCODE DETECTION (xn-- prefix): If the URL contains 'xn--', it is using Internationalized Domain Names (IDN) to disguise itself. "
    "This is a MAJOR red flag - attackers use Punycode to make malicious domains look legitimate. "
    "ALWAYS flag URLs with 'xn--' as HIGH RISK.\n\n"
    "2. DOMAIN AGE (Recently Created): If the domain was created in the LAST 7 DAYS, it is extremely suspicious. "
    "Legitimate banks and services have established domains, not newly registered ones. "
    "Domains created within 7 days should be flagged as CRITICAL RISK.\n\n"
    "When analyzing, prioritize these signals:\n"
    "- Any URL with 'xn--' = AUTOMATIC HIGH RISK\n"
    "- Any domain created < 7 days ago = AUTOMATIC CRITICAL RISK\n"
    "- URLs pretending to be Indian banks but not ending in '.in' or '.gov.in' = SUSPICIOUS\n\n"
    "Respond with a JSON object containing two keys: 'is_scam' (boolean) and 'reason' (a brief explanation)."
)
MODEL_NAME = "gemini-2.5-flash"


def extract_domain(url: str) -> str:
    """Extract domain from URL."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain
    except Exception:
        return ""


def check_punycode(url: str) -> dict:
    """Check if URL contains Punycode (xn-- prefix)."""
    domain = extract_domain(url)
    
    if 'xn--' in domain.lower():
        return {
            "is_punycode": True,
            "domain": domain,
            "warning": f"Punycode detected in domain: {domain}. This is a common phishing technique."
        }
    
    return {"is_punycode": False, "domain": domain, "warning": None}


def get_domain_age(domain: str) -> dict:
    """Perform RDAP lookup to get domain creation date."""
    try:
        parts = domain.split('.')
        if len(parts) < 2:
            return {"error": "Invalid domain"}
        
        rdap_url = f"http://rdap.org/domain/{domain}"
        response = requests.get(rdap_url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            events = data.get('events', [])
            
            for event in events:
                if event.get('eventAction') == 'registration':
                    creation_date_str = event.get('eventDate')
                    if creation_date_str:
                        creation_date = datetime.fromisoformat(creation_date_str.replace('Z', '+00:00'))
                        age_days = (datetime.now(creation_date.tzinfo) - creation_date).days
                        
                        return {
                            "creation_date": creation_date.isoformat(),
                            "age_days": age_days,
                            "is_new": age_days <= 7,
                            "warning": f"Domain created {age_days} days ago" if age_days <= 30 else None
                        }
        
        return {"error": "RDAP lookup failed or domain not found"}
        
    except Exception as e:
        return {"error": str(e)}


def store_scam_report(report: dict):
    """Stores a scam report in Firestore."""
    if not db:
        return
    try:
        reports_collection = db.collection('scam_reports')
        report['timestamp'] = datetime.utcnow()
        reports_collection.add(report)
    except Exception:
        pass


def get_trending_threats() -> str:
    """Fetches documents from trending_threats collection."""
    if not db:
        return "No threat intelligence database available."
    
    try:
        threats_ref = db.collection("trending_threats")
        threats_docs = threats_ref.stream()
        threat_list = [doc.to_dict() for doc in threats_docs]
        
        if not threat_list:
            return "No trending threats found in the intelligence feed."
            
        return json.dumps(threat_list, indent=2)
        
    except Exception:
        return "Error retrieving threat intelligence."


TEST_MODE_FORCE_SCAM = False


@app.post("/analyze")
async def analyze(request: AnalysisRequest):
    if not client:
        raise HTTPException(status_code=500, detail="Vertex AI client is not initialized.")

    if TEST_MODE_FORCE_SCAM:
        return {
            "is_scam": True, 
            "reason": "DEBUG TEST: This is a simulated high-risk alert to verify banner injection."
        }

    try:
        trending_threats_json = get_trending_threats()

        # Punycode check
        punycode_result = check_punycode(request.url)
        punycode_context = ""
        is_punycode_risk = False
        
        if punycode_result.get("is_punycode"):
            is_punycode_risk = True
            punycode_context = f"\n⚠️ CRITICAL: PUNYCODE DETECTED - {punycode_result.get('warning')}"

        # Domain age check
        domain = extract_domain(request.url)
        domain_age_result = get_domain_age(domain)
        age_context = ""
        is_age_risk = False
        
        if "error" not in domain_age_result and domain_age_result.get("is_new"):
            is_age_risk = True
            age_context = f"\n⚠️ CRITICAL: NEWLY REGISTERED DOMAIN - {domain_age_result.get('warning')}"

        # Build prompt
        final_prompt = (
            f"{SECURITY_SCOUT_PROMPT}\n\n"
            "Here is the latest threat intelligence on trending scams:\n"
            "--- START INTELLIGENCE FEED ---\n"
            f"{trending_threats_json}\n"
            "--- END INTELLIGENCE FEED ---\n\n"
            "Analyze the following web page content. If the user's current page matches any of these specific patterns, "
            "flag it as 'High Risk' and mention in the 'reason' field that the match was found in the 'Intelligence Feed'.\n\n"
            "=== CRITICAL CONTEXT (Automated Threat Signals) ===\n"
            f"Punycode Check:{punycode_context if punycode_context else ' - No Punycode detected'}\n"
            f"Domain Age Check:{age_context if age_context else ' - Domain age check completed'}\n"
            "===================================================\n\n"
            f"URL: {request.url}\n\n"
            f"Page Text Content:\n---\n{request.text[:4000]}...\n---"
        )
        
        # Call Gemini
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[final_prompt]
        )

        clean_response = response.text.strip().replace('`', '').replace('json', '')
        analysis_result = json.loads(clean_response)

        # Override if automated checks flagged risk
        if is_punycode_risk or is_age_risk:
            analysis_result["is_scam"] = True
            reasons = []
            if is_punycode_risk:
                reasons.append("Punycode detected - definite phishing indicator")
            if is_age_risk:
                reasons.append(f"Domain age: {domain_age_result.get('age_days')} days (recently created)")
            analysis_result["reason"] = "; ".join(reasons) + ". " + analysis_result.get("reason", "")

        if analysis_result.get("is_scam", False):
            report = {
                "url": request.url,
                "reason": analysis_result.get("reason", "No reason provided."),
                "analysis_provider": MODEL_NAME,
                "is_punycode": is_punycode_risk,
                "is_new_domain": is_age_risk
            }
            store_scam_report(report)

        return analysis_result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/history")
async def get_history():
    if not db:
        raise HTTPException(status_code=500, detail="Firestore client not available.")

    try:
        reports_ref = db.collection('scam_reports')
        query = reports_ref.order_by('timestamp', direction=firestore.Query.DESCENDING).limit(10)
        docs = query.stream()

        history = []
        for doc in docs:
            data = doc.to_dict()
            history.append({
                "url": data.get("url"),
                "reason": data.get("reason"),
                "timestamp": data.get("timestamp").strftime("%Y-%m-%d %H:%M:%S UTC")
            })

        return history if history else []

    except Exception:
        raise HTTPException(status_code=500, detail="Could not retrieve scam history.")


@app.post("/scout/add")
async def add_scout_report(request: ScoutReportRequest):
    """Add a new threat to trending_threats collection."""
    if not db:
        raise HTTPException(status_code=500, detail="Firestore client not available.")

    try:
        threats_collection = db.collection('trending_threats')
        
        threat_data = {
            "url": request.url,
            "reason": request.reason,
            "source": request.source,
            "reported_at": datetime.utcnow(),
            "active": True
        }
        
        threats_collection.add(threat_data)
        
        return {
            "status": "success",
            "message": "Threat reported successfully",
            "url": request.url
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def get():
    return {"status": "Aegis-Live Backend is running", "version": "2.0-guardian"}
