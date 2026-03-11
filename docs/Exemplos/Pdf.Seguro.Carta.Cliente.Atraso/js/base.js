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

montarCarta(data.CartaCancelamento);

ko.applyBindings(data);

function montarCarta(carta) {
  setTimeout(() => {
    montarInicioCarta();

    var limitePagina = document.querySelector('.page:last-of-type').offsetHeight - 30;
    var tbody = document.querySelector('.tbody');
    tbody.innerHTML = '';

    if (!Array.isArray(carta.Planos.Planos) && typeof carta.Planos.Planos === 'object' && carta.Planos.Planos !== null) {
      var linha = document.createElement('div');
      linha.classList.add('row');

      var celulaProduto = document.createElement('div');
      celulaProduto.classList.add('tr-plano');
      celulaProduto.innerHTML = `<span>${carta.Planos.Planos.Plano}</span>`;
      linha.appendChild(celulaProduto);

      var celulaInscricao = document.createElement('div');
      celulaInscricao.classList.add('tr-inscricao');
      celulaInscricao.innerHTML = `<span>${carta.Planos.Planos.Inscricao}</span>`;
      linha.appendChild(celulaInscricao);

      var celulaValorBeneficio = document.createElement('div');
      celulaValorBeneficio.classList.add('tr-competencia');
      celulaValorBeneficio.innerHTML = `<span>${carta.Planos.Planos.DataCancelamento}</span>`;
      linha.appendChild(celulaValorBeneficio);

      var celulaValorCompetencia = document.createElement('div');
      celulaValorCompetencia.classList.add('tr-valor');
      celulaValorCompetencia.innerHTML = `<span>${carta.Planos.Planos.ValorContribuicao}</span>`;
      linha.appendChild(celulaValorCompetencia);

      tbody.appendChild(linha);
    }
    else {
      carta.Planos.Planos.forEach(function (plano, index) {
        var linha = document.createElement('div');
        linha.classList.add('row');

        var celulaProduto = document.createElement('div');
        celulaProduto.classList.add('tr-plano');
        celulaProduto.innerHTML = `<span>${plano.Plano}</span>`;
        linha.appendChild(celulaProduto);

        var celulaInscricao = document.createElement('div');
        celulaInscricao.classList.add('tr-inscricao');
        celulaInscricao.innerHTML = `<span>${plano.Inscricao}</span>`;
        linha.appendChild(celulaInscricao);

        var celulaValorBeneficio = document.createElement('div');
        celulaValorBeneficio.classList.add('tr-competencia');
        celulaValorBeneficio.innerHTML = `<span>${plano.DataCancelamento}</span>`;
        linha.appendChild(celulaValorBeneficio);

        var celulaValorCompetencia = document.createElement('div');
        celulaValorCompetencia.classList.add('tr-valor');
        celulaValorCompetencia.innerHTML = `<span>${plano.ValorContribuicao}</span>`;
        linha.appendChild(celulaValorCompetencia);

        tbody.appendChild(linha);

        var paginaAtual = document.querySelector('.page:last-of-type');

        var posicaoLinhaAtual = linha.offsetTop + linha.offsetHeight;

        var pages = document.querySelectorAll('.page');

        var quantidadeDePaginas = pages.length;

        if (posicaoLinhaAtual > limitePagina * quantidadeDePaginas) {
          tbody.removeChild(linha);

          var newPageHtml = `
                            <div class="page">
                                <div class="content">
                                    <div class="header">
                                        <div class="logo">
                                            <img src="./img/logoMagSeguros.png" height="53.088" width="107.1936" alt="Logo Mongeral" />
                                            <img src="./img/logoMongeralAegonColorido.png" height="17.5679" width="134.688" alt="Logo Mongeral" />
                                        </div>
                                    </div>
                                        <div class="div-table">
                                          <div class="thead">
                                              <div class="th-plano"><strong>Plano</strong></div>
                                              <div class="th-inscricao"><strong>Inscrição</strong></div>
                                              <div class="th-competencia"><strong>Competência em aberto</strong></div>
                                              <div class="th-valor"><strong>Valor em aberto (R$)</strong></div>
                                          </div>
                                          <div class="tbody"></div>
                                      </div> 
                                </div>
                                <div class="footer">
                                    <div>www.mag.com.br</div>
                                </div>
                            </div>`;

          paginaAtual = document.querySelector('.page:last-of-type');
          paginaAtual.insertAdjacentHTML('afterend', newPageHtml);

          var allTbodyElements = document.querySelectorAll('.tbody');
          tbody = allTbodyElements[allTbodyElements.length - 1];

          tbody.appendChild(linha);
        }
      });
    }
    montarFinalCarta();
  }, 5);
}

function montarInicioCarta() {
  var tableCartaCancelamento = `
                                <div class="div-table">
                                    <div class="thead">
                                        <div class="th-plano"><strong>Plano</strong></div>
                                        <div class="th-inscricao"><strong>Inscrição</strong></div>
                                        <div class="th-competencia"><strong>Competência em aberto</strong></div>
                                        <div class="th-valor"><strong>Valor em aberto (R$)</strong></div>
                                    </div>
                                    <div class="tbody"></div>
                                </div> 
                               `;

  var subheaderElement = document.querySelector('.textoInicialCartaCancelamento');
  subheaderElement.insertAdjacentHTML('afterend', tableCartaCancelamento);
}

function montarFinalCarta() {
  var textoFinal = `
                    <div class="textoFinalCartaCancelamento">
                      <div class="boxes">
                          <div class="box1">
                              <div
                                  data-bind="html: 'O atraso no pagamento pode suspender automaticamente as garantias que você contratou conosco, podendo até resultar no cancelamento, dependendo do número de contribuições em aberto. Caso já tenha realizado o pagamento, pedimos por favor que desconsidere essa carta.' + '</br></br>' + 'Você pode acessar as faturas para pagamento na Área do Cliente, no site ou aplicativo. Entretanto, se precisar de ajuda sobre outras maneiras de manter em dia a proteção financeira da sua família, entre em contato conosco. Veja todos os nossos Canais de Relacionamento em www.mag.com.br'">
                              </div>
                          </div>
                      </div>
                  </div>
                  <div class="textoFinalCartaCancelamento">
                      <div class="boxes">
                          <div class="box2">
                              <div
                                  data-bind="text: 'Na MAG Seguros, valorizamos o respeito e a dignidade de todos os nossos clientes, por isso somos adeptos ao Nome Social. Reforçamos nosso compromisso em tratar cada cliente com o máximo respeito e garantir que todos se sintam acolhidos.'">
                              </div>
                          </div>
                      </div>
                  </div>
                  </div>
                  <div class="textoFinalCartaCancelamento">
                      <div class="boxes">
                          <div class="box2">
                              <div data-bind="html: 'Um abraço,'+'</br>'+'Equipe MAG Seguros'"></div>
                          </div>
                      </div>
                  </div>
                  `
  var paginaNova = `
                    <div class="page">
                      <div class="content">
                        <div class="header">
                          <div class="logo">
                            <img src="./img/logoMagSeguros.png" height="53.088" width="107.1936" alt="Logo Mongeral" />
                            <img src="./img/logoMongeralAegonColorido.png" height="17.5679" width="134.688" alt="Logo Mongeral" />
                          </div>
                        </div>
                      </div>
                    </div>
                    `
  var limitePagina = document.querySelector('.page:last-of-type').offsetHeight - 30;

  var paginaAtual = document.querySelector('.page:last-of-type');

  var lastDivTable = paginaAtual.querySelector('.div-table:last-of-type');

  lastDivTable.insertAdjacentHTML('afterend', textoFinal);

  var nextSiblings = [];
  var sibling = lastDivTable.nextElementSibling;

  while (sibling) {
    nextSiblings.push(sibling);
    sibling = sibling.nextElementSibling;
  }
  var remover = false;
  var elementosHTML = [];

  nextSiblings.forEach(function (element) {
    ko.applyBindingsToDescendants(data, element);

    var elementAlturaEmRelacaoAPagina = element.offsetHeight + element.offsetTop;

    var pages = document.querySelectorAll('.page');

    var quantidadeDePaginas = pages.length;

    if ((elementAlturaEmRelacaoAPagina > (limitePagina * quantidadeDePaginas)) || remover) {
      elementosHTML.push(element.outerHTML);
      element.remove();

      remover = true;
    }
  });

  if (remover) {
    elementosHTML.reverse();

    paginaAtual.insertAdjacentHTML('afterend', paginaNova)

    paginaAtual = document.querySelector('.page:last-of-type');

    var lastHeader = paginaAtual.querySelector('.header');

    elementosHTML.forEach(function (html) {
      lastHeader.insertAdjacentHTML('afterend', html);
    });
  }
}