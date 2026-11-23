# Tasks

## 0. Fundações

- [x] 0.1 Criar a estrutura `src/arbitrationlab/`, `tests/`, `frontend/`, `docs/learn/`, `datasets/claims/`, `experiments/`; verificar com `git status`
- [x] 0.2 Confirmar e fixar versões em `pyproject.toml` (FastAPI, Pydantic v2, SQLAlchemy, httpx, pytest, Ruff, scikit-learn); `Settings`, `.env.example`, `/health`, autenticação demo com papéis; verificar que `ruff check` e `pytest` passam
- [x] 0.3 Escrever `docs/learn/00-visao-geral.md` com o diagrama do pipeline; verificar que corresponde aos módulos


## 1. Dataset e geração

- [x] 1.1 Criar o gerador de ≥100 participações sintéticas rotuladas com as dificuldades da spec e o manifesto; verificar com o validador de schema do dataset e as estatísticas por dificuldade
- [x] 1.2 Implementar os candidatos (adaptador compatível com OpenAI e mock com perfis de erro, incluindo correlacionado) com geração paralela, timeout e orçamento; verificar com testes de timeout, `skipped: budget` e erro correlacionado

## 2. Arbitragem

- [x] 2.1 Implementar a normalização por tipo (datas com ambiguidade, montantes, matrículas, booleanos); verificar com testes de "3/2/2026" ambíguo e montantes por extenso
- [x] 2.2 Implementar a localização de evidência com offsets no texto original; verificar com testes de valor inventado → `evidence: none` e offsets exactos
- [x] 2.3 Implementar a fiabilidade histórica (Beta), o score de confiança e a calibração (ECE, reliability diagram); verificar com testes sobre dados com calibração conhecida
- [x] 2.4 Implementar a decisão por campo, a verificação barata, o juiz consultivo e a flag `suspected_injection`; verificar com testes de `evidence_conflict`, desacordo com orçamento e injecção
- [x] 2.5 Escrever `docs/learn/01` a `05`; verificar que os exemplos vêm dos testes

## 3. API e revisão

- [x] 3.1 Implementar a persistência e `POST /arbitrations`, `GET /arbitrations/{id}`, `GET .../candidates`, `POST .../human-review` e `GET /metrics` com papéis; verificar com testes de API (422, 403, auditoria)
- [x] 3.2 Implementar a exportação de revisões para JSONL golden (`source: human_review`); verificar com teste
- [x] 3.3 Implementar o painel de três colunas com destaque de spans; verificar no browser

## 4. Experiência

- [x] 4.1 Implementar o runner das 5 estratégias com revisão simulada e as métricas da spec; verificar que corre em mock e gera tabela e gráfico
- [x] 4.2 Correr a experiência em mock, gravar o relatório com os casos desfavoráveis e os erros correlacionados; verificar que os números vêm da run
- [x] 4.3 (Opcional) Criar o adaptador que expõe a arbitragem como avaliador do RegressionGuard; verificado com suite de exemplo (8 casos, `experiments/regressionguard/claims-smoke.jsonl`) e com testes saltados sem o extra (`tests/test_regressionguard_adapter.py`).
- [x] 4.4 Escrever `docs/learn/06-custo-vs-qualidade.md` e documentar onde o sistema falha; verificar a consistência com o relatório

## 5. Entrega

- [x] 5.1 Dockerfile, `docker-compose.yml` (marcado como não testado localmente) e CI (Ruff, pytest, experiência em mock, build do frontend); verificar a validade do workflow
- [x] 5.2 `README.md`, `docs/architecture.md`, `docs/decisions.md` e `docs/case-study.md`; verificar que os comandos correm
- [x] 5.3 `docs/learn/07-perguntas-de-entrevista.md` (≥25); verificar a consistência com o código
- [x] 5.4 Revisão de segurança independente (entrada não confiável, injecção, PII sintética, papéis de revisão); verificar que os achados estão resolvidos ou documentados

## Workflow follow-up

- Execução real manual com 2-3 modelos e `max_spend`.
- Arquivar após revisão.
