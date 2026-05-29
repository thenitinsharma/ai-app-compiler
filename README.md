# AI App Compiler Dashboard

An advanced, full-stack LLM-driven compiler pipeline that translates natural language prompts into relational sandbox applications complete with FastAPI backends, SQLite databases, and structured UI components.

---

## 🏗 Repository Structure

*   `frontend/` — Vite + React + Tailwind CSS client dashboard.
*   `pipeline/` — Compiler logic stages (Intent Extraction, Architecture, Schema, Validator, Repair, Runtime).
*   `runtime/` — Executable sandbox containing generated SQLite databases and APIs.
*   `app.py` — FastAPI dashboard backend server.
*   `run_compiler.py` — Local bootstrap script to build the frontend and serve the FastAPI application.

---

## 💻 Local Development & Execution

To compile and execute the entire pipeline locally:

1.  **Clone the Repository**:
    ```bash
    git clone <your-repo-url>
    cd <your-repo-folder>
    ```

2.  **Install Python Dependencies**:
    Make sure you have Python 3.10+ installed.
    ```bash
    pip install fastapi uvicorn pydantic
    ```

3.  **Install Node Dependencies**:
    ```bash
    cd frontend
    npm install
    cd ..
    ```

4.  **Run the Compiler Bootstrapper**:
    This builds the frontend and spawns the FastAPI application.
    ```bash
    python run_compiler.py
    ```
    Open [http://localhost:8000](http://localhost:8000) in your browser.

---

## ⚡ Deployment Guide

### 1. Push Code to GitHub

Initialize git, track the root files, and push to your GitHub repository:
```bash
git init
git add .
git commit -m "feat: setup compiler dashboard deployment support"
git branch -M main
git remote add origin git@github.com:YOUR_USERNAME/YOUR_REPOSITORY.git
git push -u origin main
```

---

### 2. Deploy Frontend on Vercel

The frontend runs on Vercel and communicates with a hosted FastAPI backend.

1.  Log in to [Vercel](https://vercel.com) and click **Add New > Project**.
2.  Import your GitHub repository.
3.  Configure Project Settings:
    *   **Framework Preset**: Select `Vite`
    *   **Root Directory**: Set to `frontend`
    *   **Build Command**: `npm run build`
    *   **Output Directory**: `dist` (Automatically configured by the dual-mode `vite.config.js` settings)
4.  Add **Environment Variables**:
    *   `VITE_API_BASE_URL`: The URL of your hosted backend (e.g. `https://api-compiler-backend.onrender.com`).
5.  Click **Deploy**.

---

### 3. Deploy Backend (Render, Railway, VPS, or Docker)

The backend hosts the API and spawns the live sandbox preview environments.

#### Option A: Render (Web Service)
1.  Create a new **Web Service** pointing to your GitHub repository.
2.  Configure Settings:
    *   **Runtime**: `Python`
    *   **Build Command**: `pip install -r requirements.txt`
    *   **Start Command**: `uvicorn app:app --host 0.0.0.0 --port $PORT`
3.  Add **Environment Variables**:
    *   Add any Groq API Key env vars if needed (or configure them via the dashboard client sidebar).
4.  Set up a **Persistent Disk** (Optional but Recommended):
    *   Since Vercel and Render filesystems are ephemeral, mount a volume at `/runtime` (size: 1GB is more than enough) to persist compiler databases (`app.db`).

#### Option B: Docker / VPS
Expose port `8000` (FastAPI backend) and port `8001` (Live Sandboxes). Ensure ports are bound properly to allow standard HTTP requests and iframe connections.
