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

function criarTextoProcessoSUSEP() {
    data.KIT_BOAS_VINDAS.TextoProcessoSUSEP = ko.computed(() => {
        let texto = '';

        const planoPrev = data.KIT_BOAS_VINDAS.DADOS_PREV?.PLANOS;
        const planosRisco = data.KIT_BOAS_VINDAS.DADOS_RISCO?.PLANOS_COBERTURAS;

        if (planoPrev) {
            texto += planoPrev.NOME_PLANO_PREV + ': ' + planoPrev.PROC_SUSEP + '; ';
        }

        // Normaliza para array
        const listaPlanosRisco = Array.isArray(planosRisco)
            ? planosRisco
            : (planosRisco ? [planosRisco] : []);

        listaPlanosRisco.forEach(p => {
            texto += p.NOME_COBERTURA + ': ' + p.PROC_SUSEP + '; ';
        });

        return texto;
    });
}

function formatarParaArray(obj, key) {
    if (obj && obj[key] && !Array.isArray(obj[key])) {
        obj[key] = [obj[key]];
    }

}

function formatarTextoData() {
    data.KIT_BOAS_VINDAS.TextoDataEmissaoFormatada = ko.computed(() => {
        const dataEmissao = data.KIT_BOAS_VINDAS.DATA_EMISSAO;

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

function montarBeneficiarios() {
    const beneficiariosComProdutoID = [];

    const dadosBenef = data.KIT_BOAS_VINDAS?.DADOS_BENEFICIARIO;
    let listaProdutos = [];

    if (dadosBenef && typeof dadosBenef === 'object') {
        if (Array.isArray(dadosBenef.PRODUTO_BENEFICIARIO)) {
            // Se já é array, use-o diretamente
            listaProdutos = dadosBenef.PRODUTO_BENEFICIARIO;
        } else if (dadosBenef.PRODUTO_BENEFICIARIO) {
            // Se não for array, embrulhe-o em um array
            listaProdutos = [dadosBenef.PRODUTO_BENEFICIARIO];
        } else {
            listaProdutos = [dadosBenef];
        }
    }

    listaProdutos.forEach(produto => {
        const produtoId = produto.PRODUTO_ID || '';
        let listaBenef = produto.BENEFICIARIOS;
        let beneficiariosArray = [];

        if (Array.isArray(listaBenef)) {
            beneficiariosArray = listaBenef;
        } else if (listaBenef && typeof listaBenef === 'object') {
            beneficiariosArray = [listaBenef];
        }

        beneficiariosArray.forEach(benef => {
            // Trata a data de nascimento somente se for uma string não vazia
            let dataFormatada = '';
            if (typeof benef.DATA_NASCIMENTO === 'string' && benef.DATA_NASCIMENTO.trim() !== '') {
                const partes = benef.DATA_NASCIMENTO.split(' ')[0].split('/');
                if (Array.isArray(partes) && partes.length === 3) {
                    dataFormatada = `${partes[0]}/${partes[1]}/${partes[2]}`;
                }
            }

            // Trata o percentual: converte de string para número, formata e adiciona o símbolo '%'
            let percentual = '';
            if (typeof benef.PERCENTUAL_BENEFICIARIO === 'string') {
                const percentualNumerico = parseFloat(benef.PERCENTUAL_BENEFICIARIO.replace(',', '.'));
                if (!isNaN(percentualNumerico)) {
                    percentual = `${percentualNumerico.toFixed(2).replace('.', ',')}%`;
                }
            }

            beneficiariosComProdutoID.push({
                ...benef,
                DATA_NASCIMENTO: dataFormatada,
                PERCENTUAL_BENEFICIARIO: percentual,
                PRODUTO_ID: produtoId
            });
        });
    });

    data.KIT_BOAS_VINDAS.BENEFICIARIOS = beneficiariosComProdutoID;
}

function montarDadosPrevidenciaGroup() {
    const listaFundos = data.KIT_BOAS_VINDAS?.DADOS_PREV?.PLANOS?.FUNDOS || [];

    mostrarElementoEReaplicarBindEReposicionar('.tabela-dados-planos-prev');

    if (existeRepeticaoRenderizada('tabela-row-dados-planos-prev-fundos')) {
        quebrarTabelaEntrePaginas(
            'tabela-dados-fundos-prev',
            'tabela-header-fundos-prev',
            'tabela-row-dados-planos-prev-fundos',
            null, '0in'
        );
    }

    mostrarElementoEReaplicarBindEReposicionar('.texto-prev-footer');

    // Verifica se pelo menos um fundo tem FLAG_PORTABILIDADE = 'SIM'
    if (listaFundos.some(f => f.FLAG_PORTABILIDADE?.trim().toUpperCase() === 'SIM')) {
        mostrarElementoEReaplicarBind('.portabilidade');
    }
}

function montarDadosMorteInvalidezGroup() {
    quebrarTabelaEntrePaginas(
        'tabela-dados-planos-morte-ou-invalidez',
        'tabela-header-dados-planos-morte-ou-invalidez',
        'tabela-row-dados-planos-morte-ou-invalidez'
    );
    mostrarElementoEReaplicarBindEReposicionar('.tabela-premios');
}

function montarTextosAdicionaisGroup() {
    mostrarElementoEReaplicarBindEReposicionar('.textos-adicionais')

    if (data.KIT_BOAS_VINDAS.MODELO_PROPOSTA && ['AN', 'AO', 'Y9'].includes(data.KIT_BOAS_VINDAS.MODELO_PROPOSTA.toUpperCase())) {
        mostrarElementoEReaplicarBind('.texto-assistencia-funeral')
    }
}

function montarTabelaCarencia() {
    const tabela = data.KIT_BOAS_VINDAS?.FRANQUIA_CARENCIA?.CARENCIA_PROGRESSIVA_MESES?.TABELA_CARENCIA_PROGRESSIVA;
    const normalizada = [];

    if (Array.isArray(tabela)) {
        tabela.forEach(item => {
            if (item?.TEXTO_PERIODO_VIGENCIA || item?.TEXTO_CAPITAL_SEGURADO) {
                normalizada.push({
                    TEXTO_PERIODO_VIGENCIA: item.TEXTO_PERIODO_VIGENCIA || '',
                    TEXTO_CAPITAL_SEGURADO: item.TEXTO_CAPITAL_SEGURADO || ''
                });
            }
        });
    } else if (typeof tabela === 'object' && tabela !== null) {
        // Caso venha só um objeto
        normalizada.push({
            TEXTO_PERIODO_VIGENCIA: tabela.TEXTO_PERIODO_VIGENCIA || '',
            TEXTO_CAPITAL_SEGURADO: tabela.TEXTO_CAPITAL_SEGURADO || ''
        });
    }

    data.KIT_BOAS_VINDAS.TABELA_CARENCIA_NORMALIZADA = normalizada;
}


function dividirTabelaCarenciaEmColunas() {
    const tabela = data.KIT_BOAS_VINDAS.TABELA_CARENCIA_NORMALIZADA || [];
    const metade = Math.ceil(tabela.length / 2);

    // Atualiza arrays normais, não observables
    data.KIT_BOAS_VINDAS.TABELA_CARENCIA_COLUNA_ESQUERDA = tabela.slice(0, metade);
    data.KIT_BOAS_VINDAS.TABELA_CARENCIA_COLUNA_DIREITA = tabela.slice(metade);
}

function inicializarCamposParaBindings() {
    const kit = data.KIT_BOAS_VINDAS;

    // Helpers
    const garantirArray = (campo) => {
        if (Array.isArray(campo)) return campo.filter(e => Object.keys(e || {}).length > 0);
        if (typeof campo === 'object' && campo !== null && Object.keys(campo).length > 0) return [campo];
        return [];
    };

    // ================= DADOS GERAIS =================
    kit.PROPOSTA ??= '';
    kit.DATA_EMISSAO ??= '';

    // ================= DADOS_PAGAMENTO =================
    data.KIT_BOAS_VINDAS = data.KIT_BOAS_VINDAS || {};
    data.KIT_BOAS_VINDAS.DADOS_PAGAMENTO = data.KIT_BOAS_VINDAS.DADOS_PAGAMENTO || {};
    const pag = data.KIT_BOAS_VINDAS.DADOS_PAGAMENTO;

    pag.FORMA_PAGAMENTO ??= '';
    pag.PERIODICIDADE_PAGAMENTO ??= '';
    pag.DIA_VENCIMENTO ??= '';
    pag.NUMERO_BANCO ??= '';
    pag.NOME_BANCO ??= '';
    pag.NUMERO_AGENCIA ??= '';
    pag.NUMERO_CONTA_CORRENTE ??= '';
    pag.INICIO_VIGENCIA ??= '';
    pag.NOME_TITULAR_CONTA ??= '';
    pag.CPFCNPJ_TITULAR_CONTA ??= '';

    // ================= DADOS_SEGURADO =================
    kit.DADOS_SEGURADO = kit.DADOS_SEGURADO || {};
    const s = kit.DADOS_SEGURADO;
    s.NOME ??= '';
    s.NOME_CIVIL ??= '';
    s.CPF ??= '';
    s.CEP ??= '';
    s.UF ??= '';
    s.NACIONALIDADE ??= '';
    s.DATA_NASCIMENTO ??= '';
    s.ENDERECO ??= '';
    s.BAIRRO ??= '';
    s.CIDADE ??= '';

    // ================= DADOS_PREV =================
    kit.DADOS_PREV = kit.DADOS_PREV || {};
    const p = kit.DADOS_PREV.PLANOS = kit.DADOS_PREV.PLANOS || {};
    p.NOME_PLANO_PREV ??= '';
    p.PROC_SUSEP ??= '';
    p.DATA_BENEFICIO ??= '';
    p.INSCRICAO ??= '';
    p.DATA_INI_VIGENCIA ??= '';
    p.REGIME_IR ??= '';
    p.PERIODICIDADE ??= '';
    p.INDEX_PLANO ??= '';
    p.EXCEDENTE_FINANC ??= '';
    p.TIPO_RENDA ??= '';
    p.FUNDOS = garantirArray(p.FUNDOS);
    p.FUNDOS.forEach(f => {
        f.FUNDO ??= '';
        f.VALOR_APORTE ??= '';
        f.FLAG_PORTABILIDADE ??= '';
        f.VALOR_CONTRIBUICAO ??= '';
    });

    // DADOS_PLANO

    // ================= DADOS_RISCO =================
    kit.DADOS_RISCO = kit.DADOS_RISCO || {};
    const r = kit.DADOS_RISCO;
    r.DADOS_PLANO = r.DADOS_PLANO || {};
    r.DADOS_PLANO.FORMA_PAGAMENTO ??= '';
    r.PERIODICIDADE ??= '';
    r.INDEX_PLANO ??= '';
    r.PREMIO_LIQUIDO_TOTAL ??= '';
    r.IOF_TOTAL ??= '';
    r.PREMIO_TOTAL ??= '';
    r.TEXTO_SEGUROS ??= '';

    // CORRETOR
    r.CORRETOR = r.CORRETOR || {};
    r.CORRETOR.NOME ??= '';
    r.CORRETOR.REGISTRO_SUSEP ??= '';
    r.NOME_CONJUGE ??= '';
    r.DATA_NASC_CONJUGE ??= '';

    // APÓLICE
    r.APOLICE = r.APOLICE || {};
    r.APOLICE.ESTIPULANTE ??= '';
    r.APOLICE.CNPJ_ESTIPULANTE ??= '';
    r.APOLICE.ENDERECO_ESTIPULANTE ??= '';
    r.APOLICE.UF_ESTIPULANTE ??= '';
    r.APOLICE.CEP_ESTIPULANTE ??= '';
    r.APOLICE.CIDADE_ESTIPULANTE ??= '';
    r.APOLICE.BAIRRO_ESTIPULANTE ??= '';
    r.APOLICE.DADOS_APOLICES = garantirArray(r.APOLICE.DADOS_APOLICES);
    r.APOLICE.DADOS_APOLICES.forEach(a => {
        a.NOME_PLANO_APOLICE ??= '';
        a.APOLICE ??= '';
        a.DATA_EMISSAO ??= '';
        a.DATA_FIM_VIGENCIA ??= '';
    });

    // COBERTURAS
    r.PLANOS_COBERTURAS = garantirArray(r.PLANOS_COBERTURAS);
    r.PLANOS_COBERTURAS.forEach(p => {
        p.PLANO ??= '';
        p.NOME_COBERTURA ??= '';
        p.PROC_SUSEP ??= '';
        p.VALOR_BENEFICIO ??= '';
        p.VALOR_CONTRIBUICAO ??= '';
        p.CONTROLE_APOLICE ??= '';
        p.DATA_INI_VIGENCIA ??= '';
        p.DATA_FIM_VIGENCIA ??= '';
    });

    // RISCOS_EXCLUIDOS
    r.RISCOS_EXCLUIDOS = r.RISCOS_EXCLUIDOS || {};
    r.RISCOS_EXCLUIDOS.RISCO = garantirArray(r.RISCOS_EXCLUIDOS.RISCO);

    r.RISCOS_EXCLUIDOS.RISCO.forEach(risco => {
        risco.NOMEITEMPRODUTO ??= '';
        risco.DESCRICAO ??= '';
    });

    // ================= RAMO =================
    kit.RAMO = garantirArray(kit.RAMO);
    kit.RAMO.forEach(r => {
        r.CODIGO ??= '';
        r.DESCRICAO ??= '';
        r.GRUPO_RAMO ??= '';
    });

    // ================= BENEFICIÁRIOS =================
    kit.BENEFICIARIOS = garantirArray(kit.BENEFICIARIOS);
    kit.BENEFICIARIOS.forEach(b => {
        b.PRODUTO_ID ??= '';
        b.NOME_BENEFICIARIO ??= '';
        b.DATA_NASCIMENTO ??= '';
        b.GRAU_PARENTESCO ??= '';
        b.PERCENTUAL_BENEFICIARIO ??= '';
    });

    // ================= FRANQUIA_CARENCIA =================
    const f = kit.FRANQUIA_CARENCIA = kit.FRANQUIA_CARENCIA || {};
    f.CARENCIA_PROGRESSIVA_MESES ??= {};
    f.CARENCIA_DEFINIDA_MESES ??= {};
    f.CARENCIA_DEFINIDA_PARCELAS ??= {};
    f.CARENCIA_DEFINIDA_DIA ??= {};
    f.CARENCIA_PROGRESSIVA_CAUSA ??= {};
    f.CARENCIA_SUICIDIO ??= {};

    // ================= ARRAYS KO FOREACH =================
    const foreachListas = [
        'TEXTOS_CARENCIA',
        'TABELA_CARENCIA_COLUNA_ESQUERDA',
        'TABELA_CARENCIA_COLUNA_DIREITA',
        'TEXTOS_FRANQUIA',
        'PLANOS_PAGAMENTO_POR',
        'PLANOS_PAGAMENTO_ATE',
        'PLANOS_PRAZO_DECRESCIMO'
    ];

    foreachListas.forEach(nome => {
        const valor = kit[nome];
        if (Array.isArray(valor)) return;
        kit[nome] = valor ? [valor] : [];
    });

    // ================= CAMPOS DE TEXTO =================
    kit.TextoProcessoSUSEP ??= '';
    kit.TextoDataEmissaoFormatada ??= '';
    kit.TEXTO_CARENCIA_PROGRESSIVA ??= '';


    // ================= SORTEIO =================
    r.SORTEIO = r.SORTEIO || {};
    const srt = r.SORTEIO;
    srt.NR_SORTE ??= '';
    srt.QTD_SORTEIOS ??= '';
    srt.DATA_VIGENCIA_SORTEIO ??= '';
    srt.VALOR_SORTEIO ??= '';
    srt.PROC_SUSEP_SORTEIO ??= '';

}

function montarTextosCarencia() {
    const franquia = data.KIT_BOAS_VINDAS?.FRANQUIA_CARENCIA;
    const textos = [];

    // Verifica se TABELA_CARENCIA_PROGRESSIVA existe como array ou objeto
    const tabela = franquia?.CARENCIA_PROGRESSIVA_MESES?.TABELA_CARENCIA_PROGRESSIVA;
    let countTabela = 0;

    if (Array.isArray(tabela)) {
        countTabela = tabela.length;
    } else if (typeof tabela === 'object' && tabela !== null) {
        countTabela = 1; // único objeto presente
    }

    // Helper para extrair texto de forma segura (string única, array ou objeto)
    const extrairTextos = estrutura => {
        if (typeof estrutura === 'string') {
            return [estrutura.trim()];
        }
        if (Array.isArray(estrutura)) {
            return estrutura
                .map(item => item?.TEXTO_CARENCIA_DEFINIDA || '')
                .filter(t => t.trim() !== '')
                .map(t => t.trim());
        }
        if (typeof estrutura === 'object' && estrutura !== null && estrutura.TEXTO_CARENCIA_DEFINIDA) {
            return [estrutura.TEXTO_CARENCIA_DEFINIDA.trim()];
        }
        return [];
    };

    // Adiciona todos os textos (de todas as fontes possíveis)
    textos.push(
        ...extrairTextos(franquia?.CARENCIA_PROGRESSIVA_MESES?.TEXTO_CARENCIA_DEFINIDA),
        ...extrairTextos(franquia?.CARENCIA_DEFINIDA_MESES),
        ...extrairTextos(franquia?.CARENCIA_DEFINIDA_PARCELAS),
        ...extrairTextos(franquia?.CARENCIA_DEFINIDA_DIA)
    );

    // Também inclui os textos de CAUSA e SUICÍDIO, se existirem
    const textoCausa = franquia?.CARENCIA_PROGRESSIVA_CAUSA?.TEXTO_CARENCIA_PROGRESSIVA;
    if (typeof textoCausa === 'string' && textoCausa.trim() !== '') {
        textos.push(textoCausa.trim());
    }

    const textoSuicidio = franquia?.CARENCIA_SUICIDIO?.TEXTO_CARENCIA_SUICIDIO;
    if (typeof textoSuicidio === 'string' && textoSuicidio.trim() !== '') {
        textos.push(textoSuicidio.trim());
    }

    data.KIT_BOAS_VINDAS.TEXTOS_CARENCIA = textos;

    // Se existe tabela, define o texto resumido separadamente
    if (countTabela !== 0) {
        const textoResumo = franquia?.CARENCIA_PROGRESSIVA_MESES?.TEXTO_CARENCIA_PROGRESSIVA;
        if (typeof textoResumo === 'string' && textoResumo.trim() !== '') {
            data.KIT_BOAS_VINDAS.TEXTO_CARENCIA_PROGRESSIVA = textoResumo.trim();
        }

        montarTabelaCarencia();
        dividirTabelaCarenciaEmColunas();
    }
}

function montarFranquia() {
    const franquia = data.KIT_BOAS_VINDAS?.FRANQUIA_CARENCIA?.REGRA_FRANQUIA;

    const listaFranquia = Array.isArray(franquia)
        ? franquia
        : (franquia ? [franquia] : []);

    const textosFranquia = listaFranquia
        .map(f => f?.TEXTO_FRANQUIA?.trim())
        .filter(Boolean); // Remove strings vazias ou undefined

    // Cria como observableArray se necessário
    data.KIT_BOAS_VINDAS.TEXTOS_FRANQUIA = textosFranquia;
}

function verificarTextoSAF() {
    // Lista de códigos SAF (como array de inteiros)
    const codigoSaf = [
        2036, 2703, 2605, 2725, 2007, 2025, 2068, 2080, 2081, 2210, 2241, 2242, 2243, 2244,
        2362, 2363, 2364, 2365, 2415, 2601, 2710, 2715, 2720, 2730, 2735, 2741, 2052, 2237,
        2238, 2239, 2285, 2337, 2338, 2339, 2340, 2369, 2371, 2372, 2373, 2374, 2375, 2376,
        2378, 2379, 2380, 2423, 2452, 2460, 2466, 2467, 2468, 2491, 2494, 2510, 2556, 2557,
        2611, 2805, 2604, 2437, 2438, 2439, 2191, 2313, 2094, 2122, 2126, 2673, 2705, 2293,
        2294, 2492, 2026, 2069, 2180, 2211, 2225, 2226, 2361, 2416, 2549, 2739, 2742, 2748,
        2749, 2051, 2350, 2351, 2352, 2538, 2539, 2540, 2541, 2542, 2543, 2558, 2648, 2806,
        2813, 2818, 2822, 2826, 2672, 2704, 2417, 1956, 2027, 2070, 2716, 2721, 2726, 2731,
        2736, 2743, 2536, 2711, 2123, 2127, 2706, 2418, 2028, 2071, 2134, 2751, 2537, 2590,
        2591, 2592, 2560, 2745, 2747, 2750, 2559, 2002, 2001, 2003, 2004, 1633, 2282, 2283,
        2284, 1662, 1640, 1645, 1650, 1663, 1667, 1665, 2311, 2312, 1697, 1423, 1424, 1426,
        1428, 1489, 1544, 2014, 2024, 2074, 1085, 1088, 1084, 1086, 1087, 1036, 1281, 1297,
        1325, 1421, 1422, 1425, 1427, 1465, 1466, 1469, 1470, 1471, 1476, 1488, 1492, 1494,
        1496, 1497, 1499, 1031, 1032, 1034, 1429, 1493, 1117, 1116, 1680, 1505, 2079, 1504,
        1542, 1620, 1679, 2078, 2135, 2152, 2149, 2148, 2153, 1543, 2050, 2138, 2139, 2140,
        2260, 2261, 2262, 2263, 2264, 2265, 2266, 2267, 2268, 2269, 2270, 2271, 2272, 2335,
        2478, 2479, 2147, 2154, 2158, 2150, 2093, 2092, 1659, 1670, 1526, 152, 1522, 1669,
        1655, 1521, 1523, 1525, 1066, 1068, 1065, 1067
    ];

    // Acessa os códigos dos planos renderizados (exemplo com Knockout)
    const planos = data?.KIT_BOAS_VINDAS?.DADOS_RISCO?.PLANOS_COBERTURAS || [];

    for (let i = 0; i < planos.length; i++) {
        const codigo = parseInt(planos[i]?.PLANO, 10);
        if (codigoSaf.includes(codigo)) {
            return true; // encontrou
        }
    }

    return false; // nenhum código bateu
}

function verificarProdutosSAFBioParque() {
    // Lista de códigos SAF (como array de inteiros)
    const codigoSaf = [
        3087, 3088, 3089, 3090, 3091, 3092, 3093, 3094
    ];

    // Acessa os códigos dos planos renderizados (exemplo com Knockout)
    const planos = data?.KIT_BOAS_VINDAS?.DADOS_RISCO?.PLANOS_COBERTURAS || [];

    for (let i = 0; i < planos.length; i++) {
        const codigo = parseInt(planos[i]?.PLANO, 10);
        if (codigoSaf.includes(codigo)) {
            return true; // encontrou
        }
    }

    return false; // nenhum código bateu
}

function temNomeSocial() {
    const nome = (data.KIT_BOAS_VINDAS.DADOS_SEGURADO?.NOME || '').trim().toLowerCase();
    const nomeCivil = (data.KIT_BOAS_VINDAS.DADOS_SEGURADO?.NOME_CIVIL || '').trim().toLowerCase();

    return nome !== nomeCivil;
}

function processarPlanosComPrazos() {
    const planos = data.KIT_BOAS_VINDAS?.DADOS_RISCO?.PLANOS_COBERTURAS || [];
    const codigosValidos = ['2798', '2795', '2799', '2797', '2800', '2794', '2834', '2796', '2395', '1510', '2020', '2200', '2390', '2009'];

    const resultado = {
        por: [],
        ate: [],
        decrescimo: [],
    };

    planos.forEach(p => {
        const plano = p.PLANO;
        const nome = p.NOME_COBERTURA;

        if (!codigosValidos.includes(plano)) return;

        const por = p.PAGAMENTO_ANTECIPADO_POR;
        const ate = p.PAGAMENTO_ANTECIPADO_ATE;
        const decrescimo = p.PRAZO_DECRESCIMO;

        // Função auxiliar para normalizar para array
        const toArray = (item) => {
            if (!item) return [];
            return Array.isArray(item) ? item : [item];
        };

        const porArray = toArray(por);
        const ateArray = toArray(ate);
        const decrescimoArray = toArray(decrescimo);

        porArray.forEach(pa => {
            if (pa.NOME) {
                resultado.por.push({ codigo: plano, nome, tempo: pa.TEMPO });
            }
        });

        ateArray.forEach(pa => {
            if (pa.NOME) {
                resultado.ate.push({ codigo: plano, nome, tempo: pa.TEMPO });
            }
        });

        decrescimoArray.forEach(pd => {
            if (pd.NOME) {
                resultado.decrescimo.push({ codigo: plano, nome, tempo: pd.TEMPO });
            }
        });
    });

    // Armazenar diretamente no objeto principal
    data.KIT_BOAS_VINDAS.PLANOS_PAGAMENTO_POR = resultado.por;
    data.KIT_BOAS_VINDAS.PLANOS_PAGAMENTO_ATE = resultado.ate;
    data.KIT_BOAS_VINDAS.PLANOS_PRAZO_DECRESCIMO = resultado.decrescimo;
}

function ajustarPeriodoVigenciaPlanos() {
    const planos = data.KIT_BOAS_VINDAS?.DADOS_RISCO?.PLANOS_COBERTURAS;

    if (!planos) return;

    const listaPlanos = Array.isArray(planos) ? planos : [planos];

    listaPlanos.forEach(plano => {
        const ini = typeof plano.DATA_INI_VIGENCIA === 'string' ? plano.DATA_INI_VIGENCIA.trim() : '';
        const fim = typeof plano.DATA_FIM_VIGENCIA === 'string' ? plano.DATA_FIM_VIGENCIA.trim() : '';

        if (ini && fim) {
            plano.DATA_INI_VIGENCIA = `${ini} até ${fim}`;
        }
        // Caso contrário, mantém DATA_INI_VIGENCIA como está
    });
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


function dadosDoSorteioExistem() {
    const sorteio = data?.KIT_BOAS_VINDAS?.DADOS_RISCO?.SORTEIO;

    if (!sorteio) return false;

    // Verifica se pelo menos um dos campos está preenchido
    return ['NR_SORTE', 'QTD_SORTEIOS', 'DATA_VIGENCIA_SORTEIO', 'VALOR_SORTEIO', 'PROC_SUSEP_SORTEIO']
        .some(chave => {
            const valor = sorteio[chave];
            return typeof valor === 'string' ? valor.trim() !== '' : valor != null;
        });
}

function identificarEFormatarCpfCnpj() {
    const dadosPagamento = data?.KIT_BOAS_VINDAS?.DADOS_PAGAMENTO;
    if (!dadosPagamento || !dadosPagamento.CPFCNPJ_TITULAR_CONTA) return "null";

    let somenteNumeros = dadosPagamento.CPFCNPJ_TITULAR_CONTA.replace(/\D/g, "");

    if (somenteNumeros.length === 10) {
        somenteNumeros += "0"; // completa CPF
    } else if (somenteNumeros.length === 13) {
        somenteNumeros += "0"; // completa CNPJ
    }

    if (somenteNumeros.length === 11) {
        dadosPagamento.CPFCNPJ_TITULAR_CONTA = somenteNumeros.replace(
            /(\d{3})(\d{3})(\d{3})(\d{2})/,
            "$1.$2.$3-$4"
        );
        return "CPF";
    }

    if (somenteNumeros.length === 14) {
        dadosPagamento.CPFCNPJ_TITULAR_CONTA = somenteNumeros.replace(
            /(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/,
            "$1.$2.$3/$4-$5"
        );
        return "CNPJ";
    }

    // Se não tiver tamanho válido, mantém os dígitos e retorna CPF
    dadosPagamento.CPFCNPJ_TITULAR_CONTA = somenteNumeros;
    return "CPF";
}

function deveExibirTabelaDadosBasicosPagamento() {
    const dadosPagamento = data?.KIT_BOAS_VINDAS?.DADOS_PAGAMENTO;
    if (!dadosPagamento) return false;

    const temTodosDadosBancarios =
        !!dadosPagamento.NUMERO_BANCO &&
        !!dadosPagamento.NOME_BANCO &&
        !!dadosPagamento.NUMERO_AGENCIA &&
        !!dadosPagamento.NUMERO_CONTA_CORRENTE &&
        !!dadosPagamento.INICIO_VIGENCIA &&
        !!dadosPagamento.NOME_TITULAR_CONTA &&
        !!dadosPagamento.CPFCNPJ_TITULAR_CONTA;

    if (temTodosDadosBancarios) return false;

    const temDadosMinimos =
        !!dadosPagamento.FORMA_PAGAMENTO ||
        !!dadosPagamento.PERIODICIDADE_PAGAMENTO ||
        !!dadosPagamento.DIA_VENCIMENTO;

    return temDadosMinimos;
}

iniciarRenderizacaoSequencialSincrono();

function iniciarRenderizacaoSequencialSincrono() {
    inicializarCamposParaBindings()
    ajustarPeriodoVigenciaPlanos()
    processarPlanosComPrazos()

    montarBeneficiarios()

    formatarTextoData()

    const dadosPrev = data.KIT_BOAS_VINDAS?.DADOS_PREV;
    const planos = dadosPrev?.PLANOS;

    const renderizaTextoSAF = verificarTextoSAF()

    const sorteio = dadosDoSorteioExistem();

    const ehRenovacao = data?.KIT_BOAS_VINDAS?.RENOVACAO === "SIM";
    const documentoDadosTitularPagamento = identificarEFormatarCpfCnpj();
    const exibeTabelaDadosBasicosPagamento = deveExibirTabelaDadosBasicosPagamento();

    montarTextosCarencia()

    montarFranquia()

    criarTextoProcessoSUSEP()

    ko.applyBindings(data);

    if (temNomeSocial()) {
        mostrarElementoEReaplicarBindEReposicionar('.tabela-segurado-com-nome-civil')
    }
    else {
        mostrarElementoEReaplicarBindEReposicionar('.tabela-segurado')
    }

    if (dadosPrev && planos && temValorUtil(planos)) {
        montarDadosPrevidenciaGroup();
    }

    if (existeRepeticaoRenderizada('tabela-row-dados-planos-morte-ou-invalidez')) {
        montarDadosMorteInvalidezGroup();

        if (sorteio) {
            mostrarElementoEReaplicarBindEReposicionar('.texto-sorteio')
        }
    }

    if (existeRepeticaoRenderizada('tabela-row-dados-planos-risco-excluido')) {
        quebrarTabelaEntrePaginas(
            'tabela-dados-planos-risco-excluido',
            '',
            'tabela-row-dados-planos-risco-excluido',
            'footer-dados-planos-risco-excluido'
        );
    }

    if (renderizaTextoSAF) {
        mostrarElementoEReaplicarBindEReposicionar('.texto-saf')
    }

    if (existeRepeticaoRenderizada('tabela-row-ramos')) {
        quebrarTabelaEntrePaginas('tabela-dados-ramos', 'tabela-header-ramos', 'tabela-row-ramos')
    }

    if (existeRepeticaoRenderizada('tabela-row-beneficiarios')) {
        quebrarTabelaEntrePaginas('tabela-beneficiarios', 'tabela-header-beneficiarios', 'tabela-row-beneficiarios')
    } else {
        mostrarElementoEReaplicarBindEReposicionar('.texto-beneficiarios-herdeiros')
    }

    montarTextosAdicionaisGroup()

    if (verificarProdutosSAFBioParque()) {
        mostrarElementoEReaplicarBindEReposicionar('.texto-saf-bioparque')
    }

    if (!ehRenovacao) {
        if (exibeTabelaDadosBasicosPagamento) {
            mostrarElementoEReaplicarBindEReposicionar('.tabela-dados-pagamento-basicos');
        } else if (documentoDadosTitularPagamento === 'CPF') {
            mostrarElementoEReaplicarBindEReposicionar('.tabela-dados-pagamento-com-cpf');
        } else if (documentoDadosTitularPagamento === 'CNPJ') {
            mostrarElementoEReaplicarBindEReposicionar('.tabela-dados-pagamento-com-cnpj');
        }
    }

    mostrarElementosComValorEReaplicarBind('.textos-dados-plano-informacoes-adicionais')

    reposicionarElementoFixo('.textos-dados-plano-informacoes-adicionais')

    if (existeRepeticaoRenderizada('tabela-row-pagamento-antecipado-por')) {
        quebrarTabelaEntrePaginas('tabela-dados-pagamento-antecipado-por', '', 'tabela-row-pagamento-antecipado-por')
    }

    if (existeRepeticaoRenderizada('tabela-row-pagamento-antecipado-ate')) {
        quebrarTabelaEntrePaginas('tabela-dados-pagamento-antecipado-ate', '', 'tabela-row-pagamento-antecipado-ate')
    }

    if (existeRepeticaoRenderizada('tabela-row-pagamento-prazo-decrescimo')) {
        quebrarTabelaEntrePaginas('tabela-dados-pagamento-prazo-decrescimo', '', 'tabela-row-pagamento-prazo-decrescimo')
    }

    mostrarElementosComValorEReaplicarBind('.texto-dados-corretor-conjuge-group');
    reposicionarElementoFixo('.texto-dados-corretor-conjuge-group')

    if (existeRepeticaoRenderizada('tabela-row-apolices')) {
        quebrarTabelaEntrePaginas('tabela-dados-apolices', '', 'tabela-row-apolices')
    }

    mostrarElementosComValorEReaplicarBind('.texto-dados-estipulante-group')
    reposicionarElementoFixo('.texto-dados-estipulante-group')

    mostrarElementosComValorEReaplicarBind('.texto-seguro');
    reposicionarElementoFixo('.texto-seguro')

    if (existeRepeticaoRenderizada('row-tabela-carencia')) {
        mostrarElementoEReaplicarBindEReposicionar('.tabela-carencia-em-duas-colunas');

    } else if (existeRepeticaoRenderizada('row-carencia')) {
        quebrarTabelaEntrePaginas('texto-dados-carencia-group', '', 'row-carencia')
    }

    if (existeRepeticaoRenderizada('row-franquia')) {
        quebrarTabelaEntrePaginas('texto-dados-franquia-group', '', 'row-franquia')
    }

    mostrarElementoEReaplicarBindEReposicionar('.texto-dados-susep-group')

    mostrarElementoEReaplicarBindEReposicionar('.texto-final-group')

    if (sorteio) {
        RenderizarEstruturaFixa('page-final')
    }
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

    console.log(ultimaPagina)
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