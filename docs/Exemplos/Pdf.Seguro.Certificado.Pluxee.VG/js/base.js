// --- Binding Handler para Moeda (currency) ---
ko.bindingHandlers.currency = {
  update: function (element, valueAccessor) {
    const raw = ko.unwrap(valueAccessor());
    if (raw === null || raw === undefined || raw === '') {
      element.textContent = '';
      return;
    }

    // Se já for número, usa direto
    const num = typeof raw === 'number'
      ? raw
      : parseFloat(String(raw).replace(/[^\d,-]/g, '').replace(',', '.'));

    element.textContent = isNaN(num) ? raw : 'R$ ' + num.toLocaleString('pt-BR', { minimumFractionDigits: 2 });
  }
};

// --- Binding Handler para Datas (dd/mm/yyyy ou ISO) ---
ko.bindingHandlers.dateBR = {
  update: function (element, valueAccessor) {
    const raw = ko.unwrap(valueAccessor());
    if (!raw) {
      element.textContent = '';
      return;
    }

    let date = new Date(raw);

    // Detecta formato dd/mm/yyyy
    if (/^\d{2}\/\d{2}\/\d{4}$/.test(raw)) {
      const parts = raw.split('/');
      date = new Date(parts[2], parts[1] - 1, parts[0]);
    }

    if (isNaN(date.getTime())) {
      element.textContent = raw; // se não for data válida, mostra original
      return;
    }

    element.textContent = date.toLocaleDateString('pt-BR');
  }
};

// --- Binding Handler para Strings seguras (evita null/undefined) ---
ko.bindingHandlers.safeText = {
  update: function (element, valueAccessor) {
    const raw = ko.unwrap(valueAccessor());
    element.textContent = (raw === null || raw === undefined) ? '' : raw;
  }
};

// --- Função auxiliar para somar valores de observableArray ---
ko.observableArray.fn.sum = function (field) {
  return this().reduce((acc, item) => {
    const value = item[field] ? ko.unwrap(item[field]) : 0;
    const num = typeof value === 'number'
      ? value
      : parseFloat(String(value).replace(/[^\d,-]/g, '').replace(',', '.'));
    return acc + (isNaN(num) ? 0 : num);
  }, 0);
};

// --- ViewModel ---
const vm = ko.mapping.fromJS(data);

// --- Computed para Prêmio Total ---
vm.CertificadoGlobalXMLDTO.Coberturas.CoberturaXMLDTO().forEach(cobertura => {
  cobertura.ValorPremioTotal = ko.computed(() => {
    const val = cobertura.ValorPremioIndividual();
    return typeof val === 'number'
      ? 'R$ ' + val.toLocaleString('pt-BR', { minimumFractionDigits: 2 })
      : val;
  });
});

// --- Computed para cada Prêmio Individual (opcional, para usar no foreach) ---
vm.CertificadoGlobalXMLDTO.Coberturas.CoberturaXMLDTO().forEach(cobertura => {
  cobertura.ValorPremioIndividualFormatado = ko.computed(() => {
    const val = cobertura.ValorPremioIndividual();
    return typeof val === 'number'
      ? 'R$ ' + val.toLocaleString('pt-BR', { minimumFractionDigits: 2 })
      : val;
  });
});

// ==================== FUNÇÕES DE CARÊNCIA, FRANQUIA E GARANTIAS ====================

const garantirArray = (campo) => {
  if (Array.isArray(campo)) return campo.filter(e => Object.keys(e || {}).length > 0);
  if (campo && typeof campo === 'object' && Object.keys(campo).length > 0) return [campo];
  return [];
};

function isValorUtil(valor) {
  if (valor === null || valor === undefined) return false;
  if (typeof valor === 'string') return valor.trim() !== '';
  if (typeof valor === 'object') return Object.keys(valor).length > 0;
  return true;
}

function montarTextoCarenciaPeriodoDefinido(nomeCobertura, carenciaPeriodo) {
  if (!carenciaPeriodo) return null;

  const tempo = carenciaPeriodo.Tempo;
  const tempoEm = carenciaPeriodo.TempoEm;

  if (!isValorUtil(tempo) || !isValorUtil(tempoEm)) return null;

  return `Para a cobertura ${nomeCobertura} haverá carência de ${tempo} ${tempoEm.toLowerCase()}.`;
}

function montarFranquias(certificadoJS) {
  const detalhes = garantirArray(certificadoJS?.FranquiasCarencias?.DetalheFranquiaCarencia || []);
  const franquiasValidas = [];

  detalhes.forEach(item => {
    const nome = item.NomeCobertura || '';
    const franquiaCarencia = item.FranquiaCarencia || {};
    const franquias = franquiaCarencia.Franquias;
    
    // Verificar se Franquias existe e não é string vazia
    if (franquias && typeof franquias === 'object' && franquias !== null) {
      const franquia = franquias.Franquia;
      
      // Verificar se Franquia existe e tem Tempo ou TempoEm
      if (franquia && (franquia.Tempo || franquia.TempoEm)) {
        franquiasValidas.push({
          NomeCobertura: nome,
          Tempo: franquia.Tempo || '',
          TempoEm: franquia.TempoEm || ''
        });
      }
    }
  });

  return franquiasValidas;
}

function existeCarencia() {
  const raiz = vm.CertificadoGlobalXMLDTO?.FranquiasCarencias?.();
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

function extrairCarenciasEmPeriodosDefinidos(certificadoJS) {
  const resultado = [];
  const detalhes = garantirArray(certificadoJS?.FranquiasCarencias?.DetalheFranquiaCarencia || []);

  detalhes.forEach(detalhe => {
    const nomeCobertura = detalhe.NomeCobertura || '';
    const fc = detalhe.FranquiaCarencia || {};
    const carenciasPeriodo = fc.CarenciasEmPeriodosDefinidos;

    if (!isValorUtil(carenciasPeriodo)) return;

    const carenciaDefinida = carenciasPeriodo.CarenciaEmPeriodoDefinido;

    const texto = montarTextoCarenciaPeriodoDefinido(
      nomeCobertura,
      carenciaDefinida
    );

    if (texto) {
      resultado.push({ Texto: texto });
    }
  });

  return resultado;
}

function existeCarenciaPorSuicidio() {
  const certificadoJS = ko.toJS(vm.CertificadoGlobalXMLDTO);

  const raiz = certificadoJS?.FranquiasCarencias;
  if (!raiz) return false;

  const detalhes = garantirArray(raiz?.DetalheFranquiaCarencia || []);

  if (!detalhes.length) return false;

  return detalhes.some(det => {

    const fc = det?.FranquiaCarencia;
    if (!fc) return false;

    return (
      isValorUtil(fc.CarenciasProgressivas) ||
      isValorUtil(fc.CarenciasEmPeriodosDefinidos) ||
      isValorUtil(fc.CarenciasPorCausas) ||
      isValorUtil(fc.CarenciasPorSuicidios)
    );
  });
}


// ==================== FUNÇÕES DE EXTRAÇÃO DE CARÊNCIAS ====================

function normalizarTexto(texto) {
  return (texto || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toUpperCase();
}

// CARÊNCIA DEFINIDA (meses - SAF)
function extrairCarenciaDefinidaMesesSAF(certificado) {
  const resultado = [];
  const detalhes = garantirArray(certificado?.FranquiasCarencias?.DetalheFranquiaCarencia || []);

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

// CARÊNCIA DEFINIDA (MESES)
function extrairCarenciaDefinidaMeses(certificado) {
  const resultado = [];
  const detalhes = garantirArray(certificado?.FranquiasCarencias?.DetalheFranquiaCarencia || []);

  detalhes.forEach(detalhe => {
    const nome = detalhe.NomeCobertura;
    const carencia = detalhe.FranquiaCarencia?.CarenciasEmPeriodosDefinidos?.CarenciaEmPeriodoDefinido;

    if (!carencia) return;

    if (carencia.TempoEm?.toLowerCase() === 'meses') {
      // Excluir SAF pois já é tratado em extrairCarenciaDefinidaMesesSAF
      const isSAF = normalizarTexto(nome).includes('SAF');
      if (isSAF) return;

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
  const detalhes = garantirArray(certificado?.FranquiasCarencias?.DetalheFranquiaCarencia || []);

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
  const detalhes = garantirArray(certificado?.FranquiasCarencias?.DetalheFranquiaCarencia || []);

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

// CARÊNCIA POR CAUSAS
function extrairCarenciaPorCausas(certificado) {
  const resultado = [];
  const detalhes = garantirArray(certificado?.FranquiasCarencias?.DetalheFranquiaCarencia || []);

  detalhes.forEach(d => {
    const nome = d?.NomeCobertura || '';
    const carencia = d?.FranquiaCarencia
      ?.CarenciasPorCausas
      ?.CarenciaPorCausa;

    if (!carencia) return;

    const causa = carencia.Causa;
    const tempo = carencia.Tempo;
    const tempoEm = carencia.TempoEm;

    if (!isValorUtil(causa)) {
      return;
    }

    resultado.push({
      Tipo: 'CARENCIA_POR_CAUSAS',
      Texto: `Para o(s) plano(s)/cobertura(s) ${nome}, haverá carência de ${tempo} ${tempoEm.toLowerCase()} para a seguinte causa: ${causa}.`
    });
  });

  return resultado;
}

// CARÊNCIA PROGRESSIVA (parcelas)
function extrairCarenciaProgressivaParcelas(certificado) {
  const resultado = [];
  const detalhes = garantirArray(certificado?.FranquiasCarencias?.DetalheFranquiaCarencia || []);

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

// CARÊNCIA PROGRESSIVA (meses)
function extrairCarenciaProgressivaMeses(certificado) {
  const resultado = [];
  const detalhes = garantirArray(certificado?.FranquiasCarencias?.DetalheFranquiaCarencia || []);

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

// Função para extrair todas as carências definidas
function extrairTodasCarencias(certificado) {
  return [
    ...extrairCarenciaDefinidaMesesSAF(certificado),
    ...extrairCarenciaDefinidaMeses(certificado),
    ...extrairCarenciaDefinidaParcelas(certificado),
    ...extrairCarenciaDefinidaDias(certificado),
    ...extrairCarenciaPorCausas(certificado)
  ];
}

// Função para extrair carências progressivas por parcelas
function extrairCarenciasProgressivas(certificado) {
  return [
    ...extrairCarenciaProgressivaParcelas(certificado)
  ];
}

// Função para extrair carências progressivas por meses
function extrairCarenciasProgressivasPorMes(certificado) {
  return [
    ...extrairCarenciaProgressivaMeses(certificado)
  ];
}

// ==================== INICIALIZAÇÃO ====================

function inicializarDados() {
  const certificado = vm.CertificadoGlobalXMLDTO;

  // Garantir que Coberturas é um array
  if (certificado.Coberturas && certificado.Coberturas.CoberturaXMLDTO) {
    const coberturas = ko.unwrap(certificado.Coberturas.CoberturaXMLDTO);
    if (!Array.isArray(coberturas)) {
      certificado.Coberturas.CoberturaXMLDTO(garantirArray(coberturas));
    }
  }

  // Garantir que DescricaoCurta existe em cada cobertura como observable
  if (certificado.Coberturas && certificado.Coberturas.CoberturaXMLDTO) {
    const coberturas = certificado.Coberturas.CoberturaXMLDTO();
    coberturas.forEach(cob => {
      // Se DescricaoCurta não é observable, criar
      if (!ko.isObservable(cob.DescricaoCurta)) {
        const valorAtual = cob.DescricaoCurta || '';
        cob.DescricaoCurta = ko.observable(valorAtual);
      }
      // Garantir que Descricao também é observable
      if (!ko.isObservable(cob.Descricao)) {
        const valorAtual = cob.Descricao || '';
        cob.Descricao = ko.observable(valorAtual);
      }
    });
  }

  // Inicialização do JS PURO para renderização dos conteúdos (carência)
  const certificadoJS = ko.toJS(certificado);

  certificado.TextosCarencias = ko.computed(() => {
    return extrairTodasCarencias(certificadoJS);
  });

  certificado.TextosCarenciasProgressivas = ko.computed(() => {
    return extrairCarenciasProgressivas(certificadoJS);
  });

  certificado.TextosCarenciasProgressivasMeses = ko.computed(() => {
    return extrairCarenciasProgressivasPorMes(certificadoJS);
  });

  // Inicializar FranquiasValidas 
  const franquiasJS = montarFranquias(certificadoJS);
  
  // Garantir que os objetos são plain objects (não observables)
  const franquiasPlain = franquiasJS.map(f => ({
    NomeCobertura: String(f.NomeCobertura || ''),
    Tempo: String(f.Tempo || ''),
    TempoEm: String(f.TempoEm || '')
  }));
  
  certificado.FranquiasValidas = ko.observableArray(franquiasPlain);

  // Adicionar computed para verificar se existe carência por suicídio
  certificado.existeCarenciaPorSuicidio = ko.computed(() => {
    return existeCarenciaPorSuicidio();
  });

  // Deve retornar true apenas se houver pelo menos uma carência (não apenas franquia)
  certificado.temCarencias = ko.computed(() => {
    const temCarenciasDefinidas = certificado.TextosCarencias().length > 0;
    const temCarenciasProgressivas = certificado.TextosCarenciasProgressivas().length > 0;
    const temCarenciasProgressivasMeses = certificado.TextosCarenciasProgressivasMeses().length > 0;
    const temCarenciaSuicidio = certificado.existeCarenciaPorSuicidio();
    
    return temCarenciasDefinidas || temCarenciasProgressivas || temCarenciasProgressivasMeses || temCarenciaSuicidio;
  });

  // Adicionar computed para verificar se há franquias
  certificado.temFranquias = ko.computed(() => {
    return certificado.FranquiasValidas().length > 0;
  });
}

// ==================== APLICAÇÃO ====================

// Inicializar dados
inicializarDados();

// --- Aplica bindings ---
ko.applyBindings(vm, document.body);
