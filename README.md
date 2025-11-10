# ElderCare Copilot

Conversational safety net that helps older adults (and the people who care for them) keep food, medicines, and daily habits in harmony. The project blends a LangGraph care agent, voice-first UX, and searchable clinical evidence into a single assistant you can run locally.

---

## Built For Aging In Place

- **Medication awareness** : logs meals and prescriptions automatically, then checks for risky food–drug combinations.
- **Warm conversations** : uses Qwen 3 8B INT4 through Ollama to answer in plain, supportive language.
- **Voice first** : browser mic input, Microsft Whisper-powered transcription, and Microsoft TTS to keep the chat hands-free.
- **Explainable results** : pulls evidence from a curated interaction database, surfaces similar cases, and cites fresh web research via Brave MCP tools.

---

## System Overview

```text
                          ┌──────────────────────────┐
                          │ React + Tailwind UI      │
                          │ • Chat & timeline        │
  Microphone  ───────────▶│ • Voice capture / TTS    │
                          └──────────┬──────────────┘
                                     │ REST / WebSocket
                          ┌──────────▼──────────────┐
                          │ FastAPI Orchestrator    │
                          │ • LangGraph agent       │
                          │ • MCP tool routing      │
                          └──────────┬──────────────┘
                                     │ LangGraph state
                          ┌──────────▼──────────────┐
                          │ Care Agent              │
                          │ • Food/drug extraction  │
                          │ • DB + Chroma search    │
                          │ • Brave web lookups     │
                          └──────────┬──────────────┘
                ┌───────────────────┴─────────────────────┐
                │ Local Services                          │
                │ • MySQL Food-Drug interaction           │
                │ • Chroma vector store                   │
                │ • Whisper ASR, Coqui TTS, Edge Voices   │
                └─────────────────────────────────────────┘
```

---

## Quick Start

### 1. Prerequisites

- Python 3.10+ (tested with 3.11)
- Node 18+ (for the Vite/React frontend)
- [Ollama](https://ollama.ai/download) with `qwen3:8b` and `nomic-embed-text` models pulled:
  ```bash
  ollama pull qwen3:8b
  ollama pull nomic-embed-text
  ```
- (Optional) Brave Search MCP key for fresher evidence (`BRAVE_API_KEY`)
Note: The default model downloaded from ollama is in INT4

### 2. Backend (FastAPI + LangGraph)

```bash
python -m venv .venv
.venv\Scripts\activate        # On Windows
pip install -r requirements.txt

# environment configuration
# create a .env file with DB credentials & optional BRAVE_API_KEY

uvicorn api_server:app --reload --port 8000
```

When the server boots it will:

- spin up the LangGraph agent (`new_agent_trial.py`)
- attach MCP tools for the local SQLite care DB and Brave Search
- expose REST endpoints for chat, TTS, health checks, and thread resets

### 3. Frontend (Voice-first companion)

```bash
cd frontend
npm install
npm run dev -- --host
```

Open `http://localhost:5173` to chat, type, or speak with the assistant. Responses can be read aloud through Edge Neural voices.

### 4. Optional: Local Voice Loop

The `asr_tts/` toolkit lets you run the full microphone → transcript → LLM → speech pipeline offline:

```bash
cd asr_tts
pip install -r requirements.txt
python main.py
```

Whisper records and transcribes, a stub LLM response is generated (swap in the agent API to go live), and Coqui TTS renders the reply.

---

## Key Modules

- `api_server.py` · FastAPI layer, conversation endpoints, and Microsoft Edge TTS bridge.
- `new_agent_trial.py` · LangGraph control loop that enforces medication logging, similarity search, and Brave news lookups.
- `food_drug_interaction_agent/` · Vector search, SQL tool wrappers, and summarisation logic for exact/similar interactions.
- `frontend/` · React app with Tailwind styling, speech recognition, and wellness-themed chat UI.
- `asr_tts/` · Whisper-based ASR, Coqui TTS, and interaction logger for offline demos.
- `evaluation/` + `model selection/` · Notebooks used to benchmark base models (Meditron, Qwen) for healthcare dialogue quality.

---

## Safety Guardrails

- **Structured logging** · every meal or medication mentioned is written to the care database and time-stamped.
- **Interaction verification** · searches exact DB matches first, if there isnt a exact match, similar cases will be returned, Brave search to surface recent updates.
- **Voice guidelines** · Allow elderly to interact with the system via voice.
- **Disclaimers** · UI and agent responses remind users that the assistant is informational, not a clinician.

---

## Repository Layout

```text
├── api_server.py                # FastAPI entry point
├── frontend/                    # Vite + React client (allow voice via UI)
├── food_drug_interaction_agent/ # LangGraph tools, vector search, index builder
├── asr_tts/                     # Local deployment of ASR/TTS (not used)
├── evaluation/                  # Agent evaluation scripts 
├── model selection/             # Jupyter notebooks for base model studies
└── README/                      # Additional setup guides (quickstart, voice, UI)
```

---

## Contributors:

-Dau Vu Dang Khoi: vdk.dau.2024@mitb.smu.edu.sg
-Koh Bo Xiang Cedric: cedric.koh.2024@mitb.smu.edu.sg
-Li Xinjie ✉: xinjie.li.2024@mitb.smu.edu.sg
-Tran Binh Minh: bm.tran.2024@mitb.smu.edu.sg
-Bryan Chang Tze Kin: tk.chang.2024@mitb.smu.edu.sg




