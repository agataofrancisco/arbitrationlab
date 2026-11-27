# PROMPT 04 — ArbitrationLab: sistema de arbitragem de saídas LLM

## Objectivo
Constrói uma camada independente que compara respostas de dois ou três modelos/prompt variants para tarefas de **extração estruturada de informações de facturas fictícias** (ou dados de transporte sintéticos). Não confundas voto majoritário com verdade: o sistema deve ter campo `abstain` e possibilidade de revisão humana. Deve funcionar isoladamente e também como módulo opcional do EvalSentinel/ModelMesh.

## Implementação
Backend FastAPI+Pydantic, PostgreSQL/SQLite em demo, OpenRouter provider adapter e mock deterministic. Request recebe `task_id`, texto de input, esquema de output JSON, políticas e `max_spend`. Dois modelos geram candidatos em paralelo com schema validation e limite de tempo/custo. Motor de arbitragem normaliza JSON, valida campos contra o texto original (evidence span + offsets), calcula acordo por campo, score de evidência e fiabilidade histórica obtida num conjunto rotulado. Um judge LLM opcional apenas sugere, sem ser autoridade final. Em desacordo, executar verificação de baixo custo se o orçamento permitir ou enviar para humana; em caso contrário abstém-se. Não armazenar PII de facturas reais.

## UI e API
`POST /arbitrations`, `GET /arbitrations/{id}`, `GET /arbitrations/{id}/candidates`, `POST /arbitrations/{id}/human-review`, `GET /metrics`. Dashboard com três colunas (candidatos, evidências, veredicto), diferenças por campo, motivo de abstenção, custo incremental e latência. Dataset sintético de >=100 registos, incluindo erros propositais: datas ambíguas, valores inconsistentes, campo ausente e prompt injection no texto.

## Experiências
Comparar single cheap model, single strong model, majority vote, evidence-based arbitration e arbitration+review sob o mesmo golden set. Reportar exact match/field-level F1, cobertura de resposta, taxa de erros críticos, latência e custo; especialmente o trade-off accuracy-vs-cost. Confirmar com testes que a arbitragem piora custo/tempo em alguns casos e que dois modelos podem repetir o mesmo erro. O diferencial do projecto é **calibração + abstenção + evidências**, não um nome sofisticado para votação.

## Critérios
Implementa datasets, eval runner, export JSON/CSV de resultados reais, autorização e validação; no CI usa mocks fixos sem custos. Documenta onde o sistema falha e quando não vale a pena arbitrar.

## Regras de execução (obrigatórias)
És um agente sénior de software engineering e AI engineering. A tua missão é IMPLEMENTAR código funcional neste repositório, não apenas escrever um plano ou pseudocódigo. Primeiro inspecciona o repositório; depois propõe em `IMPLEMENTATION_PLAN.md` um plano curto e segue-o por fases até teres uma versão executável. Não pares após criar ficheiros vazios. Usa documentação oficial actual das bibliotecas e fixa versões compatíveis; não inventes APIs nem dependências. Caso não tenhas acesso a rede/credenciais, implementa adaptadores, mocks determinísticos e testes locais, mas distingue explicitamente o que foi testado de verdade do que foi apenas preparado.

Normas comuns: Python 3.11+ (salvo indicação explícita), tipagem, Pydantic v2, configuração por `.env.example`, FastAPI com OpenAPI, Ruff, pytest, logging estruturado sem secrets/PII, Dockerfile, `docker-compose.yml` quando fizer sentido, healthcheck e README claro (arranque, decisões de arquitectura, ameaças, limitações, custos, credenciais e deploy). Não coloques chaves no cliente ou no Git; valida entradas, implementa timeouts/retries limitados e autenticacao para operações administrativas. Inclui modo DEMO com dados sintéticos e sem pagamento; implementa testes unitários e testes de integração determinísticos em CI, mais uma suite de integração real opcional. Escreve `docs/architecture.md`, `docs/decisions.md`, `docs/case-study.md` com métricas REAIS ou campos `TODO: medir` (nunca inventes resultados). Entrega exactamente os comandos de execução e testes e lista limitações.

Para deployment, prepara backend persistente numa VM/serviço de containers e frontend estático quando possível; não assumes que Vercel Functions suporta Redis, workers long-running, volumes persistentes ou treino GPU. Se houver persistência, usa serviço gerido/volume externo e documenta credenciais, migrações e backups. Antes de concluir, executa testes, corrige falhas, regista o output e documenta o que não foi possível executar.
