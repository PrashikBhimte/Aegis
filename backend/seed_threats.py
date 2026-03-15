import os
import json
from datetime import datetime
from google.cloud import firestore

def seed_threats():
    """
    Uploads a predefined list of common Indian scams to the 'trending_threats'
    collection in Firestore to simulate the threat intelligence gathering process.
    """
    print("Starting to seed Firestore with predefined threat intelligence...")

    # --- Configuration ---
    try:
        # Set Google Cloud credentials
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.join(os.path.dirname(__file__), '..', 'credentials.json')
        
        # Read the project ID from the credentials file
        with open(os.environ["GOOGLE_APPLICATION_CREDENTIALS"], 'r') as f:
            credentials = json.load(f)
            project_id = credentials.get('project_id')

        db = firestore.Client(project=project_id)
        print(f"Successfully connected to Firestore project: {project_id}")
    except Exception as e:
        print(f"Error connecting to Firestore: {e}")
        return

    # --- Predefined Scam Data ---
    common_scams = [
        {
            "id": "sbi_kyc_scam",
            "title": "Fake SBI KYC Update SMS",
            "phrases": ["SBI KYC update", "account will be blocked", "click here to update"],
            "brands": ["SBI", "State Bank of India"],
        },
        {
            "id": "electricity_bill_scam",
            "title": "Electricity Bill Disconnection Warning",
            "phrases": ["electricity bill will be disconnected tonight", "contact this number immediately"],
            "brands": ["BSES", "Tata Power", "Adani Electricity"],
        },
        {
            "id": "whatsapp_lottery_scam",
            "title": "KBC WhatsApp Lottery Scam",
            "phrases": ["you have won 25 lakh", "KBC lottery winner", "deposit processing fee"],
            "brands": ["KBC", "Kaun Banega Crorepati", "WhatsApp"],
        },
        {
            "id": "epfo_refund_scam",
            "title": "Fake EPFO Refund/Credit Message",
            "phrases": ["EPFO account credit", "claim your refund", "update your details"],
            "brands": ["EPFO"],
        },
        {
            "id": "fedex_scam",
            "title": "FedEx/Courier Package Scam",
            "phrases": ["illegal package in your name", "contact customs", "pay a fee to release"],
            "brands": ["FedEx", "Blue Dart", "DHL"],
        }
    ]

    # --- Upload to Firestore ---
    threats_collection = db.collection("trending_threats")
    
    for scam in common_scams:
        try:
            doc_ref = threats_collection.document(scam["id"])
            doc_ref.set({
                "post_title": scam["title"],
                "extracted_key_phrases": scam["phrases"],
                "targeted_brands": scam["brands"],
                "extracted_urls": [], # No URLs in this simulated data
                "source_subreddit": "seeded_data",
                "scraped_at": datetime.utcnow(),
            })
            print(f"  > Successfully seeded threat: {scam['id']}")
        except Exception as e:
            print(f"  > Error seeding threat {scam['id']}: {e}")

    print("\nFirestore seeding complete.")


if __name__ == "__main__":
    seed_threats()
