# ArbitrationLab

Arbitragem calibrada de extrações feitas por LLMs: cada valor tem de existir no texto original, a confiança vem de fiabilidade medida, e o sistema abstém-se ou pede revisão humana quando não tem certeza.

Domínio fictício e dados sintéticos: participações de sinistro automóvel da **Seguros Horizonte Azul**. Não há PII real.

> Estado: a arbitragem, a API, a revisão humana, a exportação, o painel e a experiência em mock estão implementados e testados. **Não há resultados com modelos reais**: os números do projecto são de mock e estão marcados como tal. Ver `docs/case-study.md`.

## O que faz

- Pede a 2 ou 3 candidatos (mock nesta versão) a extracção de 7 campos com schema JSON.
- Normaliza cada valor por tipo (datas com ambiguidade explícita, montantes em pt-PT ou por extenso, matrículas, moedas, booleanos).
- Procura o valor no texto e devolve o span com offsets exactos.
- Decide cada campo: `accept`, `verify`, `human_review` ou `abstain`, com motivo registado.
- Revisão humana via API e painel de três colunas, com auditoria (quem, quando, valor anterior e novo).
- Exporta revisões para JSONL com `source: human_review`.
- Compara cinco estratégias num relatório accuracy-vs-custo.

## Requisitos

- Python 3.12
- Node 22+ (só para o painel)
- Sem Docker, sem GPU, sem base de dados externa (SQLite).

## Instalar e validar

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
ruff check . && ruff format --check .
pytest
```

Gerar o dataset (determinista; o ficheiro versionado é o resultado):

```bash
python -m arbitrationlab.dataset.generator --out datasets/claims
```

Experiência em mock (sem custos; gera tabela, gráfico e JSON):

```bash
python -m arbitrationlab.experiments.run --mode mock --out experiments/reports
```

`--mode real` está recusado de propósito: exige chaves de API e execução manual.

## Correr a API

```bash
cp .env.example .env                  # não é versionado; ajustar os tokens
python -m arbitrationlab              # http://127.0.0.1:8000
```

Tokens de demo (só para desenvolvimento local): `demo-client-token` (papel `client`) e `demo-reviewer-token` (papel `reviewer`). Em qualquer outro ambiente, definir `ARBITRATIONLAB_CLIENT_TOKEN` e `ARBITRATIONLAB_REVIEWER_TOKEN`.

Exemplo (PowerShell ou Git Bash):

```bash
curl -X POST http://127.0.0.1:8000/arbitrations \
  -H "Authorization: Bearer demo-client-token" -H "Content-Type: application/json" \
  -d @request.json
curl http://127.0.0.1:8000/arbitrations/<id> -H "Authorization: Bearer demo-client-token"
```

Endpoints: `POST /arbitrations`, `GET /arbitrations/{id}`, `GET /arbitrations/{id}/candidates`, `POST /arbitrations/{id}/human-review` (papel `reviewer`; o revisor é o principal do token), `GET /reviews/export` (papel `reviewer`), `GET /metrics`, `GET /schemas/claim`, `GET /health`.

## Painel de revisão

```bash
cd frontend
npm ci
npm run dev           # http://localhost:5173 (encaminha /arbitrations etc. para 127.0.0.1:8000)
npm run build         # build de produção em frontend/dist
```

O token e o identificador do revisor ficam só em memória no separador.

## Documentação

- `docs/learn/` — percurso pedagógico (00 a 07), com as decisões e os números reais.
- `docs/architecture.md` — módulos, fluxo de dados e revisão de segurança.
- `docs/decisions.md` — decisões registadas e alternativas.
- `docs/case-study.md` — resultados medidos e o que ainda não foi medido.
- `openspec/changes/bootstrap-arbitrationlab/` — proposta, desenho, especificações e tarefas.

## Limitações conhecidas

- Os modelos são mocks deterministas com erros injectados; não medem LLMs reais.
- A revisão humana é simulada a partir dos labels (optimista).
- A identidade do revisor é a do token (principal fixo `revisor-demo`, configurável). Não há identidade por pessoa: quem tiver o token de revisor actua como esse principal.
- Docker e `docker-compose.yml` não foram testados localmente.
- O adaptador RegressionGuard (tarefa 4.3, opcional) não foi feito.
