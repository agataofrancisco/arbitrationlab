// Coluna 1: candidatos. Mostra o estado, custo, latencia e os valores de cada campo.
// Um valor que difere do sugerido e destacado, para ver onde os modelos discordam.

function formatValue(value) {
  if (value === null || value === undefined) return "—";
  if (typeof value === "boolean") return value ? "sim" : "não";
  return String(value);
}

export default function CandidatesColumn({ candidates, fields }) {
  if (!candidates) {
    return <p className="muted">Sem candidatos ainda.</p>;
  }
  return (
    <div className="column-body">
      {candidates.map((candidate) => (
        <section className="candidate" key={candidate.model}>
          <header>
            <strong>{candidate.model}</strong>
            <span className={`badge status-${candidate.status}`}>{candidate.status}</span>
          </header>
          <p className="muted small">
            custo {candidate.cost_usd.toFixed(4)} USD · latência {candidate.latency_ms.toFixed(1)} ms
            {candidate.reason ? ` · ${candidate.reason}` : ""}
          </p>
          {candidate.errors.length > 0 && (
            <ul className="errors">
              {candidate.errors.map((error) => (
                <li key={error}>{error}</li>
              ))}
            </ul>
          )}
          {candidate.output && (
            <table className="values">
              <tbody>
                {Object.entries(candidate.output).map(([name, value]) => {
                  const suggested = fields?.[name]?.suggested_value;
                  const differs = suggested !== undefined && suggested !== null && value !== suggested;
                  return (
                    <tr key={name} className={differs ? "differs" : undefined}>
                      <th scope="row">{name}</th>
                      <td>{formatValue(value)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </section>
      ))}
    </div>
  );
}
