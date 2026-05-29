import os
import time
import sqlite3
import uvicorn
import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import pipeline stages
from pipeline.intent_extractor import extract_intent
from pipeline.architect import design_system
from pipeline.schema_generator import generate_schemas
from pipeline.validator import validate_schemas
from pipeline.repair_engine import repair_schemas
from pipeline.runtime_generator import generate_runtime
from pipeline.translator import translate_llm_schemas
from sandbox_manager import SandboxManager

app = FastAPI(title="AI App Compiler Dashboard API", version="1.0.0")

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Workspace directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RUNTIME_DIR = os.path.join(BASE_DIR, "runtime")
STATIC_DIR = os.path.join(BASE_DIR, "static")

# Public base URL for sandbox proxy
BASE_URL = os.getenv("RENDER_EXTERNAL_URL", "http://127.0.0.1:8000")

# Ensure required directories exist
os.makedirs(RUNTIME_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

# Instantiate Sandbox Manager
sandbox_mgr = SandboxManager(RUNTIME_DIR)

class CompileRequest(BaseModel):
    prompt: str

class SandboxLaunchRequest(BaseModel):
    intent: dict
    architecture: dict
    ui_schema: dict
    api_schema: dict
    db_schema: dict
    auth_schema: dict

# ── Sandbox Proxy Routes ────────────────────────────────────────────────────

@app.get("/sandbox-preview")
async def sandbox_preview_root():
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get("http://127.0.0.1:8001/")
            return HTMLResponse(content=resp.text, status_code=resp.status_code)
        except Exception:
            return HTMLResponse("<h2>Sandbox is not running. Please compile an app first.</h2>", status_code=503)

@app.api_route("/sandbox-preview/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def sandbox_proxy(path: str, request: Request):
    sandbox_url = f"http://127.0.0.1:8001/{path}"
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.request(
                method=request.method,
                url=sandbox_url,
                headers={k: v for k, v in request.headers.items() if k.lower() != "host"},
                content=await request.body(),
                params=request.query_params,
            )
            return StreamingResponse(
                content=iter([resp.content]),
                status_code=resp.status_code,
                headers=dict(resp.headers),
            )
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"Sandbox unreachable: {str(e)}")

# ── API Routes ───────────────────────────────────────────────────────────────

@app.post("/api/sandbox/launch")
def launch_sandbox(req: SandboxLaunchRequest):
    try:
        raw_llm_schemas = {
            "intent": req.intent,
            "architecture": req.architecture,
            "ui_schema": req.ui_schema,
            "api_schema": req.api_schema,
            "db_schema": req.db_schema,
            "auth_schema": req.auth_schema
        }
        
        translated_schemas = translate_llm_schemas(raw_llm_schemas)
        validation = validate_schemas(translated_schemas)
        
        repaired_schemas = translated_schemas
        repair_log = {"repairs": [], "retry_count": 0, "max_retries_hit": False}
        if not validation["valid"]:
            repaired_schemas, repair_log = repair_schemas(translated_schemas, validation, retry_count=1)
            validation = validate_schemas(repaired_schemas)
            
        if not validation["valid"]:
            raise HTTPException(
                status_code=500,
                detail=f"Compiler Error: Failed to resolve translated schema constraints. Errors: {validation['errors']}"
            )
            
        raw_modules = raw_llm_schemas["architecture"].get("entities", [])
        modules_list = []
        for m in raw_modules:
            if isinstance(m, dict):
                modules_list.append(m.get("name", ""))
            elif isinstance(m, str):
                modules_list.append(m)
                
        blueprint = {
            "app_type": raw_llm_schemas["intent"].get("app_type", "crm"),
            "modules": modules_list
        }
        manifest = generate_runtime(repaired_schemas, RUNTIME_DIR, blueprint)
        
        sandbox_started = sandbox_mgr.start(port=8001)
        
        return {
            "success": True,
            "validation": validation,
            "repair_log": repair_log,
            "runtime_manifest": manifest,
            "schemas": repaired_schemas,
            "sandbox": {
                "url": f"{BASE_URL}/sandbox-preview",
                "online": sandbox_started
            }
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to launch sandbox: {str(e)}")

@app.post("/api/compile")
def compile_application(req: CompileRequest):
    prompt = req.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Application description prompt cannot be empty.")

    metrics = {}
    total_start = time.perf_counter()

    st1_start = time.perf_counter()
    extracted = extract_intent(prompt)
    metrics["intent_extraction_ms"] = round((time.perf_counter() - st1_start) * 1000, 2)
    classification = extracted["classification"]
    intent_ir = extracted["intent_ir"]

    st2_start = time.perf_counter()
    blueprint = design_system(intent_ir)
    metrics["system_design_ms"] = round((time.perf_counter() - st2_start) * 1000, 2)

    st3_start = time.perf_counter()
    raw_schemas = generate_schemas(blueprint, inject_bug=True)
    metrics["schema_generation_ms"] = round((time.perf_counter() - st3_start) * 1000, 2)

    st4_start = time.perf_counter()
    validation_pre = validate_schemas(raw_schemas)
    metrics["validation_pre_ms"] = round((time.perf_counter() - st4_start) * 1000, 2)

    repaired_schemas = raw_schemas
    repair_log = {
        "repairs": [],
        "retry_count": 0,
        "max_retries_hit": False
    }
    validation_post = validation_pre
    
    if not validation_pre["valid"]:
        st5_start = time.perf_counter()
        repaired_schemas, repair_log = repair_schemas(raw_schemas, validation_pre, retry_count=1)
        metrics["repair_ms"] = round((time.perf_counter() - st5_start) * 1000, 2)
        
        st4_post_start = time.perf_counter()
        validation_post = validate_schemas(repaired_schemas)
        metrics["validation_post_ms"] = round((time.perf_counter() - st4_post_start) * 1000, 2)
    else:
        metrics["repair_ms"] = 0.0
        metrics["validation_post_ms"] = 0.0

    if not validation_post["valid"]:
        raise HTTPException(
            status_code=500,
            detail=f"Compiler Error: Failed to resolve validation inconsistencies. Errors: {validation_post['errors']}"
        )
        
    st6_start = time.perf_counter()
    manifest = generate_runtime(repaired_schemas, RUNTIME_DIR, blueprint)
    metrics["runtime_generation_ms"] = round((time.perf_counter() - st6_start) * 1000, 2)

    sandbox_started = sandbox_mgr.start(port=8001)
    
    metrics["total_compile_ms"] = round((time.perf_counter() - total_start) * 1000, 2)

    return {
        "success": True,
        "classification": classification,
        "metrics": metrics,
        "stages": {
            "intent_extraction": intent_ir,
            "system_design": blueprint,
            "schemas": repaired_schemas,
            "validation_pre": validation_pre,
            "repair_log": repair_log,
            "validation_post": validation_post,
            "runtime_manifest": manifest
        },
        "sandbox": {
            "url": f"{BASE_URL}/sandbox-preview",
            "online": sandbox_started
        }
    }

@app.get("/api/sandbox/db-records")
def get_sandbox_db_records():
    db_path = os.path.join(RUNTIME_DIR, "app.db")
    if not os.path.exists(db_path):
        return {"tables": {}, "message": "Database not initialized. Please compile the app first."}
        
    tables_data = {}
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall() if not row[0].startswith("sqlite_")]
        
        for table in tables:
            cursor.execute(f'SELECT * FROM "{table}"')
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
            
            table_rows = []
            for r in rows:
                table_rows.append(dict(zip(columns, r)))
            tables_data[table] = table_rows
            
        conn.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query SQLite DB: {e}")
        
    return {"tables": tables_data}

@app.post("/api/sandbox/stop")
def stop_sandbox():
    sandbox_mgr.stop()
    return {"status": "success", "message": "Sandbox process terminated."}

@app.on_event("shutdown")
def shutdown_event():
    sandbox_mgr.stop()

# Serve compiler dashboard home
@app.get("/")
def get_dashboard():
    dashboard_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(dashboard_file):
        return FileResponse(
            dashboard_file,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
    return HTMLResponse("<h1>Compiler Dashboard UI is compiling... Please wait</h1>")

# Mount Static Files Directory
if os.path.exists(STATIC_DIR) and os.listdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
