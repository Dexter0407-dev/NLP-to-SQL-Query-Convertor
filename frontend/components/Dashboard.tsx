'use client';

import React, { useState, useMemo, useRef, useCallback } from "react";
import {
  Database, Send, Table2, History, Sparkles, UploadCloud,
  ShieldCheck, AlertTriangle, ChevronRight, Terminal, RotateCcw,
  Eye, MessageSquare,
} from "lucide-react";

const BG     = "#0A0D12";
const PANEL  = "#12161D";
const PANEL2 = "#181D26";
const BORDER = "#242B36";
const TEXT   = "#E7EAEE";
const MUTED  = "#7C8494";
const ACCENT = "#7C9EFF";
const TEAL   = "#4FD1C5";
const DANGER = "#FF9B9B";
const GREEN  = "#68D391";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const PAGE_SIZE = 25;

interface QueryResult {
  question: string; sql: string;
  columns: string[]; results: Record<string, unknown>[];
  row_count: number; safe: boolean;
}
interface HistoryEntry   { question: string; sql: string; ts: number; }
interface SchemaColumn   { name: string; type: string; nullable: boolean; }
interface SchemaTable    { name: string; columns: SchemaColumn[]; row_count?: number; }
interface PreviewData    { table_name: string; columns: string[]; results: Record<string, unknown>[]; row_count: number; }

type TabView = "preview" | "query";

const SUGGESTIONS = [
  "What is the total revenue?",
  "Average price by category",
  "How many orders were placed in 2024?",
  "Show top 5 most expensive orders",
  "Total quantity sold by region",
];

// ── Reusable data table component ─────────────────────────────────────────
function DataTable({ columns, rows }: { columns: string[]; rows: Record<string, unknown>[] }) {
  const [pg, setPg] = useState(0);
  const total = Math.ceil(rows.length / PAGE_SIZE);
  const paged = rows.slice(pg * PAGE_SIZE, (pg + 1) * PAGE_SIZE);

  return (
    <div>
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12.5 }}>
          <thead>
            <tr style={{ background: PANEL2 }}>
              {columns.map((c) => (
                <th key={c} className="mono"
                  style={{ textAlign: "left", padding: "9px 14px", color: MUTED, fontWeight: 600, textTransform: "uppercase", fontSize: 10, whiteSpace: "nowrap", borderBottom: `1px solid ${BORDER}` }}>
                  {c}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {paged.map((r, i) => (
              <tr key={i} style={{ borderTop: `1px solid ${BORDER}`, background: i % 2 === 0 ? "transparent" : `${PANEL2}88` }}>
                {columns.map((c) => (
                  <td key={c} className="mono"
                    style={{ padding: "8px 14px", maxWidth: 260, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}
                    title={String(r[c] ?? "")}>
                    {String(r[c] ?? "")}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {total > 1 && (
        <div style={{ display: "flex", gap: 8, marginTop: 14, alignItems: "center" }}>
          <button onClick={() => setPg(0)} disabled={pg === 0} style={pgBtn(pg === 0)}>«</button>
          <button onClick={() => setPg((p) => Math.max(0, p - 1))} disabled={pg === 0} style={pgBtn(pg === 0)}>← Prev</button>
          <span style={{ fontSize: 11.5, color: MUTED, minWidth: 80, textAlign: "center" }}>
            {pg + 1} / {total}
          </span>
          <button onClick={() => setPg((p) => Math.min(total - 1, p + 1))} disabled={pg === total - 1} style={pgBtn(pg === total - 1)}>Next →</button>
          <button onClick={() => setPg(total - 1)} disabled={pg === total - 1} style={pgBtn(pg === total - 1)}>»</button>
        </div>
      )}
    </div>
  );
}

function pgBtn(disabled: boolean): React.CSSProperties {
  return { background: PANEL2, border: `1px solid ${BORDER}`, color: disabled ? MUTED : TEXT, borderRadius: 6, padding: "4px 10px", cursor: disabled ? "not-allowed" : "pointer", fontSize: 12 };
}

// ── Main Dashboard ───────────────────────────────────────────────────────
export default function Dashboard() {
  const [schema, setSchema]         = useState<SchemaTable[]>([]);
  const [activeTable, setActiveTable] = useState<string>("");
  const [tabView, setTabView]       = useState<TabView>("preview");
  const [preview, setPreview]       = useState<PreviewData | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [question, setQuestion]     = useState("");
  const [running, setRunning]       = useState(false);
  const [uploading, setUploading]   = useState(false);
  const [current, setCurrent]       = useState<QueryResult | null>(null);
  const [history, setHistory]       = useState<HistoryEntry[]>([]);
  const [error, setError]           = useState<string | null>(null);
  const [uploadMsg, setUploadMsg]   = useState<string | null>(null);
  const [dragOver, setDragOver]     = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // ── Fetch schema ────────────────────────────────────────────────────────
  const fetchSchema = useCallback(async () => {
    try {
      const r = await fetch(`${API_BASE}/schema`);
      const d = await r.json();
      const tables: SchemaTable[] = d.tables ?? [];
      setSchema(tables);
      return tables;
    } catch {
      setError("Could not reach the backend. Is it running on port 8000?");
      return [];
    }
  }, []);

  // ── Fetch preview for a table ───────────────────────────────────────────
  const fetchPreview = useCallback(async (tableName: string) => {
    setPreviewLoading(true);
    try {
      const r = await fetch(`${API_BASE}/preview/${tableName}?limit=200`);
      const d = await r.json();
      setPreview(d);
    } catch {
      setPreview(null);
    } finally {
      setPreviewLoading(false);
    }
  }, []);

  // On mount — load schema then preview
  React.useEffect(() => {
    fetchSchema().then((tables) => {
      if (tables.length > 0) {
        setActiveTable(tables[0].name);
        fetchPreview(tables[0].name);
      }
    });
  }, []);

  // When active table changes, load its preview
  React.useEffect(() => {
    if (activeTable) fetchPreview(activeTable);
  }, [activeTable]);

  // ── CSV Upload ──────────────────────────────────────────────────────────
  const handleFile = useCallback(async (file: File | null) => {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".csv")) { setError("Only CSV files are supported."); return; }
    setUploading(true); setError(null); setUploadMsg(null);
    const form = new FormData();
    form.append("file", file);
    try {
      const resp = await fetch(`${API_BASE}/upload`, { method: "POST", body: form });
      if (!resp.ok) { const e = await resp.json(); throw new Error(e.detail ?? "Upload failed"); }
      const data = await resp.json();
      setUploadMsg(`✓ "${data.table_name}" loaded — ${data.row_count} rows · ${data.columns.length} columns`);
      const tables = await fetchSchema();
      const newTable = data.table_name;
      setActiveTable(newTable);
      setTabView("preview");
      setCurrent(null);
      setHistory([]);
      await fetchPreview(newTable);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }, [fetchSchema, fetchPreview]);

  const onFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    handleFile(e.target.files?.[0] ?? null);
    e.target.value = "";
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault(); setDragOver(false);
    handleFile(e.dataTransfer.files[0] ?? null);
  };

  // ── Query ───────────────────────────────────────────────────────────────
  const runQuery = async (q?: string) => {
    const query = (q ?? question).trim();
    if (!query) return;
    setRunning(true); setError(null);
    try {
      const resp = await fetch(`${API_BASE}/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: query, allow_write: false }),
      });
      if (!resp.ok) { const e = await resp.json(); throw new Error(e.detail ?? "Query failed"); }
      const result: QueryResult = await resp.json();
      setCurrent(result);
      setTabView("query");
      setHistory((h) => [{ question: query, sql: result.sql, ts: Date.now() }, ...h].slice(0, 8));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setRunning(false);
    }
  };

  const resetToSample = async () => {
    setError(null); setUploadMsg(null); setCurrent(null); setHistory([]);
    await fetch(`${API_BASE}/schema?refresh=true`);
    const tables = await fetchSchema();
    if (tables.length > 0) { setActiveTable(tables[0].name); setTabView("preview"); }
  };

  const currentTable = useMemo(
    () => schema.find((t) => t.name === activeTable) ?? schema[0],
    [schema, activeTable]
  );

  return (
    <div
      style={{ background: BG, minHeight: "100vh", color: TEXT, fontFamily: "'Inter', ui-sans-serif, system-ui, sans-serif" }}
      onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
      onDragLeave={() => setDragOver(false)}
      onDrop={onDrop}
    >
      <style>{`
        .mono{font-family:'JetBrains Mono',ui-monospace,'SF Mono',Menlo,monospace}
        ::selection{background:${ACCENT}55}
        input:focus-visible,button:focus-visible{outline:2px solid ${ACCENT};outline-offset:2px}
        .chip:hover{border-color:${ACCENT}!important;color:${TEXT}!important}
        @keyframes blink{0%,100%{opacity:1}50%{opacity:0.3}}
        @keyframes pulse{0%,100%{opacity:1}50%{opacity:0.5}}
      `}</style>

      {/* Drag overlay */}
      {dragOver && (
        <div style={{ position:"fixed",inset:0,background:`${ACCENT}18`,border:`2px dashed ${ACCENT}`,zIndex:50,display:"flex",alignItems:"center",justifyContent:"center",pointerEvents:"none" }}>
          <div style={{ background:PANEL,borderRadius:16,padding:"32px 48px",textAlign:"center" }}>
            <UploadCloud size={40} color={ACCENT} style={{ margin:"0 auto 12px" }} />
            <p style={{ fontSize:18,fontWeight:700,margin:0 }}>Drop your CSV here</p>
          </div>
        </div>
      )}

      {/* ── Header ── */}
      <div style={{ borderBottom:`1px solid ${BORDER}` }}>
        <div style={{ maxWidth:1240,margin:"0 auto",padding:"16px 24px",display:"flex",alignItems:"center",justifyContent:"space-between",flexWrap:"wrap",gap:12 }}>
          <div style={{ display:"flex",alignItems:"center",gap:10 }}>
            <div style={{ width:28,height:28,borderRadius:6,background:ACCENT,display:"flex",alignItems:"center",justifyContent:"center" }}>
              <Terminal size={16} color={BG} />
            </div>
            <div>
              <h1 style={{ fontSize:17,fontWeight:700,margin:0 }}>Ask Your Data</h1>
              <p className="mono" style={{ fontSize:11,color:MUTED,margin:"2px 0 0" }}>natural language → SQL</p>
            </div>
          </div>
          <div style={{ display:"flex",gap:8 }}>
            <input ref={fileInputRef} type="file" accept=".csv" style={{ display:"none" }} onChange={onFileInput} />
            <button onClick={() => fileInputRef.current?.click()} disabled={uploading}
              style={{ display:"flex",alignItems:"center",gap:6,background:ACCENT,color:BG,border:"none",borderRadius:8,padding:"8px 16px",fontSize:12.5,fontWeight:700,cursor:uploading?"not-allowed":"pointer" }}>
              <UploadCloud size={14} style={{ animation:uploading?"pulse 1s infinite":"none" }} />
              {uploading ? "Uploading…" : "Upload CSV"}
            </button>
            <button onClick={resetToSample}
              style={{ display:"flex",alignItems:"center",gap:6,background:"transparent",border:`1px solid ${BORDER}`,color:MUTED,borderRadius:8,padding:"8px 12px",fontSize:12.5,cursor:"pointer" }}>
              <RotateCcw size={13} /> Sample data
            </button>
          </div>
        </div>
      </div>

      <div style={{ maxWidth:1240,margin:"0 auto",padding:"22px 24px 60px",display:"grid",gridTemplateColumns:"250px 1fr",gap:22 }}>

        {/* ── Sidebar ── */}
        <div style={{ display:"flex",flexDirection:"column",gap:14 }}>

          {/* Table list */}
          <div style={{ background:PANEL,border:`1px solid ${BORDER}`,borderRadius:12,padding:14 }}>
            <div style={{ display:"flex",alignItems:"center",gap:7,marginBottom:10 }}>
              <Database size={13} color={TEAL} />
              <span style={{ fontSize:12,fontWeight:700,color:MUTED,textTransform:"uppercase",letterSpacing:.5 }}>Tables</span>
            </div>
            {schema.map((t) => (
              <button key={t.name} onClick={() => { setActiveTable(t.name); setTabView("preview"); }}
                style={{ width:"100%",textAlign:"left",display:"flex",alignItems:"center",justifyContent:"space-between",background:t.name===activeTable?`${ACCENT}18`:"transparent",border:`1px solid ${t.name===activeTable?ACCENT:BORDER}`,borderRadius:8,padding:"8px 10px",marginBottom:6,cursor:"pointer" }}>
                <span style={{ fontSize:12.5,fontWeight:t.name===activeTable?700:400,color:t.name===activeTable?ACCENT:TEXT,fontFamily:"monospace" }}>{t.name}</span>
                <span style={{ fontSize:10,color:MUTED }}>{t.row_count != null ? `${t.row_count}r` : ""}</span>
              </button>
            ))}
          </div>

          {/* Schema columns */}
          {currentTable && (
            <div style={{ background:PANEL,border:`1px solid ${BORDER}`,borderRadius:12,padding:14 }}>
              <div style={{ fontSize:11,color:MUTED,fontWeight:600,textTransform:"uppercase",letterSpacing:.5,marginBottom:8 }}>Columns</div>
              {currentTable.columns.map((c) => (
                <div key={c.name} style={{ display:"flex",justifyContent:"space-between",fontSize:11.5,padding:"5px 0",borderTop:`1px solid ${BORDER}` }}>
                  <span className="mono" style={{ color:TEXT }}>{c.name}</span>
                  <span style={{ color:["REAL","INTEGER","real","integer","int","float","numeric","double"].some(x=>c.type.toLowerCase().includes(x))?TEAL:MUTED,fontSize:10 }}>{c.type}</span>
                </div>
              ))}
            </div>
          )}

          {/* History */}
          <div style={{ background:PANEL,border:`1px solid ${BORDER}`,borderRadius:12,padding:14 }}>
            <div style={{ display:"flex",alignItems:"center",gap:7,marginBottom:10 }}>
              <History size={13} color={ACCENT} />
              <span style={{ fontSize:12,fontWeight:700 }}>Recent queries</span>
            </div>
            {history.length===0 ? (
              <p style={{ fontSize:11.5,color:MUTED,margin:0 }}>Nothing yet</p>
            ) : history.map((h,i) => (
              <button key={h.ts} onClick={() => { setQuestion(h.question); runQuery(h.question); }}
                style={{ textAlign:"left",background:"transparent",border:"none",padding:"4px 0",cursor:"pointer",display:"block",width:"100%" }}>
                <span style={{ fontSize:11.5,color:i===0?TEXT:MUTED }}>{h.question}</span>
              </button>
            ))}
          </div>
        </div>

        {/* ── Main area ── */}
        <div style={{ minWidth:0 }}>

          {/* Banners */}
          {uploadMsg && (
            <div style={{ display:"flex",gap:8,alignItems:"center",background:"#0D2318",border:`1px solid ${GREEN}55`,color:GREEN,padding:"10px 14px",borderRadius:8,marginBottom:14,fontSize:13 }}>
              <ShieldCheck size={15} /> {uploadMsg}
            </div>
          )}
          {error && (
            <div style={{ display:"flex",gap:8,alignItems:"center",background:"#2A1518",border:"1px solid #5C2A2E",color:DANGER,padding:"10px 14px",borderRadius:8,marginBottom:14,fontSize:13 }}>
              <AlertTriangle size={15} /> {error}
            </div>
          )}

          {/* Question box */}
          <div style={{ background:PANEL,border:`1px solid ${BORDER}`,borderRadius:12,padding:18,marginBottom:18 }}>
            <div style={{ display:"flex",gap:10 }}>
              <input value={question} onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={(e) => e.key==="Enter" && runQuery()}
                placeholder={currentTable ? `Ask about "${currentTable.name}"…` : "Ask a question about your data…"}
                style={{ flex:1,background:PANEL2,border:`1px solid ${BORDER}`,borderRadius:8,padding:"12px 14px",fontSize:14,color:TEXT }} />
              <button onClick={() => runQuery()} disabled={running||!question.trim()}
                style={{ display:"flex",alignItems:"center",gap:7,background:question.trim()?ACCENT:BORDER,color:question.trim()?BG:MUTED,border:"none",borderRadius:8,padding:"0 20px",fontSize:13.5,fontWeight:700,cursor:question.trim()?"pointer":"not-allowed",whiteSpace:"nowrap" }}>
                <Send size={14} /> Ask
              </button>
            </div>
            <div style={{ display:"flex",flexWrap:"wrap",gap:7,marginTop:12 }}>
              {SUGGESTIONS.map((s) => (
                <button key={s} className="chip" onClick={() => { setQuestion(s); runQuery(s); }}
                  style={{ fontSize:11.5,color:MUTED,background:"transparent",border:`1px solid ${BORDER}`,borderRadius:20,padding:"5px 12px",cursor:"pointer" }}>
                  {s}
                </button>
              ))}
            </div>
          </div>

          {/* Tab switcher: Data Preview / Query Results */}
          <div style={{ display:"flex",gap:0,marginBottom:16,background:PANEL,border:`1px solid ${BORDER}`,borderRadius:10,padding:4,width:"fit-content" }}>
            {([["preview","Data Preview",Eye],["query","Query Results",MessageSquare]] as const).map(([id, label, Icon]) => (
              <button key={id} onClick={() => setTabView(id)}
                style={{ display:"flex",alignItems:"center",gap:6,padding:"7px 16px",borderRadius:7,border:"none",background:tabView===id?PANEL2:"transparent",color:tabView===id?TEXT:MUTED,fontSize:13,fontWeight:tabView===id?600:400,cursor:"pointer" }}>
                <Icon size={13} /> {label}
                {id==="query" && current && (
                  <span style={{ background:ACCENT,color:BG,borderRadius:10,fontSize:9,padding:"1px 6px",fontWeight:700,marginLeft:2 }}>{current.row_count}</span>
                )}
              </button>
            ))}
          </div>

          {/* Loading indicator */}
          {running && (
            <div style={{ display:"flex",alignItems:"center",gap:8,color:MUTED,fontSize:13,marginBottom:16 }}>
              <Sparkles size={14} color={ACCENT} style={{ animation:"blink 1s infinite" }} />
              Generating SQL with Groq and executing query…
            </div>
          )}

          {/* ── DATA PREVIEW TAB ── */}
          {tabView==="preview" && (
            <div style={{ background:PANEL,border:`1px solid ${BORDER}`,borderRadius:12,padding:18 }}>
              <div style={{ display:"flex",alignItems:"center",gap:8,marginBottom:14 }}>
                <Table2 size={15} color={TEAL} />
                <span style={{ fontSize:13,fontWeight:700 }}>
                  {currentTable?.name ?? "Dataset"} — all rows
                </span>
                {preview && (
                  <span className="mono" style={{ fontSize:10.5,color:MUTED }}>
                    ({preview.row_count} rows · {preview.columns.length} columns)
                  </span>
                )}
              </div>

              {previewLoading && (
                <div style={{ display:"flex",alignItems:"center",gap:8,color:MUTED,fontSize:13,padding:"20px 0" }}>
                  <Sparkles size={14} color={ACCENT} style={{ animation:"blink 1s infinite" }} />
                  Loading data…
                </div>
              )}

              {!previewLoading && preview && preview.results.length > 0 && (
                <DataTable columns={preview.columns} rows={preview.results} />
              )}

              {!previewLoading && (!preview || preview.results.length === 0) && (
                <div style={{ textAlign:"center",padding:"40px 0",color:MUTED }}>
                  <Table2 size={28} color={BORDER} style={{ margin:"0 auto 10px" }} />
                  <p style={{ margin:0,fontSize:13 }}>No data to preview</p>
                </div>
              )}
            </div>
          )}

          {/* ── QUERY RESULTS TAB ── */}
          {tabView==="query" && !running && (
            <div>
              {current ? (
                <>
                  {/* SQL */}
                  <div style={{ background:PANEL,border:`1px solid ${BORDER}`,borderRadius:12,padding:18,marginBottom:16 }}>
                    <div style={{ display:"flex",alignItems:"center",justifyContent:"space-between",marginBottom:10 }}>
                      <div style={{ display:"flex",alignItems:"center",gap:7 }}>
                        <ChevronRight size={14} color={ACCENT} />
                        <span style={{ fontSize:12.5,fontWeight:700 }}>Generated SQL</span>
                      </div>
                      <div style={{ display:"flex",alignItems:"center",gap:5,fontSize:10.5,color:TEAL }}>
                        <ShieldCheck size={13} /> read-only · validated
                      </div>
                    </div>
                    <pre className="mono" style={{ background:PANEL2,border:`1px solid ${BORDER}`,borderRadius:8,padding:14,fontSize:12.5,color:TEAL,margin:0,overflowX:"auto",lineHeight:1.6,whiteSpace:"pre-wrap",wordBreak:"break-word" }}>
                      {current.sql}
                    </pre>
                  </div>

                  {/* Results */}
                  <div style={{ background:PANEL,border:`1px solid ${BORDER}`,borderRadius:12,padding:18 }}>
                    <div style={{ display:"flex",alignItems:"center",gap:7,marginBottom:14 }}>
                      <Table2 size={14} color={TEAL} />
                      <span style={{ fontSize:12.5,fontWeight:700 }}>Results</span>
                      <span className="mono" style={{ fontSize:10.5,color:MUTED }}>
                        ({current.row_count} row{current.row_count!==1?"s":""})
                      </span>
                    </div>
                    {current.results.length===0 ? (
                      <p style={{ fontSize:12.5,color:MUTED,margin:0 }}>No matching rows.</p>
                    ) : (
                      <DataTable columns={current.columns} rows={current.results} />
                    )}
                  </div>
                </>
              ) : (
                <div style={{ textAlign:"center",padding:"60px 20px",color:MUTED,fontSize:13 }}>
                  <MessageSquare size={28} color={BORDER} style={{ margin:"0 auto 10px" }} />
                  <p style={{ margin:"0 0 6px" }}>No query run yet</p>
                  <p style={{ margin:0,fontSize:11.5 }}>Ask a question above to see results here</p>
                </div>
              )}
            </div>
          )}

          {/* Fallback empty state */}
          {tabView==="query" && running && null}
        </div>
      </div>
    </div>
  );
}
