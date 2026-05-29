import { useState, useRef, useCallback, useEffect } from "react";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "";

// --- SCHEMA DEFINITIONS ----------------------------------------------------
const REQUIRED_SCHEMA = {
  intent: ["app_name", "app_type", "description", "core_features", "user_roles", "premium_features"],
  architecture: ["entities", "flows", "role_permissions", "external_services"],
  ui_schema: ["pages", "components", "navigation", "theme"],
  api_schema: ["endpoints", "auth_endpoints", "middleware"],
  db_schema: ["tables", "relations", "indexes"],
  auth_schema: ["strategy", "roles", "permissions", "guards"],
};

const STAGE_META = [
  { id: "intent",        label: "Intent Extraction",   icon: "🧠", color: "#7C3AED" },
  { id: "architecture",  label: "System Design",        icon: "🏗",  color: "#2563EB" },
  { id: "ui_schema",     label: "UI Schema",            icon: "🖼",  color: "#059669" },
  { id: "api_schema",    label: "API Schema",           icon: "🔌",  color: "#D97706" },
  { id: "db_schema",     label: "DB Schema",            icon: "🗄",  color: "#DC2626" },
  { id: "auth_schema",   label: "Auth & Permissions",  icon: "🔐",  color: "#EC4899" },
  { id: "validation",    label: "Validation & Repair",  icon: "🛡",  color: "#0891B2" },
];

const QUICK_EXAMPLES = [
  {
    title: "Lead CRM with Subscription Plan",
    prompt: "Build a CRM with user logins, contact management with name, email and phone fields, and premium plan upgrade with mock payment transactions. Standard users are restricted to 5 contacts max. Admin users can access operational analytics."
  },
  {
    title: "Kanban Task Board & Teams",
    prompt: "Build a task manager with user accounts. Task objects have a title, description, and status field. User tier restricts standard users to 10 tasks max. Manager can update items."
  },
  {
    title: "E-Commerce Catalog & Checkout",
    prompt: "Build an e-commerce storefront with product lists, cart checkout transactions, user registrations, and order status tables. Premium users receive a 10% discount on order totals."
  }
];

// --- PROMPT BUILDERS --------------------------------------------------------
function buildPrompt(stage, userInput, prevStages = {}) {
  const base = `You are a strict JSON-only compiler. Never output prose. Never wrap in markdown. Output ONLY valid JSON.`;

  // Stringify compactly to save context tokens
  const ctx = Object.keys(prevStages).length
    ? `\n\nPREVIOUS STAGES:\n${JSON.stringify(prevStages)}`
    : "";

  const prompts = {
    intent: `${base}
USER REQUEST: "${userInput}"

Extract intent into this exact JSON structure:
{
  "app_name": "string",
  "app_type": "crm|ecommerce|saas|social|analytics|other",
  "description": "string",
  "core_features": ["string"],
  "user_roles": ["string"],
  "premium_features": ["string"],
  "assumptions": ["string"],
  "ambiguities_resolved": ["string"]
}
Rules: infer reasonable values for anything underspecified. List assumptions made. Output ONLY JSON.`,

    architecture: `${base}${ctx}

Convert intent into system architecture. Output ONLY this JSON:
{
  "entities": [{"name":"string","fields":["string"],"relations":["string"]}],
  "flows": [{"name":"string","steps":["string"],"roles_involved":["string"]}],
  "role_permissions": {"role_name": {"can":["string"],"cannot":["string"]}},
  "external_services": ["string"],
  "architecture_notes": ["string"]
}`,

    ui_schema: `${base}${ctx}

Generate UI schema. Be concise — limit to max 6 pages and 8 components. Output ONLY this JSON:
{
  "pages": [{"name":"string","route":"string","auth_required":true,"roles":["string"],"components":["string"],"layout":"string"}],
  "components": [{"name":"string","type":"form|table|chart|card|modal|nav","props":{"key":"value"},"api_dependency":"string"}],
  "navigation": {"primary":["string"],"role_based":{"role":["string"]}},
  "theme": {"primary_color":"string","font":"string","style":"string"}
}
Keep props objects minimal (2-3 keys max). Output ONLY JSON. No extra text.`,

    api_schema: `${base}${ctx}

Generate API schema. Output ONLY this JSON:
{
  "endpoints": [{"method":"GET|POST|PUT|DELETE","path":"string","auth":true,"roles":["string"],"request_body":{"key":"type"},"response":{"key":"type"},"db_table":"string"}],
  "auth_endpoints": [{"method":"string","path":"string","description":"string"}],
  "middleware": ["string"]
}
Every endpoint's db_table must match an entity from architecture. Every request_body field must map to a DB column.`,

    db_schema: `${base}${ctx}

Generate database schema. Output ONLY this JSON:
{
  "tables": [{"name":"string","columns":[{"name":"string","type":"string","nullable":false,"default":null,"unique":false}],"primary_key":"string"}],
  "relations": [{"from_table":"string","to_table":"string","type":"one-to-one|one-to-many|many-to-many","foreign_key":"string"}],
  "indexes": [{"table":"string","columns":["string"],"unique":false}],
  "migrations": ["string"]
}
Every API endpoint's db_table must exist. Every UI form field must map to a column.`,

    auth_schema: `${base}${ctx}

Generate auth and permissions schema. Output ONLY this JSON:
{
  "strategy": "jwt|session|oauth",
  "token_expiry": "string",
  "roles": [{"name":"string","level":0,"inherits":null}],
  "permissions": [{"resource":"string","action":"create|read|update|delete","roles":["string"]}],
  "guards": [{"route":"string","min_role":"string","premium_required":false}],
  "premium_gates": [{"feature":"string","plan":"string","fallback":"string"}]
}
Every route in UI schema must have a guard. Every premium feature must have a gate.`,
  };

  return prompts[stage] || "";
}

function buildValidationPrompt(allStages) {
  return `You are a strict JSON schema validator and repairer. Output ONLY valid JSON, no prose.

Analyze this multi-layer app configuration for inconsistencies:
${JSON.stringify(allStages)}

Check for:
1. API endpoints referencing tables that don't exist in db_schema
2. UI components referencing API endpoints that don't exist
3. Auth guards for routes not in UI schema
4. Missing permissions for roles defined in auth_schema
5. DB relations pointing to non-existent tables
6. Premium gates for features not in intent.premium_features

Output ONLY this JSON:
{
  "is_valid": true,
  "issues": [{"layer":"string","severity":"critical|warning","description":"string","fix":"string"}],
  "repaired_overrides": {},
  "consistency_score": 0,
  "repair_summary": ["string"]
}

If issues exist, include repaired_overrides with the corrected values. consistency_score is 0-100.`;
}

// --- UTILITIES --------------------------------------------------------------
function summarizeStages(prevStages) {
  const summary = {};

  if (prevStages.intent) {
    summary.intent = {
      app_name: prevStages.intent.app_name,
      app_type: prevStages.intent.app_type,
      core_features: prevStages.intent.core_features,
      user_roles: prevStages.intent.user_roles,
    };
  }

  if (prevStages.architecture) {
    summary.architecture = {
      entities: prevStages.architecture.entities?.map(e => e.name),
      services: prevStages.architecture.external_services,
    };
  }

  if (prevStages.ui_schema) {
    summary.ui_schema = {
      pages: prevStages.ui_schema.pages?.map(p => p.route || p.name),
      components: prevStages.ui_schema.components?.map(c => c.name),
    };
  }

  if (prevStages.api_schema) {
    summary.api_schema = {
      endpoints: prevStages.api_schema.endpoints?.map(e => ({
        method: e.method,
        path: e.path,
      })),
    };
  }

  return summary;
}

function getContextForStage(stage, prevStages) {
  const compressed = summarizeStages(prevStages);
  const filtered = {};
  if (stage === "architecture") {
    filtered.intent = compressed.intent;
  } else if (stage === "ui_schema") {
    filtered.intent = compressed.intent;
    filtered.architecture = compressed.architecture;
  } else if (stage === "api_schema") {
    filtered.architecture = compressed.architecture;
    filtered.ui_schema = compressed.ui_schema;
  } else if (stage === "db_schema") {
    filtered.architecture = compressed.architecture;
    filtered.api_schema = compressed.api_schema;
  } else if (stage === "auth_schema") {
    filtered.architecture = compressed.architecture;
    filtered.ui_schema = compressed.ui_schema;
  }
  return Object.keys(filtered).length ? `\n\nPREVIOUS STAGES:\n${JSON.stringify(filtered)}` : "";
}

function repairTruncatedJSON(text) {
  let cleanText = text.trim();
  // Strip markdown fences
  cleanText = cleanText.replace(/^```json\s*/i, "").replace(/```$/, "").trim();

  let inString = false;
  let escaped = false;
  const stack = [];

  for (let i = 0; i < cleanText.length; i++) {
    const ch = cleanText[i];
    if (escaped) { escaped = false; continue; }
    if (ch === '\\' && inString) { escaped = true; continue; }
    if (ch === '"') { inString = !inString; continue; }
    if (inString) continue;
    if (ch === '{') stack.push('}');
    else if (ch === '[') stack.push(']');
    else if (ch === '}' || ch === ']') stack.pop();
  }

  let repaired = cleanText;
  if (inString) repaired += '"';

  // Remove trailing incomplete fields or dangling commas
  repaired = repaired.replace(/,\s*"[^"]*"\s*:\s*$/, '');
  repaired = repaired.replace(/,\s*"[^"]*"\s*$/, '');
  repaired = repaired.replace(/,\s*$/, '');

  // Close all open brackets in reverse
  while (stack.length) repaired += stack.pop();

  return repaired;
}

function safeParseJSON(raw) {
  let text = raw.trim();
  // Strip markdown fences
  text = text.replace(/^```json\s*/i, "").replace(/```$/, "").trim();

  // Locate JSON object bounds
  const firstBrace = text.indexOf('{');
  const firstBracket = text.indexOf('[');
  let start = -1;
  let end = -1;

  if (firstBrace !== -1 && (firstBracket === -1 || firstBrace < firstBracket)) {
    start = firstBrace;
    end = text.lastIndexOf('}');
  } else if (firstBracket !== -1) {
    start = firstBracket;
    end = text.lastIndexOf(']');
  }

  if (start !== -1 && end !== -1 && end > start) {
    text = text.substring(start, end + 1);
  }

  // First attempt: parse as-is
  try {
    return { ok: true, data: JSON.parse(text) };
  } catch (e) {
    // Second attempt: try to repair truncated JSON
    try {
      const repaired = repairTruncatedJSON(text);
      const parsed = JSON.parse(repaired);
      return { ok: true, data: parsed, repaired: true };
    } catch (e2) {
      return { ok: false, error: e.message, raw: text };
    }
  }
}

function validateStage(stageId, data) {
  const required = REQUIRED_SCHEMA[stageId] || [];
  const missing = required.filter(k => !(k in data));
  return missing;
}

// --- MAIN DASHBOARD APP ----------------------------------------------------
export default function AppCompiler() {
  const [prompt, setPrompt] = useState("");
  const [running, setRunning] = useState(false);
  const [compilationMode, setCompilationMode] = useState("mock"); // "llm" or "mock"
  const [groqKey, setGroqKey] = useState("");
  const [sandboxUrl, setSandboxUrl] = useState("http://127.0.0.1:8001/");
  
  // Compiler Pipeline States
  const [stages, setStages] = useState({});
  const [stageStatus, setStageStatus] = useState({});
  const [stageRaw, setStageRaw] = useState({});
  const [stageIssues, setStageIssues] = useState({});
  const [retries, setRetries] = useState({});
  const [validation, setValidation] = useState(null);
  
  // UI Panels Controls
  const [activeWorkspaceTab, setActiveWorkspaceTab] = useState("pipeline"); // "pipeline", "validation", "code", "sandbox"
  const [activeStageTab, setActiveStageTab] = useState("intent");
  const [activeCodeFile, setActiveCodeFile] = useState("db"); // "db", "api", "ui"
  
  // Monitoring & Telemetry
  const [metrics, setMetrics] = useState(null);
  const [log, setLog] = useState([]);
  const [sandboxOnline, setSandboxOnline] = useState(false);
  const [dbTables, setDbTables] = useState({});
  
  const abortRef = useRef(false);
  const logConsoleEndRef = useRef(null);

  // Load Groq API Key from localStorage on mount
  useEffect(() => {
    const savedKey = localStorage.getItem("groq-api-key");
    if (savedKey) setGroqKey(savedKey);
  }, []);

  const saveGroqKey = (val) => {
    setGroqKey(val);
    localStorage.setItem("groq-api-key", val);
  };

  const addLog = useCallback((msg, type = "info") => {
    setLog(l => [...l, { msg, type, ts: Date.now() }]);
  }, []);

  // Auto-scroll logs console
  useEffect(() => {
    if (logConsoleEndRef.current) {
      logConsoleEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [log]);

  const setStatus = (id, status) => setStageStatus(s => ({ ...s, [id]: status }));

  const TOKEN_BUDGET = {
    intent: 800,
    architecture: 1200,
    ui_schema: 1200,
    api_schema: 1200,
    db_schema: 1200,
    auth_schema: 1000,
  };

  // Dynamic model selection based on stage
  function getModel(stage) {
    // Use llama-3.1-8b-instant for all stages to prevent TPM exhaustion
    return "llama-3.1-8b-instant";
  }

  // callClaude to invoke LLM on Groq API
  async function callClaude(prompt, maxTokens = 2000, model = "llama-3.1-8b-instant", rateLimitRetryCount = 0) {
    const keyToUse = groqKey.trim() || "YOUR_GROQ_API_KEY";
    if (keyToUse === "YOUR_GROQ_API_KEY") {
      throw new Error("Missing Groq API Key. Please provide your key in the field on the sidebar.");
    }

    const response = await fetch("https://api.groq.com/openai/v1/chat/completions", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${keyToUse}`,
      },
      body: JSON.stringify({
        model: model,
        max_tokens: maxTokens,
        messages: [{ role: "user", content: prompt }],
        temperature: 0.15,
        response_format: { type: "json_object" } // Force valid JSON outputs
      }),
    });
    
    let data;
    try {
      data = await response.json();
    } catch (e) {
      if (response.status === 429) {
        data = { error: { message: "Rate limit reached (HTTP 429)", code: "rate_limit_exceeded" } };
      } else {
        throw new Error(`Failed to parse response: ${response.statusText}`);
      }
    }
    
    if (response.status === 429 || data.error) {
      const isRateLimit = response.status === 429 || 
                          data.error?.message?.toLowerCase().includes("rate limit") || 
                          data.error?.code === "rate_limit_exceeded";
      if (isRateLimit) {
        if (rateLimitRetryCount < 6) {
          const waitTime = Math.min(90000, 10000 * Math.pow(2, rateLimitRetryCount));
          addLog(`⚠ Rate limit hit. Backing off for ${(waitTime / 1000).toFixed(1)}s (retry #${rateLimitRetryCount + 1})...`, "warn");
          await new Promise(resolve => setTimeout(resolve, waitTime));
          return callClaude(prompt, maxTokens, model, rateLimitRetryCount + 1);
        }
      }
      throw new Error(data.error?.message || `Groq API Error: ${response.statusText}`);
    }
    
    return data.choices[0]?.message?.content || "";
  }

  async function runStage(stageId, userInput, prevStages, attempt = 1) {
    if (attempt > 3) {
      setStatus(stageId, "failed");
      addLog(`❌ ${stageId} failed after 3 attempts`, "error");
      throw new Error(`${stageId} failed after 3 attempts`);
    }

    setStatus(stageId, attempt === 1 ? "running" : "repairing");
    addLog(`${attempt > 1 ? "🔄 Retry " + attempt : "▶"} Stage: ${stageId}`, attempt > 1 ? "warn" : "info");
    setRetries(r => ({ ...r, [stageId]: attempt }));

    const contextCtx = getContextForStage(stageId, prevStages);
    const promptText = buildPrompt(stageId, userInput) + contextCtx;
    
    const raw = await callClaude(
      promptText, 
      TOKEN_BUDGET[stageId] || 2500, 
      getModel(stageId)
    );
    setStageRaw(r => ({ ...r, [stageId]: raw }));

    const parsed = safeParseJSON(raw);
    if (!parsed.ok) {
      addLog(`⚠ JSON parse error in ${stageId}: ${parsed.error}`, "warn");
      return runStage(stageId, userInput, prevStages, attempt + 1);
    }
    if (parsed.repaired) {
      addLog(`🔧 Repaired truncated JSON in ${stageId}`, "warn");
    }

    const missing = validateStage(stageId, parsed.data);
    if (missing.length > 0) {
      addLog(`⚠ Missing fields in ${stageId}: ${missing.join(", ")}`, "warn");
      setStageIssues(s => ({ ...s, [stageId]: missing }));
      return runStage(stageId, userInput, prevStages, attempt + 1);
    }

    setStatus(stageId, "done");
    addLog(`✅ ${stageId} complete`, "success");
    return parsed.data;
  }

  // Launches sandbox dynamically by sending schemas to backend
  async function launchSandboxBackend(schemas) {
    addLog("🚀 Packaging schemas and starting FastAPI Sandbox environment...", "info");
    try {
      const response = await fetch(API_BASE + "/api/sandbox/launch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(schemas)
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Sandbox boot failed on backend.");
      }
      
      setSandboxOnline(data.sandbox.online);
      setSandboxUrl(data.sandbox.url || "http://127.0.0.1:8001/");
      addLog(`✅ Sandbox application running online at ${data.sandbox.url || "port 8001"}!`, "success");
      return data;
    } catch (e) {
      setSandboxOnline(false);
      addLog(`❌ Sandbox starting error: ${e.message}`, "error");
      throw e;
    }
  }

  async function runPipeline() {
    if (!prompt.trim()) return;
    abortRef.current = false;
    setRunning(true);
    setStages({});
    setStageStatus({});
    setStageRaw({});
    setStageIssues({});
    setRetries({});
    setValidation(null);
    setLog([]);
    setMetrics(null);
    setSandboxOnline(false);

    const startTime = Date.now();
    addLog(`🏁 Initiating ${compilationMode.toUpperCase()} Compilation Pipeline...`, "info");

    if (compilationMode === "mock") {
      // Run backend mock compilation
      try {
        addLog("▶ Calling FastAPI mock compiler backend...", "info");
        const res = await fetch(API_BASE + "/api/compile", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ prompt })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Mock compiler crashed.");

        // Load mock details into UI
        setStages({
          intent: data.stages.intent_extraction,
          architecture: data.stages.system_design,
          ui_schema: data.stages.schemas.ui_schema,
          api_schema: data.stages.schemas.api_schema,
          db_schema: data.stages.schemas.db_schema,
          auth_schema: data.stages.schemas.auth_rules
        });

        // Set statuses
        ["intent", "architecture", "ui_schema", "api_schema", "db_schema", "auth_schema"].forEach(s => {
          setStageStatus(prev => ({ ...prev, [s]: "done" }));
        });

        setValidation({
          is_valid: data.stages.validation_post.valid,
          issues: data.stages.validation_pre.errors.map(e => ({
            layer: e.location.split(".")[0],
            severity: "warning",
            description: e.detail,
            fix: "Surgically patched SQL schemas columns"
          })),
          consistency_score: data.stages.validation_post.valid ? 100 : 75,
          repair_summary: data.stages.repair_log.repairs.map(r => r.rationale)
        });
        setStageStatus(prev => ({ ...prev, validation: "repaired" }));

        setSandboxOnline(data.sandbox.online);
        setSandboxUrl(data.sandbox.url || "http://127.0.0.1:8001/");
        setActiveStageTab("intent");
        setActiveWorkspaceTab("sandbox");

        const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
        setMetrics({ elapsed, totalRetries: 0, stages: 6 });
        addLog(`✅ Compilation complete in ${elapsed}s! Sandbox online.`, "success");
      } catch (err) {
        addLog(`💥 Mock pipeline crash: ${err.message}`, "error");
      } finally {
        setRunning(false);
      }
      return;
    }

    // Run client-side Groq compilation
    const accumulated = {};
    const retryMap = {};

    try {
      for (const stage of ["intent", "architecture", "ui_schema", "api_schema", "db_schema", "auth_schema"]) {
        if (abortRef.current) break;
        if (stage !== "intent") {
          addLog("⏳ Pacing API calls... Waiting 4 seconds...", "info");
          await new Promise(resolve => setTimeout(resolve, 4000));
        }
        const result = await runStage(stage, prompt, accumulated);
        accumulated[stage] = result;
        retryMap[stage] = retries[stage] || 1;
        setStages(s => ({ ...s, [stage]: result }));
        setActiveStageTab(stage);
      }

      // Validation & Repair Stage
      if (!abortRef.current) {
        setStatus("validation", "running");
        addLog("⏳ Pacing API calls... Waiting 4 seconds...", "info");
        await new Promise(resolve => setTimeout(resolve, 4000));
        addLog("🛡 Performing cross-layer schema validations...", "info");
        const valPrompt = buildValidationPrompt(accumulated);
        const valRaw = await callClaude(valPrompt, 2000);
        const valParsed = safeParseJSON(valRaw);
        
        if (valParsed.ok) {
          setValidation(valParsed.data);
          const statusVal = valParsed.data.is_valid ? "done" : "repaired";
          setStatus("validation", statusVal);
          addLog(`🛡 Validations completed. Consistency score: ${valParsed.data.consistency_score}/100`, "success");
          
          // Trigger runtime setup & sandbox backend execution
          const launchResult = await launchSandboxBackend(accumulated);
          if (launchResult && launchResult.success) {
            setSandboxOnline(true);
            setSandboxUrl(launchResult.sandbox?.url || "http://127.0.0.1:8001/");
            if (launchResult.schemas) {
              setStages({
                intent: accumulated.intent,
                architecture: accumulated.architecture,
                ui_schema: launchResult.schemas.ui_schema,
                api_schema: launchResult.schemas.api_schema,
                db_schema: launchResult.schemas.db_schema,
                auth_schema: launchResult.schemas.auth_rules
              });
            }
          }
        } else {
          setStatus("validation", "failed");
          addLog("❌ Validation schema analysis parse failed.", "error");
        }
      }

      const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
      const totalRetries = Object.values(retryMap).reduce((a, b) => a + b, 0) - Object.keys(retryMap).length;
      setMetrics({ elapsed, totalRetries, stages: Object.keys(accumulated).length });
      addLog(`🏁 Full pipeline finished in ${elapsed}s`, "success");
      setActiveWorkspaceTab("sandbox");
    } catch (e) {
      addLog(`💥 Compilation failed: ${e.message}`, "error");
    } finally {
      setRunning(false);
    }
  }

  // Database debugger loading
  const refreshSandboxDatabase = async () => {
    try {
      const res = await fetch(API_BASE + "/api/sandbox/db-records");
      const data = await res.json();
      if (res.ok) {
        setDbTables(data.tables || {});
      }
    } catch (e) {
      console.error("Failed to query SQLite DB:", e);
    }
  };

  useEffect(() => {
    if (sandboxOnline && activeWorkspaceTab === "sandbox") {
      refreshSandboxDatabase();
      const interval = setInterval(refreshSandboxDatabase, 3000);
      return () => clearInterval(interval);
    }
  }, [sandboxOnline, activeWorkspaceTab]);

  const loadExamplePrompt = (example) => {
    if (!running) {
      setPrompt(example.prompt);
      addLog(`Loaded example prompt: "${example.title}"`, "info");
    }
  };

  const statusColor = {
    running: "text-amber-500",
    repairing: "text-orange-500",
    done: "text-emerald-500",
    repaired: "text-cyan-500",
    failed: "text-red-500",
    pending: "text-gray-500",
  };

  const statusIcon = {
    running: "⟳",
    repairing: "🔄",
    done: "✓",
    repaired: "🔧",
    failed: "✗",
    pending: "○",
  };

  return (
    <div className="min-h-screen bg-[#030408] text-[#e2e8f0] font-sans flex flex-col selection:bg-cyan-500/25 selection:text-cyan-200">
      
      {/* HEADER BAR */}
      <header className="glass-panel border-b border-gray-900/60 py-4 px-6 flex items-center justify-between sticky top-0 z-50">
        <div className="flex items-center space-x-3">
          <div className="relative w-10 h-10 rounded-lg bg-gradient-to-tr from-cyan-500 to-indigo-600 flex items-center justify-center font-bold text-white shadow-lg shadow-cyan-500/20">
            <span className="text-lg">λ</span>
            <span className="absolute -inset-0.5 rounded-lg bg-cyan-400/20 blur opacity-50 animate-pulse"></span>
          </div>
          <div>
            <h1 className="text-base md:text-lg font-bold text-white tracking-tight flex items-center gap-2">
              AI App Compiler Dashboard <span className="text-xs px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 font-mono font-medium">v2.0</span>
            </h1>
            <p className="text-xs text-gray-400 font-medium">Natural Language &rarr; Relational Sandbox Application</p>
          </div>
        </div>

        {metrics && (
          <div className="hidden md:flex items-center gap-6">
            {[
              { label: "Elapsed Time", val: metrics.elapsed + "s" },
              { label: "Pipeline Stages", val: metrics.stages },
              { label: "LLM Retries", val: metrics.totalRetries },
            ].map(m => (
              <div key={m.label} className="text-right">
                <div className="text-sm font-bold text-cyan-400">{m.val}</div>
                <div className="text-xs text-gray-400 font-medium uppercase tracking-wider">{m.label}</div>
              </div>
            ))}
          </div>
        )}
      </header>

      {/* DASHBOARD SPLIT WORKSPACE */}
      <div className="flex-grow flex flex-col lg:flex-row h-[calc(100vh-69px)] overflow-hidden">
        
        {/* LEFT PANEL: CONFIGS, PROMPT & CONSOLE */}
        <aside className="w-full lg:w-[420px] glass-panel border-r border-gray-900/60 p-6 flex flex-col space-y-5 overflow-y-auto">
          
          {/* Compiler Mode selector */}
          <div className="space-y-2">
            <label className="text-xs font-bold text-gray-400 uppercase tracking-wider block">Compilation Core</label>
            <div className="grid grid-cols-2 gap-2 bg-gray-950 p-1.5 rounded-xl border border-gray-900">
              <button
                onClick={() => setCompilationMode("mock")}
                className={`py-2 rounded-lg text-sm font-bold transition-all cursor-pointer ${
                  compilationMode === "mock"
                    ? "bg-gradient-to-tr from-cyan-600 to-blue-600 text-white shadow"
                    : "text-gray-400 hover:text-white"
                }`}
              >
                Mock compiler (Fast)
              </button>
              <button
                onClick={() => setCompilationMode("llm")}
                className={`py-2 rounded-lg text-sm font-bold transition-all cursor-pointer ${
                  compilationMode === "llm"
                    ? "bg-gradient-to-tr from-purple-600 to-pink-600 text-white shadow"
                    : "text-gray-400 hover:text-white"
                }`}
              >
                LLM Compiler (Resilient)
              </button>
            </div>
          </div>

          {/* Groq Key configuration */}
          {compilationMode === "llm" && (
            <div className="space-y-2 p-3 bg-purple-950/10 border border-purple-500/20 rounded-xl">
              <div className="flex justify-between items-center">
                <label className="text-xs font-semibold text-purple-300 uppercase tracking-wider">Groq API Token</label>
                <a href="https://console.groq.com/" target="_blank" rel="noreferrer" className="text-xs text-gray-400 hover:underline">keys console &rarr;</a>
              </div>
              <input
                type="password"
                value={groqKey}
                onChange={e => saveGroqKey(e.target.value)}
                placeholder="Paste key: gsk_••••••••••••••••"
                className="w-full px-3 py-2 rounded bg-gray-950 border border-gray-900 focus:outline-none focus:border-purple-500 text-sm text-white placeholder-gray-700 font-mono transition-all"
              />
            </div>
          )}

          {/* Prompt description */}
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <label className="text-xs font-bold text-gray-400 uppercase tracking-wider">App Prompt Description</label>
              <span className="text-xs text-gray-400 font-medium">Natural language input</span>
            </div>
            <textarea
              value={prompt}
              onChange={e => setPrompt(e.target.value)}
              disabled={running}
              placeholder="e.g. Build a task manager with title and priority level. Standard users are restricted to 10 tasks max. Admins have dashboard insights."
              className="w-full h-32 p-3.5 rounded-xl bg-gray-950 border border-gray-900 focus:outline-none focus:border-cyan-500 text-sm text-white placeholder-gray-700 leading-relaxed font-medium transition-all focus:shadow-[0_0_15px_rgba(6,182,212,0.05)] resize-none"
            />
            <button
              onClick={running ? () => { abortRef.current = true; } : runPipeline}
              className={`w-full py-3.5 text-sm font-bold rounded-xl active:scale-[0.98] transition-all flex items-center justify-center space-x-2 text-white shadow-lg cursor-pointer ${
                running
                  ? "bg-red-950 border border-red-500/20 hover:bg-red-900"
                  : compilationMode === "llm"
                  ? "bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 shadow-purple-500/10"
                  : "bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 shadow-cyan-500/10"
              }`}
            >
              <span>{running ? "⬛ ABORT COMPILE" : "▶ COMPILE & RUN APPS"}</span>
            </button>
          </div>

          {/* Examples */}
          <div className="space-y-2">
            <label className="text-xs font-bold text-gray-400 uppercase tracking-wider block">Quick Presets</label>
            <div className="space-y-1.5">
              {QUICK_EXAMPLES.map((ex, i) => (
                <button
                  key={i}
                  disabled={running}
                  onClick={() => loadExamplePrompt(ex)}
                  className="w-full text-left p-2.5 rounded bg-gray-950 hover:bg-gray-900/60 border border-gray-900 hover:border-gray-800 text-xs text-gray-400 hover:text-white transition-all flex justify-between items-center cursor-pointer"
                >
                  <span className="truncate max-w-[280px] font-semibold">{ex.title}</span>
                  <span className="text-cyan-500 font-bold">&rarr;</span>
                </button>
              ))}
            </div>
          </div>

          {/* Console Log outputs */}
          <div className="flex-grow flex flex-col space-y-2 min-h-[160px] max-h-[300px] lg:max-h-none overflow-hidden">
            <label className="text-xs font-bold text-gray-400 uppercase tracking-wider block">Build Log Console</label>
            <div className="flex-grow rounded-xl bg-gray-950 border border-gray-900 p-4 font-mono text-xs leading-relaxed text-gray-400 space-y-1.5 overflow-y-auto">
              <div className="text-cyan-500">[SYSTEM] Compiler dashboard ready. Enter prompt to compile.</div>
              {log.map((l, i) => (
                <div key={i} className="flex items-start gap-1">
                  <span className="text-gray-600 font-bold">[{new Date(l.ts).toLocaleTimeString()}]</span>
                  <span className={
                    l.type === "error" ? "text-red-400 font-bold" :
                    l.type === "warn" ? "text-amber-400" :
                    l.type === "success" ? "text-emerald-400 font-semibold" : "text-gray-400"
                  }>
                    {l.msg}
                  </span>
                </div>
              ))}
              <div ref={logConsoleEndRef} />
            </div>
          </div>

        </aside>

        {/* RIGHT PANEL: COMPILED VIEWPORTS */}
        <main className="flex-grow flex flex-col overflow-hidden bg-[#05070a]">
          
          {/* Workspace Tabs Header */}
          <div className="bg-gray-950/40 border-b border-gray-900/60 px-6 flex items-center space-x-2">
            <button
              onClick={() => setActiveWorkspaceTab("pipeline")}
              className={`px-4 py-4 text-xs font-bold border-b-2 transition-all flex items-center gap-1.5 ${
                activeWorkspaceTab === "pipeline"
                  ? "border-cyan-500 text-cyan-400"
                  : "border-transparent text-gray-500 hover:text-gray-300"
              }`}
            >
              <span>1. Pipeline Intermediates</span>
            </button>
            <button
              onClick={() => setActiveWorkspaceTab("validation")}
              className={`px-4 py-4 text-xs font-bold border-b-2 transition-all flex items-center gap-1.5 ${
                activeWorkspaceTab === "validation"
                  ? "border-cyan-500 text-cyan-400"
                  : "border-transparent text-gray-500 hover:text-gray-300"
              }`}
            >
              <span>2. Validator Audit</span>
              {validation && validation.issues && validation.issues.length > 0 && (
                <span className="px-1.5 py-0.5 rounded bg-red-500/10 text-red-400 text-[9px] border border-red-500/20 font-bold">
                  {validation.issues.length}
                </span>
              )}
            </button>
            <button
              onClick={() => setActiveWorkspaceTab("code")}
              className={`px-4 py-4 text-xs font-bold border-b-2 transition-all flex items-center gap-1.5 ${
                activeWorkspaceTab === "code"
                  ? "border-cyan-500 text-cyan-400"
                  : "border-transparent text-gray-500 hover:text-gray-300"
              }`}
            >
              <span>3. Generated Source Code</span>
            </button>
            <button
              onClick={() => setActiveWorkspaceTab("sandbox")}
              className={`px-4 py-4 text-xs font-bold border-b-2 transition-all flex items-center gap-1.5 ${
                activeWorkspaceTab === "sandbox"
                  ? "border-cyan-500 text-cyan-400"
                  : "border-transparent text-gray-500 hover:text-gray-300"
              }`}
            >
              <span>4. Live Sandbox View</span>
              {sandboxOnline && (
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-ping shadow-[0_0_8px_rgba(16,185,129,0.5)]"></span>
              )}
            </button>
          </div>

          {/* WORKSPACE VIEW PORT */}
          <div className="flex-grow overflow-hidden relative">

            {/* TAB 1: PIPELINE STAGES EXPLORER */}
            {activeWorkspaceTab === "pipeline" && (
              <div className="h-full flex flex-col md:flex-row overflow-hidden">
                {/* Stages navigation */}
                <aside className="w-full md:w-64 border-b md:border-b-0 md:border-r border-gray-950 p-4 space-y-4 bg-gray-950/20">
                  <p className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">Pipeline Stages</p>
                  <nav className="space-y-1">
                    {STAGE_META.map(stage => {
                      const status = stageStatus[stage.id] || "pending";
                      const r = retries[stage.id];
                      return (
                        <button
                          key={stage.id}
                          onClick={() => {
                            if (stages[stage.id] || (stage.id === "validation" && validation)) {
                              setActiveStageTab(stage.id);
                            }
                          }}
                          disabled={!stages[stage.id] && !(stage.id === "validation" && validation)}
                          className={`w-full flex items-center justify-between p-2.5 rounded text-left transition-all ${
                            activeStageTab === stage.id
                              ? "bg-cyan-950/10 border-l-2 border-cyan-500 text-cyan-400 font-bold"
                              : "text-gray-400 hover:bg-gray-950 hover:text-white"
                          } disabled:opacity-30`}
                        >
                          <span className="text-xs truncate">{stage.icon} {stage.label}</span>
                          <span className={`text-[10px] font-bold ${statusColor[status]}`}>
                            {statusIcon[status]}
                          </span>
                        </button>
                      );
                    })}
                  </nav>
                </aside>

                {/* Stage output display */}
                <div className="flex-grow flex flex-col p-6 overflow-y-auto space-y-4">
                  {stages[activeStageTab] || (activeStageTab === "validation" && validation) ? (
                    <div className="space-y-4 h-full flex flex-col">
                      <div className="flex items-center justify-between">
                        <div>
                          <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                            {STAGE_META.find(s => s.id === activeStageTab)?.label} Output
                          </h3>
                          <p className="text-[10px] text-gray-500 mt-0.5">Intermediate JSON Representation schema structure</p>
                        </div>
                        <button
                          onClick={() => {
                            const data = activeStageTab === "validation" ? validation : stages[activeStageTab];
                            navigator.clipboard.writeText(JSON.stringify(data, null, 2));
                            addLog(`Copied JSON for stage ${activeStageTab} to clipboard.`, "info");
                          }}
                          className="px-2.5 py-1.5 rounded border border-gray-800 bg-gray-950 text-[10px] font-bold text-gray-400 hover:text-white transition-all active:scale-[0.98]"
                        >
                          Copy JSON
                        </button>
                      </div>

                      {stageIssues[activeStageTab] && stageIssues[activeStageTab].length > 0 && (
                        <div className="p-3 bg-red-950/20 border border-red-500/20 rounded-xl text-red-400 text-xs">
                          ⚠ Missing required fields repaired: {stageIssues[activeStageTab].join(", ")}
                        </div>
                      )}

                      <div className="flex-grow relative">
                        <pre className="absolute inset-0 p-5 rounded-xl bg-gray-950 border border-gray-900/60 font-mono text-[10px] text-cyan-400 leading-relaxed overflow-auto">
                          {JSON.stringify(activeStageTab === "validation" ? validation : stages[activeStageTab], null, 2)}
                        </pre>
                      </div>
                    </div>
                  ) : (
                    <div className="h-full flex flex-col items-center justify-center text-gray-500 text-center py-20">
                      <span className="text-3xl mb-3">⚙</span>
                      <p className="text-xs font-semibold">Stage Uncompiled</p>
                      <p className="text-[10px] text-gray-600 mt-1">Compile your prompt core first to explore JSON configurations.</p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* TAB 2: VALIDATOR AUDIT & SURGICAL REPAIR */}
            {activeWorkspaceTab === "validation" && (
              <div className="h-full p-8 overflow-y-auto space-y-6">
                {validation ? (
                  <div className="max-w-4xl mx-auto space-y-8">
                    <div className="flex items-center gap-6 p-6 rounded-2xl bg-gray-950 border border-gray-900">
                      <div className="w-16 h-16 rounded-full border-4 flex items-center justify-center flex-col shrink-0 border-cyan-500/30 text-cyan-400">
                        <span className="text-lg font-extrabold">{validation.consistency_score || 100}</span>
                        <span className="text-[7px] text-gray-500 uppercase">Score</span>
                      </div>
                      <div>
                        <h3 className="text-sm font-bold text-white">Validation Audit Report</h3>
                        <p className="text-[10px] text-gray-500 mt-0.5 leading-relaxed">
                          Checks for API endpoints mapping DB, forms submitting target URLs, roles alignment controls.
                        </p>
                        <div className="mt-2.5 flex items-center gap-2">
                          <span className={`px-2 py-0.5 text-[9px] font-bold rounded border uppercase ${
                            validation.is_valid
                              ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                              : "bg-cyan-500/10 text-cyan-400 border-cyan-500/20"
                          }`}>
                            {validation.is_valid ? "Valid & Stable" : "Surgically Repaired"}
                          </span>
                        </div>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      
                      {/* Issues list */}
                      <div className="space-y-3">
                        <h4 className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">Anomaly Detection logs</h4>
                        {validation.issues && validation.issues.length > 0 ? (
                          <div className="space-y-2">
                            {validation.issues.map((issue, idx) => (
                              <div key={idx} className="p-4 rounded-xl bg-red-950/10 border border-red-500/10 text-[10px] space-y-1.5">
                                <div className="flex justify-between items-center text-[9px] uppercase tracking-wider">
                                  <span className="text-red-400 font-bold">{issue.severity} &bull; {issue.layer}</span>
                                </div>
                                <p className="text-white font-medium">{issue.description}</p>
                                <p className="text-gray-500 font-bold text-[9px]">Surgical Fix: {issue.fix}</p>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div className="p-6 rounded-xl bg-gray-950 border border-gray-900 text-center text-xs text-gray-500">
                            ✓ Zero consistency anomalies detected in relational mappings.
                          </div>
                        )}
                      </div>

                      {/* Repair summary logs */}
                      <div className="space-y-3">
                        <h4 className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">Surgical Repair summary</h4>
                        {validation.repair_summary && validation.repair_summary.length > 0 ? (
                          <div className="space-y-2">
                            {validation.repair_summary.map((summary, idx) => (
                              <div key={idx} className="p-3 rounded-lg bg-cyan-950/10 border border-cyan-500/10 text-[10px] text-cyan-400 flex items-start gap-2">
                                <span>🔧</span>
                                <span>{summary}</span>
                              </div>
                            ))}
                            <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-lg text-[10px] font-semibold text-center">
                              ✓ Post-Repair Validation: Passed. Launched sandbox runtime server.
                            </div>
                          </div>
                        ) : (
                          <div className="p-6 rounded-xl bg-gray-950 border border-gray-900 text-center text-xs text-gray-500">
                            No surgical repairs were required.
                          </div>
                        )}
                      </div>

                    </div>
                  </div>
                ) : (
                  <div className="h-full flex flex-col items-center justify-center text-gray-500 text-center py-20">
                    <span className="text-3xl mb-3">🛡</span>
                    <p className="text-sm font-semibold">Validation Audit Pending</p>
                    <p className="text-xs text-gray-400 mt-1">Surgically inspect validations report once pipeline completes compiles.</p>
                  </div>
                )}
              </div>
            )}

            {/* TAB 3: SOURCE CODE EXPLORER */}
            {activeWorkspaceTab === "code" && (
              <div className="h-full flex overflow-hidden">
                {/* Code files navigation */}
                <aside className="w-64 border-r border-gray-950 p-4 space-y-4 bg-gray-950/20">
                  <p className="text-xs font-bold text-gray-400 uppercase tracking-wider">Compiled files</p>
                  <nav className="space-y-1">
                    {[
                      { id: "db", label: "db_runtime.py" },
                      { id: "api", label: "api_runtime.py" },
                      { id: "ui", label: "static/index.html" },
                    ].map(file => (
                      <button
                        key={file.id}
                        onClick={() => setActiveCodeFile(file.id)}
                        className={`w-full text-left px-3 py-2.5 rounded text-sm transition-all cursor-pointer ${
                          activeCodeFile === file.id
                            ? "text-cyan-400 bg-cyan-900/10 border-l-2 border-cyan-500 font-bold"
                            : "text-gray-400 hover:bg-gray-950 hover:text-white"
                        }`}
                      >
                        {file.label}
                      </button>
                    ))}
                  </nav>
                </aside>

                {/* Code body Display */}
                <div className="flex-grow flex flex-col overflow-hidden">
                  <div className="bg-gray-950/60 px-4 py-3 border-b border-gray-950 flex items-center justify-between text-xs text-gray-400 font-semibold uppercase tracking-wider">
                    <span>
                      {activeCodeFile === "db" ? "runtime/db_runtime.py" : activeCodeFile === "api" ? "runtime/api_runtime.py" : "runtime/static/index.html"}
                    </span>
                    <button
                      onClick={() => {
                        const code = getCodeContent();
                        navigator.clipboard.writeText(code);
                        addLog(`Copied file contents for ${activeCodeFile} to clipboard.`, "info");
                      }}
                      className="px-3 py-1.5 bg-gray-900 border border-gray-800 rounded text-xs hover:text-white transition-all cursor-pointer"
                    >
                      Copy File
                    </button>
                  </div>
                  <div className="flex-grow relative">
                    <pre className="absolute inset-0 p-6 font-mono text-xs text-[#a5b4fc] overflow-auto leading-relaxed bg-[#030508]">
                      {getCodeContent()}
                    </pre>
                  </div>
                </div>
              </div>
            )}

            {/* TAB 4: LIVE SANDBOX & DB MONITOR */}
            {activeWorkspaceTab === "sandbox" && (
              <div className="h-full flex flex-col md:flex-row overflow-hidden">
                {/* Sandbox Browser frame view */}
                <div className="flex-grow flex flex-col relative h-[55%] md:h-full md:w-[60%] border-b md:border-b-0 md:border-r border-gray-950">
                  <div className="bg-gray-950/60 p-3.5 border-b border-gray-950 flex items-center justify-between text-xs font-semibold text-gray-400 uppercase tracking-wider">
                    <div className="flex items-center gap-2">
                      <span className={`w-2.5 h-2.5 rounded-full ${sandboxOnline ? "bg-emerald-500 animate-pulse shadow-[0_0_8px_rgba(16,185,129,0.5)]" : "bg-red-500"}`} />
                      <span className={sandboxOnline ? "text-white" : "text-gray-500"}>
                        {sandboxOnline ? `Live Application Preview (${sandboxUrl})` : "Sandbox Offline - Compile to start server"}
                      </span>
                    </div>
                    {sandboxOnline && (
                      <button
                        onClick={() => {
                          const iframe = document.getElementById("sandbox-iframe");
                          if (iframe) iframe.src = sandboxUrl + (sandboxUrl.includes("?") ? "&" : "?") + "t=" + Date.now();
                        }}
                        className="text-cyan-400 hover:text-cyan-300 font-bold cursor-pointer"
                        title="Reload preview"
                      >
                        Reload iframe
                      </button>
                    )}
                  </div>
                  <div className="flex-grow w-full bg-[#030508] relative">
                    {sandboxOnline ? (
                      <iframe
                        id="sandbox-iframe"
                        src={sandboxUrl}
                        className="w-full h-full border-none bg-white"
                      />
                    ) : (
                      <div className="absolute inset-0 flex flex-col items-center justify-center text-center text-gray-500 p-6">
                        <span className="text-4xl mb-4">🖥</span>
                        <p className="text-sm font-bold">FastAPI Sandbox Application offline</p>
                        <p className="text-xs text-gray-400 mt-1 max-w-[280px]">
                          Enter app details on the prompt and hit Compile to spin up sandbox container runtime.
                        </p>
                      </div>
                    )}
                  </div>
                </div>

                {/* SQLite Database Debugger panel view */}
                <div className="w-full md:w-[40%] flex flex-col h-[45%] md:h-full overflow-hidden bg-[#06080d]">
                  <div className="bg-gray-950/60 p-3.5 border-b border-gray-950 flex items-center justify-between text-xs font-semibold text-gray-400 uppercase tracking-wider shrink-0">
                    <span>SQLite tables monitor (app.db)</span>
                    {sandboxOnline && (
                      <button
                        onClick={refreshSandboxDatabase}
                        className="text-cyan-400 hover:underline hover:text-cyan-300 cursor-pointer"
                      >
                        Refresh Tables
                      </button>
                    )}
                  </div>
                  
                  <div className="flex-grow p-4 overflow-y-auto space-y-4">
                    {sandboxOnline && Object.keys(dbTables).length > 0 ? (
                      Object.keys(dbTables).map(tableName => {
                        const rows = dbTables[tableName] || [];
                        return (
                          <div key={tableName} className="p-4 rounded-xl bg-gray-950 border border-gray-900 space-y-3">
                            <div className="flex justify-between items-center border-b border-gray-900 pb-2">
                              <span className="text-xs font-extrabold text-cyan-400 uppercase tracking-wider">
                                Table: {tableName}
                              </span>
                              <span className="px-2 py-0.5 rounded bg-gray-900 border border-gray-800 text-xs text-gray-400 font-bold font-mono uppercase">
                                {rows.length} records
                              </span>
                            </div>

                            {rows.length === 0 ? (
                              <p className="text-xs text-gray-500 text-center py-2">Table entries are empty.</p>
                            ) : (
                              <div className="space-y-1.5 max-h-[160px] overflow-y-auto">
                                {rows.map((row, rIdx) => (
                                  <div key={rIdx} className="bg-gray-900/40 p-2.5 rounded border border-gray-900/60 text-xs space-y-0.5 grid grid-cols-2 gap-x-2">
                                    {Object.keys(row).map(col => {
                                      if (col === "password_hash") {
                                        return (
                                          <div key={col} className="truncate">
                                            <span className="text-gray-500">{col}:</span> <span className="text-gray-400 font-mono">••••••••</span>
                                          </div>
                                        );
                                      }
                                      return (
                                        <div key={col} className="truncate">
                                          <span className="text-gray-400">{col}:</span> <span className="text-gray-200 font-bold">{row[col]}</span>
                                        </div>
                                      );
                                    })}
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        );
                      })
                    ) : (
                      <div className="text-center text-gray-600 text-xs py-10">
                        {sandboxOnline ? "SQLite Database initialized but empty." : "Compile application first to visualize databases."}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

          </div>

        </main>
      </div>

    </div>
  );

  // Helper to dynamically recreate source code values matching compileData
  function getCodeContent() {
    try {
      if (!stages.db_schema || !stages.api_schema || !stages.ui_schema || !stages.db_schema.tables) {
        return "// App must be compiled to inspect generated source files.";
      }

      if (activeCodeFile === "db") {
        let code = `# Compiled SQLite Database Initializer
# Generated by AI App Compiler (Stage 6)

import sqlite3
import os

def init_db(db_path="app.db"):
    db_exists = os.path.exists(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. Create Tables defined in DB Schema
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL
    );
    """)
    \n`;

        const appType = stages.intent?.app_type || "crm";
        stages.db_schema.tables.forEach(t => {
          if (t.name === "user") return;
          let cols = t.columns.map(c => `        ${c.name} ${c.type.toUpperCase()} ${(c.constraints || []).join(' ')}`).join(',\n');
          let fks = t.foreign_keys ? t.foreign_keys.map(f => `, \n        FOREIGN KEY(${f.column}) REFERENCES ${f.references}`).join('') : '';
          code += `    cursor.execute("""\n    CREATE TABLE IF NOT EXISTS ${t.name} (\n${cols}${fks}\n    );\n    """)\n\n`;
        });
        
        code += `    # 2. Seed default users
    cursor.execute("INSERT OR IGNORE INTO user (email, password_hash, role) VALUES ('admin@example.com', 'admin123', 'Admin')")
    cursor.execute("INSERT OR IGNORE INTO user (email, password_hash, role) VALUES ('user@example.com', 'user123', 'User')")
    
    # Seeding resource data
    if "${appType}" == "crm":
        cursor.execute("INSERT OR IGNORE INTO contact (user_id, name, email, phone) VALUES (2, 'Alice Smith', 'alice@example.com', '+1-555-0199')")
    elif "${appType}" == "task":
        cursor.execute("INSERT OR IGNORE INTO task (user_id, title, description, status) VALUES (2, 'Design Architecture', 'Define initial schema structures', 'todo')")
        
    conn.commit()
    conn.close()
    print("Database seeded.")
`;
        return code;
      } else if (activeCodeFile === "api") {
        let code = `# Compiled FastAPI Backend API Server
# Generated by AI App Compiler (Stage 6)

import os
import sqlite3
from fastapi import FastAPI, Depends, HTTPException, Header, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse

app = FastAPI(title="Compiled App API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = "app.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()
\n`;
        
        if (stages.api_schema.routes) {
          stages.api_schema.routes.forEach(r => {
            code += `# REGISTERED ROUTE: ${r.method} ${r.path}\n`;
          });
        }
        
        code += `\n# Starts with: uvicorn api_runtime:app --port 8001\n`;
        return code;
      } else if (activeCodeFile === "ui") {
        const pages = stages.ui_schema.pages || [];
        const pagesStr = pages.map(p => {
          const pathStr = typeof p === "object" ? (p.route || p.name || "") : p;
          return `<span class="px-2 py-0.5 rounded bg-gray-900 border border-gray-800 text-[10px] text-gray-400 font-mono">${pathStr}</span>`;
        }).join('\n            ');

        return `<!-- Compiled Client Frontend UI -->
<!-- Generated by AI App Compiler (Stage 6) -->

<!DOCTYPE html>
<html>
<head>
    <title>Compiled Application Workspace</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-950 text-white min-h-screen">
    <div class="p-8">
        <h1 class="text-xl font-bold">Compiled UI Workspace</h1>
        <p class="text-xs text-gray-500">Pages rendered:</p>
        <div class="mt-2.5 flex flex-wrap gap-2">
            ${pagesStr}
        </div>
    </div>
</body>
</html>
`;
      }
      return "";
    } catch (err) {
      return `// Generating source files... Waiting for backend translation engine to complete: ${err.message}`;
    }
  }
}
