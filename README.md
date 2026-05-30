# AI App Compiler Dashboard
### Architecture & Planning Document
*Advanced Full-Stack LLM-Driven Compiler Pipeline*

---

## 1. System Overview

AI App Compiler Dashboard is a browser-based single-page application powered by the Groq API (Llama 3.3 70B). The compiler pipeline translates natural language prompts into relational sandbox applications complete with FastAPI backends, SQLite databases, and structured UI components. The FastAPI backend (`app.py`) orchestrates all pipeline stages and spawns live sandbox environments at runtime.

```
┌──────────────────────────────────────────────────────────┐
│                    Browser (Client)                       │
│                                                          │
│  ┌─────────────┐  ┌─────────────┐  ┌────────────────┐  │
│  │  Prompt UI  │  │  Code View  │  │ Sandbox Preview│  │
│  └──────┬──────┘  └──────┬──────┘  └───────┬────────┘  │
│         │                │                  │           │
│  ┌──────▼────────────────▼──────────────────▼────────┐  │
│  │           Vite + React Dashboard (JS)              │  │
│  │   Pipeline Trigger | Stage Monitor | Log Stream    │  │
│  └───────────────────────┬────────────────────────────┘  │
└──────────────────────────┼───────────────────────────────┘
                           │ HTTPS (REST)
           ┌───────────────▼──────────────────┐
           │      FastAPI Backend (app.py)     │
           │                                  │
           │  ┌────────────────────────────┐  │
           │  │    Agent Router (Python)   │  │
           │  │  intentExtractor           │  │
           │  │  architect | schemaDesigner│  │
           │  │  codeGen | validator       │  │
           │  │  repair                    │  │
           │  └──────────────┬─────────────┘  │
           │                 │                │
           │  ┌──────────────▼─────────────┐  │
           │  │     Groq API Wrapper        │  │
           │  └──────────────┬─────────────┘  │
           └─────────────────┼────────────────┘
                             │ HTTPS (REST)
                 ┌───────────▼───────────┐
                 │       Groq API         │
                 │    Llama 3.3 70B       │
                 └───────────────────────┘
           ┌──────────────────────────────────┐
           │       /runtime  (sandbox)         │
           │  SQLite DB  |  FastAPI Server     │
           │  port 8001  |  Live Preview       │
           └──────────────────────────────────┘
```

---

## 2. Repository Structure

The project follows a clean separation between the frontend dashboard, the compiler logic pipeline, and the generated runtime sandbox environments:

| Directory / File | Purpose |
| ---------------- | ------- |
| `frontend/` | Vite + React + Tailwind CSS client dashboard |
| `pipeline/` | Compiler logic stages: Intent Extraction, Architecture, Schema, Validator, Repair, Runtime |
| `runtime/` | Executable sandbox containing generated SQLite databases and APIs |
| `app.py` | FastAPI dashboard backend server |
| `run_compiler.py` | Local bootstrap script — builds frontend and serves the FastAPI app |

---

## 3. Compiler Pipeline

The compiler pipeline is the core of the application. It accepts a natural language description of an app, passes it through a series of LLM-powered stages, and outputs a fully runnable sandbox application.

```
┌──────────────────────────────────────────────────────┐
│              AI App Compiler Pipeline                 │
│                                                      │
│  Natural Language Prompt                             │
│         │                                            │
│         ▼                                            │
│  [1] Intent Extraction  ──► Extract goals & domain  │
│         │                                            │
│         ▼                                            │
│  [2] Architecture Gen   ──► Define modules & APIs   │
│         │                                            │
│         ▼                                            │
│  [3] Schema Design      ──► SQLite table schemas    │
│         │                                            │
│         ▼                                            │
│  [4] Code Generation    ──► FastAPI + UI code       │
│         │                                            │
│         ▼                                            │
│  [5] Validator          ──► Syntax & schema checks  │
│         │                                            │
│         ▼                                            │
│  [6] Auto-Repair        ──► Fix errors, re-validate │
│         │                                            │
│         ▼                                            │
│  [7] Runtime Sandbox    ──► Spawn live preview app  │
│                                                      │
└──────────────────────────────────────────────────────┘
```

| Stage | Module | Key Behavior |
| ----- | ------ | ------------ |
| 1 | Intent Extraction | Parses user prompt to extract app goals, domain, entities, and constraints |
| 2 | Architecture Generation | Defines modules, API routes, and relationships between components |
| 3 | Schema Design | Produces normalized SQLite table schemas with data types and foreign keys |
| 4 | Code Generation | Emits FastAPI backend code and structured UI component definitions |
| 5 | Validator | Runs syntax checks, schema validation, and import verification |
| 6 | Auto-Repair | Detects and fixes errors from the validator, then re-validates |
| 7 | Runtime Sandbox | Spawns a live preview server with the generated database and API |

---

## 4. Agent Design

Each pipeline stage is a different persona of the Groq LLM, activated by swapping the `system_instruction` sent with each API call. All agents are designed for structured, deterministic output to enable reliable downstream parsing.

| Agent | System Role | Key Behavior |
| ----- | ----------- | ------------ |
| **Intent Extractor** | Requirements analyst | Returns structured JSON of app goals, entities, and constraints |
| **Architect** | Software architect | Defines API modules, relationships, and component boundaries |
| **Schema Designer** | Database engineer | Produces normalized SQLite schemas with keys and types |
| **Code Generator** | Senior developer | Emits FastAPI Python code and UI structure definitions |
| **Validator** | QA engineer | Checks syntax correctness, import validity, and schema compliance |
| **Repair Agent** | Debugger | Identifies and fixes specific errors reported by the Validator |

### Conversation Memory

- Chat history is maintained as an array of `{role, parts}` objects.
- The last 10 turns are sent with each request to stay within context limits.
- History resets when the pipeline switches stages (clean slate per stage session).

---

## 5. Local Development & Execution

### Step 1 — Clone the Repository

```bash
git clone <your-repo-url>
cd <your-repo-folder>
```

### Step 2 — Install Python Dependencies

Ensure Python 3.10+ is installed, then:

```bash
pip install fastapi uvicorn pydantic
```

### Step 3 — Install Node Dependencies

```bash
cd frontend
npm install
cd ..
```

### Step 4 — Run the Compiler Bootstrapper

This builds the frontend and spawns the FastAPI application:

```bash
python run_compiler.py
```

Open [http://localhost:8000](http://localhost:8000) in your browser.

---

## 6. State Management

All compilation state lives in server-side module-level variables during a pipeline run. After generation, state is persisted to the runtime SQLite database for sandbox continuity.

```javascript
groqApiKey;       // Groq API key (entered via dashboard sidebar)
currentStage;     // Active pipeline stage ID
pipelineHistory;  // [{role, parts}] — full LLM conversation for repair context
generatedSchema;  // Parsed SQLite table definitions from Schema stage
generatedCode;    // FastAPI code output from Code Generation stage
validationErrors; // string[] — error list from Validator passed to Repair Agent
sandboxPort;      // Port assigned to the live preview sandbox
```

| Variable | Type | Description |
| -------- | ---- | ----------- |
| `groqApiKey` | `string` | Groq API key (entered via dashboard sidebar) |
| `currentStage` | `string` | Active pipeline stage ID |
| `pipelineHistory` | `[{role, parts}]` | Full LLM conversation for repair context |
| `generatedSchema` | `object` | Parsed SQLite table definitions from Schema stage |
| `generatedCode` | `object` | FastAPI code output from Code Generation stage |
| `validationErrors` | `string[]` | Error list from Validator passed to Repair Agent |
| `sandboxPort` | `number` | Port assigned to the live preview sandbox |

> **Future:** Persist pipeline runs to Firebase Firestore for cross-session history and team collaboration.

---

## 7. Key Technical Decisions

| Decision | Rationale |
| -------- | --------- |
| Groq `Llama 3.3 70B` | Fast inference, low latency, strong code generation for the compiler pipeline |
| Vanilla JS over React (Agent Router) | Zero build tooling for the core routing layer; instant deploy and easy collaboration |
| SQLite for sandboxes | Self-contained, zero-config databases ideal for ephemeral sandbox environments |
| FastAPI over Express | Native async support, auto-generated OpenAPI docs, and Pydantic validation |
| Vite + React + Tailwind (Dashboard) | Modern DX with hot reload; Tailwind keeps UI consistent without a design system dependency |
| Client-side API key input | Prototype simplicity; production should proxy through the FastAPI backend |
| No backend for compilation state | Keeps the compiler stateless and horizontally scalable — each run is independent |

---

## 8. Known Limitations & Roadmap

| Limitation | Planned Fix |
| ---------- | ----------- |
| API key exposed in browser sidebar | Add a backend proxy route in FastAPI to hold secrets server-side |
| No data persistence across deploys | Integrate Firebase Firestore + Auth for cross-session pipeline history |
| Single sandbox per session | Multi-sandbox support with named project slots and persistent volumes |
| Ephemeral filesystem on Render free tier | Attach a persistent disk at `/runtime` for database durability |
| No voice input for prompt entry | Add Web Speech API for mic-based prompt dictation |
| Static motivational messages in UI | Make all status messages dynamic via a motivator LLM call |
| No real-time build logs streaming | Add Server-Sent Events (SSE) from FastAPI to stream pipeline progress |
