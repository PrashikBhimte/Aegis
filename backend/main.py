import json
import os
import re
from datetime import datetime, timedelta
from urllib.parse import urlparse
import requests
from google import genai
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from google.cloud import firestore

# --- Configuration ---
# Set the GOOGLE_APPLICATION_CREDENTIALS environment variable, required for Vertex AI auth
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.join(os.path.dirname(__file__), '..', 'credentials.json')

# Read the project ID from the credentials file
try:
    with open(os.environ["GOOGLE_APPLICATION_CREDENTIALS"], 'r') as f:
        credentials = json.load(f)
        PROJECT_ID = credentials.get('project_id')
        if not PROJECT_ID:
            raise ValueError("project_id not found in credentials.json")
except (FileNotFoundError, ValueError) as e:
    print(f"Error loading project_id: {e}")
    # Fallback project ID if credentials file is missing or misconfigured
    PROJECT_ID = "aegis-live-guardian"


# --- FastAPI App & Models ---
app = FastAPI()

class AnalysisRequest(BaseModel):
    url: str
    text: str

class ScoutReportRequest(BaseModel):
    url: str
    reason: str
    source: str = "user_report"

# --- Google Cloud & AI Services ---
# Initialize Firestore Client
try:
    db = firestore.Client(project=PROJECT_ID)
except Exception as e:
    print(f"Error initializing Firestore: {e}")
    db = None

# Initialize Vertex AI Client
try:
    client = genai.Client(vertexai=True, project=PROJECT_ID, location='us-central1')
except Exception as e:
    print(f"Error initializing Vertex AI Client: {e}")
    client = None

# System instruction for the "Security Scout" - UPDATED with Punycode & Domain Age priorities
SECURITY_SCOUT_PROMPT = (
    "You are a 'Security Scout' for Aegis-Live, a cybersecurity guardian. "
    "Your mission is to analyze web page text content and its URL to identify potential phishing scams targeting Indian users. "
    "You have access to two CRITICAL threat signals that are definitive markers of modern phishing attacks:\n\n"
    "1. PUNYCODE DETECTION (xn-- prefix): If the URL contains 'xn--', it is using Internationalized Domain Names (IDN) to disguise itself. "
    "This is a MAJOR red flag - attackers use Punycode to make malicious domains look legitimate (e.g., 'xn--sbi.com' looks like 'sbi.com' but is different). "
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

# --- Helper Functions ---

def extract_domain(url: str) -> str:
    """Extract domain from URL."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path
        # Remove www. prefix if present
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain
    except Exception:
        return ""

def check_punycode(url: str) -> dict:
    """
    Check if URL contains Punycode (xn-- prefix).
    Returns dict with is_punycode and details.
    """
    domain = extract_domain(url)
    
    if 'xn--' in domain.lower():
        return {
            "is_punycode": True,
            "domain": domain,
            "warning": f"Punycode detected in domain: {domain}. This is a common phishing technique."
        }
    
    return {
        "is_punycode": False,
        "domain": domain,
        "warning": None
    }

def get_domain_age(domain: str) -> dict:
    """
    Perform RDAP lookup to get domain creation date.
    Returns dict with is_new (created in last 7 days), creation_date, and age_days.
    """
    try:
        # Extract the base domain (remove TLD)
        parts = domain.split('.')
        if len(parts) < 2:
            return {"error": "Invalid domain"}
        
        # RDAP lookup
        rdap_url = f"http://rdap.org/domain/{domain}"
        
        response = requests.get(rdap_url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # Try to get creation date from RDAP response
            events = data.get('events', [])
            creation_date = None
            
            for event in events:
                if event.get('eventAction') == 'registration':
                    creation_date_str = event.get('eventDate')
                    if creation_date_str:
                        creation_date = datetime.fromisoformat(creation_date_str.replace('Z', '+00:00'))
                        break
            
            if creation_date:
                age_days = (datetime.now(creation_date.tzinfo) - creation_date).days
                
                return {
                    "creation_date": creation_date.isoformat(),
                    "age_days": age_days,
                    "is_new": age_days <= 7,
                    "warning": f"Domain created {age_days} days ago" if age_days <= 30 else None
                }
        
        return {"error": "RDAP lookup failed or domain not found"}
        
    except Exception as e:
        print(f"RDAP lookup error: {e}")
        return {"error": str(e)}

def store_scam_report(report: dict):
    """Stores a scam report in the Firestore 'scam_reports' collection."""
    if not db:
        print("Firestore client not available. Skipping report storage.")
        return
    try:
        reports_collection = db.collection('scam_reports')
        report['timestamp'] = datetime.utcnow()
        reports_collection.add(report)
        print(f"Scam report stored: {report['url']}")
    except Exception as e:
        print(f"Error storing scam report: {e}")

def get_trending_threats() -> str:
    """Fetches all documents from the 'trending_threats' collection and returns them as a JSON string."""
    if not db:
        return "No threat intelligence database available."
    
    try:
        threats_ref = db.collection("trending_threats")
        threats_docs = threats_ref.stream()
        
        threat_list = [doc.to_dict() for doc in threats_docs]
        
        if not threat_list:
            return "No trending threats found in the intelligence feed."
            
        # Convert the list of threats to a JSON string for the prompt
        return json.dumps(threat_list, indent=2)
        
    except Exception as e:
        print(f"Error fetching trending threats: {e}")
        return "Error retrieving threat intelligence."



# --- API Endpoints ---
# Set this to True to force the red banner to show on every page you visit
TEST_MODE_FORCE_SCAM = False

@app.post("/analyze")
async def analyze(request: AnalysisRequest):
    if not client:
        raise HTTPException(status_code=500, detail="Vertex AI client is not initialized.")

    # --- START TEST LOGIC ---
    if TEST_MODE_FORCE_SCAM:
        print(f"DEBUG: Test mode active. Forcing scam alert for: {request.url}")
        return {
            "is_scam": True, 
            "reason": "DEBUG TEST: This is a simulated high-risk alert to verify banner injection."
        }
    # --- END TEST LOGIC ---

    try:
        # 1. Get the latest threat intelligence
        trending_threats_json = get_trending_threats()

        # 2. Check for PUNYCODE (Critical Signal #1)
        punycode_result = check_punycode(request.url)
        punycode_context = ""
        is_punycode_risk = False
        
        if punycode_result.get("is_punycode"):
            is_punycode_risk = True
            punycode_context = f"\n⚠️ CRITICAL: PUNYCODE DETECTED - {punycode_result.get('warning')}"

        # 3. Check Domain Age via RDAP (Critical Signal #2)
        domain = extract_domain(request.url)
        domain_age_result = get_domain_age(domain)
        age_context = ""
        is_age_risk = False
        
        if "error" not in domain_age_result and domain_age_result.get("is_new"):
            is_age_risk = True
            age_context = f"\n⚠️ CRITICAL: NEWLY REGISTERED DOMAIN - {domain_age_result.get('warning')}"

        # 4. Build the dynamic prompt with enriched context
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
        
        # 5. Call Gemini API
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[final_prompt]
        )

        # 6. Process response and store report
        clean_response = response.text.strip().replace('`', '').replace('json', '')
        analysis_result = json.loads(clean_response)

        # If automated checks flagged high risk, override the AI decision
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
        print(f"An unexpected error occurred during analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/history")
async def get_history():
    """Retrieves the 10 most recent scam reports from Firestore."""
    if not db:
        raise HTTPException(status_code=500, detail="Firestore client not available.")

    try:
        reports_ref = db.collection('scam_reports')
        # Query sorted by timestamp descending and limit to 10
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

        if not history:
            return [] # Return empty list if no reports found
            
        return history

    except Exception as e:
        print(f"An error occurred while fetching history: {e}")
        raise HTTPException(status_code=500, detail="Could not retrieve scam history.")

@app.post("/scout/add")
async def add_scout_report(request: ScoutReportRequest):
    """
    Add a new threat to the trending_threats collection.
    This endpoint is used for crowdsourced threat reporting.
    """
    if not db:
        raise HTTPException(status_code=500, detail="Firestore client not available.")

    try:
        # Add to trending_threats collection
        threats_collection = db.collection('trending_threats')
        
        threat_data = {
            "url": request.url,
            "reason": request.reason,
            "source": request.source,
            "reported_at": datetime.utcnow(),
            "active": True
        }
        
        # Add document
        doc_ref = threats_collection.add(threat_data)
        
        print(f"Aegis: New threat added to trending_threats: {request.url}")
        
        return {
            "status": "success",
            "message": "Threat reported successfully",
            "url": request.url
        }
        
    except Exception as e:
        print(f"Error adding scout report: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def get():
    return {"status": "Aegis-Live Backend is running", "version": "2.0-guardian"}
