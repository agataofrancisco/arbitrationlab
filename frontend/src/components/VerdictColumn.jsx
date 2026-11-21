// Coluna 3: veredicto por campo, motivo de abstencao, custo, latencia e revisao humana.
import { useState } from "react";

const DECISION_LABEL = {
  accept: "aceite",
  verify: "verificar",
  human_review: "revisão",
  abstain: "abstenção",
};

function formatValue(value) {
  if (value === null || value === undefined) return "—";
  if (typeof value === "boolean") return value ? "sim" : "não";
  return String(value);
}

function ReviewForm({ name, field, busy, onSubmit }) {
  const [value, setValue] = useState(field.suggested_value ?? "");
  return (
    <div className="review">
      <label>
        Valor corrigido
        <input value={value} onChange={(event) => setValue(event.target.value)} />
      </label>
      <div className="actions">
        <button
          type="button"
          disabled={busy || field.suggested_value === null || field.suggested_value === undefined}
          onClick={() => onSubmit(name, "confirm")}
        >
          Confirmar sugestão
        </button>
        <button type="button" disabled={busy || value === ""} onClick={() => onSubmit(name, "correct", value)}>
          Corrigir
        </button>
        <button type="button" disabled={busy} onClick={() => onSubmit(name, "unreadable")}>
          Ilegível
        </button>
      </div>
    </div>
  );
}

export default function VerdictColumn({
  arbitration,
  selected,
  onSelect,
  onReview,
  busy,
}) {
  const fields = arbitration.fields;
  return (
    <div className="column-body">
      <p className="muted small">
        custo {arbitration.spent_usd.toFixed(4)} / {arbitration.max_spend.toFixed(4)} USD · latência{" "}
        {arbitration.latency_ms.toFixed(1)} ms
        {arbitration.suspected_injection ? " · instrução suspeita no texto" : ""}
      </p>
      {Object.entries(fields).map(([name, field]) => (
        <section
          key={name}
          className={`verdict decision-${field.decision} ${selected === name ? "selected" : ""}`}
        >
          <button type="button" className="field-title" onClick={() => onSelect(name)}>
            <strong>{name}</strong>
            <span className="badge">{DECISION_LABEL[field.decision] ?? field.decision}</span>
          </button>
          <p className="small">
            valor <strong>{formatValue(field.value)}</strong> · sugerido{" "}
            {formatValue(field.suggested_value)} · confiança {field.confidence.toFixed(2)}
          </p>
          <p className="muted small">motivo: {field.reason}</p>
          {field.human_status && <p className="small">revisão: {field.human_status}</p>}
          {field.pending_review && (
            <ReviewForm name={name} field={field} busy={busy} onSubmit={onReview} />
          )}
        </section>
      ))}
    </div>
  );
}
