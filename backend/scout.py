import os
import json
import praw
from datetime import datetime
from google.cloud import firestore
from google import genai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Configuration ---
# Set Google Cloud credentials
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.join(os.path.dirname(__file__), '..', 'credentials.json')

# Read the project ID from the credentials file
try:
    with open(os.environ["GOOGLE_APPLICATION_CREDENTIALS"], 'r') as f:
        credentials = json.load(f)
        PROJECT_ID = credentials.get('project_id')
except (FileNotFoundError, ValueError) as e:
    PROJECT_ID = "aegis-live-guardian" # Fallback

# Reddit API Credentials (ensure these are set in your .env file)
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "AegisScout/1.0")

# --- AI & DB Clients ---
db = firestore.Client(project=PROJECT_ID)
vertex_client = genai.Client(vertexai=True, project=PROJECT_ID, location='us-central1')
MODEL_NAME = "gemini-1.5-flash"

# AI prompt for threat extraction
EXTRACTION_PROMPT = (
    "You are a threat intelligence analyst. Analyze the following Reddit post content. "
    "Extract any potential scam information and return it as a structured JSON object. "
    "The JSON object should have three keys: 'urls' (a list of strings), 'key_phrases' (a list of strings), and 'brands' (a list of strings). "
    "Focus on information related to financial scams, phishing, and online fraud. "
    "If no relevant information is found in a category, return an empty list for that key. "
    "Post Title: {title}
"
    "Post Body: {body}"
)

def refresh_threat_intel():
    """
    Connects to Reddit, scrapes r/Scams for hot posts, uses Gemini to extract
    threat intelligence, and saves it to Firestore.
    """
    print("Starting Aegis-Scout threat intel refresh...")

    if not all([REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT]):
        print("Reddit API credentials are not configured. Please set them in your .env file.")
        return

    try:
        reddit = praw.Reddit(
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_CLIENT_SECRET,
            user_agent=REDDIT_USER_AGENT,
        )
        subreddit = reddit.subreddit("Scams")
        hot_posts = subreddit.hot(limit=10)

        print(f"Fetched {len(list(hot_posts))} posts from r/Scams. Analyzing...")
        hot_posts = subreddit.hot(limit=10) # Re-fetch since the previous line consumed the iterator

        for post in hot_posts:
            if post.stickied:
                continue

            print(f"
Analyzing post: '{post.title}'")
            prompt = EXTRACTION_PROMPT.format(title=post.title, body=post.selftext)

            try:
                # Generate content using the Vertex AI client
                response = vertex_client.models.generate_content(
                    model=MODEL_NAME,
                    contents=[prompt]
                )

                # Clean and parse the JSON response
                clean_response = response.text.strip().replace('`', '').replace('json', '')
                threat_data = json.loads(clean_response)

                urls = threat_data.get("urls", [])
                key_phrases = threat_data.get("key_phrases", [])
                brands = threat_data.get("brands", [])

                if urls or key_phrases or brands:
                    # Save to Firestore
                    doc_ref = db.collection("trending_threats").document(post.id)
                    doc_ref.set({
                        "source_subreddit": "r/Scams",
                        "post_title": post.title,
                        "post_url": post.url,
                        "extracted_urls": urls,
                        "extracted_key_phrases": key_phrases,
                        "targeted_brands": brands,
                        "scraped_at": datetime.utcnow(),
                    })
                    print(f"  > Threat intel found and saved for post {post.id}.")
                else:
                    print("  > No specific threat intel found.")

            except (json.JSONDecodeError, KeyError) as e:
                print(f"  > Error parsing AI response for post {post.id}: {e}")
            except Exception as e:
                print(f"  > An unexpected error occurred during analysis for post {post.id}: {e}")

    except Exception as e:
        print(f"An error occurred while connecting to Reddit or fetching posts: {e}")

    print("
Aegis-Scout threat intel refresh complete.")


if __name__ == "__main__":
    refresh_threat_intel()
