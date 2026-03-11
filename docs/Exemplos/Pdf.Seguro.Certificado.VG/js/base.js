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
    console.log(seletor)
    const el = document.querySelector(seletor);
    if (!el) return;

    const displayOriginal = el.getAttribute('data-display-original') || 'block';
    el.style.display = displayOriginal;

    // Força o reflow para garantir altura atualizada
    el.offsetHeight;
}

function mostrarElementoEReaplicarBindEReposicionar(seletorItem, margemEspacoPadrao = '0.2in') {
    const seletor = seletorItem.startsWith('.') ? seletorItem : '.' + seletorItem;
    const el = document.querySelector(seletor);
    if (!el) return;

    const displayOriginal = el.getAttribute('data-display-original') || 'block';
    el.style.display = displayOriginal;

    // Força o reflow para garantir altura atualizada
    el.offsetHeight;
    reposicionarElementoFixo(seletor, margemEspacoPadrao);
}

const garantirArray = (campo) => {
    if (Array.isArray(campo)) return campo.filter(e => Object.keys(e || {}).length > 0);
    if (campo && typeof campo === 'object' && Object.keys(campo).length > 0) return [campo];
    return [];
};

function formatarTextoData() {
    data.CertificadoGlobalXMLDTO.TextoDataEmissaoFormatada = ko.computed(() => {
        const dataEmissao = ko.unwrap(data.CertificadoGlobalXMLDTO.DataEnvio);

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


function inicializarCamposParaBindings() {
    const certificado = data.CertificadoGlobalXMLDTO || {};
    /* --- utilitário para padronizar listas --- */
    const garantirArray = (campo) => {
        if (Array.isArray(campo)) return campo.filter(e => Object.keys(e || {}).length > 0);
        if (campo && typeof campo === 'object' && Object.keys(campo).length > 0) return [campo];
        return [];
    };

    // ================= COBERTURAS =================
    certificado.Coberturas = certificado.Coberturas || {};

    certificado.Coberturas.CoberturaXMLDTO = garantirArray(certificado.Coberturas.CoberturaXMLDTO);
    certificado.Coberturas.CoberturaXMLDTO.forEach(cob => {
        cob.ContratoSeguradoCertificadoEndossoID ??= '';
        cob.Descricao ??= '';
        cob.DescricaoCurta ??= '';
        cob.ValorBen ??= '';
        cob.DataInicioVigencia ??= '';
        cob.ValorBenConjuge ??= '';
        cob.DataInicioVigenciaConjuge ??= '';
        cob.ValorBenFilho ??= '';
        cob.DataInicioVigenciaFilho ??= '';
        cob.ValorBenPais ??= '';
        cob.DataInicioVigenciaPais ??= '';
        cob.ValorBenSogros ??= '';
        cob.DataInicioVigenciaSogros ??= '';
        cob.ValorPremioIndividual ??= '';
        cob.CodigoRamo ??= '';
        cob.DescricaoRamoSusep ??= '';
        cob.DescricaoGrupoRamo ??= '';
    });

    // ================= DETALHE FRANQUIA CARENCIA =================
    certificado.FranquiasCarencias = certificado.FranquiasCarencias || {};

    certificado.FranquiasCarencias.DetalheFranquiaCarencia = garantirArray(certificado.FranquiasCarencias.DetalheFranquiaCarencia);
    certificado.FranquiasCarencias.DetalheFranquiaCarencia.forEach(caren => {
        caren.NomeCobertura ??= '';
    });

    // ================= FRANQUIA CARENCIA =================
    certificado.FranquiasCarencias = certificado.FranquiasCarencias || {};

    certificado.FranquiasCarencias.CarenciasProgressivas ??= '';
    certificado.FranquiasCarencias.CarenciasEmPeriodosDefinidos ??= '';
    certificado.FranquiasCarencias.CarenciasPorCausas ??= '';
    certificado.FranquiasCarencias.CarenciasPorSuicidios ??= '';


    // ================= CARENCIA / FRANQUIA =================
    certificado.FranquiasValidas = [];

    // ================= CORRETOR =================
    certificado.Corretor = certificado.Corretor || {};

    certificado.Corretor.Nome ??= '';
    certificado.Corretor.Registro ??= '';
    certificado.Corretor.Documento ??= '';
    certificado.Corretor.EnderecoCorretor ??= '';

    // ================= ASSISTÊNCIA EMPRESA =================
    certificado.AssistenciasEmpresa = certificado.AssistenciasEmpresa || {};
    certificado.AssistenciasEmpresa.CoberturaXMLDTO = garantirArray(certificado.AssistenciasEmpresa.CoberturaXMLDTO);

    certificado.AssistenciasEmpresa.CoberturaXMLDTO.forEach(assis => {
        assis.ContratoSeguradoCertificadoEndossoID ??= '';
        assis.Descricao ??= '';
        assis.ValorBen ??= '';
        assis.DataInicioVigencia ??= '';
        assis.ValorBenConjuge ??= '';
        assis.ValorBenFilho ??= '';
        assis.ValorBenPais ??= '';
        assis.ValorBenSogros ??= '';
        assis.ValorPremioIndividual ??= '';

    });


    // ================= ASSISTÊNCIA FUNCIONÁRIO =================
    certificado.AssistenciasFuncionario = certificado.AssistenciasFuncionario || {};
    certificado.AssistenciasFuncionario.CoberturaXMLDTO = garantirArray(certificado.AssistenciasFuncionario.CoberturaXMLDTO);

    certificado.AssistenciasFuncionario.CoberturaXMLDTO.forEach(assist => {
        assist.ContratoSeguradoCertificadoEndossoID ??= '';
        assist.Descricao ??= '';
        assist.ValorBen ??= '';
        assist.DataInicioVigencia ??= '';
        assist.ValorBenConjuge ??= '';
        assist.ValorBenFilho ??= '';
        assist.ValorBenPais ??= '';
        assist.ValorBenSogros ??= '';
        assist.ValorPremioIndividual ??= '';

    });

    // ================= DADOS GERAIS =================

    // GERAL 
    certificado.ValorPremioLiquidoTotal ??= '';
    certificado.ValorIOFTotal ??= '';
    certificado.ExibirSAF ??= '';
    certificado.ExibirAFD ??= '';
    certificado.ExibeLogo ??= '';
    certificado.ContratoSeguradoCertificadoEndossoID ??= '';
    certificado.TipoContratoPrestamista ??= '';
    certificado.DataEnvio ??= '';
    certificado.TextoAssistenciasContratadas ??= '';
    certificado.Prestamista ??= '';
    certificado.VgCotado ??= '';

    // SEGURADO
    certificado.NomeSegurado ??= '';
    certificado.CPFSegurado ??= '';
    certificado.NumeroContrato ??= '';
    certificado.Certificado ??= '';
    certificado.NumeroApolice ??= '';
    certificado.PEP ??= '';
    certificado.DataNascimentoSegurado ??= '';
    certificado.CapitalSeguradoIndividualMaximo ??= '';
    certificado.NumeroSegurados ??= '';

    // ESTIPULANTE
    certificado.NomeEstipulante ??= '';
    certificado.NumeroLogradouroEstipulante ??= '';
    certificado.CNPJEstip ??= '';
    certificado.EnderecoEstipulante ??= '';
    certificado.CidadeEstipulante ??= '';
    certificado.BairroEstipulante ??= '';
    certificado.UFEstipulante ??= '';
    certificado.CEPEstipulante ??= '';
    certificado.TextoDocEstip ??= '';
    certificado.LogradouroEstipulante ??= '';

    // SUBESTIPULANTE
    certificado.NomeSub ??= '';
    certificado.CNPJSub ??= '';
    certificado.NumeroSub ??= '';
    certificado.TextoDocSub ??= '';

    //EMPRESA
    certificado.NomeEmpresa ??= '';
    certificado.CNPJEmpresa ??= '';

    // ENDEREÇO
    certificado.Endereco ??= '';
    certificado.Bairro ??= '';
    certificado.Cidade ??= '';
    certificado.UF ??= '';
    certificado.CEP ??= '';

    //Logradouro
    certificado.Logradouro ??= '';
    certificado.NumeroLogradouro ??= '';
    certificado.ComplementoLogradouro ??= '';

    // DADOS SORTEIO
    certificado.IsSorteio ??= '';
    certificado.SeguradoraSorteio ??= '';
    certificado.CNPJSorteio ??= '';
    certificado.QtdeSorteioMes ??= '';
    certificado.ValorSorteio ??= '';
    certificado.NumeroSorte ??= '';
    certificado.InicioVigenciaSorteio ??= '';
    certificado.ProcessoSusepSorteio ??= '';

    // INFORMAÇÕES ADICIONAIS
    certificado.ValorPremioTotal ??= '';
    certificado.UltimaAlteracao ??= '';
    certificado.IndexadorPlano ??= '';
    certificado.VidaGrupoProcessoSusep ??= '';
    certificado.Sucursal ??= '';
    certificado.FormaPagamento ??= '';

    // DADOS VIGÊNCIA
    certificado.PeriodicidadePagamento ??= '';
    certificado.InicioVigencia ??= '';
    certificado.TerminoVigencia ??= '';

}

function montarFranquias(certificado) {
    const detalhes = certificado.FranquiasCarencias.DetalheFranquiaCarencia || [];

    detalhes.forEach(item => {
        const nome = item.NomeCobertura || '';
        const franquia = item.FranquiaCarencia?.Franquias?.Franquia;

        if (franquia?.Tempo || franquia?.TempoEm) {
            certificado.FranquiasValidas.push({
                NomeCobertura: nome,
                Tempo: franquia.Tempo,
                TempoEm: franquia.TempoEm
            });
        }
    });
}

function temValorUtil(obj) {
    return Object.entries(obj || {}).some(([_, valor]) => {
        if (Array.isArray(valor)) return valor.length > 0;
        if (typeof valor === 'object' && valor !== null) return temValorUtil(valor);
        return String(valor).trim() !== '';
    });
}

//Verificar se existe carência para inserir o bloco de texto fixo
function existeCarencia() {

    const raiz = data?.CertificadoGlobalXMLDTO?.FranquiasCarencias;
    if (!raiz) return false;

    const detalhes = raiz?.DetalheFranquiaCarencia;
    if (!detalhes) return false;

    const lista = Array.isArray(detalhes) ? detalhes : [detalhes];

    if (lista.length === 0) return false;


    return lista.some(detalhe => {

        const fc = detalhe?.FranquiaCarencia;
        if (!fc) return false;

        return Boolean(
            fc.CarenciasProgressivas?.CarenciaProgressiva ||
            fc.CarenciasEmPeriodosDefinidos?.CarenciaEmPeriodoDefinido ||
            fc.CarenciasPorCausas?.CarenciaPorCausa ||
            fc.CarenciasPorSuicidios?.CarenciaPorSuicidio
        );
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

function GerenciarEstruturasCircular642(seletor) {
    const certificado = data.CertificadoGlobalXMLDTO || {};

    const campos = [
        certificado.EnderecoEstipulante,
        certificado.CidadeEstipulante,
        certificado.UFEstipulante,
        certificado.CEPEstipulante
    ];

    // Detecta se TODOS estão vazios
    const todosVazios = campos.every(c =>
        !c || String(c).trim() === ""
    );

    // Seleciona o bloco
    const el = document.querySelector(seletor);
    if (!el) return;

    if (todosVazios) {
        // Nenhum campo → bloco some
        el.style.display = 'none';
        return;
    }

    mostrarElementoEReaplicarBindEReposicionar(seletor);
}

function verificarExistenciaAssistencias() {
    const certificado = data.CertificadoGlobalXMLDTO || {};
    const assistEmp = certificado.AssistenciasEmpresa;
    const assistFunc = certificado.AssistenciasFuncionario;

    // função auxiliar pra validar se existe algum objeto com ContratoSeguradoCertificadoEndossoID preenchido
    const existeAssistenciaValida = (assist) => {
        if (!assist) return false;

        const lista = Array.isArray(assist) ? assist : assist.CoberturaXMLDTO ? assist.CoberturaXMLDTO : [assist];

        const coberturas = Array.isArray(lista)
            ? lista.flatMap(item => item?.CoberturaXMLDTO || item)
            : [];

        return coberturas.some(item => {
            const id = item?.ContratoSeguradoCertificadoEndossoID;
            return typeof id === 'string' && id.trim() !== '';
        });
    };

    const existeAssistEmpresa = existeAssistenciaValida(assistEmp);
    const existeAssistFuncionario = existeAssistenciaValida(assistFunc);

    return { existeAssistEmpresa, existeAssistFuncionario };
}

function GerenciarEstruturasPremio() {
    const cert = data.CertificadoGlobalXMLDTO || {};

    const campos = [
        cert.ValorPremioLiquidoTotal,
        cert.ValorIOFTotal,
        cert.ValorPremioTotal
    ];

    // Verifica se TODOS têm valor útil
    const todosPreenchidos = campos.every(
        c => typeof c === "string" && c.trim() !== ""
    );

    const el = document.querySelector('.linha-footer');
    if (!el) return;

    if (!todosPreenchidos) {
        el.style.display = 'none';
    }
}

function dadosDoCorretorSaoValidos() {
    const corretor = data.CertificadoGlobalXMLDTO?.Corretor;

    if (!corretor) return false;

    const camposObrigatorios = ["Nome", "Registro", "Documento", "EnderecoCorretor"];

    return camposObrigatorios.every(campo => {
        const valor = corretor[campo];
        return typeof valor === "string" && valor.trim() !== "";
    });
}

function GerenciarAssistenciasFuncionario() {
    const certificado = data.CertificadoGlobalXMLDTO || {};
    const assistFunc = certificado.AssistenciasFuncionario;

    // Se não existir, não renderiza
    if (!assistFunc) return false;

    // Garante array no padrão já usado no inicializador
    const lista = Array.isArray(assistFunc.CoberturaXMLDTO)
        ? assistFunc.CoberturaXMLDTO
        : assistFunc.CoberturaXMLDTO
            ? [assistFunc.CoberturaXMLDTO]
            : [];

    if (lista.length === 0) return false;

    const existeValida = lista.some(item => {
        if (!item) return false;

        // Se qualquer valor existir, considera como válido
        const id = item.ContratoSeguradoCertificadoEndossoID;
        return id && typeof id === "string" && id.trim() !== "";
    });

    return existeValida;
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

// CARÊNCIA PROGRESSIVA (parcelas)
function extrairCarenciaProgressivaParcelas(certificado) {

    const resultado = [];
    const detalhes = certificado?.FranquiasCarencias?.DetalheFranquiaCarencia || [];

    detalhes.forEach(det => {

        const nomeCob = det?.NomeCobertura?.trim();
        const raiz = det?.FranquiaCarencia?.CarenciasProgressivas;

        if (!raiz) return;

        const lista = garantirArray(raiz?.CarenciaProgressiva);
        if (!lista.length) return;

        // filtra apenas progressiva por parcelas
        const filtrados = lista.filter(p => {
            return normalizarTexto(p?.PeriodoEm) === "PARCELAS";
        });

        if (!filtrados.length) return;

        // validação mínima de campos
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
                Periodo:
                    `De ${inicial} até ${final} parcela(s)`,
                Percentual:
                    `${String(perc).replace(".", ",")}%`
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

//CARÊNCIA PROGRESSIVA (meses)
function extrairCarenciaProgressivaMeses(certificado) {
    const resultado = [];
    const detalhes = certificado?.FranquiasCarencias?.DetalheFranquiaCarencia || [];

    detalhes.forEach(det => {
        const nomeCob = det?.NomeCobertura?.trim();
        const raiz = det?.FranquiaCarencia?.CarenciasProgressivas;

        if (!raiz || !nomeCob) return;

        // normaliza CarenciaProgressiva para array
        const lista = garantirArray(raiz?.CarenciaProgressiva);
        if (!lista.length) return;

        // filtra somente progressivas EM MESES com 4 campos válidos
        const validos = lista.filter(p =>
            normalizarTexto(p?.PeriodoEm) === "MESES" &&
            isValorUtil(p?.Inicio) &&
            isValorUtil(p?.Termino) &&
            isValorUtil(p?.PercentualCapitalSegurado)
        );

        if (!validos.length) return;

        // texto igual ao back, usando NomeCobertura no lugar do {0}
        const texto =
            `Para o(s) plano(s) ${nomeCob} quando não preenchida DPS, ` +
            `será adotado um período de carência em que o(s) beneficiário(s) fazem jus ` +
            `a um percentual do capital segurado, da seguinte forma:`;

        // tabela
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

function normalizarTexto(texto) {
    return (texto || '')
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .toUpperCase();
}

// CARÊNCIA DENIFIDA (meses - SAF)
function extrairCarenciaDefinidaMesesSAF(certificado) {
    const resultado = [];
    const detalhes = certificado?.FranquiasCarencias?.DetalheFranquiaCarencia || [];

    detalhes.forEach(d => {
        const nome = d.NomeCobertura;
        const carencia = d.FranquiaCarencia?.CarenciasEmPeriodosDefinidos?.CarenciaEmPeriodoDefinido;

        if (!carencia || carencia.TempoEm?.toLowerCase() !== 'meses') return;

        const isSAF = normalizarTexto(nome).includes('SAF');
        if (!isSAF) return;

        resultado.push({
            Tipo: 'CARENCIA_DEFINIDA_MESES_SAF',
            Texto: `Para o plano/cobertura ${nome} haverá carência de ${carencia.Tempo} mês(es) para segurados a partir de 65 anos ou quando não houver o preenchimento de DPS (Declaração Pessoal de Saúde). Esta carência é aplicável somente ao titular do seguro.`
        });
    });

    return resultado;
}

//CARÊNCIA DENIFIDA (MESES)
function extrairCarenciaDefinidaMeses(certificado) {
    const resultado = [];
    const detalhes = certificado?.FranquiasCarencias?.DetalheFranquiaCarencia || [];

    detalhes.forEach(detalhe => {
        const nome = detalhe.NomeCobertura;
        const carencia = detalhe.FranquiaCarencia?.CarenciasEmPeriodosDefinidos?.CarenciaEmPeriodoDefinido;

        if (!carencia) return;

        if (carencia.TempoEm?.toLowerCase() === 'meses') {
            resultado.push({
                Tipo: 'CARENCIA_DEFINIDA_MESES',
                Texto: `Para o(s) plano(s)/cobertura(s) ${nome} haverá carência de ${carencia.Tempo} mes(es).`
            });
        }
    });

    return resultado;
}


// CARÊNCIA DEFINIDA (dias)
function extrairCarenciaDefinidaDias(certificado) {
    const resultado = [];
    const detalhes = certificado?.FranquiasCarencias?.DetalheFranquiaCarencia || [];

    detalhes.forEach(d => {
        const nome = d?.NomeCobertura || '';
        const carencia = d?.FranquiaCarencia
            ?.CarenciasEmPeriodosDefinidos
            ?.CarenciaEmPeriodoDefinido;


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
function extrairCarenciaDefinidaParcelas(certificado) {
    const resultado = [];
    const detalhes = certificado?.FranquiasCarencias?.DetalheFranquiaCarencia || [];

    detalhes.forEach(d => {
        const nome = d?.NomeCobertura || '';
        const carencia = d?.FranquiaCarencia
            ?.CarenciasEmPeriodosDefinidos
            ?.CarenciaEmPeriodoDefinido;


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

//CARÊNCIA POR (Causa)
function extrairCarenciaPorCausas(certificado) {
    const resultado = [];
    const detalhes = certificado?.FranquiasCarencias?.DetalheFranquiaCarencia || [];

    detalhes.forEach(d => {
        const nome = d?.NomeCobertura || '';
        const carencia = d?.FranquiaCarencia
            ?.CarenciasPorCausas
            ?.CarenciaPorCausa;


        if (!carencia) return;

        const causa = carencia.Causa;
        const tempo = carencia.Tempo;
        const tempoEm = carencia.TempoEm;

        if (
            !isValorUtil(causa)
        ) {
            return;
        }

        resultado.push({
            Tipo: 'CARENCIA_POR_CAUSAS',
            Texto: `Para o(s) plano(s)/cobertura(s) ${nome}, haverá carência de ${tempo} ${tempoEm.toLowerCase()} para a seguinte causa: ${causa}.`
        });
    });

    return resultado;
}

function extrairTodasCarencias(certificado) {
    return [
        ...extrairCarenciaDefinidaMesesSAF(certificado),
        ...extrairCarenciaDefinidaMeses(certificado),
        ...extrairCarenciaDefinidaParcelas(certificado),
        ...extrairCarenciaDefinidaDias(certificado),
        ...extrairCarenciaPorCausas(certificado)
    ];
}

function extrairCarenciasProgressivas(certificado) {
    return [
        ...extrairCarenciaProgressivaParcelas(certificado)
    ];
}

function extrairCarenciasProgressivasPorMes(certificado) {
    return [
        ...extrairCarenciaProgressivaMeses(certificado)
    ];
}


iniciarRenderizacaoSequencialSincrono();

function iniciarRenderizacaoSequencialSincrono() {

    inicializarCamposParaBindings()

    const certificado = data.CertificadoGlobalXMLDTO || {};

    certificado.TextosCarencias = ko.computed(() => {
        return extrairTodasCarencias(certificado);
    });

    certificado.TextosCarenciasProgressivas = ko.computed(() => {
        return extrairCarenciasProgressivas(certificado);
    });

    certificado.TextosCarenciasProgressivasMeses = ko.computed(() => {
        return extrairCarenciasProgressivasPorMes(certificado);
    });

    montarFranquias(certificado)

    formatarTextoData(data)

    GerenciarEstruturasPremio()

    const corretor = data.CertificadoGlobalXMLDTO?.Corretor;

    const cobertura = data.CertificadoGlobalXMLDTO?.Coberturas?.CoberturaXMLDTO;

    const { existeAssistEmpresa, existeAssistFuncionario } = verificarExistenciaAssistencias();


    ko.applyBindings(data);

    RenderizarEstruturaFixa('.page-inicial', 'inicio')

    GerenciarEstruturasCircular642('.dados-certificado');

    if (data.CertificadoGlobalXMLDTO.NumeroContrato) {
        mostrarElementoEReaplicarBindEReposicionar('.tabela-dados-segurado');
    }

    if (data.CertificadoGlobalXMLDTO.Coberturas.CoberturaXMLDTO.length > 0) {
        mostrarElementoEReaplicarBindEReposicionar('.titulo-coberturas');
    }

    if (temValorUtil(cobertura)) {

        quebrarTabelaEntrePaginas(
            'bloco-tabela-coberturas',
            'linha-header',
            'linha-cobertura',
            'linha-footer'
        );
    }

    data.CertificadoGlobalXMLDTO?.ExibirAFD === "true" &&
        mostrarElementoEReaplicarBindEReposicionar('.bloco-dados-afd');

    data.CertificadoGlobalXMLDTO?.ExibirSAF === "true" &&
        mostrarElementoEReaplicarBindEReposicionar('.bloco-texto-saf');

    if (existeAssistEmpresa || existeAssistFuncionario) {
        mostrarElementoEReaplicarBindEReposicionar('.titulo-servicos-assistenciais');
    }

    if (existeAssistEmpresa) {
        mostrarElementoEReaplicarBindEReposicionar('.bloco-servicos-assistenciais');
    }

    if (existeAssistFuncionario) {
        mostrarElementoEReaplicarBindEReposicionar('.bloco-servicos-assistenciais-funcionario');
    }

    if (GerenciarAssistenciasFuncionario()) {
        mostrarElementoEReaplicarBindEReposicionar('.bloco-sem-servicos-assistenciais');
    }

    mostrarElementoEReaplicarBindEReposicionar('.bloco-informacoes-adicionais');

    mostrarElementoEReaplicarBindEReposicionar('.bloco-container-condicoes-gerais');

    mostrarElementoEReaplicarBindEReposicionar('bloco-texto-apolice');

    if (temValorUtil(corretor)) {
        mostrarElementoEReaplicarBindEReposicionar('.secao-corretor');
    }

    if (temValorUtil(cobertura)) {
        mostrarElementoEReaplicarBindEReposicionar('bloco-texto-fixo-garantia-seguro');
    }

    if (temValorUtil(cobertura)) {
        mostrarElementoEReaplicarBindEReposicionar('secao-garantia-seguro');
    }

    mostrarElementoEReaplicarBindEReposicionar('bloco-risco-excluido');

    mostrarElementoEReaplicarBindEReposicionar('bloco-despesas-salvamento');

    mostrarElementoEReaplicarBindEReposicionar('bloco-cobertos-pelo-seguro');

    if (existeCarencia()) {
        mostrarElementoEReaplicarBindEReposicionar('.bloco-carencia');
    }

    mostrarElementoEReaplicarBindEReposicionar('bloco-texto-explicativo-carencias');

    mostrarElementoEReaplicarBindEReposicionar('texto-carencia-progressiva-parcelas', '0.0in');

    mostrarElementoEReaplicarBindEReposicionar('texto-carencia-progressiva-meses', '0.04in');

    if (existeCarencia()) {
        mostrarElementoEReaplicarBindEReposicionar('texto-suicidio-fixo');
    }

    if (certificado.FranquiasValidas.length > 0) {
        mostrarElementoEReaplicarBindEReposicionar('.bloco-franquia');
    }

    if (certificado.FranquiasValidas.length > 0) {
        mostrarElementoEReaplicarBindEReposicionar('.bloco-texto-explicativo-franquia');
    }

    mostrarElementoEReaplicarBindEReposicionar('conteudo-data');

    mostrarElementoEReaplicarBindEReposicionar('bloco-texto-nome-social');

    mostrarElementoEReaplicarBindEReposicionar('.assinatura-wrapper');

}

function quebrarTabelaEntrePaginas(seletorClasse, seletorHeader, seletorRow, seletorFooter = null, margemEspaco = '0.2in', margemQuebra = '1.1in') {
    const tabelaOriginal = document.querySelector('.' + seletorClasse);
    if (!tabelaOriginal) return;

    const tituloEl = [...tabelaOriginal.querySelectorAll('[class*="titulo"]')][0];
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

function RenderizarEstruturaFixa(seletorElemento, posicao = 'fim') {
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

    if (posicao === 'inicio') {
        const primeira = divsVisiveisBody[0];
        if (primeira && primeira.parentNode === document.body) {
            document.body.insertBefore(elemento, primeira);
        } else {
            document.body.insertBefore(elemento, document.body.firstChild);
        }
    } else {
        const ultima = divsVisiveisBody[divsVisiveisBody.length - 1];
        if (ultima && ultima.parentNode === document.body) {
            document.body.insertBefore(elemento, ultima.nextSibling);
        } else {
            document.body.appendChild(elemento);
        }
    }

    // Força reflow
    elemento.offsetHeight;
}

