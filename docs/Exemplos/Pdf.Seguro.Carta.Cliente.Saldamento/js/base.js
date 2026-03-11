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

montarCarta(data.CartaSaldamento);
ajustarTipos(data.CartaSaldamento);
ko.applyBindings(data);


function montarCarta(carta) {
    var htmlLoopSaldamento = `
                <div class="div-table">
                    <div class="thead">
                        <div class="th-produto">Produto</div>
                        <div class="th-plano">Plano</div>
                        <div class="th-inscricao">Inscrição</div>
                        <div class="th-beneficio">Valor Benefício</div>
                    </div>
                    <div class="tbody"></div>
                </div> `;

    var textoFinalParteUmSemPaginaNova = `<div class="textosaldamentoParteDois">
                <div class="boxes">
                  <div class="box1">
                    <div
                      data-bind="text: 'Saldamento é um dispositivo que mantém o direito ao recebimento proporcional do benefício no prazo contratado mediante a interrupção definitiva do pagamento das contribuições para o plano. O valor do benefício proporcional será atualizado anualmente, no mês de aniversário do Saldamento, pelo Índice de Preços ao Consumidor Amplo (IPCA) acumulado nos 12 meses que antecedem o reajuste.'">
                    </div>
                  </div>
                </div>
              </div>`
    var textoFinalParteDoisSemPaginaNova = `<div class="textosaldamentoParteDois">
                <div class="boxes">
                  <div class="box2">
                    <div
                      data-bind="text: 'Aproveitamos para informar que, na hipótese de óbito do segurado, o benefício será pago para MARIA RITA SAYURI NAKATSUKASA JACINTO DALZOCHIO. Caso deseje designar o benefício para um ou para o conjunto de beneficiários, você poderá fazê-lo a qualquer tempo, na Área do Cliente, disponível em www.mag.com.br.'">
                    </div>
                  </div>
                </div>
              </div>`
    var textoFinalParteTresSemPaginaNova = `<div class="textosaldamentoParteDois">
                <div class="boxes">
                  <div class="box2">
                    <div
                      data-bind="text: 'Caso necessite de informações adicionais, ficamos à sua disposição para quaisquer esclarecimentos.'">
                    </div>
                  </div>
                </div>
                </div>
                <div class="textosaldamentoParteDois">
                <div class="boxes">
                  <div class="box2">
                    <div
                      data-bind="text: 'Na MAG Seguros, valorizamos o respeito e a dignidade de todos os nossos clientes, por isso somos adeptos ao Nome Social. Reforçamos nosso compromisso em tratar cada cliente com o máximo respeito e garantir que todos se sintam acolhidos.'">
                    </div>
                  </div>
                  </div>
                </div>
              </div>
              <div class="textosaldamentoParteDois">
                <div class="boxes">
                  <div class="box2">
                    <div data-bind="text: 'Gerência de Relacionamento.'"></div>
                  </div>
                </div>
              </div>`

    var textoFinalParteUmComPaginaNova = `<div class="page">
            <div class="content">
              <div class="header">
                <div class="logo">
                  <img src="./img/logoMagSeguros.png" height="53.088" width="107.1936" alt="Logo Mongeral" />
                  <img src="./img/logoMongeralAegonColorido.png" height="17.5679" width="134.688" alt="Logo Mongeral" />
                </div>
              </div>
              <div class="textosaldamentoParteDois">
              <div class="boxes">
                <div class="box1">
                  <div
                    data-bind="text: 'Saldamento é um dispositivo que mantém o direito ao recebimento proporcional do benefício no prazo contratado mediante a interrupção definitiva do pagamento das contribuições para o plano. O valor do benefício proporcional será atualizado anualmente, no mês de aniversário do Saldamento, pelo Índice de Preços ao Consumidor Amplo (IPCA) acumulado nos 12 meses que antecedem o reajuste.'">
                  </div>
                </div>
              </div>
            </div></div</div>`
    var textoFinalParteDoisComPaginaNova = `<div class="page">
            <div class="content">
              <div class="header">
                <div class="logo">
                  <img src="./img/logoMagSeguros.png" height="53.088" width="107.1936" alt="Logo Mongeral" />
                  <img src="./img/logoMongeralAegonColorido.png" height="17.5679" width="134.688" alt="Logo Mongeral" />
                </div>
              </div><div class="textosaldamentoParteDois">
              <div class="boxes">
                <div class="box2">
                  <div
                    data-bind="text: 'Aproveitamos para informar que, na hipótese de óbito do segurado, o benefício será pago para MARIA RITA SAYURI NAKATSUKASA JACINTO DALZOCHIO. Caso deseje designar o benefício para um ou para o conjunto de beneficiários, você poderá fazê-lo a qualquer tempo, na Área do Cliente, disponível em www.mag.com.br.'">
                  </div>
                </div>
              </div>
            </div></div>`
    var textoFinalParteTresComPaginaNova = `<div class="page">
  <div class="content">
    <div class="header">
      <div class="logo">
        <img src="./img/logoMagSeguros.png" height="53.088" width="107.1936" alt="Logo Mongeral" />
        <img src="./img/logoMongeralAegonColorido.png" height="17.5679" width="134.688" alt="Logo Mongeral" />
        </div>
    </div>
    <div class="textosaldamentoParteDois">
      <div class="boxes">
        <div class="box2">
          <div
            data-bind="text: 'Caso necessite de informações adicionais, ficamos à sua disposição para quaisquer esclarecimentos.'">
          </div>
        </div>
      </div>
    </div>
    <div class="textosaldamentoParteDois">
      <div class="boxes">
        <div class="box2">
          <div
            data-bind="text: 'Na MAG Seguros, valorizamos o respeito e a dignidade de todos os nossos clientes, por isso somos adeptos ao Nome Social. Reforçamos nosso compromisso em tratar cada cliente com o máximo respeito e garantir que todos se sintam acolhidos.'">
          </div>
        </div>
      </div>
    </div>
    <div class="textosaldamentoParteDois">
      <div class="boxes">
        <div class="box2">
          <div data-bind="text: 'Gerência de Relacionamento.'"></div>
        </div>
      </div>
    </div>
  </div>
</div>`


    var subheaderElement = document.querySelector('.textosaldamentoParteUm');
    subheaderElement.insertAdjacentHTML('afterend', htmlLoopSaldamento);

    var tbody = document.querySelector('.tbody');
    tbody.innerHTML = '';
    var rect = 0
    var posicaoVertical = 0

    var footer = document.querySelector('.footer');
    var rectFooter = footer.getBoundingClientRect();
    var alturaFooter = rectFooter.top;

    if (!Array.isArray(carta.Planos.Plano) && typeof carta.Planos.Plano === 'object' && carta.Planos.Plano !== null) {
      var linha = document.createElement('div');
      linha.classList.add('row');

      var celulaProduto = document.createElement('div');
      celulaProduto.classList.add('tr-produto');
      celulaProduto.innerHTML = `<span>${carta.Planos.Plano.Produto}</span>`;
      linha.appendChild(celulaProduto);

      var celulaPlano = document.createElement('div');
      celulaPlano.classList.add('tr-plano');
      celulaPlano.innerHTML = `<span>${carta.Planos.Plano.NomePlano}</span>`;
      linha.appendChild(celulaPlano);

      var celulaInscricao = document.createElement('div');
      celulaInscricao.classList.add('tr-inscricao');
      celulaInscricao.innerHTML = `<span>${carta.Planos.Plano.Inscricao}</span>`;
      linha.appendChild(celulaInscricao);

      var celulaValorBeneficio = document.createElement('div');
      celulaValorBeneficio.classList.add('tr-beneficio');
      celulaValorBeneficio.innerHTML = `<span>R$ ${carta.Planos.Plano.ValorContribuicao}</span>`;
      linha.appendChild(celulaValorBeneficio);

      tbody.appendChild(linha);
  }
else
{
    carta.Planos.Plano.forEach(function (plano, index) {
        var linha = document.createElement('div');
        linha.classList.add('row');

        var celulaProduto = document.createElement('div');
        celulaProduto.classList.add('tr-produto');
        celulaProduto.innerHTML = `<span>${plano.Produto}</span>`;
        linha.appendChild(celulaProduto);

        var celulaPlano = document.createElement('div');
        celulaPlano.classList.add('tr-plano');
        celulaPlano.innerHTML = `<span>${plano.NomePlano}</span>`;
        linha.appendChild(celulaPlano);

        var celulaInscricao = document.createElement('div');
        celulaInscricao.classList.add('tr-inscricao');
        celulaInscricao.innerHTML = `<span>${plano.Inscricao}</span>`;
        linha.appendChild(celulaInscricao);

        var celulaValorBeneficio = document.createElement('div');
        celulaValorBeneficio.classList.add('tr-beneficio');
        celulaValorBeneficio.innerHTML = `<span>R$ ${plano.ValorContribuicao}</span>`;
        linha.appendChild(celulaValorBeneficio);

        tbody.appendChild(linha);

        rect = linha.getBoundingClientRect();
        posicaoVertical = rect.top + window.scrollY + linha.offsetHeight;

        if (posicaoVertical > alturaFooter - 40) {

            let alturaPage = document.querySelector('.page').offsetHeight;
            alturaFooter += alturaPage
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
                                    <div class="th-produto">Produto</div>
                                    <div class="th-plano">Plano</div>
                                    <div class="th-inscricao">Inscrição</div>
                                    <div class="th-beneficio">Valor Benefício</div>
                                </div>
                                <div class="tbody"></div>
                            </div>
                    </div>
                    <div class="footer">
                        <div>www.mag.com.br</div>
                        <div>Travessa Belas Artes n°15</div>
                        <div>CEP 20060-000 | Centro</div>
                        <div>Rio de Janeiro (RJ)</div>
                        <div>Tel: 21 3722 2200 | Fax: 21 3722 2222</div>
                    </div>
                </div>`;

            var lastPage = document.querySelector('.page:last-of-type');
            lastPage.insertAdjacentHTML('afterend', newPageHtml);

            var allTbodyElements = document.querySelectorAll('.tbody');
            tbody = allTbodyElements[allTbodyElements.length - 1];

            tbody.appendChild(linha);
        }
    });
  }
    lastPage = document.querySelector('.page:last-of-type');
    lastDivTable = lastPage.querySelector('.div-table:last-of-type');
    
    rect = lastDivTable.getBoundingClientRect();
    posicaoVertical = rect.top + lastDivTable.offsetHeight

    var lastFooter = lastPage.querySelector('.footer:last-of-type');

    var rectLastFooter = lastFooter.getBoundingClientRect();

    if (posicaoVertical + 400 < rectLastFooter.top - 40) {
        lastDivTable.insertAdjacentHTML('afterend', textoFinalParteUmSemPaginaNova + textoFinalParteDoisSemPaginaNova + textoFinalParteTresSemPaginaNova);
    }
    else
        if (posicaoVertical + 250 < rectLastFooter.top - 40) {
            lastDivTable.insertAdjacentHTML('afterend', textoFinalParteUmSemPaginaNova + textoFinalParteDoisSemPaginaNova);
            lastPage.insertAdjacentHTML('afterend', textoFinalParteTresComPaginaNova)

        }
        else
            if (posicaoVertical + 130 < rectLastFooter.top - 40) {
                lastDivTable.insertAdjacentHTML('afterend', textoFinalParteUmSemPaginaNova);

                lastPage.insertAdjacentHTML('afterend', textoFinalParteDoisComPaginaNova)

                pages = document.querySelectorAll('.page');

                lastPage = pages[pages.length - 1];

                var lastDivTextoFinal = lastPage.querySelector('.textosaldamentoParteDois:last-of-type');

                lastDivTextoFinal.insertAdjacentHTML('afterend', textoFinalParteTresSemPaginaNova)

            }
            else {
                lastPage.insertAdjacentHTML('afterend', textoFinalParteUmComPaginaNova)

                pages = document.querySelectorAll('.page');

                lastPage = pages[pages.length - 1];

                var lastDivTextoFinal = lastPage.querySelector('.textosaldamentoParteDois:last-of-type');

                lastDivTextoFinal.insertAdjacentHTML('afterend', textoFinalParteDoisSemPaginaNova + textoFinalParteTresSemPaginaNova)

            }
        }


function ajustarTipos(cartaSaldamento) {
    cartaSaldamento.Planos = converterParaArray(cartaSaldamento.Planos.Plano);
}

function converterParaArray(objeto) {
    if (objeto == null)
        return [];

    if (objeto instanceof Array)
        return objeto;

    return [objeto];
}