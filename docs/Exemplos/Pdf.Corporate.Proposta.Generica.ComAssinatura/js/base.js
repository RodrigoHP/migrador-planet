// ================== Funções Utilitárias ==================
const fmtMoeda = v => typeof v === 'string' ? v : (v ?? '').toString();
const qs = sel => document.querySelector(sel);

function koLista(propriedade) {
    return propriedade instanceof Function ? propriedade : ko.observableArray([propriedade]);
}

// Função para converter valores monetários com vírgula ou ponto
function parseValorMonetario(valor) {
    if (!valor) return 0;
    const valorStr = ko.unwrap(valor).toString();
    // Remove espaços e substitui vírgula por ponto
    return parseFloat(valorStr.replace(/\s/g, '').replace(',', '.')) || 0;
}

// Função para formatar valor monetário
function formatarMoeda(valor) {
    const valorNumerico = parseValorMonetario(valor);
    return 'R$ ' + valorNumerico.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

// Função segura para obter valores opcionais
function getValorSeguro(valor, padrao = '') {
    const val = ko.unwrap(valor);
    return (val !== null && val !== undefined && val !== '') ? val : padrao;
}

function getCampoDocumento(documento, campo, padrao = 'Não Informado') {
    try {
        const doc = ko.unwrap(documento);
        if (!doc || typeof doc !== 'object') return padrao;
        const valor = ko.unwrap(doc[campo]);
        return (valor !== null && valor !== undefined && valor !== '') ? valor : padrao;
    } catch (e) {
        return padrao;
    }
}

// Função para processar OBS_RESPOSTA da DPS
function processarObsResposta(obsResposta) {
    const obs = ko.unwrap(obsResposta);
    if (!obs || obs === '') return null;

    // Verifica se contém o separador "#"
    if (obs.indexOf('#') === -1) {
        return { temSeparador: false, textoCompleto: obs };
    }

    // Divide pelo "#"
    const partes = obs.split('#');
    const pergunta = partes[0].trim();
    let resposta = partes.slice(1).join('#').trim(); // Junta caso tenha mais de um "#"

    // Remove ".&amp;", "&amp;" e "&" do final
    resposta = resposta.replace(/\.&amp;$/g, '').replace(/&amp;$/g, '').replace(/\.&$/g, '').replace(/&$/g, '');

    return {
        temSeparador: true,
        pergunta: pergunta,
        resposta: resposta
    };
}

async function carregarExemploJSON() {
    try {
        const response = await fetch('./js/exemplo2.json');
        if (!response.ok)
            throw new Error('Erro ao carregar o JSON');

        const json = await response.json();
        console.log('JSON carregado com sucesso:', json);
        return json;

    } catch (err) {
        console.error('Erro ao carregar JSON:', err);
    }
}




