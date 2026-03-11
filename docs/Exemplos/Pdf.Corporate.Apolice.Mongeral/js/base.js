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

const alturaMaximaGlobal = 900;


function apoliceParaSubEstipulante(valor) {
    if (typeof valor === 'boolean') return valor;
    if (typeof valor === 'string') return valor.toLowerCase() === 'true';
    return false;
}

function montarRamosUnicos(apolice) {
    if (!apolice || typeof apolice !== 'object') return;

    apolice.RamosUnicos = [];

    if (!apolice?.Coberturas?.Cobertura) return;

    const coberturas = Array.isArray(apolice.Coberturas.Cobertura)
        ? apolice.Coberturas.Cobertura
        : [apolice.Coberturas.Cobertura];

    const mapa = new Map();

    coberturas.forEach(cob => {
        if (!cob || typeof cob !== 'object') return;

        const codigo = String(cob.CodigoRamo || '').trim();
        if (!codigo) return;

        if (!mapa.has(codigo)) {
            mapa.set(codigo, {
                CodigoRamo: codigo,
                DescricaoRamo: cob.DescricaoRamo || '',
                DescricaoGrupoRamo: cob.DescricaoGrupoRamo || ''
            });
        }
    });

    apolice.RamosUnicos = Array.from(mapa.values());
}

//Verifica se existe o "Código" para exibir a tabela de "ramos"
function existeRamoValido() {
    const apolice = data.CorporateApoliceMongeral;
    if (!apolice) return false;

    const ramos = apolice.RamosUnicos;
    if (!Array.isArray(ramos) || ramos.length === 0) return false;

    return ramos.some(ramo => {
        if (!ramo || typeof ramo !== 'object') return false;

        const codigo = String(ramo.CodigoRamo || '').trim();

        return codigo !== '';
    });
}

function converterParaArray(objeto) {
    if (objeto == null)
        return [];

    if (objeto instanceof Array)
        return objeto;

    return [objeto];
}

function temValorUtil(obj) {
    return Object.entries(obj || {}).some(([_, valor]) => {
        if (Array.isArray(valor)) return valor.length > 0;
        if (typeof valor === 'object' && valor !== null) return temValorUtil(valor);
        return String(valor).trim() !== '';
    });
}

function normalizarArray(valor) {
    if (Array.isArray(valor)) return valor;
    if (valor && typeof valor === 'object') return [valor];
    return [];
}

function isValorUtil(valor) {
    if (valor === null || valor === undefined) return false;
    if (typeof valor === 'string') return valor.trim() !== '';
    if (typeof valor === 'object') return Object.keys(valor).length > 0;
    return true;
}

function inicializarCamposParaBindings() {
    // Garantir que data existe
    if (typeof data === 'undefined' || data === null) {
        data = {};
    }

    // Garantir que CorporateApoliceMongeral existe
    if (!data.CorporateApoliceMongeral || typeof data.CorporateApoliceMongeral !== 'object') {
        data.CorporateApoliceMongeral = {};
    }

    const ca = data.CorporateApoliceMongeral;

    ca.ContratoAditivoId ??= '';
    ca.NomeBeneficiario ??= '';
    ca.NomeEmpresa ??= '';
    ca.Data ??= '';
    ca.ContratoAditivoSubEstipulanteId ??= '';
    ca.NomeSubestipulante ??= '';
    ca.CNPJSubestipulante ??= '';
    ca.DataInicioVigenciaSubestipulante ??= '';
    ca.DataFimVigenciaSubestipulante ??= '';

    // Garantir que Plano existe e é um objeto válido
    if (!ca.Plano || typeof ca.Plano !== 'object') {
        ca.Plano = {};
    }
    const dp = ca.Plano;

    dp.PropostaId ??= '';
    dp.ContratoId ??= '';
    dp.NomeCorretor ??= '';
    dp.CPFCnpjCorretor ??= '';
    dp.SusepCorretor ??= '';
    dp.EnderecoCorretor ??= '';
    dp.ProcessoSusep ??= '';
    dp.NumApolice ??= '';
    dp.DataInicioVigenciaContrato ??= '';
    dp.DataFimVigenciaContrato ??= '';
    dp.NomeEstipulante ??= '';
    dp.CNPJ ??= '';
    dp.UnidadeProducao ??= '';
    dp.TipoCapitalSegurado ??= '';
    dp.PremioEstimado ??= '';
    dp.TaxaSeguro ??= '';
    dp.CusteioSeguro ??= '';
    dp.IdadeImplantacao ??= '';
    dp.IdadeNovaAdesao ??= '';


    // Garantir que Coberturas existe e é um objeto válido
    if (!ca.Coberturas || typeof ca.Coberturas !== 'object') {
        ca.Coberturas = {};
    }
    ca.Coberturas.Cobertura = converterParaArray(ca.Coberturas.Cobertura);

    // Garantir que Cobertura é um array
    if (Array.isArray(ca.Coberturas.Cobertura)) {
        ca.Coberturas.Cobertura.forEach(cb => {
            if (cb && typeof cb === 'object') {
                cb.NomeCobertura ??= '';
                cb.GarantiaDescricao ??= '';
                cb.ValorCoberturaTitular ??= '';
                cb.ValorCoberturaConjuge ??= '';
                cb.ValorCoberturaFilhos ??= '';
                cb.ValorCoberturaPais ??= '';
                cb.ValorCoberturaSogros ??= '';
                cb.ValorCoberturaTotal ??= '';
                cb.Processo ??= '';
                cb.CodigoRamo ??= '';
                cb.DescricaoRamo ??= '';
                cb.DescricaoGrupoRamo ??= '';
            }
        });
    }
}

function temRegistroNaTabela(seletorTabela) {
    const tabela = document.querySelector(
        seletorTabela.startsWith('.') ? seletorTabela : '.' + seletorTabela
    );

    return !!tabela?.querySelector('tbody tr');
}

function isCoberturaSAF(nome) {
    if (!nome) return false;

    const texto = normalizarTexto(nome).toLowerCase();
    return /\bsaf\b/.test(texto);
}


// Montar Franquias
function montarFranquias(apolice) {
    if (!apolice || typeof apolice !== 'object') return;

    apolice.FranquiasValidas = apolice.FranquiasValidas || [];

    if (!apolice?.Coberturas?.Cobertura) return;

    const coberturas = Array.isArray(apolice.Coberturas.Cobertura)
        ? apolice.Coberturas.Cobertura
        : [apolice.Coberturas.Cobertura];

    coberturas.forEach(item => {
        if (!item || typeof item !== 'object') return;

        const nome = item.NomeCobertura?.trim();
        if (!nome) return;

        // Franquias pode ser "" ou objeto
        if (typeof item.Franquias !== 'object' || !item.Franquias) return;

        const franquia = item.Franquias.Franquia;
        if (!franquia || typeof franquia !== 'object') return;

        const tempo = franquia.Tempo?.trim();
        const tempoEm = franquia.TempoEm?.trim();

        if (!tempo || !tempoEm) return;

        apolice.FranquiasValidas.push({
            NomeCobertura: nome,
            Tempo: tempo,
            TempoEm: tempoEm
        });
    });
}


function formatarTextoData() {
    // Garantir que a estrutura existe 
    if (typeof data === 'undefined' || !data.CorporateApoliceMongeral) {
        return;
    }

    data.CorporateApoliceMongeral.TextoDataEmissaoFormatada = ko.computed(() => {
        const dataEmissao = ko.unwrap(data.CorporateApoliceMongeral?.Data);

        function mesPorExtenso(mesStr) {
            const meses = [
                "janeiro", "fevereiro", "março", "abril", "maio", "junho",
                "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"
            ];
            const indice = parseInt(mesStr, 10) - 1;
            return meses[indice] || '';
        }

        if (!dataEmissao || dataEmissao.length !== 10) return '';

        const dia = dataEmissao.substring(0, 2);
        const mes = mesPorExtenso(dataEmissao.substring(3, 5));
        const ano = dataEmissao.substring(6, 10);

        return `Rio de Janeiro, ${dia} de ${mes} de ${ano}`;
    });
}

function garantirArrayCarencia(campo) {
    if (Array.isArray(campo)) return campo.filter(e => Object.keys(e || {}).length > 0);
    if (campo && typeof campo === 'object' && Object.keys(campo).length > 0) return [campo];
    return [];
}

function normalizarTexto(texto) {
    return (texto || '')
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .toUpperCase();
}

// Verificar se existe carência para inserir o bloco de texto fixo
function existeCarencia() {
    const apolice = data?.CorporateApoliceMongeral;
    if (!apolice) return false;

    const coberturas = apolice?.Coberturas?.Cobertura;
    if (!coberturas) return false;

    const lista = Array.isArray(coberturas) ? coberturas : [coberturas];
    if (lista.length === 0) return false;

    return lista.some(cobertura => {
        const cp = cobertura?.CarenciasProgressivas;
        const cepd = cobertura?.CarenciasEmPeriodosDefinidos;
        const cpc = cobertura?.CarenciasPorCausas;
        const cps = cobertura?.CarenciasPorSuicidios;

        return Boolean(
            (cp && typeof cp === 'object' && cp !== '' && cp.CarenciaProgressiva) ||
            (cepd && typeof cepd === 'object' && cepd !== '' && cepd.CarenciaEmPeriodoDefinido) ||
            (cpc && typeof cpc === 'object' && cpc.CarenciaPorCausa && (cpc.CarenciaPorCausa.Causa || cpc.CarenciaPorCausa.Tempo)) ||
            (cps && typeof cps === 'object' && cps !== '' && cps.CarenciaPorSuicidio)
        );
    });
}


// CARÊNCIA PROGRESSIVA (PARCELAS)
function extrairCarenciaProgressivaParcelas(apolice) {
    const resultado = [];
    const coberturas = apolice?.Coberturas?.Cobertura || [];
    const lista = Array.isArray(coberturas) ? coberturas : [coberturas];

    lista.forEach(cobertura => {
        const nomeCob = cobertura?.NomeCobertura?.trim();
        const raiz = cobertura?.CarenciasProgressivas;

        if (!raiz || typeof raiz !== 'object' || raiz === '') return;

        const listaProgressiva = garantirArrayCarencia(raiz?.CarenciaProgressiva || raiz);
        if (!listaProgressiva.length) return;

        // Filtra apenas progressiva por PARCELAS
        const filtrados = listaProgressiva.filter(p => {
            return normalizarTexto(p?.PeriodoEm) === "PARCELAS";
        });

        if (!filtrados.length) return;

        // Validação dos campos exigidos para a condição ser satisfeita
        const validos = filtrados.filter(p => {
            if (!isValorUtil(p?.Inicio)) return false;
            if (!isValorUtil(p?.Termino)) return false;
            if (!isValorUtil(p?.PercentualCapitalSegurado)) return false;
            return true;
        });

        if (!validos.length) return;

        const texto =
            `Para a cobertura ${nomeCob}, quando não preenchida DPS, ` +
            `será adotado um período de carência progressiva por parcelas, ` +
            `na qual o(s) beneficiário(s) fazem jus a um percentual do capital segurado, ` +
            `da seguinte forma:`;

        const tabela = validos.map(p => {
            const inicial = p.Inicio;
            const final = p.Termino;
            const perc = p.PercentualCapitalSegurado;

            return {
                Periodo: `De ${inicial} até ${final} parcela(s)`,
                Percentual: `${String(perc).replace(".", ",")}%`
            };
        });

        resultado.push({
            Tipo: "CARENCIA_PROGRESSIVA_PARCELAS",
            Texto: texto,
            Tabela: tabela
        });
    });

    return resultado;
}


// CARÊNCIA PROGRESSIVA (MESES)
function extrairCarenciaProgressivaMeses(apolice) {
    const resultado = [];
    const coberturas = apolice?.Coberturas?.Cobertura || [];
    const lista = Array.isArray(coberturas) ? coberturas : [coberturas];

    lista.forEach(cobertura => {
        const nomeCob = cobertura?.NomeCobertura?.trim();
        const raiz = cobertura?.CarenciasProgressivas;

        if (!raiz || typeof raiz !== 'object' || raiz === '' || !nomeCob) return;

        const listaProgressiva = garantirArrayCarencia(raiz?.CarenciaProgressiva || raiz);
        if (!listaProgressiva.length) return;

        // Filtra somente progressivas EM MESES com 4 campos válidos
        const validos = listaProgressiva.filter(p =>
            normalizarTexto(p?.PeriodoEm) === "MESES" &&
            isValorUtil(p?.Inicio) &&
            isValorUtil(p?.Termino) &&
            isValorUtil(p?.PercentualCapitalSegurado)
        );

        if (!validos.length) return;

        const texto =
            `Para o(s) plano(s)/cobertura(s) ${nomeCob} quando não preenchida DPS, ` +
            `será adotado um período de carência em que o(s) beneficiário(s) fazem jus ` +
            `a um percentual do capital segurado, da seguinte forma:`;

        const tabela = validos.map(p => {
            const inicial = p.Inicio;
            const final = p.Termino;
            const perc = p.PercentualCapitalSegurado;

            const periodo = String(final) === "9999"
                ? `A partir de ${inicial} meses`
                : `De ${inicial} até ${final} meses`;

            return {
                Periodo: periodo,
                Percentual: `${String(perc).replace(".", ",")}%`
            };
        });

        resultado.push({
            Tipo: "CARENCIA_PROGRESSIVA_MESES",
            Texto: texto,
            Tabela: tabela
        });
    });

    return resultado;
}


// CARÊNCIA DEFINIDA (meses - SAF)
function extrairCarenciaDefinidaMesesSAF(apolice) {
    const resultado = [];
    const coberturas = apolice?.Coberturas?.Cobertura || [];
    const lista = Array.isArray(coberturas) ? coberturas : [coberturas];

    lista.forEach(cobertura => {
        const nome = cobertura?.NomeCobertura;
        if (!nome) return;

        if (!isCoberturaSAF(nome)) return;

        const carencia = cobertura?.CarenciasEmPeriodosDefinidos?.CarenciaEmPeriodoDefinido;
        if (!carencia || carencia.TempoEm?.toLowerCase() !== 'meses') return;

        resultado.push({
            Tipo: 'CARENCIA_DEFINIDA_MESES_SAF',
            Texto: `Para o plano/cobertura ${nome} haverá carência de ${carencia.Tempo} mês(es) para segurados a partir de 65 anos ou quando não houver o preenchimento de DPS (Declaração Pessoal de Saúde). Esta carência é aplicável somente ao titular do seguro.`
        });
    });

    return resultado;
}


// CARÊNCIA DEFINIDA (MESES)
function extrairCarenciaDefinidaMeses(apolice) {
    const resultado = [];
    const coberturas = apolice?.Coberturas?.Cobertura || [];
    const lista = Array.isArray(coberturas) ? coberturas : [coberturas];

    lista.forEach(cobertura => {
        const nome = cobertura?.NomeCobertura;
        if (!nome) return;

        if (isCoberturaSAF(nome)) return;

        const carencia = cobertura?.CarenciasEmPeriodosDefinidos?.CarenciaEmPeriodoDefinido;
        if (!carencia || carencia.TempoEm?.toLowerCase() !== 'meses') return;

        resultado.push({
            Tipo: 'CARENCIA_DEFINIDA_MESES',
            Texto: `Para o plano/cobertura ${nome} haverá carência de ${carencia.Tempo} mês(es).`
        });
    });

    return resultado;
}


// CARÊNCIA DEFINIDA (DIAS)
function extrairCarenciaDefinidaDias(apolice) {
    const resultado = [];
    const coberturas = apolice?.Coberturas?.Cobertura || [];
    const lista = Array.isArray(coberturas) ? coberturas : [coberturas];

    lista.forEach(cobertura => {
        const nome = cobertura?.NomeCobertura || '';
        const carencia = cobertura?.CarenciasEmPeriodosDefinidos?.CarenciaEmPeriodoDefinido;

        if (!carencia) return;

        if (
            !isValorUtil(carencia.Tempo) ||
            String(carencia.TempoEm || '').toLowerCase() !== 'dias'
        ) {
            return;
        }

        resultado.push({
            Tipo: 'CARENCIA_DEFINIDA_DIAS',
            Texto: `Para o(s) plano(s)/cobertura(s) ${nome}, haverá carência de ${carencia.Tempo} dia(s) para doenças específicas assim caracterizadas nas condições gerais/cláusulas especiais.`
        });
    });

    return resultado;
}


// CARÊNCIA DEFINIDA (parcelas)
function extrairCarenciaDefinidaParcelas(apolice) {
    const resultado = [];
    const coberturas = apolice?.Coberturas?.Cobertura || [];
    const lista = Array.isArray(coberturas) ? coberturas : [coberturas];

    lista.forEach(cobertura => {
        const nome = cobertura?.NomeCobertura || '';
        const carencia = cobertura?.CarenciasEmPeriodosDefinidos?.CarenciaEmPeriodoDefinido;

        if (!carencia) return;

        if (
            !isValorUtil(carencia.Tempo) ||
            String(carencia.TempoEm || '').toLowerCase() !== 'parcelas'
        ) {
            return;
        }

        resultado.push({
            Tipo: 'CARENCIA_DEFINIDA_PARCELAS',
            Texto: `Para o(s) plano(s)/cobertura(s) ${nome}, quando não preenchida DPS, haverá carência de ${carencia.Tempo} parcela(s).`
        });
    });

    return resultado;
}


// CARÊNCIA POR (Causa)
function extrairCarenciaPorCausas(apolice) {
    const resultado = [];
    const coberturas = apolice?.Coberturas?.Cobertura || [];
    const lista = Array.isArray(coberturas) ? coberturas : [coberturas];

    lista.forEach(cobertura => {
        const nome = cobertura?.NomeCobertura || '';
        const carencia = cobertura?.CarenciasPorCausas;

        if (!carencia || typeof carencia !== 'object') return;

        const carenciaPorCausa = carencia.CarenciaPorCausa;
        if (!carenciaPorCausa) return;

        const causa = carenciaPorCausa.Causa;
        const tempo = carenciaPorCausa.Tempo;
        const tempoEm = carenciaPorCausa.TempoEm;

        if (!isValorUtil(causa)) return;

        resultado.push({
            Tipo: 'CARENCIA_POR_CAUSAS',
            Texto: `Para o(s) plano(s)/cobertura(s) ${nome}, haverá carência de ${tempo} ${(tempoEm || '').toLowerCase()} para a seguinte causa: ${causa}.`
        });
    });

    return resultado;
}

function extrairTodasCarencias(apolice) {
    return [
        ...extrairCarenciaDefinidaMesesSAF(apolice),
        ...extrairCarenciaDefinidaMeses(apolice),
        ...extrairCarenciaDefinidaParcelas(apolice),
        ...extrairCarenciaDefinidaDias(apolice),
        ...extrairCarenciaPorCausas(apolice)
    ];
}

function extrairCarenciasProgressivas(apolice) {
    return [
        ...extrairCarenciaProgressivaParcelas(apolice)
    ];
}

function extrairCarenciasProgressivasPorMes(apolice) {
    return [
        ...extrairCarenciaProgressivaMeses(apolice)
    ];
}

iniciarRenderizacaoSequencialSincrono();

function iniciarRenderizacaoSequencialSincrono() {

    inicializarCamposParaBindings()

    const apolice = data.CorporateApoliceMongeral || {};

    apolice.TextosCarencias = ko.computed(() => {
        return extrairTodasCarencias(apolice);
    });

    apolice.TextosCarenciasProgressivas = ko.computed(() => {
        return extrairCarenciasProgressivas(apolice);
    });

    apolice.TextosCarenciasProgressivasMeses = ko.computed(() => {
        return extrairCarenciasProgressivasPorMes(apolice);
    });

    montarFranquias(apolice);

    montarRamosUnicos(apolice)

    formatarTextoData()

    var temSubEstipulante = data.CorporateApoliceMongeral?.ApoliceParaSubEstipulante

    if (!apoliceParaSubEstipulante(temSubEstipulante)) {
        mostrarElementoEReaplicarBind('dados-plano');
        mostrarElementoEReaplicarBind('dados-seguro');
    } else {
        mostrarElementoEReaplicarBind('dados-plano-subestipulante');
        mostrarElementoEReaplicarBind('dados-seguro-subestipulante');
    }

    // Garantir estrutura final objeto
    if (!data.CorporateApoliceMongeral || typeof data.CorporateApoliceMongeral !== 'object') {
        data.CorporateApoliceMongeral = {};
    }
    if (!data.CorporateApoliceMongeral.Plano || typeof data.CorporateApoliceMongeral.Plano !== 'object') {
        data.CorporateApoliceMongeral.Plano = {};
    }
    if (!data.CorporateApoliceMongeral.Coberturas || typeof data.CorporateApoliceMongeral.Coberturas !== 'object') {
        data.CorporateApoliceMongeral.Coberturas = {};
    }

    ko.applyBindings(data);

    if (temRegistroNaTabela('tbl-dados-cobertura')) {
        quebrarTabelaEntrePaginas('secao-cobertura', 'titulo', 'tbl-dados-cobertura', 'tr', null, '0.1in', '0.5in');
    }
    mostrarElementoEReaplicarBindEReposicionar('.dados-corretor', '0.1in');

    mostrarElementoEReaplicarBindEReposicionar('.texto-prazo-seguro');

    mostrarElementoEReaplicarBindEReposicionar('.texto-apolice-1');

    mostrarElementoEReaplicarBindEReposicionar('.texto-apolice-2');

    mostrarElementoEReaplicarBindEReposicionar('.texto-apolice-3');

    mostrarElementoEReaplicarBindEReposicionar('.texto-apolice-4');

    if (existeRamoValido()) {
        mostrarElementoEReaplicarBindEReposicionar('.tabela-dados-ramos', '0.1in');
    }

    mostrarElementoEReaplicarBindEReposicionar('.garantias-seguro', '0.1in');

    mostrarElementoEReaplicarBindEReposicionar('.secao-garantia-seguro');

    mostrarElementoEReaplicarBindEReposicionar('.bloco-risco-excluido', '0.1in');

    mostrarElementoEReaplicarBindEReposicionar('.despesas-salvamento', '0.1in');

    mostrarElementoEReaplicarBindEReposicionar('.locais-cobertos-seguro', '0.1in');

    if (existeCarencia()) {
        mostrarElementoEReaplicarBindEReposicionar('.carencia', '0.1in');
    }

    mostrarElementoEReaplicarBindEReposicionar('.bloco-texto-explicativo-carencias');

    mostrarElementoEReaplicarBindEReposicionar('.texto-carencia-progressiva-parcelas');

    mostrarElementoEReaplicarBindEReposicionar('.texto-carencia-progressiva-meses');

    if (existeCarencia()) {
        mostrarElementoEReaplicarBindEReposicionar('.texto-suicidio-fixo');
    }

    if (apolice.FranquiasValidas && Array.isArray(apolice.FranquiasValidas) && apolice.FranquiasValidas.length > 0) {
        mostrarElementoEReaplicarBindEReposicionar('.franquia-texto-fixo', '0.1in');
    }

    if (apolice.FranquiasValidas && Array.isArray(apolice.FranquiasValidas) && apolice.FranquiasValidas.length > 0) {
        mostrarElementoEReaplicarBindEReposicionar('.bloco-texto-explicativo-franquia');
    }

    mostrarElementoEReaplicarBindEReposicionar('.nome-social');

    mostrarElementoEReaplicarBindEReposicionar('.texto-final-contato');

    // Mostra a data dentro do container de assinatura
    const dataAssinatura = document.querySelector('.assinatura-local-data');
    if (dataAssinatura) {
        const displayOriginal = dataAssinatura.getAttribute('data-display-original') || 'block';
        dataAssinatura.style.display = displayOriginal;
    }

    mostrarElementoEReaplicarBindEReposicionar('.assinatura');

}

function mostrarElementoEReaplicarBind(seletorItem) {
    const seletor = seletorItem.startsWith('.') ? seletorItem : '.' + seletorItem;
    const el = document.querySelector(seletor);
    if (!el) return;

    const displayOriginal = el.getAttribute('data-display-original') || 'block';
    el.style.display = displayOriginal;

    // Força o reflow para garantir altura atualizada
    el.offsetHeight;
}

function mostrarElementoEReaplicarBindEReposicionar(seletorItem, margemEspacoPadrao = '0.0in') {
    const seletor = seletorItem.startsWith('.') ? seletorItem : '.' + seletorItem;
    const el = document.querySelector(seletor);
    if (!el) return;

    const displayOriginal = el.getAttribute('data-display-original') || 'block';
    el.style.display = displayOriginal;

    el.offsetHeight;
    reposicionarElementoFixo(seletor, margemEspacoPadrao);
}

function reposicionarElementoFixo(seletor, margemEspacoPadrao = '0.0in', margemQuebraPadrao = '0.5in') {
    const elemento = document.querySelector(seletor);
    if (!elemento) return;

    const margemEspaco = elemento.getAttribute('data-margem-espaco') || margemEspacoPadrao;
    const margemQuebra = elemento.getAttribute('data-margem-quebra') || margemQuebraPadrao;

    elemento.parentNode.removeChild(elemento);

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

function quebrarTabelaEntrePaginas(
    seletorSecaoClasse,
    seletorTituloClasse,
    seletorTabelaClasse,
    seletorRow,
    seletorFooter = null,
    margemEspaco = '0.2in',
    margemQuebra = '1.1in'
) {
    const secaoOriginal = document.querySelector('.' + seletorSecaoClasse);
    if (!secaoOriginal) return;

    const tituloEl = seletorTituloClasse ? secaoOriginal.querySelector('.' + seletorTituloClasse) : null;
    const tabelaOriginal = seletorTabelaClasse ? secaoOriginal.querySelector('.' + seletorTabelaClasse) : null;
    if (!tabelaOriginal) return;

    const colgroupOriginal = tabelaOriginal.querySelector('colgroup');
    const theadOriginal = tabelaOriginal.querySelector('thead');
    const tbodyOriginal = tabelaOriginal.querySelector('tbody');

    const linhas = Array.from((tbodyOriginal || tabelaOriginal).querySelectorAll(seletorRow));
    const linhasRestantes = [...linhas];

    let footerClonado = null;
    if (seletorFooter) {
        const footerOriginal =
            tabelaOriginal.querySelector(seletorFooter) ||
            secaoOriginal.querySelector('.' + seletorFooter) ||
            secaoOriginal.querySelector(seletorFooter);

        if (footerOriginal) {
            footerClonado = footerOriginal.cloneNode(true);
            footerOriginal.remove();
        }
    }

    secaoOriginal.remove();

    let paginas = Array.from(document.querySelectorAll('.page'));
    let ultimaPagina = paginas[paginas.length - 1];
    let contentAtual = ultimaPagina ? ultimaPagina.querySelector('.content') : criarNovaPagina();

    let blocoAtual = null;
    let tbodyAtual = null;

    while (linhasRestantes.length > 0) {
        const temBlocosRenderizados = contentAtual.children.length > 0;
        const margem = temBlocosRenderizados ? margemEspaco : margemQuebra;

        const teste = criarBlocoTabela(margem, seletorSecaoClasse, tituloEl, tabelaOriginal, colgroupOriginal, theadOriginal);
        teste.tbody.appendChild(linhasRestantes[0].cloneNode(true));

        const alturaEstimativa = alturaProspectiva(contentAtual, teste.bloco);

        if (alturaEstimativa > alturaMaximaGlobal) {
            contentAtual = criarNovaPagina();
            continue;
        }

        const real = criarBlocoTabela(margem, seletorSecaoClasse, tituloEl, tabelaOriginal, colgroupOriginal, theadOriginal);
        blocoAtual = real.bloco;
        tbodyAtual = real.tbody;

        blocoAtual.style.display = 'block';

        tbodyAtual.appendChild(linhasRestantes.shift());
        contentAtual.appendChild(blocoAtual);

        while (linhasRestantes.length > 0) {
            const proxLinha = linhasRestantes[0];

            tbodyAtual.appendChild(proxLinha);
            proxLinha.offsetHeight; // força reflow

            const alturaAtual = blocoAtual.getBoundingClientRect().bottom - contentAtual.getBoundingClientRect().top;

            if (alturaAtual > alturaMaximaGlobal) {
                tbodyAtual.removeChild(proxLinha);
                break;
            }

            linhasRestantes.shift();
        }
    }

    if (footerClonado && blocoAtual) {
        const blocoTesteFooter = blocoAtual.cloneNode(true);
        blocoTesteFooter.style.display = 'block';

        blocoTesteFooter.appendChild(footerClonado.cloneNode(true));

        const alturaComFooter = alturaProspectiva(contentAtual, blocoTesteFooter);

        if (alturaComFooter > alturaMaximaGlobal) {
            contentAtual = criarNovaPagina();

            const temBlocosRenderizados = contentAtual.children.length > 0;
            const margem = temBlocosRenderizados ? margemEspaco : margemQuebra;

            const blocoFooter = document.createElement('div');
            blocoFooter.className = seletorSecaoClasse;
            blocoFooter.style.marginTop = margem;
            blocoFooter.style.display = 'block';
            blocoFooter.appendChild(footerClonado);

            contentAtual.appendChild(blocoFooter);
        } else {
            blocoAtual.appendChild(footerClonado);
        }
    }
}

function criarBlocoTabela(marginValue, secaoClasse, tituloEl, tabelaOriginal, colgroupOriginal, theadOriginal) {
    const bloco = document.createElement('div');
    bloco.className = secaoClasse;
    bloco.style.marginTop = marginValue;

    if (tituloEl) {
        const tituloClone = tituloEl.cloneNode(true);
        tituloClone.style.display = '';
        bloco.appendChild(tituloClone);
    }

    const table = document.createElement('table');
    table.className = tabelaOriginal.className;

    for (const attr of tabelaOriginal.attributes) {
        if (attr.name !== 'class') table.setAttribute(attr.name, attr.value);
    }

    if (colgroupOriginal) table.appendChild(colgroupOriginal.cloneNode(true));
    if (theadOriginal) table.appendChild(theadOriginal.cloneNode(true));

    const tbody = document.createElement('tbody');
    table.appendChild(tbody);

    bloco.appendChild(table);

    return { bloco, tbody };
}

function criarNovaPagina() {
    const page = document.createElement('div');
    page.className = 'page';

    const logoTemplate = document.querySelector('.page-logo-container');
    if (logoTemplate) {
        page.appendChild(logoTemplate.cloneNode(true));
    }

    const content = document.createElement('div');
    content.className = 'content';
    page.appendChild(content);

    const footerTemplate = document.querySelector('.footer');
    if (footerTemplate) {
        content.appendChild(footerTemplate.cloneNode(true));
    }

    document.body.appendChild(page);

    return content;
}

function alturaProspectiva(content, bloco) {
    const originalDisplay = bloco.style.display;
    bloco.style.display = 'block';

    content.appendChild(bloco);
    bloco.offsetHeight;

    const contentRect = content.getBoundingClientRect();
    const blocoRect = bloco.getBoundingClientRect();

    content.removeChild(bloco);
    bloco.style.display = originalDisplay;

    return blocoRect.bottom - contentRect.top;
}
