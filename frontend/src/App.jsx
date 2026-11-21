import { useEffect, useState } from "react";
import { apiRequest } from "./api.js";
import CandidatesColumn from "./components/CandidatesColumn.jsx";
import EvidenceColumn from "./components/EvidenceColumn.jsx";
import VerdictColumn from "./components/VerdictColumn.jsx";
import { SAMPLE_TEXT } from "./sample.js";

const POLL_MS = 400;
const POLL_LIMIT = 50;

export default function App() {
  const [token, setToken] = useState("");
  const [actor, setActor] = useState("");
  const [text, setText] = useState(SAMPLE_TEXT);
  const [schema, setSchema] = useState(null);
  const [arbitration, setArbitration] = useState(null);
  const [candidates, setCandidates] = useState(null);
  const [selected, setSelected] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!token) return;
    apiRequest("/schemas/claim", { token })
      .then(setSchema)
      .catch((err) => setError(err.message));
  }, [token]);

  async function loadResult(id) {
    for (let attempt = 0; attempt < POLL_LIMIT; attempt += 1) {
      const view = await apiRequest(`/arbitrations/${id}`, { token });
      setArbitration(view);
      if (view.status !== "pending") {
        const list = await apiRequest(`/arbitrations/${id}/candidates`, { token });
        setCandidates(list.candidates);
        return view;
      }
      await new Promise((resolve) => setTimeout(resolve, POLL_MS));
    }
    throw new Error("a arbitragem demorou demasiado");
  }

  async function run(action) {
    setBusy(true);
    setError("");
    try {
      await action();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  function arbitrate() {
    return run(async () => {
      if (!schema) throw new Error("indique um token válido para carregar o schema");
      const created = await apiRequest("/arbitrations", {
        token,
        method: "POST",
        body: {
          task_id: "painel-revisao",
          text,
          output_schema: schema,
          policy: { candidates: ["cheap-a", "cheap-b", "strong-c"], judge: false },
        },
      });
      setCandidates(null);
      const view = await loadResult(created.arbitration_id);
      const firstPending = view.pending_review[0] ?? Object.keys(view.fields)[0];
      setSelected(firstPending ?? null);
    });
  }

  function review(name, action, value) {
    return run(async () => {
      const payload = { field: name, action };
      if (action === "correct") payload.value = value;
      const view = await apiRequest(`/arbitrations/${arbitration.arbitration_id}/human-review`, {
        token,
        actor,
        method: "POST",
        body: { decisions: [payload] },
      });
      setArbitration(view);
    });
  }

  const selectedField = arbitration && selected ? arbitration.fields[selected] : null;
  const canRun = Boolean(token && actor);

  return (
    <div className="app">
      <header className="topbar">
        <h1>ArbitrationLab · revisão</h1>
        <div className="auth">
          <label>
            Token
            <input type="password" value={token} onChange={(e) => setToken(e.target.value)} />
          </label>
          <label>
            Revisor (X-Actor)
            <input value={actor} onChange={(e) => setActor(e.target.value)} />
          </label>
        </div>
      </header>

      <section className="input">
        <label>
          Texto da participação (dados sintéticos)
          <textarea rows={6} value={text} onChange={(e) => setText(e.target.value)} />
        </label>
        <div className="actions">
          <button type="button" disabled={busy || !canRun} onClick={arbitrate}>
            Arbitrar
          </button>
          <span className="muted small">
            O token de revisão é necessário para submeter revisões; um token de cliente só arbitra.
          </span>
        </div>
        {error && <p role="alert" className="error">{error}</p>}
      </section>

      {arbitration && (
        <main className="columns">
          <section className="column" aria-label="Candidatos">
            <h2>Candidatos</h2>
            <CandidatesColumn candidates={candidates} fields={arbitration.fields} />
          </section>
          <section className="column" aria-label="Evidências">
            <h2>Evidências {selected ? `· ${selected}` : ""}</h2>
            <EvidenceColumn text={arbitration.text} field={selectedField} fieldName={selected} />
          </section>
          <section className="column" aria-label="Veredicto">
            <h2>Veredicto</h2>
            <VerdictColumn
              arbitration={arbitration}
              selected={selected}
              onSelect={setSelected}
              onReview={review}
              busy={busy}
            />
          </section>
        </main>
      )}
    </div>
  );
}
