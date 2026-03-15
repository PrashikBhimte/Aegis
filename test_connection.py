import os
from google import genai

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "credentials.json"

client = genai.Client(vertexai=True, project="aegis-live-guardian", location="us-central1")

# for model in client.models.list():
#     print(f"Model ID: {model.name}")

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="Aegis-Live connection test. Are you Online?"
)

print(response.text)