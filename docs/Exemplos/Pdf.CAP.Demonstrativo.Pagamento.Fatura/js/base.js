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

ajustarTipos(data.Fatura);
gerarResumoFatura(data.Fatura);
gerarPaginasDetalhes(data.Fatura);
gerarTotais(data.Fatura);
formatarDadosParaVisualizacao(data.Fatura);

ko.applyBindings(data);

function ajustarTipos(fatura) {
    fatura.Produtos = converterParaArray(fatura.Produtos.ProdutoFatura);

    for (let produto of fatura.Produtos) {
        produto.Valor = +produto.Valor;
        produto.NumeroTitulos = +produto.NumeroTitulos;
    }
}

function converterParaArray(objeto) {
    if (objeto == null)
        return [];

    if (objeto instanceof Array)
        return objeto;

    return [objeto];
}

function gerarResumoFatura(fatura) {
    let resumo = [];

    fatura.Produtos.reduce(function (resultadoAnterior, item) {
        if (!resultadoAnterior[item.NomeReduzido]) {
            resultadoAnterior[item.NomeReduzido] = {
                Nome: item.NomeReduzido,
                NumeroTitulos: 0,
                Valor: 0
            };

            resumo.push(resultadoAnterior[item.NomeReduzido])
        }

        resultadoAnterior[item.NomeReduzido].NumeroTitulos += item.NumeroTitulos;
        resultadoAnterior[item.NomeReduzido].Valor += item.Valor;

        return resultadoAnterior;
    }, {});

    resumo.sort(function (a, b) { return b.Valor - a.Valor; });

    fatura.Resumo = resumo;
}

function gerarPaginasDetalhes(fatura) {
    const itensPorPagina = 16;
    const numeroPaginasFixas = 3; // Capa, sumário, fim.

    let detalhes = [];

    fatura.Produtos.reduce(function (resultadoAnterior, item) {
        if (!resultadoAnterior[item.Codigo]) {
            resultadoAnterior[item.Codigo] = {
                Codigo: item.Codigo,
                NomeReduzido: item.NomeReduzido,
                NomePromocaoComercial: item.NomePromocaoComercial,
                NumeroTitulos: 0,
                Valor: 0
            };

            detalhes.push(resultadoAnterior[item.Codigo])
        }

        resultadoAnterior[item.Codigo].NumeroTitulos += item.NumeroTitulos;
        resultadoAnterior[item.Codigo].Valor += item.Valor;

        return resultadoAnterior;
    }, {});

    detalhes.sort(function (a, b) { return b.Valor - a.Valor; });

    fatura.Paginas = [];

    for (let i = 0; i < detalhes.length; i += itensPorPagina) {
        const grupo = detalhes.slice(i, i + itensPorPagina);

        fatura.Paginas.push({
            Itens: grupo
        });
    }

    fatura.NumeroPaginas = fatura.Paginas.length + numeroPaginasFixas;
}

function gerarTotais(fatura) {
    let totalNumeroTitulos = 0;
    let totalValor = 0;

    fatura.Resumo.reduce(function (resultadoAnterior, item) {
        totalNumeroTitulos += item.NumeroTitulos;
        totalValor += item.Valor;
    }, 0);

    fatura.Totais = {
        NumeroTitulos: totalNumeroTitulos,
        Valor: totalValor
    }
}

function formatarDadosParaVisualizacao(fatura) {
    fatura.Vencimento = fatura.Vencimento.split('T')[0].split('-').reverse().join('/');
}
