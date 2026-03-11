ko.bindingHandlers.number = {
    update: function (element, valueAccessor, allBindingsAccessor) {
        var value = ko.unwrap(valueAccessor());

        if (typeof value == 'number' && isFinite(value)) {
            var precision = ko.utils.unwrapObservable(allBindingsAccessor().precision) || ko.bindingHandlers.number.defaultPrecision;

            value = value.toFixed(precision).replace('.', ',').replace(/(\d)(?=(\d{3})+(?!\d))/g, "$1.");

            ko.bindingHandlers.text.update(element, function () { return value; });
        } else {
            ko.bindingHandlers.text.update(element, function () { return "—" });
        }
    },
    defaultPrecision: 2
};

ajustarTipos();
prepararPaginasDadosDoPlano();
prepararPaginasDadosDoProduto();
prepararTabelaResgateDeProdutos();

if (usePartnershipCustomization()) {
    setPartnershipColor();
    setPartnershipBanner();
    setPartnershipPositiveLogo();
    setPartnershipNegativeLogo();
}

ko.applyBindings(data);

function ajustarTipos() {
    data.Simulacao.RendaMensal = +data.Simulacao.RendaMensal;
    data.Simulacao.TotalContribuicao = +data.Simulacao.TotalContribuicao;
    data.Simulacao.DataSimulacao = getDataPorExtenso(data.Simulacao.DataSimulacao);
    data.Simulacao.Produtos = converterParaArray(data.Simulacao.Produtos);
    data.Simulacao.IdadeProponente = +data.Simulacao.IdadeProponente;

    // Propriedade customizada; que não existem no JSON de dados.
    data.Simulacao.PeriodicidadeDecricao =  getPeriodicidadeDescricao(data.Simulacao.Periodicidade);

    for (var i = 0; i < data.Simulacao.Produtos.length; i++) {
        produto = data.Simulacao.Produtos[i];

        produto.Id = +produto.Id;
        produto.Coberturas = converterParaArray(produto.Coberturas);
        produto.TabelaResgate = converterParaArray(produto.TabelaResgate);
        produto.PossuiTabelaResgate = (produto.PossuiTabelaResgate == 'true');

        for (var j = 0; j < produto.Coberturas.length; j++) {
            cobertura = data.Simulacao.Produtos[i].Coberturas[j];

            cobertura.Beneficio = +cobertura.Beneficio;
            cobertura.Contribuicao = +cobertura.Contribuicao;
        }

        for (var j = 0; j < produto.TabelaResgate.length; j++) {
            resgate = produto.TabelaResgate[j];

            resgate.Beneficio = +resgate.Beneficio;
            resgate.ValorResgate = +resgate.ValorResgate;
            resgate.Valor = +resgate.Valor;
            resgate.PrazoProlongadoMeses = converterMesesEmAnosEMeses(resgate.PrazoProlongadoMeses);
        }

        if(produto.PossuiTabelaResgate) {
            produto.NomeTratado = produto.Nome.toLowerCase();
        }
    }
}

function converterMesesEmAnosEMeses(mesesString) {
    if (!mesesString || mesesString === '0' || isNaN(mesesString)) {
        return '-';
    }

    var meses = parseInt(mesesString, 10);
    
    var anos = Math.floor(meses / 12);
    var mesesRestantes = meses % 12;

    var resultado = '';
    if (anos > 0) {
        resultado += anos + (anos === 1 ? ' ano' : ' anos');
    }
    
    if (mesesRestantes > 0) {
        if (anos > 0) {
            resultado += ' e ';
        }
        resultado += mesesRestantes + (mesesRestantes === 1 ? ' mês' : ' meses');
    }

    return resultado;
}

function prepararPaginasDadosDoPlano() {

    // Propriedade customizada; que não existem no JSON de dados.
    data.Simulacao.PaginasDadosPlano = [];
    var maxItensPerPage = 15;

   var pageItens = [];
    
    for (var i = 0; i < data.Simulacao.Produtos.length; i++) {
        var produto = data.Simulacao.Produtos[i];

        for (var j = 0; j < produto.Coberturas.length; j++) {
            var cobertura = produto.Coberturas[j];

            var pageItem = { 
                "Nome": produto.Coberturas.length == 1? produto.Nome : cobertura.Descricao, 
                "Beneficio": cobertura.Beneficio, 
                "Contribuicao": cobertura.Contribuicao 
            };

            pageItens.push(pageItem);
        }
    }

    var indexLastElement = 0;
    var firstPage = { "first": true, items: [] };

    for (var i = 0; i < pageItens.length && i < maxItensPerPage; i++) {
        indexLastElement++;
        firstPage.items.push(pageItens[i]);
    }

    data.Simulacao.PaginasDadosPlano.push(firstPage);

    while (indexLastElement < pageItens.length) {
        maxItensPerPage = 18;

        var elementCount = 0;
        var otherPage = { "first": false, items: [] }
        var indexLastElementClone = indexLastElement;

        for (var i = indexLastElementClone; i < pageItens.length && elementCount < maxItensPerPage; i++) {
            otherPage.items.push(pageItens[i]);
            elementCount++;
            indexLastElement++;
        }

        data.Simulacao.PaginasDadosPlano.push(otherPage);
    }
}

function prepararPaginasDadosDoProduto() {

    // Propriedade customizada; que não existem no JSON de dados.
    data.Simulacao.PaginasDadosProduto = [];
    var maxILinesPerPage = 14;

    var pageItens = [];
    
    for (var i = 0; i < data.Simulacao.Produtos.length; i++) {
        var produto = data.Simulacao.Produtos[i];

        for (var j = 0; j < produto.Coberturas.length; j++) {
            var cobertura = produto.Coberturas[j];

            var pageItem = { 
                "Nome": produto.Coberturas.length == 1? produto.Nome : cobertura.Descricao, 
                "DescricaoComercial": cobertura.DescricaoComercial
            };

            pageItens.push(pageItem);
        }
    }

    var characterCount = 0;
    var indexLastElement = 0;
    var averageLineLength = 90;
    var maxItensPerPage = 10;

    var firstPage = { "first": true, items: [] };

    for (var i = 0; i < pageItens.length; i++) {

        characterCount += pageItens[i].DescricaoComercial.length;

        if((characterCount / averageLineLength) >= maxILinesPerPage || firstPage.items.length >= maxItensPerPage) {
            break;
        }      

        indexLastElement++;
        firstPage.items.push(pageItens[i]);    
    }

    data.Simulacao.PaginasDadosProduto.push(firstPage);


    while (indexLastElement < pageItens.length) {
        characterCount = 0;
        var otherPage = { "first": false, items: [] }
        var indexLastElementClone = indexLastElement;

        for (var i = indexLastElementClone; i < pageItens.length; i++) {

            characterCount += pageItens[i].DescricaoComercial.length;

            if((characterCount / averageLineLength) >= maxILinesPerPage || otherPage.items.length >= maxItensPerPage) {
                break;
            }      

            indexLastElement++;
            otherPage.items.push(pageItens[i]);    
        }

        data.Simulacao.PaginasDadosProduto.push(otherPage);
    }
}

function prepararTabelaResgateDeProdutos() {
    var totalContribution = 0;

    // Propriedades customizadas; que não existem no JSON de dados.
    data.Simulacao.proponent = {};
    data.Simulacao.proponent.firstName = data.Simulacao.NomeProponente.split(' ')[0];
    data.Simulacao.proponent.Idade = data.Simulacao.IdadeProponente;
    data.Simulacao.listaCoberturasRisco = [];
    data.Simulacao.coberturasContratadas = [];
    data.Simulacao.chartsData = {};
    data.Simulacao.chartsData.coverageTimeChart = { data: [], labels: [], "show": false, "fullPage": false };
    data.Simulacao.chartsData.equivalenceChart = { data: [], labels: [], "show": false, "fullPage": false };

    var count = 0, perPage = 5, Produtos = [], countRisco = 0, perPageRisco = 14, Coberturas = [];
    var countChartTime = 0, perPageChartTime = 14, CoberturasTimeData = [], CoberturasTimeLabels = [];
    var countChartEquivalence = 0, perPageChartEquivalence = 14, equivalenceData = [], equivalenceLabels = [];
    var income = data.Simulacao.RendaMensal;

    for (var i = 0; i < data.Simulacao.Produtos.length; i++) {
        var produto = data.Simulacao.Produtos[i];

        var product = { "Nome": produto.Nome, "Coberturas": [] }, produtoIncluido = false;

        // Propriedades customizadas; que não existem no JSON de dados.
        produto.pagedRescueTable = [];

        if (produto.TabelaResgate != null) {
            var TabelaResgate = produto.TabelaResgate;
            var maxPerPage = Math.min(14, produto.TabelaResgate.length);
            var indexLastElement = 0;

            var page = { "first": true, items: [] };

            for (var element = 0; element < maxPerPage; element++) {
                page.items.push(TabelaResgate[element]);
                indexLastElement++;
            }

            produto.pagedRescueTable.push(page);

            maxPerPage = 22;

            while (indexLastElement !== TabelaResgate.length) {
                var page = { "first": false, items: [] }
                var indexLastElementClone = indexLastElement;

                for (var element = indexLastElement; ((element < TabelaResgate.length) && (element < indexLastElementClone + maxPerPage)); element++) {
                    page.items.push(TabelaResgate[element]);
                    indexLastElement++;
                }

                produto.pagedRescueTable.push(page);
            } 
        }

        for (var j = 0; j < produto.Coberturas.length; j++) {
            var coverage = produto.Coberturas[j];

            if (!produtoIncluido) {
                Produtos.push(product);
                produtoIncluido = true;
            }

            var IdadeExclusao = isNaN(coverage.IdadeExclusao) ? 0 : coverage.IdadeExclusao;

            coverage.id = produto.Id;
            totalContribution += coverage.Contribuicao;

            if (IdadeExclusao == 0) {
                IdadeExclusao = coverage.PrazoCerto ? (coverage.Prazo + data.Simulacao.proponent.age) : 100;
            }

            CoberturasTimeData.push(IdadeExclusao);
            CoberturasTimeLabels.push(obterLabelGrafico(coverage.Descricao + ' ' + coverage.id));
            countChartTime++;

            if (countChartTime >= perPageChartTime) {
                countChartTime = 0;
                data.Simulacao.chartsData.coverageTimeChart.data.push(CoberturasTimeData.slice());
                data.Simulacao.chartsData.coverageTimeChart.labels.push(CoberturasTimeLabels.slice());

                CoberturasTimeData = [];
                CoberturasTimeLabels = [];
                perPageChartTime = 16;
            }

            equivalenceData.push(Math.ceil(coverage.Beneficio / income));
            equivalenceLabels.push(coverage.Descricao + ' ' + coverage.id);
            countChartEquivalence++;

            if (countChartEquivalence >= perPageChartEquivalence) {
                data.Simulacao.chartsData.equivalenceChart.data.push(equivalenceData.slice());
                data.Simulacao.chartsData.equivalenceChart.labels.push(equivalenceLabels.slice());

                countChartEquivalence = 0;
                equivalenceData = [];
                equivalenceLabels = [];
                perPageChartEquivalence = 16;
            }

            product.Coberturas.push({
                "Descricao": coverage.Descricao,
                "DescricaoComercial": coverage.DescricaoComercial
            });

            count++;

            if (count >= perPage) {
                data.Simulacao.coberturasContratadas.push({
                    "Produtos": Produtos,
                    "first": data.Simulacao.coberturasContratadas.length == 0
                });
                Produtos = [];
                produtoIncluido = false;
                product = { "Nome": produto.Nome, "Coberturas": [] };
                count = 0;
            }

            var coberturaRisco = coverage;

            coberturaRisco.IdadeAntecipacao = produto.IdadeAntecipacao;
            coberturaRisco.TempoAntecipacao = produto.TempoAntecipacao;
            coberturaRisco.showAgeAnticipation = produto.IdadeAntecipacao > 0;
            coberturaRisco.showTimeAnticipation = produto.TempoAntecipacao > 0;

            if (produto.Coberturas.length == 1) {
                coberturaRisco.Descricao = produto.Nome;
            }

            Coberturas.push(coberturaRisco);
            countRisco++;

            if (countRisco >= perPageRisco) {
                perPageRisco = 16;
                data.Simulacao.listaCoberturasRisco.push({ "Coberturas": Coberturas.slice() });
                Coberturas = [];
                countRisco = 0;
            }
        }
    }
}

function usePartnershipCustomization() {
    return data.Simulacao.ParceiroLogo
        && data.Simulacao.ParceiroLogoNegativo
        && data.Simulacao.ParceiroCorPrimaria;
}

function setPartnershipColor() {
    const colorElements = document.querySelectorAll('.title, .sub-title, .disclaimer-subtitle, .content-subtitle, .protecoes-title, .first-column, .coverage-box-title, .protecoes-total-value, .beneficios-por-risco-linha');

    for (var element = 0; element < colorElements.length; element++) {
        setDocumentStyleProperty(colorElements[element], 'color', data.Simulacao.ParceiroCorPrimaria);
    }

    const backGroundElements = document.querySelectorAll('.personal-information, .footer, .footer-big');

    for (var element = 0; element < backGroundElements.length; element++) {
        setDocumentStyleProperty(backGroundElements[element], 'background-color', data.Simulacao.ParceiroCorPrimaria);
    }

    const svgElements = document.querySelectorAll('svg');

    for (var element = 0; element < svgElements.length; element++) {
        setDocumentStyleProperty(svgElements[element], 'fill', data.Simulacao.ParceiroCorPrimaria);
    }
}

function setPartnershipBanner() {
    if(data.Simulacao.ParceiroBanner) {
        const container = document.querySelectorAll('.header-image');

        for (var element = 0; element < container.length; element++) {
            setImgSrc(container[element], data.Simulacao.ParceiroBanner);
        }
    }
}

function setPartnershipPositiveLogo() {
    const container = document.querySelectorAll('.header-text img');

    for (var element = 0; element < container.length; element++) {
        setImgSrc(container[element], data.Simulacao.ParceiroLogo);
    }
}

function setPartnershipNegativeLogo() {
    const container = document.querySelectorAll('.container-footer img');

    for (var element = 0; element < container.length; element++) {
        setImgSrc(container[element], data.Simulacao.ParceiroLogoNegativo);
    }
}

function setDocumentStyleProperty(element, property, value) {
    element.style[property] = value;
}

function setImgSrc(element, value) {
    element.src = value.replace(/'/g, '');
}

function obterLabelGrafico(label) {
    var splittedLabel = [];
    var words = label.split(' ');

    if (words.length < 4) {
        splittedLabel.push(words.join(' '));
    }
    else {
        const half = words.length / 2.0;

        splittedLabel.push(words.slice(0, half).join(' '));
        splittedLabel.push(words.slice(-half).join(' '));
    }
    return splittedLabel;
}

function getDataPorExtenso(data) {
    const meses = new Array("janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro");
    const date = new Date(data);

    return date.getDate() + " de " + meses[date.getMonth()] + " de " + date.getFullYear();
}

function getPeriodicidadeDescricao(periodicidade) {
    switch(periodicidade) {
        case 'mensal':
            return 'mês';

        case 'trimestral':
            return 'trimestre';

        case 'semestral':
            return 'semestre';

        case 'anual':
            return 'ano';

        case 'unico':
            return 'único';
        
        default: '';
    }

    return date.getDate() + " de " + meses[date.getMonth()] + " de " + date.getFullYear();
}

function converterParaArray(objeto) {
    if (objeto == null)
        return [];

    if (objeto instanceof Array)
        return objeto;

    return [objeto];
}