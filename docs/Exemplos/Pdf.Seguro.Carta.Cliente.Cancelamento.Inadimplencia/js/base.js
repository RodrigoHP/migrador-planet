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
console.log(data.CartaCancelamento)
montarCarta(data.CartaCancelamento);
ajustarTipos(data.CartaCancelamento);
ko.applyBindings(data);


function montarCarta(carta) {
  var tableCartaCancelamento = `
                          <div class="div-table">
                              <div class="thead">
                                  <div class="th-produto"><strong>Plano</strong></div>
                                  <div class="th-plano"><strong>Matricula</strong></div>
                                  <div class="th-inscricao"><strong>Inscrição</strong></div>
                                  <div class="th-beneficio"><strong>Data do cancelamento</strong></div>
                                  <div class="th-competencia"><strong>Competência</strong></div>
                              </div>
                              <div class="tbody"></div>
                          </div> 
                          `;

  var textoFinalSemPaginaNova = `
                                <div class="textoFinalCartaCancelamento">
                                  <div class="boxes">
                                      <div class="box1">
                                          <div
                                              data-bind="html: 'Obrigado por nos permitir proteger o seu futuro, enquanto cliente MAG Seguros.' + '</br></br>' + 'Caso você precise de outras informações ou tenha alguma dúvida, entre em contato conosco.' + '</br></br>' + 'Todos os nossos Canais de Relacionamento estão disponíveis em nosso site.'+'</br></br>'+'<strong>Para contratar novamente suas coberturas, entre em contato com o seu corretor ou acesse:</strong><span> www.mag.com.br.</span>'">
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


  var textoFinalComPaginaNova = `
                                <div class="page">
                                  <div class="content">
                                    <div class="header">
                                      <div class="logo">
                                        <img src="./img/logoMagSeguros.png" height="53.088" width="107.1936" alt="Logo Mongeral" />
                                        <img src="./img/logoMongeralAegonColorido.png" height="17.5679" width="134.688" alt="Logo Mongeral" />
                                      </div>
                                    </div>
                                    <div class="textoFinalCartaCancelamento">
                                      <div class="boxes">
                                        <div class="box1">
                                          <div
                                            data-bind="html: 'Obrigado por nos permitir proteger o seu futuro, enquanto cliente MAG Seguros.' + '</br></br>' + 'Caso você precise de outras informações ou tenha alguma dúvida, entre em contato conosco.' + '</br></br>' + 'Todos os nossos Canais de Relacionamento estão disponíveis em nosso site.'+'</br></br>'+'<strong>Para contratar novamente suas coberturas, entre em contato com o seu corretor ou acesse:</strong><span> www.mag.com.br.</span>'">
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
                                    <div class="textoFinalCartaCancelamento">
                                      <div class="boxes">
                                        <div class="box2">
                                          <div data-bind="html: 'Um abraço,'+'</br>'+'Equipe MAG Seguros'"></div>
                                        </div>
                                      </div>
                                    </div>
                                  </div>
                                </div>
                                `


  var subheaderElement = document.querySelector('.textoInicialCartaCancelamento');
  subheaderElement.insertAdjacentHTML('afterend', tableCartaCancelamento);

  var tbody = document.querySelector('.tbody');
  tbody.innerHTML = '';

  var footer = document.querySelector('.footer');
  var rectFooter = footer.getBoundingClientRect();
  var alturaFooter = rectFooter.top;

  if (!Array.isArray(carta.Planos.Planos) && typeof carta.Planos.Planos === 'object' && carta.Planos.Planos !== null) {
    var linha = document.createElement('div');
    linha.classList.add('row');

    var celulaProduto = document.createElement('div');
    celulaProduto.classList.add('tr-produto');
    celulaProduto.innerHTML = `<span>${carta.Planos.Planos.Plano}</span>`;
    linha.appendChild(celulaProduto);

    var celulaPlano = document.createElement('div');
    celulaPlano.classList.add('tr-plano');
    celulaPlano.innerHTML = `<span>${carta.Planos.Planos.Matricula}</span>`;
    linha.appendChild(celulaPlano);

    var celulaInscricao = document.createElement('div');
    celulaInscricao.classList.add('tr-inscricao');
    celulaInscricao.innerHTML = `<span>${carta.Planos.Planos.Inscricao}</span>`;
    linha.appendChild(celulaInscricao);

    var celulaValorBeneficio = document.createElement('div');
    celulaValorBeneficio.classList.add('tr-beneficio');
    celulaValorBeneficio.innerHTML = `<span>${carta.Planos.Planos.DataCancelamento}</span>`;
    linha.appendChild(celulaValorBeneficio);

    var celulaValorCompetencia = document.createElement('div');
    celulaValorCompetencia.classList.add('tr-competencia');
    celulaValorCompetencia.innerHTML = `<span>${carta.Planos.Planos.CompetenciaCancelamento}</span>`;
    linha.appendChild(celulaValorCompetencia);

    tbody.appendChild(linha);
  }
  else {
    carta.Planos.Planos.forEach(function (plano, index) {
      var linha = document.createElement('div');
      linha.classList.add('row');

      var celulaProduto = document.createElement('div');
      celulaProduto.classList.add('tr-produto');
      celulaProduto.innerHTML = `<span>${plano.Plano}</span>`;
      linha.appendChild(celulaProduto);

      var celulaPlano = document.createElement('div');
      celulaPlano.classList.add('tr-plano');
      celulaPlano.innerHTML = `<span>${plano.Matricula}</span>`;
      linha.appendChild(celulaPlano);

      var celulaInscricao = document.createElement('div');
      celulaInscricao.classList.add('tr-inscricao');
      celulaInscricao.innerHTML = `<span>${plano.Inscricao}</span>`;
      linha.appendChild(celulaInscricao);

      var celulaValorBeneficio = document.createElement('div');
      celulaValorBeneficio.classList.add('tr-beneficio');
      celulaValorBeneficio.innerHTML = `<span>${plano.DataCancelamento}</span>`;
      linha.appendChild(celulaValorBeneficio);

      var celulaValorCompetencia = document.createElement('div');
      celulaValorCompetencia.classList.add('tr-competencia');
      celulaValorCompetencia.innerHTML = `<span>${plano.CompetenciaCancelamento}</span>`;
      linha.appendChild(celulaValorCompetencia);

      tbody.appendChild(linha);

      var paginaAtual = document.querySelector('.page:last-of-type');

      rectLinha = linha.getBoundingClientRect();

      var rectPagina = paginaAtual.getBoundingClientRect();

      var posicaoVerticalRelativa = rectLinha.top - rectPagina.top + linha.offsetHeight;

      if (posicaoVerticalRelativa > alturaFooter - 40) {
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
                                  <div class="th-produto"><strong>Plano</strong></div>
                                  <div class="th-plano"><strong>Matricula</strong></div>
                                  <div class="th-inscricao"><strong>Inscrição</strong></div>
                                  <div class="th-beneficio"><strong>Data do cancelamento</strong></div>
                                  <div class="th-competencia"><strong>Competência</strong></div>
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

  paginaAtual = document.querySelector('.page:last-of-type');

  var rectPagina = paginaAtual.getBoundingClientRect();

  lastDivTable = paginaAtual.querySelector('.div-table:last-of-type');


  linhaAtual = lastDivTable.querySelector('.row:last-of-type');

  rectLinha = linhaAtual.getBoundingClientRect();

  var lastFooter = paginaAtual.querySelector('.footer:last-of-type');

  var rectLastFooter = lastFooter.getBoundingClientRect();

  setTimeout(() => {
    const rectLinha = linhaAtual.getBoundingClientRect();

    posicaoVerticalRelativa = rectLinha.top - rectPagina.top + linhaAtual.offsetHeight
   
    if (posicaoVerticalRelativa + 290 < rectLastFooter.top) {
      lastDivTable.insertAdjacentHTML('afterend', textoFinalSemPaginaNova);

      var nextSiblings = [];
      var sibling = lastDivTable.nextElementSibling;

      while (sibling) {
        nextSiblings.push(sibling);
        sibling = sibling.nextElementSibling;
      }

      nextSiblings.forEach(function (element) {
        ko.applyBindingsToDescendants(data, element);
      });
    } else {
      paginaAtual.insertAdjacentHTML('afterend', textoFinalComPaginaNova)

      pages = document.querySelectorAll('.page');

      paginaAtual = pages[pages.length - 1];

      var firstDivTextoFinal = paginaAtual.querySelector('.textoFinalCartaCancelamento');

      var nextSiblings = [];
      var sibling = firstDivTextoFinal

      while (sibling) {
        nextSiblings.push(sibling);
        sibling = sibling.nextElementSibling;
      }

      nextSiblings.forEach(function (element) {
        ko.applyBindingsToDescendants(data, element);
      });
    }


  }, 0);
}

function ajustarTipos(cartaCancelamento) {
  cartaCancelamento.Planos.Planos = converterParaArray(cartaCancelamento.Planos.Planos.Plano);
}

function converterParaArray(objeto) {
  if (objeto == null)
    return [];

  if (objeto instanceof Array)
    return objeto;

  return [objeto];
}