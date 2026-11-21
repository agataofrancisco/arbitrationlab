// Coluna 2: texto original com o span de evidencia do campo selecionado destacado.
// Os offsets vem da API e apontam para o texto original, por isso o destaque e exacto.

function spanFor(field) {
  const evidence = field?.evidence;
  if (!evidence || evidence.start === null || evidence.start === undefined) return null;
  return evidence;
}

export default function EvidenceColumn({ text, field, fieldName }) {
  if (!text) return <p className="muted">Sem texto.</p>;
  const span = spanFor(field);
  if (!span) {
    return (
      <div className="column-body">
        <p className="muted">
          {fieldName ? `"${fieldName}" não tem evidência no texto.` : "Escolha um campo."}
        </p>
        <pre className="document">{text}</pre>
      </div>
    );
  }
  const before = text.slice(0, span.start);
  const middle = text.slice(span.start, span.end);
  const after = text.slice(span.end);
  return (
    <div className="column-body">
      <p className="muted small">
        evidência {span.method} (score {span.score}) em [{span.start}, {span.end}]
      </p>
      <pre className="document">
        {before}
        <mark>{middle}</mark>
        {after}
      </pre>
    </div>
  );
}
