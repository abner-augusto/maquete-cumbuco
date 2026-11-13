# 01 - Medir cobertura no check, pôr os componentes Svelte no gate e mover os contratos do pipeline para um guia

Status: resolved

Origem: adoção da tropa, 2026-11-12. Decisões já tomadas pelo dono do repo.

## O que fazer

1. **Cobertura do Python no check.** Acrescente `pytest-cov` ao grupo de desenvolvimento do `pyproject.toml` (atualize o `uv.lock`). Faça o `scripts/check` rodar o pytest com cobertura do pacote `scripts` e gravar `coverage.json` na raiz (`--cov=scripts --cov-report=json:coverage.json`), nos dois modos. Ponha `coverage.json` e `.coverage` no `.gitignore`. Em `docs/agents/tropa.toml`, `[quality] coverage = "coverage.json"`. O front continua sem cobertura: a chave guarda um caminho só.
2. **Svelte no gate.** O `tropa quality` passou a ler `.svelte` (o bloco `<script>` pelo scanner de TypeScript, o arquivo inteiro no limite de linhas). Acrescente `frontend/src/**/*.svelte` ao `[quality] include` do `docs/agents/tropa.toml`.
3. **Guia do pipeline.** A seção "Contratos entre planos" de `docs/archive/superpowers/plans/2026-10-14-00-plano-mestre.md` ainda é referência viva (id do lote, origem local, esquemas dos JSON, ordem de geração). Copie o conteúdo dela, sem reescrever os fatos, para `.agents/guides/pipeline.md`, que abre com a linha "Leia este guia antes de mudar um script do pipeline, um esquema de `dados/` ou a ordem de geração." Tire do texto o que só fazia sentido como plano (numeração de planos, "o plano N faz"), mantendo cada contrato. No `AGENTS.md`, acrescente uma linha de rota para o guia. O plano arquivado não muda.

## Não faça

- **Não toque em `docs/agents/quality-baseline.json`.** Os passos 1 e 2 fazem o `tropa quality` acusar achados novos (`function.crap` e os dos `.svelte`); o orquestrador atualiza a linha de base depois de conferir. Por isso o `bash scripts/check --tudo` vai sair com 1 só por causa do quality: relate a contagem de achados novos por regra.
- Não rode deploy (`npm run publicar`, `wrangler`), nem o e2e do Playwright, nem nada na porta 4173.
- Não leia nem imprima o `.env`. Respeite a seção Confidentiality do `AGENTS.md`.
- Não mude código de aplicação nem testes.
- Não faça push.

## Critérios de aceite

- [ ] `bash scripts/check --tudo`: pytest, svelte-check, vitest e node passam; a única parte vermelha é o `tropa quality`, só com achados `[new]`.
- [ ] `coverage.json` existe depois do check e está ignorado pelo git.
- [ ] `tropa quality .` não imprime mais `crap: not run` e lista arquivos `.svelte`.
- [ ] `.agents/guides/pipeline.md` existe, abre com a linha de leitura e contém cada contrato da seção de origem.
- [ ] `AGENTS.md` tem a linha de rota para o guia.

## Commits

Três commits na convenção do repo (tipo em inglês, descrição em português, sem trailers): cobertura no check; Svelte no gate; guia do pipeline. Este ticket fica como está (`Status: claimed`): o orquestrador o resolve com a linha de base.
