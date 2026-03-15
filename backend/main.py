import json
import os
from datetime import datetime
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

# System instruction for the "Security Scout"
SECURITY_SCOUT_PROMPT = (
    "You are a 'Security Scout' for Aegis-Live, a cybersecurity guardian. "
    "Your mission is to analyze web page text content and its URL to identify potential phishing scams targeting Indian users. "
    "Pay close attention to URLs pretending to be Indian banks. A legitimate Indian bank URL should ideally end in '.in' or '.gov.in'. "
    "If you detect a suspicious URL claiming to be a bank but not matching these TLDs, or if the page content seems phishy, flag it. "
    "Respond with a JSON object containing two keys: 'is_scam' (boolean) and 'reason' (a brief explanation)."
)
MODEL_NAME = "gemini-2.5-flash"

# --- Helper Functions ---
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

        # 2. Build the dynamic prompt
        final_prompt = (
            f"{SECURITY_SCOUT_PROMPT}\n\n"
            "Here is the latest threat intelligence on trending scams:\n"
            "--- START INTELLIGENCE FEED ---\n"
            f"{trending_threats_json}\n"
            "--- END INTELLIGENCE FEED ---\n\n"
            "Analyze the following web page content. If the user's current page matches any of these specific patterns, "
            "flag it as 'High Risk' and mention in the 'reason' field that the match was found in the 'Intelligence Feed'.\n\n"
            f"URL: {request.url}\n\n"
            f"Page Text Content:\n---\n{request.text[:4000]}...\n---"
        )
        
        # 3. Call Gemini API
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[final_prompt]
        )

        # 4. Process response and store report
        clean_response = response.text.strip().replace('`', '').replace('json', '')
        analysis_result = json.loads(clean_response)

        if analysis_result.get("is_scam", False):
            report = {
                "url": request.url,
                "reason": analysis_result.get("reason", "No reason provided."),
                "analysis_provider": MODEL_NAME
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

@app.get("/")
async def get():
    return {"status": "Aegis-Live Backend is running"}
