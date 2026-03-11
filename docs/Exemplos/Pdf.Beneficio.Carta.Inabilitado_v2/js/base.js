ko.bindingHandlers.number = {
  update: function (element, valueAccessor, allBindingsAccessor) {
    let value = ko.unwrap(valueAccessor());

    if (typeof value == 'number' && isFinite(value)) {
      let precision = ko.utils.unwrapObservable(allBindingsAccessor().precision);

      if (precision == undefined) {
        precision = ko.bindingHandlers.number.defaultPrecision;
      }

      value = value.toFixed(precision).replace('.', ',').replace(/(\d)(?=(\d{3})+(?!\d))/g, "$1.");

      ko.bindingHandlers.text.update(element, function () { return value; });
    } else {
      ko.bindingHandlers.text.update(element, function () { return "—" });
    }
  },
  defaultPrecision: 2
};

let alturaMaximaGlobal = 1060;

function mostrarElementoEReaplicarBind(seletorItem) {
  const seletor = seletorItem.startsWith('.') ? seletorItem : '.' + seletorItem;
  const el = document.querySelector(seletor);
  if (!el) return;

  const displayOriginal = el.getAttribute('data-display-original') || 'block';
  el.style.display = displayOriginal;

  // Força o reflow para garantir altura atualizada
  el.offsetHeight;
}

function mostrarElementoEReaplicarBindEReposicionar(seletorItem) {
  const seletor = seletorItem.startsWith('.') ? seletorItem : '.' + seletorItem;
  const el = document.querySelector(seletor);
  if (!el) return;

  const displayOriginal = el.getAttribute('data-display-original') || 'block';
  el.style.display = displayOriginal;

  // Força o reflow para garantir altura atualizada
  el.offsetHeight;
  reposicionarElementoFixo(seletor);
}

function formatarParaArray(obj, key) {
  if (obj && obj[key] && !Array.isArray(obj[key])) {
    obj[key] = [obj[key]];
  }

}

function inicializarCamposParaBindings() {
  const carta = data.CartaInabilitado = data.CartaInabilitado || {};

  carta.Data ??= '';
  carta.Logradouro ??= '';
  carta.Numero ??= '';
  carta.Complemento ??= '';
  carta.Bairro ??= '';
  carta.Cidade ??= '';
  carta.Cep ??= '';
  carta.NomeSolicitante ??= '';
  carta.CPFSolicitante ??= '';
  carta.EmailSolicitante ??= '';
  carta.Processo ??= '';
  carta.NomeSegurado ??= '';
  carta.CPFSegurado ??= '';
  carta.CPFSolicitante ??= '';
  carta.MotivoRecusa ??= '';
  carta.CelularSolicitante ??= '';
  carta.LinkDocumento ??= '';
}

function formatarDadosBeneficiario(carta = data.CartaInabilitado) {
  const trim = (v) => (typeof v === 'string' ? v.trim() : '');

  const campoBairro = trim(carta.Bairro);
  const campoCidade = trim(carta.Cidade);
  const campoComplemento = trim(carta.Complemento);
  const campoEstado = trim(carta.Estado);
  const campoLogradouro = trim(carta.Logradouro);
  const campoNumero = trim(carta.Numero);
  const campoCep = trim(carta.Cep);

  let Cep = '';
  if (campoCidade !== '' && campoCep !== '') {
    Cep = ', ' + campoCep;
  } else if (campoCep !== '') {
    Cep = campoCep;
  }

  let Logradouro = '';
  if (campoLogradouro !== '' && campoNumero !== '') {
    Logradouro = campoLogradouro + ', ';
  } else if (campoLogradouro !== '') {
    Logradouro = campoLogradouro;
  }

  let Numero = '';
  if (campoLogradouro !== '' && campoNumero !== '' && campoComplemento !== '') {
    Numero = campoNumero + ', ' + campoComplemento;
  } else if (campoLogradouro !== '' && campoNumero !== '') {
    Numero = campoNumero;
  }

  let Bairro = '';
  if (campoBairro === '') {
    Bairro = '';
  } else if (
    !campoBairro.toLowerCase().includes('bairro')
  ) {
    Bairro = ', Bairro ' + campoBairro;
  } else {
    Bairro = ', ' + campoBairro;
  }

  return {
    Cep,
    Logradouro,
    Numero,
    Bairro,
    Cidade: campoCidade,
    Estado: campoEstado // opcional: caso precise montar endereço completo
  };
}

function gerarDataFormatada(dataString = data.CartaInabilitado?.Data) {
  if (!dataString || typeof dataString !== 'string') return '';

  const [dia, mes, ano] = dataString.split(' ')[0].split('/');

  const nomesMeses = {
    '01': 'Janeiro',
    '02': 'Fevereiro',
    '03': 'Março',
    '04': 'Abril',
    '05': 'Maio',
    '06': 'Junho',
    '07': 'Julho',
    '08': 'Agosto',
    '09': 'Setembro',
    '10': 'Outubro',
    '11': 'Novembro',
    '12': 'Dezembro'
  };

  const mesNome = nomesMeses[mes] || '';
  return `${dia} de ${mesNome} de ${ano}`;
}

function temValorUtil(obj) {
  return Object.entries(obj || {}).some(([_, valor]) => {
    if (Array.isArray(valor)) return valor.length > 0;
    if (typeof valor === 'object' && valor !== null) return temValorUtil(valor);
    return String(valor).trim() !== '';
  });
}

function mostrarElementosComValorEReaplicarBind(seletorPai) {
  const container = document.querySelector(seletorPai);
  if (!container) return;

  // Oculta todos os blocos no início
  const todosBlocos = container.querySelectorAll('[data-display-original], div');
  todosBlocos.forEach(bloco => {
    bloco.style.display = 'none';
  });

  // Encontra todos os spans com data-bind de texto
  const spansComBind = container.querySelectorAll('span[data-bind^="text:"]');

  spansComBind.forEach(span => {
    const valor = span.textContent?.trim();

    if (valor) {
      let pai = span.parentElement;
      // Sobe até encontrar divs e exibe todas até o container principal
      while (pai && pai !== container) {
        if (pai.tagName === 'DIV') {
          const displayOriginal = pai.getAttribute('data-display-original') || 'block';
          pai.style.display = displayOriginal;
        }
        pai = pai.parentElement;
      }
    }

  });

  // Se ao menos uma div interna foi exibida, mostra o container principal
  const existeAlgumVisivel = Array.from(container.querySelectorAll('div')).some(div => div.style.display !== 'none');
  container.style.display = existeAlgumVisivel ? 'flex' : 'none';
}

function existeRepeticaoRenderizada(seletorItem) {
  const seletor = seletorItem.startsWith('.') ? seletorItem : '.' + seletorItem;

  const itens = document.querySelectorAll(seletor);
  return itens.length > 0;
}

iniciarRenderizacaoSequencialSincrono();

function iniciarRenderizacaoSequencialSincrono() {
  inicializarCamposParaBindings()
  const dados = formatarDadosBeneficiario();
  data.CartaInabilitado.Endereco = dados;
  data.CartaInabilitado.DataFormatada = gerarDataFormatada();

  ko.applyBindings(data);
}

function quebrarTabelaEntrePaginas(seletorClasse, seletorHeader, seletorRow, seletorFooter = null, margemEspaco = '0.2in', margemQuebra = '1.1in') {
  const tabelaOriginal = document.querySelector('.' + seletorClasse);
  if (!tabelaOriginal) return;

  const tituloEl = tabelaOriginal.querySelector('.campo-tabela-titulo');
  const headerEl = seletorHeader ? tabelaOriginal.querySelector('.' + seletorHeader) : null;

  const usarHeader = !!(headerEl?.childElementCount);
  const titulo = tituloEl?.cloneNode(true);
  const header = usarHeader ? headerEl.cloneNode(true) : titulo;

  const linhas = Array.from(tabelaOriginal.querySelectorAll('.' + seletorRow));
  const linhasRestantes = [...linhas];

  // Captura e remove o footer
  let footerClonado = null;
  if (seletorFooter) {
    const footerOriginal = tabelaOriginal.querySelector('.' + seletorFooter);
    if (footerOriginal) {
      footerClonado = footerOriginal.cloneNode(true);
      footerOriginal.remove();
    }
  }

  tabelaOriginal.remove();

  let paginas = Array.from(document.querySelectorAll('.page'));
  let ultimaPagina = paginas[paginas.length - 1];

  let contentAtual = ultimaPagina ? ultimaPagina.querySelector('.content') : criarNovaPagina();
  let blocoAtual = null;

  while (linhasRestantes.length > 0) {
    const linha = linhasRestantes[0];
    const temBlocosRenderizados = contentAtual.children.length > 0;
    const margem = temBlocosRenderizados ? margemEspaco : margemQuebra;

    // Testa bloco hipotético com header/título + linha
    const blocoTeste = criarBlocoTabela(margem, titulo, usarHeader ? header : null, seletorClasse);
    blocoTeste.appendChild(linha.cloneNode(true));
    const alturaEstimativa = alturaProspectiva(contentAtual, blocoTeste);

    if (alturaEstimativa > alturaMaximaGlobal) {
      contentAtual = criarNovaPagina();
      continue;
    } else {

    }

    // Cabe: cria bloco real e insere linha
    blocoAtual = criarBlocoTabela(margem, titulo, usarHeader ? header : null, seletorClasse);
    blocoAtual.appendChild(linhasRestantes.shift());
    contentAtual.appendChild(blocoAtual);

    // Adiciona o máximo possível de linhas
    while (linhasRestantes.length > 0) {
      const proxLinha = linhasRestantes[0];
      blocoAtual.appendChild(proxLinha);
      proxLinha.offsetHeight;

      const alturaAtual = blocoAtual.getBoundingClientRect().bottom - contentAtual.getBoundingClientRect().top;

      if (alturaAtual > alturaMaximaGlobal) {
        blocoAtual.removeChild(proxLinha);
        break;
      }

      linhasRestantes.shift();
    }
  }

  // Adiciona o footer no final, se existir
  if (footerClonado && blocoAtual) {
    const alturaComFooter = alturaProspectiva(contentAtual, footerClonado);
    const alturaRestante = alturaMaximaGlobal + contentAtual.getBoundingClientRect().top;

    if (alturaComFooter > alturaRestante) {
      contentAtual = criarNovaPagina();
      const blocoFooter = criarBlocoTabela('1.1in', null, null, seletorClasse);
      blocoFooter.appendChild(footerClonado);
      contentAtual.appendChild(blocoFooter);
    } else {
      blocoAtual.appendChild(footerClonado);
    }
  }
}

function criarBlocoTabela(marginValue, titulo = null, header = null, className) {
  const bloco = document.createElement('div');
  bloco.className = className;
  bloco.style.marginTop = marginValue;

  if (titulo && header && titulo === header) {
    bloco.appendChild(titulo.cloneNode(true));
  } else {
    if (titulo) bloco.appendChild(titulo.cloneNode(true));
    if (header) bloco.appendChild(header.cloneNode(true));
  }

  return bloco;
}

function criarNovaPagina() {
  const page = document.createElement('div');
  page.className = 'page';

  const content = document.createElement('div');
  content.className = 'content';

  page.appendChild(content);
  document.body.appendChild(page);

  // Retornamos o .content
  return content;
}

function criarNovaPagina(temFundo = true) {
  if (temFundo) {
    // Cria o container da página
    const page = document.createElement('div');
    page.className = 'page';

    // Cria o container da imagem de fundo e insere a imagem
    const backgroundContainer = document.createElement('div');
    backgroundContainer.className = 'background-image-container';
    const backgroundImg = document.createElement('img');
    backgroundImg.src = './img/papel_Timbrado_novo_MGA_MAG06.png';
    backgroundImg.alt = 'Fundo';
    backgroundContainer.appendChild(backgroundImg);
    // Insere o container de background na página antes do conteúdo
    page.appendChild(backgroundContainer);

    // Cria o container de conteúdo
    const content = document.createElement('div');
    content.className = 'content';
    page.appendChild(content);

    // Adiciona a página ao body
    document.body.appendChild(page);

    // Retorna o container de conteúdo (para seguir a lógica atual)
    return content;
  }
  else {
    const page = document.createElement('div');
    page.className = 'page';

    const content = document.createElement('div');
    content.className = 'content';

    page.appendChild(content);
    document.body.appendChild(page);

    // Retornamos o .content
    return content;
  }
}


function alturaProspectiva(content, bloco) {
  // Captura o scroll original, se houver (em alguns cenários)
  const scrollY = window.scrollY || window.pageYOffset;

  // Salva a visibilidade original do bloco (caso reutilize clone)
  const originalDisplay = bloco.style.display;
  bloco.style.display = 'block'; // força display para medir corretamente

  // Adiciona bloco temporariamente
  content.appendChild(bloco);

  // Força reflow para garantir cálculo preciso
  bloco.offsetHeight;

  // Mede a posição real do final do bloco em relação ao topo do content
  const contentRect = content.getBoundingClientRect();
  const blocoRect = bloco.getBoundingClientRect();

  // Remove o bloco do DOM
  content.removeChild(bloco);

  // Restaura display original
  bloco.style.display = originalDisplay;

  // Calcula altura real que o bloco ocuparia dentro do content
  return blocoRect.bottom - contentRect.top;
}

function reposicionarElementoFixo(seletor, margemEspacoPadrao = '0.2in', margemQuebraPadrao = '1.1in') {
  const elemento = document.querySelector(seletor);
  if (!elemento) return;

  // Pega margens do atributo ou usa o padrão
  const margemEspaco = elemento.getAttribute('data-margem-espaco') || margemEspacoPadrao;
  const margemQuebra = elemento.getAttribute('data-margem-quebra') || margemQuebraPadrao;

  // Remove do DOM para reposicionar
  elemento.parentNode.removeChild(elemento);

  // Pega a última página (ou cria uma nova)
  let paginas = document.querySelectorAll('.page');
  let contentAtual;

  if (paginas.length === 0) {
    contentAtual = criarNovaPagina();
  } else {
    const ultimaPagina = paginas[paginas.length - 1];
    contentAtual = ultimaPagina.querySelector('.content');
  }

  const alturaCalculada = alturaProspectiva(contentAtual, elemento);

  if (alturaCalculada > alturaMaximaGlobal) {
    contentAtual = criarNovaPagina();
    elemento.style.marginTop = margemQuebra;
  } else {
    elemento.style.marginTop = margemEspaco;
  }

  contentAtual.appendChild(elemento);
}

function RenderizarEstruturaFixa(seletorElemento) {
  const seletorItem = seletorElemento.startsWith('.') ? seletorElemento : '.' + seletorElemento;
  const elemento = document.querySelector(seletorItem);
  if (!elemento) return;

  // Restaura o display original
  const displayOriginal = elemento.getAttribute('data-display-original') || 'block';
  elemento.style.display = displayOriginal;

  // Remove do DOM para reposicionar
  if (elemento.parentNode) {
    elemento.parentNode.removeChild(elemento);
  }

  // Seleciona os elementos diretos filhos do body (nível raiz)
  const divsVisiveisBody = Array.from(document.body.children)
    .filter(el => el.tagName === 'DIV' && getComputedStyle(el).display !== 'none');

  const ultima = divsVisiveisBody[divsVisiveisBody.length - 1];

  if (ultima && ultima.parentNode === document.body) {
    // Insere como próximo irmão da última div visível no body
    document.body.insertBefore(elemento, ultima.nextSibling);
  } else {
    // Fallback
    document.body.appendChild(elemento);
  }

  // Força reflow
  elemento.offsetHeight;
}