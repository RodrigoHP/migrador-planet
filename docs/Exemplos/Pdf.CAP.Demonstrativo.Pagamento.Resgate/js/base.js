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

ajustarTipos(data.Resgate);
gerarResumoResgate(data.Resgate);
gerarPaginasDetalhes(data.Resgate);
gerarTotais(data.Resgate);
formatarDadosParaVisualizacao(data.Resgate);

ko.applyBindings(data);

function ajustarTipos(resgate) {
    resgate.Produtos = converterParaArray(resgate.Produtos.ProdutoResgate);

    for (let produto of resgate.Produtos) {
        produto.Valor = +produto.Valor;
        produto.NumeroTitulos = +produto.NumeroTitulos;
    }

    if (resgate.Cliente && resgate.Cliente.Pagamento) {
        resgate.Cliente.Pagamento.formataAgenciaConta = ko.computed(function() {
          return resgate.Cliente.Pagamento.NumeroAgencia + " - " + resgate.Cliente.Pagamento.NumeroConta;
        });
    }
}

function converterParaArray(objeto) {
    if (objeto == null)
        return [];

    if (objeto instanceof Array)
        return objeto;

    return [objeto];
}

function gerarResumoResgate(resgate) {
    let resumo = [];

    resgate.Produtos.reduce(function (resultadoAnterior, item) {
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

    resgate.Resumo = resumo;
}

function gerarPaginasDetalhes(resgate) {
    const itensPorPagina = 16;
    const numeroPaginasFixas = 3; // Capa, sumário, fim.

    resgate.Paginas = [];

    for (let i = 0; i < resgate.Produtos.length; i += itensPorPagina) {
        const grupo = resgate.Produtos.slice(i, i + itensPorPagina);

        resgate.Paginas.push({
            Itens: grupo
        });
    }

    resgate.NumeroPaginas = resgate.Paginas.length + numeroPaginasFixas;
}

function gerarTotais(resgate) {
    let totalNumeroTitulos = 0;
    let totalValor = 0;
    let valorAtualizacao = 0;
    let valorTotal = 0;

    resgate.Resumo.reduce(function (resultadoAnterior, item) {
        totalNumeroTitulos += item.NumeroTitulos;
        totalValor += item.Valor;
    }, 0);

    if (resgate.Produtos.length > 0) {
        const primeiroProduto = resgate.Produtos[0];
        valorAtualizacao = primeiroProduto?.ValorAtualizacao ?? 0;
        valorTotal = primeiroProduto?.ValorTotal ?? 0;
    }

    resgate.Totais = {
        NumeroTitulos: totalNumeroTitulos,
        Valor: totalValor,
        ValorAtualizacao: valorAtualizacao,
        ValorTotal: valorTotal
    }
}

function formatarDadosParaVisualizacao(resgate) {
    resgate.DataPagamento = resgate.DataPagamento.split('T')[0].split('-').reverse().join('/');
}
