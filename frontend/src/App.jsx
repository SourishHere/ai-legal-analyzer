import React, { useMemo, useState } from "react";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

function App() {
  const [description, setDescription] = useState("");
  const [files, setFiles] = useState([]);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const previews = useMemo(
    () => files.filter((file) => file.type.startsWith("image/")).map((file) => ({ file, url: URL.createObjectURL(file) })),
    [files]
  );

  const handleFiles = (event) => {
    const selected = Array.from(event.target.files || []);
    setFiles((current) => [...current, ...selected].slice(0, 8));
    setResult(null);
    setError("");
  };

  const removeFile = (index) => setFiles((current) => current.filter((_, i) => i !== index));

  const analyze = async () => {
    if (!description.trim()) {
      setError("Please describe what happened first.");
      return;
    }

    setLoading(true);
    setError("");
    setResult(null);

    try {
      const form = new FormData();
      form.append("description", description);
      files.forEach((file) => form.append("evidence", file));

      const response = await fetch(`${API_URL}/api/analyze`, { method: "POST", body: form });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Analysis failed");
      setResult(data);
    } catch (err) {
      setError(err.message || "Could not connect to the backend.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="page">
      <nav className="nav">
        <div className="brand"><span className="brand-mark">⚖</span> CaseLens AI</div>
        <span className="demo-badge">HACKATHON MVP</span>
      </nav>

      <section className="hero">
        <div className="eyebrow">AI-POWERED EVIDENCE ANALYSIS</div>
        <h1>Turn evidence into a<br /><span>clearer case.</span></h1>
        <p>Upload photos or video evidence, explain what happened, and get an evidence-grounded case assessment in seconds.</p>
      </section>

      <section className="workspace">
        <div className="panel input-panel">
          <div className="section-title"><span>01</span> Tell us what happened</div>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Example: A car hit my parked vehicle outside my apartment and drove away. I recorded part of the incident..."
          />

          <div className="section-title evidence-title"><span>02</span> Add evidence</div>
          <label className="dropzone">
            <input type="file" accept="image/*,video/*" multiple onChange={handleFiles} />
            <div className="upload-icon">↑</div>
            <strong>Drop evidence here or browse</strong>
            <small>JPG, PNG, WEBP, MP4, MOV · Up to 8 files</small>
          </label>

          {files.length > 0 && (
            <div className="file-list">
              {files.map((file, index) => (
                <div className="file-row" key={`${file.name}-${index}`}>
                  <span>{file.type.startsWith("video/") ? "🎥" : "🖼️"}</span>
                  <div><strong>{file.name}</strong><small>{(file.size / 1024 / 1024).toFixed(2)} MB</small></div>
                  <button onClick={() => removeFile(index)} aria-label="Remove file">×</button>
                </div>
              ))}
            </div>
          )}

          {previews.length > 0 && <div className="previews">{previews.map(({ file, url }) => <img src={url} alt={file.name} key={url} />)}</div>}

          <button className="analyze-btn" onClick={analyze} disabled={loading}>
            {loading ? "Analyzing evidence…" : "Analyze my case →"}
          </button>
          {error && <div className="error">{error}</div>}
        </div>

        <div className="panel result-panel">
          {!result && !loading ? (
            <div className="empty-state">
              <div className="empty-icon">✦</div>
              <h2>Your case analysis will appear here</h2>
              <p>Our AI will compare your description with the visual evidence and highlight what is supported, what is uncertain, and what evidence is still missing.</p>
              <div className="mini-flow"><span>Evidence</span><b>→</b><span>Analysis</span><b>→</b><span>Next steps</span></div>
            </div>
          ) : loading ? (
            <div className="loading-state"><div className="spinner" /><h2>Examining your evidence…</h2><p>Checking the uploaded visuals against your description.</p></div>
          ) : (
            <Analysis result={result} />
          )}
        </div>
      </section>

      <footer>This demo provides AI-assisted information, not legal advice or a prediction of court outcomes.</footer>
    </main>
  );
}

function Analysis({ result }) {
  const score = Number(result.case_strength || 0);
  return (
    <div className="analysis">
      <div className="analysis-head"><div><div className="eyebrow">CASE ANALYSIS</div><h2>Evidence assessment</h2></div><div className="score"><strong>{score}</strong><span>/10</span><small>evidence strength</small></div></div>

      <section><h3>Incident summary</h3><p>{result.incident_summary}</p></section>
      <section><h3>What the evidence appears to show</h3><List items={result.evidence_observations} /></section>
      <section><h3>Potentially relevant issues</h3><List items={result.potential_legal_issues} /></section>
      <section className="reason"><h3>Why this score?</h3><p>{result.case_strength_reason}</p></section>
      <section><h3>Missing evidence</h3><List items={result.missing_evidence} warning /></section>
      <section><h3>Recommended next steps</h3><List items={result.next_steps} /></section>
      <div className="disclaimer">{result.disclaimer}</div>
    </div>
  );
}

function List({ items = [], warning = false }) {
  if (!items.length) return <p className="muted">None identified from the submitted information.</p>;
  return <ul className={warning ? "warning-list" : "check-list"}>{items.map((item, index) => <li key={index}>{item}</li>)}</ul>;
}

export default App;
