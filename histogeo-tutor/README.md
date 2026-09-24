# Histogeo Tutor 🏛️🌍

An AI-powered learning assistant for History and Geography built with the **Google Agent Development Kit (ADK)**, **A2UI**, **Vertex AI**, and **Google Cloud Platform**.

Histogeo Tutor helps students explore historical eras and physical geography topics. It grounds its answers in real historical and geographical facts, generates custom AI visual scenes and data visualization charts (timelines and comparisons), tracks study progress in Firestore, remembers student interaction history in Vertex AI Memory Bank, and formats all responses into rich, responsive A2UI cards.

![Histogeo Tutor Demo](demo.gif)

---

## Key Features & Capabilities

- 📖 **Factual Wikipedia Grounding**: Fetches live summary extracts from the Wikipedia REST API to ground explanations in accurate historical and geographical data.
- 🎨 **AI Scene Illustrations**: Uses **Imagen** (`gemini-3.1-flash-lite-image`) via Vertex AI to generate vivid historical scenes or realistic physical geography landscapes.
- 📊 **Data & Timeline Charts**: Uses Python `matplotlib` to render data visualizations—including milestone timelines, comparison bar charts (e.g., river lengths or empire spans), and line graphs.
- 🧠 **Persistent Memory Bank**: Uses **Vertex AI Memory Bank** to automatically store session facts across user interactions.
- 📂 **Firestore Progress Tracking**: Manages a per-student `study_topics` collection in **Google Cloud Firestore** to log revised topics, mastery status, and notes.
- 🃏 **Rich A2UI UI Cards**: Formats response payloads into native A2UI cards featuring headers, formatted text, and embedded visual media.
- 🗂️ **Multi-Project Chat Sessions**: Web frontend sidebar allows students to organize separate study chats (e.g., "Ancient India Revision" or "River Systems") with isolated chat histories.
- 📥 **Export Study Notes**: One-click client-side download compiles agent answers and visual images into downloadable Markdown (`.md`) study notes.
- 🌙 **Dark & Light Mode**: Theme toggle in the web header with persistent preference saved in `localStorage`.

---

## Architecture & Google Cloud Services

Histogeo Tutor leverages the following services and tools:

| Service / Tool | Purpose in Codebase |
| :--- | :--- |
| **Google ADK** | Core framework for orchestrating agents, tools, and lifecycle callbacks (`Agent`, `Gemini`, `a2ui_callback`, `generate_memories_callback`). |
| **Vertex AI Memory Bank** | Session memory persistence using `PreloadMemoryTool` and post-turn callbacks (`callback_context.add_session_to_memory`). |
| **Google Cloud Firestore** | Persists student study progress in the `study_topics` Firestore collection via `add_study_topic`, `get_study_topic`, and `list_study_topics`. |
| **Vertex AI Imagen** | Generates visual scene illustrations (`gemini-3.1-flash-lite-image`) in `generate_topic_illustration`. |
| **Python Matplotlib** | Renders chart PNGs (`timeline`, `bar`, `line`) in `generate_topic_chart`. |
| **Google Cloud Storage** | Hosts generated scene images and matplotlib charts in a public Cloud Storage bucket (`gs://histogeo-tutor-media-d87f671e`). |
| **Wikipedia REST API** | Live factual lookup tool (`lookup_wikipedia_summary`) to prevent model hallucination. |
| **A2UI Agent SDK** | Renders structured response surfaces using the A2UI basic component catalog (`Card`, `Column`, `Row`, `Text`, `Image`). |
| **Vertex AI Agent Runtime** | Reasoning Engine deployment target for serverless agent execution. |
| **Google Cloud Run** | Hosts the FastAPI backend proxy and static frontend web application. |

---

## Repository Structure

```
histogeo-tutor/
├── app/                        # ADK Agent package
│   ├── agent.py                # Main ADK agent declaration, tools, and callbacks
│   ├── a2ui_utils.py           # A2UI callback transformer and JSON extractor
│   ├── firestore_utils.py      # Firestore study_topics CRUD helper functions
│   └── fast_api_app.py         # FastAPI application wrapper for Reasoning Engine
├── frontend/                   # Web application
│   ├── fast_api_app.py         # Cloud Run FastAPI server proxying requests to Reasoning Engine
│   ├── Dockerfile              # Container spec for Cloud Run frontend deployment
│   └── static/
│       └── index.html          # Responsive web UI with sidebar, projects, A2UI renderer & dark mode
├── agents-cli-manifest.yaml    # Deployment manifest for agents-cli tool
├── demo.gif                    # Animated demonstration preview
├── pyproject.toml              # Dependencies and project definition
└── README.md                   # Documentation
```

---

## Setup & Local Execution

### Prerequisites

- **Python**: Version 3.11 or higher
- **uv**: Fast Python package installer (`pip install uv`)
- **Google Cloud SDK**: Logged in with a GCP project where Vertex AI and Firestore are enabled

### Installation

1. Clone the repository and install dependencies:
   ```bash
   uv sync
   ```

2. Authenticate with Google Cloud:
   ```bash
   gcloud auth application-default login
   ```

### Running the Agent Locally

To query the agent from the CLI using `agents-cli`:
```bash
uv run agents-cli run "Tell me about the geography and rise of the Maurya Empire"
```

### Running the Web Server Locally

1. Start the FastAPI server locally:
   ```bash
   uv run uvicorn app.fast_api_app:app --host 0.0.0.0 --port 8080
   ```

2. Open your web browser to `http://localhost:8080` to interact with the web interface.

---

## 📱💻 How to Access & Use Histogeo Tutor (Mobile & Desktop)

Histogeo Tutor is fully responsive and designed to work on both **Desktop computers** (Chrome, Firefox, Safari, Edge) and **Mobile devices** (iOS Safari, Android Chrome, tablets).

### Accessing the Web UI

- **Desktop Browser**: Open `http://localhost:8080` in your web browser.
- **Mobile Device (Same Wi-Fi Network)**:
  1. Find your desktop computer's local IP address (e.g. `192.168.1.50` on Linux/Mac via `ip a` or `ifconfig`, or `ipconfig` on Windows).
  2. Start the server bound to `0.0.0.0`:
     ```bash
     uv run uvicorn app.fast_api_app:app --host 0.0.0.0 --port 8080
     ```
  3. Open `http://<YOUR_LOCAL_IP>:8080` in Chrome or Safari on your mobile phone or tablet.
- **Deployed Cloud Run**: Simply navigate to your deployed Cloud Run HTTPS URL on any mobile phone, tablet, or desktop browser.

### How to Use App Features

1. **Ask a Study Question**:
   - Type any History or Geography question into the chat box (e.g. *"Tell me about the rise of the Maurya Empire"* or *"Compare the lengths of major Indian rivers with a chart"*).
   - Tap or click **Send**.
2. **View Interactive Cards & Visuals**:
   - Fact-checked Wikipedia summaries will render in structured A2UI cards.
   - Scene illustrations or Matplotlib timelines and bar charts will automatically display inside the card.
3. **Organize Projects & Study Sessions**:
   - Click **+ New Project** in the sidebar to start a new chat session (e.g., *"Ancient India Revision"*, *"River Systems"*).
   - Easily tap between projects on mobile or desktop to view individual chat histories.
4. **Export Study Notes**:
   - Click the **Save Notes** button on any agent response card to instantly download a Markdown (`.md`) file containing summary notes and embedded image links.
5. **Toggle Dark / Light Mode**:
   - Tap the **Sun/Moon icon** in the top-right header to switch between Dark and Light themes. Your preference is automatically saved across visits.

---

## Deployment Instructions

### 1. Deploy Agent to Vertex AI Agent Runtime

Deploy the core agent package to Vertex AI Reasoning Engine using `agents-cli`:
```bash
uv run agents-cli deploy \
  --project=YOUR_PROJECT_ID \
  --region=us-east1
```

### 2. Deploy Frontend to Google Cloud Run

Deploy the web interface container to Cloud Run:
```bash
gcloud run deploy histogeo-tutor-frontend \
  --source=frontend \
  --region=us-central1 \
  --allow-unauthenticated \
  --set-env-vars="AGENT_ENGINE_RESOURCE_NAME=projects/YOUR_PROJECT_NUMBER/locations/us-east1/reasoningEngines/YOUR_ENGINE_ID,AGENT_DIRECTORY=app"
```

---

## License

Copyright 2026 Google LLC. Licensed under the Apache License, Version 2.0.
