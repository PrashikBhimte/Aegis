import os
import json
import hashlib
from google.cloud import firestore
import google.generativeai as genai

# --- Configuration ---
# Set the GOOGLE_APPLICATION_CREDENTIALS environment variable
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.join(os.path.dirname(__file__), '..', 'credentials.json')

try:
    with open(os.environ["GOOGLE_APPLICATION_CREDENTIALS"], 'r') as f:
        credentials = json.load(f)
        PROJECT_ID = credentials.get('project_id')
        if not PROJECT_ID:
            raise ValueError("project_id not found in credentials.json")
except (FileNotFoundError, ValueError) as e:
    print(f"Error loading project_id: {e}")
    PROJECT_ID = "aegis-live-guardian" # Fallback

# --- Initialize Services ---
try:
    db = firestore.Client(project=PROJECT_ID)
except Exception as e:
    print(f"Error initializing Firestore: {e}")
    db = None

try:
    # Initialize Vertex AI Client, consistent with main.py
    client = genai.Client(vertexai=True, project=PROJECT_ID, location='us-central1')
except Exception as e:
    print(f"Error initializing Vertex AI Client: {e}")
    client = None


def generate_threat_intelligence():
    """
    Generates a list of trending digital scams using Gemini and stores them in Firestore.
    """
    if not db or not client:
        print("Firestore or Vertex AI client not available. Exiting.")
        return

    model = client.get_model("gemini-1.5-flash-latest") # Correctly get model from client
    
    system_prompt = (
        "You are a cybersecurity intelligence analyst. Your task is to generate a list of exactly 5 "
        "currently trending digital scams in India as of March 2026. "
        "Focus specifically on scams related to banking, utility bills, and emerging AI-driven deepfake frauds. "
        "For each scam, provide a JSON object with the following keys: 'title' (a concise name for the scam), "
        "'description' (a brief explanation of how the scam works), "
        "'target_keywords' (a list of keywords or phrases associated with the scam), "
        "and 'threat_level' (a rating from 1 to 10). "
        "Return a single JSON array containing these 5 objects."
    )
    
    try:
        response = client.models.generate_content(
            model="gemini-1.5-flash-latest",
            contents=[system_prompt]
        )
        
        # Clean and parse the JSON response
        clean_response = response.text.strip().replace('`', '').replace('json', '')
        scams = json.loads(clean_response)

        if not isinstance(scams, list):
            print("Error: Gemini did not return a list of scams.")
            return

        threats_collection = db.collection('trending_threats')

        for scam_data in scams:
            # Create a unique ID by hashing the title
            title = scam_data.get('title')
            if not title:
                continue # Skip if there's no title
                
            doc_id = hashlib.sha256(title.encode('utf-8')).hexdigest()
            
            # Use .set() with merge=True to create/update without duplication
            threats_collection.document(doc_id).set(scam_data, merge=True)
        
        print("Intelligence Feed Updated")

    except Exception as e:
        print(f"An error occurred during intelligence generation: {e}")


if __name__ == "__main__":
    generate_threat_intelligence()
