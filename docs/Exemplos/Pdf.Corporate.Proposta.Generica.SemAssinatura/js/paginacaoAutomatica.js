// ================== Paginação Automática (A4) ==================

// Cria uma nova página (section.sheet) baseada na primeira, mas com .content/.secao-proposta vazio
function criarNovaSheetVazia() {
  const primeiraSheet = document.querySelector('.sheet');
  if (!primeiraSheet) return null;

  const nova = primeiraSheet.cloneNode(true);

  const content = nova.querySelector('.content, .secao-proposta');
  if (content) {
    content.innerHTML = '';
  }

  nova.innerHTML = nova.innerHTML.replace('secao-proposta', 'content');

  return nova;
}

// Altura "extra" ocupada pelo conteúdo em relação à base vazia
function alturaDeltaConteudo(ctx) {
  if (!ctx.currentContent) return 0;
  const atual = ctx.currentContent.scrollHeight;
  return Math.max(0, atual - (ctx.baseAltura || 0));
}

// Append genérico com checagem de overflow (para elementos que NÃO são tabela)
function appendElementoComPaginacao(el, ctx) {
  if (!ctx.currentContent) return;

  ctx.currentContent.appendChild(el);

  // força reflow
  ctx.currentContent.offsetHeight;

  if (alturaDeltaConteudo(ctx) > ctx.maxDelta) {
    // Estourou: remove da página atual
    ctx.currentContent.removeChild(el);

    // Cria nova página
    const novaSheet = criarNovaSheetVazia();
    if (!novaSheet) return;

    ctx.currentSheet.insertAdjacentElement('afterend', novaSheet);
    ctx.currentSheet = novaSheet;
    ctx.currentContent = novaSheet.querySelector('.content, .secao-proposta');

    // Recomputa baseAltura para a nova página vazia
    ctx.baseAltura = ctx.currentContent.scrollHeight;

    ctx.currentContent.appendChild(el);

    if (alturaDeltaConteudo(ctx) > ctx.maxDelta) {
      console.warn('Elemento maior que uma página, deixado inteiro mesmo assim:', el);
    }
  }
}

// Paginar uma tabela, quebrando por <tr> e replicando o <thead> em cada página
function paginarTabela(tableNode, ctx) {
  if (!ctx.currentContent) return;

  const originalTable = tableNode;
  const originalThead = originalTable.tHead
    ? originalTable.tHead.cloneNode(true)
    : null;

  const originalTbody = originalTable.tBodies[0];
  if (!originalTbody) {
    appendElementoComPaginacao(originalTable, ctx);
    return;
  }

  const todasLinhas = Array.from(originalTbody.rows);

  let restante = todasLinhas.slice();
  let primeiraTabela = true;

  while (restante.length > 0) {
    let tabelaPagina;
    if (primeiraTabela) {
      tabelaPagina = originalTable.cloneNode(false);
      primeiraTabela = false;
    } else {
      tabelaPagina = originalTable.cloneNode(false);
    }

    if (originalThead) {
      tabelaPagina.appendChild(originalThead.cloneNode(true));
    }

    const tbodyPagina = document.createElement('tbody');
    tabelaPagina.appendChild(tbodyPagina);

    ctx.currentContent.appendChild(tabelaPagina);

    // força reflow da tabela vazia (com thead) antes de começar a adicionar linhas
    ctx.currentContent.offsetHeight;

    while (restante.length > 0) {
      const linha = restante[0];

      tbodyPagina.appendChild(linha);

      if (alturaDeltaConteudo(ctx) > ctx.maxDelta) {
        tbodyPagina.removeChild(linha);

        // Caso extremo: nem a linha sozinha cabe numa página nova
        if (tbodyPagina.rows.length === 0) {
          ctx.currentContent.removeChild(tabelaPagina);

          const novaSheetEspecial = criarNovaSheetVazia();
          if (!novaSheetEspecial) return;

          ctx.currentSheet.insertAdjacentElement('afterend', novaSheetEspecial);
          ctx.currentSheet = novaSheetEspecial;
          ctx.currentContent = novaSheetEspecial.querySelector('.content, .secao-proposta');

          ctx.baseAltura = ctx.currentContent.scrollHeight;

          const tabelaGigante = originalTable.cloneNode(false);
          if (originalThead) {
            tabelaGigante.appendChild(originalThead.cloneNode(true));
          }
          const tbodyGigante = document.createElement('tbody');
          tabelaGigante.appendChild(tbodyGigante);
          ctx.currentContent.appendChild(tabelaGigante);

          tbodyGigante.appendChild(linha);
          console.warn('Linha maior que uma página, deixada inteira:', linha);

          restante.shift();
          break;
        }

        const novaSheet = criarNovaSheetVazia();
        if (!novaSheet) return;

        ctx.currentSheet.insertAdjacentElement('afterend', novaSheet);
        ctx.currentSheet = novaSheet;
        ctx.currentContent = novaSheet.querySelector('.content, .secao-proposta');

        ctx.baseAltura = ctx.currentContent.scrollHeight;

        break;
      } else {
        restante.shift();
      }
    }
  }
}

// Calcula o quanto o conteúdo pode crescer (delta) antes de bater no footer
function calcularMaxDelta(sheetBase, headerBase, footerBase, contentBase) {
  const rootStyles = getComputedStyle(document.documentElement);
  let paginaAltura = parseFloat(rootStyles.getPropertyValue('--pg-h'));

  if (!isFinite(paginaAltura) || paginaAltura <= 0) {
    const sheetStyles = getComputedStyle(sheetBase);
    paginaAltura =
      parseFloat(sheetStyles.height) ||
      sheetBase.getBoundingClientRect().height ||
      1123;
  }

  const alturaHeader = headerBase.offsetHeight ||
    parseFloat(getComputedStyle(headerBase).height) || 0;

  const alturaFooter = footerBase.offsetHeight ||
    parseFloat(getComputedStyle(footerBase).height) || 0;

  const maxScrollPermitido = paginaAltura - alturaHeader - alturaFooter;

  // altura "base" do conteúdo vazio (só padding etc.)
  const baseAltura = contentBase.scrollHeight;

  let maxDelta = maxScrollPermitido - baseAltura + 80;

  if (!isFinite(maxDelta) || maxDelta <= 0) {
    console.log('maxDelta inválido, desativando limite de página.', {
      paginaAltura,
      alturaHeader,
      alturaFooter,
      baseAltura,
      maxScrollPermitido
    });
    maxDelta = Number.POSITIVE_INFINITY;
  }

  return { baseAltura, maxDelta };
}

// Paginação do documento: repagina TODAS as .sheet existentes
function paginarDocumento() {
  const todasSheets = Array.from(document.querySelectorAll('.sheet'));
  if (todasSheets.length === 0) return;

  const sheetBase = todasSheets[0];
  const headerBase = sheetBase.querySelector('.header');
  const footerBase = sheetBase.querySelector('.footer');
  const contentBase = sheetBase.querySelector('.content, .secao-proposta');

  if (!headerBase || !footerBase || !contentBase) return;

  // Junta o conteúdo de TODAS as sheets, na ordem em que aparecem
  const elementos = [];
  todasSheets.forEach(sheet => {
    const c = sheet.querySelector('.content, .secao-proposta');
    if (!c) return;
    elementos.push(...Array.from(c.children));
  });

  // Remove todas as sheets, exceto a primeira
  for (let i = 1; i < todasSheets.length; i++) {
    todasSheets[i].remove();
  }

  // Limpa o conteúdo da base
  contentBase.innerHTML = '';

  // Agora que está vazia, medimos a altura base e o delta máximo
  const { baseAltura, maxDelta } = calcularMaxDelta(sheetBase, headerBase, footerBase, contentBase);

  const ctx = {
    currentSheet: sheetBase,
    currentContent: contentBase,
    baseAltura,
    maxDelta
  };

  elementos.forEach(el => {

    // --- MARCADOR DE QUEBRA DE PÁGINA MANUAL ---
    // Se for uma div com id="quebra-linha", força nova página em branco
    if (el.id == 'quebra-linha') {
      // Cria nova sheet vazia
      const novaSheet = criarNovaSheetVazia();
      if (!novaSheet) return;

      // Insere logo após a sheet atual
      ctx.currentSheet.insertAdjacentElement('afterend', novaSheet);

      // Atualiza contexto para apontar para a nova página
      ctx.currentSheet = novaSheet;
      ctx.currentContent = novaSheet.querySelector('.content, .secao-proposta');

      // Recalcula baseAltura para o conteúdo vazio da nova página
      ctx.baseAltura = ctx.currentContent.scrollHeight;

      // Não adiciona o elemento "quebra-linha" em nenhuma página
      return;
    }

    // --- LÓGICA NORMAL ---
    if (el.tagName === 'TABLE') {
      paginarTabela(el, ctx);
    } else {
      appendElementoComPaginacao(el, ctx);
    }
  });
}