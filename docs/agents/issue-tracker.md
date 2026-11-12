# Issue tracker: Markdown local

Specs e tickets ficam em `.scratch/`, versionados com o código.

- Uma feature por pasta: `.scratch/<feature-slug>/`, com a spec em `.scratch/<feature-slug>/spec.md` quando houver.
- Um arquivo por ticket: `.scratch/<feature-slug>/issues/<NN>-<slug>.md`, numerados a partir de `01`.
- O estado é a linha `**Status:**` perto do topo, com os papéis de `triage-labels.md`; `**Blocked by:**` lista os tickets que o travam; uma linha opcional `**Needs:**` marca o que uma execução sem gente não faz (`gpu`, `gui`, `live`, `design`).
- Decisões de quem implementou vão em `## Decisions`; conversa vai em `## Comments`, no fim.
- Os planos antigos do superpowers, todos concluídos, estão em `docs/archive/superpowers/plans/`.
