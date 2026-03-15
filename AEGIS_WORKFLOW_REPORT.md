## Aegis-Live: Gemini Live Agent Challenge Project Report
## Executive Summary
Aegis-Live is an immersive, real-time AI cybersecurity guardian. It leverages Gemini 1.5 Flash to proactively neutralize phishing threats by combining continuous multimodal monitoring with a self-evolving threat intelligence system. Designed for the 2026 threat landscape, it offers a proactive defense that speaks, sees, and learns.

## System Architecture Workflow
Intelligent Capture: extension/background.js detects page completion and triggers content.js to extract text and URLs.

Deep Analysis & Grounding: The FastAPI backend enriches the user's data with Punycode detection and Real-time Domain Age lookups (RDAP).

Threat Intelligence Infusion: The agent queries a Firestore-backed 'Memory' populated by the Aegis-Scout agent.

Dynamic Verdict: Gemini 1.5 Flash analyzes the combined context (Page data + Scams + Metadata) via the Vertex AI SDK.

Immersive Alerts:

Visual: A high-urgency neon-red banner is injected into the DOM.

Audio: If not muted via the User Toggle, Aegis-Voice provides an audible warning using chrome.tts.

Crowdsourced Learning: Users can report new scams via the banner, which feeds directly back into the Aegis-Scout intelligence loop.

## Core Feature List
Continuous Sentinel: Zero-click, automated background monitoring.

Punycode & Metadata Guard: Identifies sophisticated "look-alike" domains using regex and RDAP age checks.

Agentic Scout Intelligence: Uses Gemini to autonomously generate and update trending threat patterns.

Aegis-Voice Alerts: Real-time audio warnings with a User-Controlled Mute Toggle.

Threat Vault Dashboard: A neon-themed historical log of the last 10 detections.

Community Reporting: One-click feedback loop to update the global threat memory.

## Technical Stack
AI & Cloud: Google Gemini 1.5 Flash, Vertex AI SDK, Google Cloud Firestore.

Backend: FastAPI (Python), rdap integration.

Frontend: Chrome Manifest V3, Neon-Grid CSS Framework, chrome.tts API.

## Agentic Logic: The Aegis-Scout
The backend/scout.py agent acts as a cybersecurity analyst. It uses generative prompting to predict and identify trending scams (e.g., March 2026 Indian Banking Frauds), hashes them for deduplication, and maintains the Firestore 'Memory'. This ensures the Aegis-Core is never analyzing in a vacuum, but is always grounded in current threat intelligence.