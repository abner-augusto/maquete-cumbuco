<script lang="ts">
  import Icone from './Icone.svelte';

  let { escuro }: { escuro: boolean } = $props();
</script>

<img class="logo" src={escuro ? 'marca/produto-vertical-negativo.svg' : 'marca/produto-vertical-positivo.svg'} alt="" />
<h2>Como explorar</h2>

<section class="secao">
  <h3 class="subtitulo">Gestos na tela</h3>
  <ul class="lista gestos">
    <li>
      <div class="icone-gesto"><Icone gesto="girar" tamanho={40} /></div>
      <span>Arraste para girar<small>Com um dedo na cena para orbitar e ver de outros ângulos.</small></span>
    </li>
    <li>
      <div class="icone-gesto"><Icone gesto="pincar" tamanho={40} /></div>
      <span>Pince para aproximar<small>Afaste ou junte os dois dedos para regular a distância.</small></span>
    </li>
    <li>
      <div class="icone-gesto"><Icone gesto="tocar" tamanho={40} /></div>
      <span>Toque num lote ou ponto<small>Abre a ficha com dimensões, imagens e detalhes.</small></span>
    </li>
  </ul>
</section>

<section class="secao">
  <h3 class="subtitulo">Botões na lateral</h3>
  <ul class="lista botoes">
    <li>
      <div class="icone-btn"><Icone nome="enquadrar" tamanho={18} /></div>
      <span>Bússola e enquadrar<small>Indica o norte e retorna à vista panorâmica da maquete.</small></span>
    </li>
    <li>
      <div class="icone-btn"><Icone nome="buscar" tamanho={18} /></div>
      <span>Busca de lotes<small>Localize rapidamente qualquer lote por quadra e número.</small></span>
    </li>
    <li>
      <div class="icone-btn"><Icone nome="entorno" tamanho={18} /></div>
      <span>Entorno regional<small>Veja praias, lagoas e pontos de interesse com rotas e tempo de carro.</small></span>
    </li>
    <li>
      <div class="icone-btn"><Icone nome="mapa" tamanho={18} /></div>
      <span>Projeção do masterplan<small>Alterna a arte urbanística projetada sobre o chão.</small></span>
    </li>
    <li>
      <div class="icone-btn"><Icone nome="mais" tamanho={18} /></div>
      <span>Zoom da câmera (+ / −)<small>Aproxime ou afaste a visualização com um toque.</small></span>
    </li>
    <li>
      <div class="icone-btn"><Icone nome="lua" tamanho={18} /></div>
      <span>Modo claro / escuro<small>Alterne a iluminação solar diurna e o modo noturno.</small></span>
    </li>
    <li>
      <div class="icone-btn"><Icone nome="cinema" tamanho={18} /></div>
      <span>Modo cinema<small>Oculte os botões para navegar na maquete limpa em tela cheia.</small></span>
    </li>
    <li>
      <div class="icone-btn"><Icone nome="ajuda" tamanho={18} /></div>
      <span>Como explorar<small>Reabre este guia explicativo a qualquer instante.</small></span>
    </li>
  </ul>
</section>

<style>
  .logo { display: block; width: 120px; height: auto; margin: 4px auto 10px; }
  h2 { font-size: 22px; font-weight: 600; letter-spacing: -.01em; margin: 4px 0 16px; text-align: center; }
  .secao + .secao { margin-top: 18px; padding-top: 14px; border-top: 1px solid var(--tema-filete); }
  .subtitulo { font-size: 13px; font-weight: 700; text-transform: uppercase; letter-spacing: .06em; color: var(--tema-tinta-2); margin: 0 0 10px; }
  .lista { list-style: none; margin: 0; padding: 0; display: grid; gap: 10px; }
  li { display: grid; grid-template-columns: 36px 1fr; gap: 12px; align-items: center; font-size: 14.5px; font-weight: 600; }
  .gestos li { grid-template-columns: 40px 1fr; }
  .icone-gesto { display: grid; place-items: center; color: var(--tema-acento); }
  .icone-btn {
    width: 32px; height: 32px; display: grid; place-items: center;
    border-radius: var(--raio-1); background: var(--tema-papel-2);
    border: 1px solid var(--tema-filete); color: var(--tema-tinta);
  }
  small { display: block; font-weight: 400; font-size: 12.5px; color: var(--tema-tinta-2); line-height: 1.35; margin-top: 2px; }
</style>
