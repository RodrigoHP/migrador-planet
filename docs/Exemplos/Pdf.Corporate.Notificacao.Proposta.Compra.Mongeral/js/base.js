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
let alturaMaximaGlobalTexto = 1060;


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

function formatarParaArray(obj, key) {
    if (obj && obj[key] && !Array.isArray(obj[key])) {
        obj[key] = [obj[key]];
    }
}

function inicializarCamposParaBindings() {
    const proposta = data.PROPOSTA;

    const garantirArray = (campo) => {
        if (Array.isArray(campo)) return campo.filter(e => Object.keys(e || {}).length > 0);
        if (campo && typeof campo === 'object' && Object.keys(campo).length > 0) return [campo];
        return [];
    };

    // ================= DADOS_PROPONENTE =================
    proposta.PROPONENTES ??= {};
    proposta.PROPONENTES.PROPONENTE = garantirArray(proposta.PROPONENTES.PROPONENTE);

    proposta.PROPONENTES.PROPONENTE.forEach(proponente => {

        // ================= CAMPOS BÁSICOS =================
        proponente.TIPOPROPONENTEID ??= '';
        proponente.MATRICULA ??= '';
        proponente.NOME ??= '';
        proponente.NOME_CIVIL ??= '';
        proponente.DT_NASCIMENTO ??= '';
        proponente.IDADE ??= '';
        proponente.SEXO ??= '';
        proponente.ESTADO_CIVIL ??= '';
        proponente.CPF ??= '';
        proponente.TITULAR_CPF ??= '';
        proponente.RECEBE_INFO_EMAIL ??= '';
        proponente.EMAIL ??= '';
        proponente.RESIDE_BRASIL ??= '';
        proponente.RENDA_MENSAL ??= '';
        proponente.NUM_FILHOS ??= '';
        proponente.PPE ??= '';

        // ================= CAMPOS ADICIONAIS (QUE FALTAVAM PARA EVITAR ERROR DE BIND) =================
        proponente.RG ??= '';
        proponente.NATURALIDADE ??= '';
        proponente.NACIONALIDADE ??= '';
        proponente.CELULAR ??= '';
        proponente.TELEFONE ??= '';
        proponente.OCUPACAO ??= '';
        proponente.EMPRESA_TRABALHO ??= '';

        // ================= DOCUMENTOS =================
        proponente.DOCUMENTOS ??= {};
        proponente.DOCUMENTOS.DOCUMENTO = garantirArray(proponente.DOCUMENTOS.DOCUMENTO);

        proponente.DOCUMENTOS.DOCUMENTO.forEach(doc => {
            doc.NATUREZA_DOC ??= '';
            doc.DOCUMENTO ??= '';
            doc.ORGAO_EXPEDIDOR ??= '';
            doc.DATA_EXPEDICAO ??= '';
            doc.UF ??= '';
        });

        // ================= TELEFONES =================
        proponente.TELEFONES ??= {};
        proponente.TELEFONES.TELEFONE = garantirArray(proponente.TELEFONES.TELEFONE);

        proponente.TELEFONES.TELEFONE.forEach(tel => {
            tel.TIPO ??= '';
            tel.DDD ??= '';
            tel.NUMERO ??= '';
        });

        // ================= ENDERECOS =================
        proponente.ENDERECOS ??= {};
        proponente.ENDERECOS.ENDERECO = garantirArray(proponente.ENDERECOS.ENDERECO);

        proponente.ENDERECOS.ENDERECO.forEach(end => {
            end.TP_CORRESPONDENCIA ??= '';
            end.TIPO ??= '';
            end.LOGRADOURO ??= '';
            end.NUMERO ??= '';
            end.COMPLEMENTO ??= '';
            end.BAIRRO ??= '';
            end.CIDADE ??= '';
            end.ESTADO ??= '';
            end.CEP ??= '';
            end.PAIS ??= '';
        });

        // ================= DADOS BANCÁRIOS (SE EXISTIR) =================
        proponente.DADOS_BANCARIOS ??= {};
        proponente.DADOS_BANCARIOS.BANCO ??= '';
        proponente.DADOS_BANCARIOS.AGENCIA ??= '';
        proponente.DADOS_BANCARIOS.CONTA ??= '';
        proponente.DADOS_BANCARIOS.TIPO_CONTA ??= '';
        proponente.DADOS_BANCARIOS.NUM_INST_FIN ??= '';
        proponente.DADOS_BANCARIOS.INSTITUICAO_FINANCEIRA ??= '';
        proponente.DADOS_BANCARIOS.NUM_AGENCIA ??= '';
        proponente.DADOS_BANCARIOS.NUM_CONTA_CORRENTE ??= '';
        proponente.DADOS_BANCARIOS.CODIGO_OPERACAO ??= '';
        proponente.DADOS_BANCARIOS.A_PARTIR_DE ??= '';
        proponente.DADOS_BANCARIOS.NOME_TITULAR_CONTA ??= '';
        proponente.DADOS_BANCARIOS.CPF_TITULAR_CONTA ??= '';

    });

    // ================= INSTITUIDOR =================
    proposta.INSTITUIDOR ??= {};
    proposta.INSTITUIDOR.NUMERO ??= '';
    proposta.INSTITUIDOR.NOME ??= '';

    // ================= PLANOS =================
    proposta.PROPONENTES.PROPONENTE.forEach(proponente => {
        proponente.PLANOS.PLANO = garantirArray(proponente.PLANOS.PLANO);
        proponente.PLANOS.PLANO.forEach(plano => {
            plano.CODIGO ??= '';
            plano.NOME ??= '';
            plano.VL_AP_INICIAL ??= '';
            plano.VL_PORTAB ??= '';
            plano.TP_TRIBUTACAO ??= '';
            plano.DT_CONCESSAO ??= '';
            plano.PRAZO_CERTO ??= '';
            plano.PRAZO_DECRESCIMO ??= '';
            plano.FUNDOS ??= '';
            plano.COBERTURAS ??= {};
            plano.COBERTURAS.COBERTURA = garantirArray(plano.COBERTURAS.COBERTURA);
            plano.COBERTURAS.COBERTURA.forEach(cobertura => {
                cobertura.CODIGO ??= '';
                cobertura.NOME ??= '';
                cobertura.VL_CONTRIB ??= '';
                cobertura.VL_COBERTURA ??= '';
                cobertura.CLASSE_RISCO ??= '';
            });
        });
    });

    // ================= RECIBO_PRIM_PAGTO =================
    data.PROPOSTA = data.PROPOSTA || {};
    data.PROPOSTA.RECIBO_PRIM_PAGTO = data.PROPOSTA.RECIBO_PRIM_PAGTO || {};
    const pag = data.PROPOSTA.RECIBO_PRIM_PAGTO;

    pag.TP_PAGAMENTO ??= '';
    pag.VALOR ??= '';
    pag.NM_PAGADOR ??= '';
    pag.CPF_PAGADOR ??= '';
    pag.CHEQUE ??= '';
    pag.CARTAO_CREDITO ??= '';

    // ================= DADOS_COBRANCA =================
    proposta.PROPONENTES.PROPONENTE.forEach(proponente => {
        proponente.DADOS_COBRANCA ??= {};
        proponente.DADOS_COBRANCA.PERIODICIDADE ??= '';
        proponente.DADOS_COBRANCA.TIPO_COBRANCA ??= '';
        proponente.DADOS_COBRANCA.DIA_VENCIMENTO ??= '';
        proponente.DADOS_COBRANCA.COMP_DEBITO ??= '';
        proponente.DADOS_COBRANCA.NUM_CONVENIO ??= '';
        proponente.DADOS_COBRANCA.IDADE_PAGAMENTO_ANTECIPADO ??= '';
        proponente.DADOS_COBRANCA.TEMPO_PAGAMENTO_ANTECIPADO ??= '';
        proponente.DADOS_COBRANCA.DEBITO ??= '';
        proponente.DADOS_COBRANCA.FOLHA ??= '';
        proponente.DADOS_COBRANCA.CARTAO ??= '';
    });

    // ================= USO_MONGERAL =================
    proposta.USO_MONGERAL = proposta.USO_MONGERAL || {};
    proposta.USO_MONGERAL.CONV_ADESAO ??= '';
    proposta.USO_MONGERAL.ACAO_MARKETING ??= '';
    proposta.USO_MONGERAL.ALTERNATIVA ??= '';
    proposta.USO_MONGERAL.SUCURSAL ??= '';
    proposta.USO_MONGERAL.MODELO_PROPOSTA ??= '';
    proposta.USO_MONGERAL.MODELO_PROPOSTA_GED ??= '';
    proposta.USO_MONGERAL.TIPO_COMISSAO ??= '';
    proposta.USO_MONGERAL.DIR_REGIONAL ??= '';
    proposta.USO_MONGERAL.GER_SUCURSAL ??= '';
    proposta.USO_MONGERAL.GER_COMERCIAL ??= '';
    proposta.USO_MONGERAL.AGENTE ??= '';
    proposta.USO_MONGERAL.CORRETOR1 ??= '';
    proposta.USO_MONGERAL.CORRETOR2 ??= '';
    proposta.USO_MONGERAL.AGENTE_FIDELIZACAO ??= '';

    // ================= BENEFICIARIOS =================
    proposta.BENEFICIARIOS = proposta.BENEFICIARIOS || {};
    proposta.BENEFICIARIOS.BENEFICIARIO = garantirArray(proposta.BENEFICIARIOS.BENEFICIARIO);

    proposta.BENEFICIARIOS.BENEFICIARIO.forEach(beneficiario => {
        beneficiario.CD_PLANO ??= '';
        beneficiario.NOME ??= '';
        beneficiario.NASCIMENTO ??= '';
        beneficiario.PARENTESCO ??= '';
        beneficiario.PARTICIPACAO ??= '';
    });

    // ================= USO_CORRETOR =================
    proposta.USO_CORRETOR ??= {};
    proposta.USO_CORRETOR.NOME ??= '';
    proposta.USO_CORRETOR.CD_SUSEP ??= '';

    // ================= LINK_DOWNLOAD_PROPOSTA =================
    proposta.LINK_DOWNLOAD_PROPOSTA ??= '';

    // ================= FORMULARIOS.FORMULARIO =================
    proposta.PROPONENTES.PROPONENTE.forEach(proponente => {
        proponente.DECLARACOES = proponente.DECLARACOES || {};
        proponente.DECLARACOES.FORMULARIOS = proponente.DECLARACOES.FORMULARIOS || {};
        proponente.DECLARACOES.FORMULARIOS.FORMULARIO = garantirArray(proponente.DECLARACOES.FORMULARIOS.FORMULARIO);

        proponente.DECLARACOES.FORMULARIOS.FORMULARIO.forEach(formulario => {
            formulario.NOME ??= '';
            formulario.CODIGO ??= '';
            formulario.PERGUNTAS = formulario.PERGUNTAS || {};
            formulario.PERGUNTAS.PERGUNTA = garantirArray(formulario.PERGUNTAS.PERGUNTA);

            formulario.PERGUNTAS.PERGUNTA.forEach(pergunta => {
                pergunta.NUMERO ??= '';
                pergunta.QUESTAO ??= '';
                pergunta.RESPOSTA ??= '';
                pergunta.OBS_RESPOSTA ??= '';
            });
        });

        // ================= ENTREVISTAS =================
        proponente.DECLARACOES.ENTREVISTAS = proponente.DECLARACOES.ENTREVISTAS || {};
        proponente.DECLARACOES.ENTREVISTAS.ENTREVISTA = garantirArray(proponente.DECLARACOES.ENTREVISTAS.ENTREVISTA);

        proponente.DECLARACOES.ENTREVISTAS.ENTREVISTA.forEach(entrevista => {
            entrevista.TITULO ??= '';
            entrevista.GRUPOS_PERGUNTAS = entrevista.GRUPOS_PERGUNTAS || {};
            entrevista.GRUPOS_PERGUNTAS.GRUPO_PERGUNTA = garantirArray(entrevista.GRUPOS_PERGUNTAS.GRUPO_PERGUNTA);

            entrevista.GRUPOS_PERGUNTAS.GRUPO_PERGUNTA.forEach(grupo => {
                grupo.TITULO ??= '';
                grupo.PERGUNTAS = grupo.PERGUNTAS || {};
                grupo.PERGUNTAS.PERGUNTA = garantirArray(grupo.PERGUNTAS.PERGUNTA);

                grupo.PERGUNTAS.PERGUNTA.forEach(pergunta => {
                    pergunta.ID ??= '';
                    pergunta.DESCRICAO ??= '';
                    pergunta.RESPOSTA ??= '';
                    pergunta.GRUPOS_PERGUNTAS = pergunta.GRUPOS_PERGUNTAS || {};

                    // Processa sub-perguntas aninhadas
                    if (pergunta.GRUPOS_PERGUNTAS && typeof pergunta.GRUPOS_PERGUNTAS === 'object' && !Array.isArray(pergunta.GRUPOS_PERGUNTAS)) {
                        pergunta.GRUPOS_PERGUNTAS.GRUPO_PERGUNTA = garantirArray(pergunta.GRUPOS_PERGUNTAS.GRUPO_PERGUNTA);

                        pergunta.GRUPOS_PERGUNTAS.GRUPO_PERGUNTA.forEach(subGrupo => {
                            subGrupo.TITULO ??= '';
                            subGrupo.PERGUNTAS = subGrupo.PERGUNTAS || {};
                            subGrupo.PERGUNTAS.PERGUNTA = garantirArray(subGrupo.PERGUNTAS.PERGUNTA);

                            subGrupo.PERGUNTAS.PERGUNTA.forEach(subPergunta => {
                                subPergunta.ID ??= '';
                                subPergunta.DESCRICAO ??= '';
                                subPergunta.RESPOSTA ??= '';
                            });
                        });
                    }
                });
            });
        });
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

    const todosBlocos = container.querySelectorAll('[data-display-original], div');
    todosBlocos.forEach(bloco => {
        bloco.style.display = 'none';
    });

    const spansComBind = container.querySelectorAll('span[data-bind^="text:"]');

    spansComBind.forEach(span => {
        const valor = span.textContent?.trim();

        if (valor) {
            let pai = span.parentElement;
            while (pai && pai !== container) {
                if (pai.tagName === 'DIV') {
                    const displayOriginal = pai.getAttribute('data-display-original') || 'block';
                    pai.style.display = displayOriginal;
                }
                pai = pai.parentElement;
            }
        }

    });

    const existeAlgumVisivel = Array.from(container.querySelectorAll('div')).some(div => div.style.display !== 'none');
    container.style.display = existeAlgumVisivel ? 'flex' : 'none';
}

function existeRepeticaoRenderizada(seletorItem) {
    const seletor = seletorItem.startsWith('.') ? seletorItem : '.' + seletorItem;

    const itens = document.querySelectorAll(seletor);
    return itens.length > 0;
}

function criarBlocoTextoSimples() {
    const bloco = document.createElement('div');
    bloco.className = "texto-long-block";
    return bloco;
}

iniciarRenderizacaoSequencialSincrono();

function iniciarRenderizacaoSequencialSincrono() {
    inicializarCamposParaBindings()

    ko.applyBindings(data);

    RenderizarEstruturaFixa('.page-inicial', 'inicio')

    if (document.querySelector('.plano-container') &&
        document.querySelector('.plano-container').querySelectorAll('.plano-item-wrapper').length > 0) {
        quebrarPlanosEntrePaginas();
    } else {
        mostrarElementoEReaplicarBindEReposicionar('plano-container');
    }

    if (
        existeRepeticaoRenderizada('linha-beneficiarios') &&
        data.PROPOSTA.BENEFICIARIOS.BENEFICIARIO.length > 0
    ) {
        quebrarTabelaEntrePaginas(
            'bloco-tabela-beneficiarios',
            'linha-beneficiarios header',
            'linha-beneficiarios'
        );
    }

    mostrarElementoEReaplicarBindEReposicionar('container-dados-pagamento');
    mostrarElementoEReaplicarBindEReposicionar('assinatura-wrapper');
    mostrarElementoEReaplicarBindEReposicionar('textos-conteudo-forma-pagamento');

    if (
        existeRepeticaoRenderizada('linha-historico') &&
        data.PROPOSTA.PROPONENTES.PROPONENTE.length > 0
    ) {
        quebrarTabelaEntrePaginas(
            'bloco-tabela-historico',
            'linha-historico header',
            'linha-historico'
        );
    }

    if (
        existeRepeticaoRenderizada('container-entrevista-pergunta') &&
        data.PROPOSTA.PROPONENTES.PROPONENTE.length > 0
    ) {
        quebrarEntrevistasEntrePaginas();
    }

    mostrarElementoEReaplicarBindEReposicionar('container-aceitacao-seguro');
    mostrarElementoEReaplicarBindEReposicionar('secao-corretor');
    mostrarElementoEReaplicarBindEReposicionar('texto-conteudo-declaracao-fixo');
    mostrarElementoEReaplicarBindEReposicionar('texto-conteudo-beneficios-fixo', '0.0in');
    mostrarElementoEReaplicarBindEReposicionar('texto-conteudo-beneficio-2', '0.0in');
    mostrarElementoEReaplicarBindEReposicionar('texto-conteudo-beneficio-3', '0.0in');
    mostrarElementoEReaplicarBindEReposicionar('conteudo-carencia', '0.0in');
    mostrarElementoEReaplicarBindEReposicionar('conteudo-carencia-2', '0.0in');
    mostrarElementoEReaplicarBindEReposicionar('conteudo-vidaInteira');
    mostrarElementoEReaplicarBindEReposicionar('conteudo-atualizacao-monetaria');
    mostrarElementoEReaplicarBindEReposicionar('conteudo-carregamento');
    mostrarElementoEReaplicarBindEReposicionar('conteudo-tributacao');
    mostrarElementoEReaplicarBindEReposicionar('conteudo-vigencia');
    mostrarElementoEReaplicarBindEReposicionar('conteudo-apoliceEstipulante');
    mostrarElementoEReaplicarBindEReposicionar('conteudo-processoSUSEP', '0.2in');
    mostrarElementoEReaplicarBindEReposicionar('conteudo-investimento');
    mostrarElementoEReaplicarBindEReposicionar('conteudo-informacoes-gerais');
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

        const blocoTeste = criarBlocoTabela(margem, titulo, usarHeader ? header : null, seletorClasse);
        blocoTeste.appendChild(linha.cloneNode(true));
        const alturaEstimativa = alturaProspectiva(contentAtual, blocoTeste);

        if (alturaEstimativa > alturaMaximaGlobal) {
            contentAtual = criarNovaPagina();
            continue;
        } else {

        }

        blocoAtual = criarBlocoTabela(margem, titulo, usarHeader ? header : null, seletorClasse);
        blocoAtual.appendChild(linhasRestantes.shift());
        contentAtual.appendChild(blocoAtual);

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

function quebrarPlanosEntrePaginas() {
    const containerOriginal = document.querySelector('.plano-container');
    if (!containerOriginal) return;

    const titulo = containerOriginal.querySelector('.plano-tabela-titulo');
    const itensPlano = Array.from(containerOriginal.querySelectorAll('.plano-item-wrapper'));

    if (itensPlano.length === 0) {
        containerOriginal.style.display = 'none';
        return;
    }

    containerOriginal.remove();

    let paginas = Array.from(document.querySelectorAll('.page'));
    let contentAtual = paginas.length > 0 ? paginas[paginas.length - 1].querySelector('.content') : criarNovaPagina();
    let blocoAtual = null;
    let tituloAdicionado = false;

    // Calcula altura da logo para considerar no espaço disponível
    const logoHeight = 0.9;
    const logoHeightPx = logoHeight * 96;

    itensPlano.forEach((itemPlano) => {

        const existePlanoNaPagina = contentAtual.querySelector('.plano-container') !== null;
        const margem = existePlanoNaPagina ? '0.2in' : '1.1in';

        // Calcula altura disponível considerando a logo no topo
        let alturaDisponivel = alturaMaximaGlobal;
        if (!existePlanoNaPagina) {
            // Se é o primeiro elemento da página, precisa considerar a logo
            alturaDisponivel = alturaMaximaGlobal - logoHeightPx;
        }

        const blocoTeste = document.createElement('div');
        blocoTeste.className = 'plano-container';
        blocoTeste.style.width = '7.48in';
        blocoTeste.style.marginTop = margem;
        blocoTeste.style.display = 'flex';
        blocoTeste.style.flexDirection = 'column';

        if (!tituloAdicionado && titulo) {
            const tituloClone = titulo.cloneNode(true);
            blocoTeste.appendChild(tituloClone);
        }
        blocoTeste.appendChild(itemPlano.cloneNode(true));

        const alturaEstimativa = alturaProspectiva(contentAtual, blocoTeste);

        if (alturaEstimativa > alturaDisponivel) {
            // Não cabe, cria nova página
            contentAtual = criarNovaPagina();
            paginas = Array.from(document.querySelectorAll('.page'));
            blocoAtual = null;
            tituloAdicionado = false;
            alturaDisponivel = alturaMaximaGlobal - logoHeightPx;
        }

        if (!blocoAtual) {
            const temBlocosNaPagina = contentAtual.querySelector('.plano-container') !== null;
            blocoAtual = document.createElement('div');
            blocoAtual.className = 'plano-container';
            blocoAtual.style.width = '7.48in';
            blocoAtual.style.marginTop = temBlocosNaPagina ? '0.2in' : '1.1in';
            blocoAtual.style.display = 'flex';
            blocoAtual.style.flexDirection = 'column';
            contentAtual.appendChild(blocoAtual);

            if (titulo && !tituloAdicionado) {
                const tituloClone = titulo.cloneNode(true);
                blocoAtual.appendChild(tituloClone);
                tituloAdicionado = true;
            }
        }

        blocoAtual.appendChild(itemPlano);
        itemPlano.offsetHeight;

        const blocoRect = blocoAtual.getBoundingClientRect();
        const contentRect = contentAtual.getBoundingClientRect();
        const alturaAtual = blocoRect.bottom - contentRect.top;

        const alturaDisponivelAtual = contentAtual.children.length === 1 &&
            contentAtual.children[0] === blocoAtual ?
            alturaMaximaGlobal - logoHeightPx :
            alturaMaximaGlobal;

        if (alturaAtual > alturaDisponivelAtual) {
            // Remove o último item e quebra página
            blocoAtual.removeChild(itemPlano);
            contentAtual = criarNovaPagina();
            paginas = Array.from(document.querySelectorAll('.page'));
            blocoAtual = null;
            tituloAdicionado = false;

            blocoAtual = document.createElement('div');
            blocoAtual.className = 'plano-container';
            blocoAtual.style.width = '7.48in';
            blocoAtual.style.marginTop = '1.1in';
            blocoAtual.style.display = 'flex';
            blocoAtual.style.flexDirection = 'column';
            contentAtual.appendChild(blocoAtual);

            if (titulo && !tituloAdicionado) {
                const tituloClone = titulo.cloneNode(true);
                blocoAtual.appendChild(tituloClone);
                tituloAdicionado = true;
            }

            // Re-adiciona o item na nova página
            blocoAtual.appendChild(itemPlano);
        }
    });
}

function quebrarEntrevistasEntrePaginas() {
    const blocoOriginal = document.querySelector('.bloco-entrevistas');
    if (!blocoOriginal) return;

    // Processa cada conteúdo de entrevista separadamente
    const conteudosEntrevista = Array.from(blocoOriginal.querySelectorAll('.conteudo-entrevista'));
    if (conteudosEntrevista.length === 0) return;

    blocoOriginal.remove();

    let paginas = Array.from(document.querySelectorAll('.page'));
    let ultimaPagina = paginas[paginas.length - 1];
    let contentAtual = ultimaPagina ? ultimaPagina.querySelector('.content') : criarNovaPagina();

    conteudosEntrevista.forEach((conteudoEntrevista) => {
        const tituloEntrevista = conteudoEntrevista.querySelector('.texto-titulo-entrevista');

        const todasPerguntas = Array.from(conteudoEntrevista.querySelectorAll('.container-entrevista-pergunta'));
        if (todasPerguntas.length === 0) return;

        let blocoAtual = null;
        let tituloEntrevistaAdicionado = false;
        let tituloGrupoAtual = null;

        todasPerguntas.forEach((pergunta) => {
            let grupoPergunta = pergunta.parentElement;
            while (grupoPergunta && !grupoPergunta.classList.contains('conteudo-entrevista')) {
                if (grupoPergunta.querySelector('.texto-titulo-grupo-pergunta')) {
                    break;
                }
                grupoPergunta = grupoPergunta.parentElement;
            }
            const tituloGrupo = grupoPergunta ? grupoPergunta.querySelector('.texto-titulo-grupo-pergunta') : null;

            const mudouGrupo = tituloGrupo && tituloGrupo !== tituloGrupoAtual;
            const temBlocosRenderizados = contentAtual.children.length > 0;
            const margem = temBlocosRenderizados ? '0.2in' : '1.1in';

            const blocoTeste = document.createElement('div');
            blocoTeste.className = 'bloco-entrevistas';
            blocoTeste.style.marginTop = margem;
            blocoTeste.style.display = 'flex';
            blocoTeste.style.flexDirection = 'column';

            if (!tituloEntrevistaAdicionado && tituloEntrevista) {
                blocoTeste.appendChild(tituloEntrevista.cloneNode(true));
            }
            if (mudouGrupo && tituloGrupo) {
                blocoTeste.appendChild(tituloGrupo.cloneNode(true));
            }
            blocoTeste.appendChild(pergunta.cloneNode(true));

            const alturaEstimativa = alturaProspectiva(contentAtual, blocoTeste);

            if (alturaEstimativa > alturaMaximaGlobal) {
                // Não cabe, cria nova página
                contentAtual = criarNovaPagina();
                blocoAtual = null;
                tituloEntrevistaAdicionado = false;
                tituloGrupoAtual = null;
            }

            // Cria ou reutiliza bloco atual
            if (!blocoAtual || blocoAtual.parentNode !== contentAtual) {
                blocoAtual = document.createElement('div');
                blocoAtual.className = 'bloco-entrevistas';
                blocoAtual.style.marginTop = contentAtual.children.length > 0 ? '0.2in' : '1.1in';
                blocoAtual.style.display = 'flex';
                blocoAtual.style.flexDirection = 'column';
                contentAtual.appendChild(blocoAtual);
            }

            if (!tituloEntrevistaAdicionado && tituloEntrevista) {
                blocoAtual.appendChild(tituloEntrevista.cloneNode(true));
                tituloEntrevistaAdicionado = true;
            }

            if (mudouGrupo && tituloGrupo) {
                blocoAtual.appendChild(tituloGrupo.cloneNode(true));
                tituloGrupoAtual = tituloGrupo;
            }

            blocoAtual.appendChild(pergunta);
            pergunta.offsetHeight;

            const contentRect = contentAtual.getBoundingClientRect();
            const blocoRect = blocoAtual.getBoundingClientRect();
            const alturaAtual = blocoRect.bottom - contentRect.top;

            if (alturaAtual > alturaMaximaGlobal) {
                blocoAtual.removeChild(pergunta);
                contentAtual = criarNovaPagina();
                blocoAtual = null;
                tituloEntrevistaAdicionado = false;
                tituloGrupoAtual = mudouGrupo ? null : tituloGrupoAtual;

                blocoAtual = document.createElement('div');
                blocoAtual.className = 'bloco-entrevistas';
                blocoAtual.style.marginTop = '1.1in';
                blocoAtual.style.display = 'flex';
                blocoAtual.style.flexDirection = 'column';
                contentAtual.appendChild(blocoAtual);

                if (tituloEntrevista && !tituloEntrevistaAdicionado) {
                    blocoAtual.appendChild(tituloEntrevista.cloneNode(true));
                    tituloEntrevistaAdicionado = true;
                }
                if (tituloGrupo && !tituloGrupoAtual) {
                    blocoAtual.appendChild(tituloGrupo.cloneNode(true));
                    tituloGrupoAtual = tituloGrupo;
                }

                blocoAtual.appendChild(pergunta);
            }
        });
    });
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

        return content;
    }
}

function alturaProspectiva(content, bloco) {
    const scrollY = window.scrollY || window.pageYOffset;

    const originalDisplay = bloco.style.display;
    bloco.style.display = 'block'; // força display para medir corretamente

    content.appendChild(bloco);

    // Força reflow para garantir cálculo preciso
    bloco.offsetHeight;

    const contentRect = content.getBoundingClientRect();
    const blocoRect = bloco.getBoundingClientRect();

    content.removeChild(bloco);

    bloco.style.display = originalDisplay;

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