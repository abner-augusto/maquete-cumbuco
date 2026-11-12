# 01: Os tiles do mapa do chão vão embutidos em dois GLBs

**Status:** needs-triage

**Origem:** item "Adiado (minor)" de `docs/archive/superpowers/plans/2026-10-16-05-front-publicacao.md` ("Depois do plano"). O plano o deixou sem bloquear a entrega; falta o Abner dizer se vale fazer.

**Situação (12/11/2026):** `frontend/modelos-finais/loteamento.glb` e `frontend/modelos-finais/entorno.glb` trazem as mesmas quatro imagens `mapa_00`, `mapa_01`, `mapa_10` e `mapa_11` (JPEG; 636 191, 609 005, 780 090 e 283 932 bytes, cerca de 2,3 MB no total), então o primeiro carregamento baixa o mapa do chão duas vezes. A causa está em `scripts/loteamento/blender.py`: `com_tiles` pinta `Terreno_<ij>` na cena do loteamento e `Entorno_<ij>` na cena do entorno com os mesmos tiles, e o Blender embute as imagens em cada GLB.

**O que fazer (do plano):** a correção é no pipeline: um dos GLBs sai sem as imagens, e o front reaproveita os materiais `chao_mapa_<ij>` do outro (`frontend/src/lib/cena/chao.ts` já reconhece esses materiais nos dois modelos).

**Critérios de aceite:**

- Só um entre `loteamento.glb` e `entorno.glb` contém as imagens `mapa_<ij>`; o outro não tem nenhuma imagem de tile.
- No front, `Terreno_<ij>` e `Entorno_<ij>` aparecem com o mesmo mapa de hoje, com o masterplan ligado e desligado (a troca pelos `mapa-osm_<ij>.jpg` continua funcionando).
- `npm run verificar` reporta um primeiro carregamento cerca de 2,3 MB menor, e nenhum arquivo passa de 15 MB.
- `frontend/modelos-finais/` é regenerado pelo pipeline e commitado junto; nenhum GLB é editado à mão.
- `bash scripts/check --tudo` e o e2e (`npm test` em `frontend/`) passam.

**Pré-requisitos:** Blender e a pasta do terreno (`TERRENO_DIR`) para regenerar os GLBs.
