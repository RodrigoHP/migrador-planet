// https://github.com/wkhtmltopdf/wkhtmltopdf/issues/3242#issuecomment-518099192
(function (setLineDash) {
    CanvasRenderingContext2D.prototype.setLineDash = function () {
        if (!arguments[0].length) {
            arguments[0] = [1, 0];
        }
        // Now, call the original method
        return setLineDash.apply(this, arguments);
    };
})(CanvasRenderingContext2D.prototype.setLineDash);
Function.prototype.bind = Function.prototype.bind || function (thisp) {
    var fn = this;
    return function () {
        return fn.apply(thisp, arguments);
    };
};
Chart.defaults.global.responsive = false;
Chart.defaults.global.responsiveAnimationDuration = 0;
Chart.defaults.global.animation.duration = 0;
Chart.defaults.global.hover.animationDuration = 0;

function PossuiTabelaResgate(product) {
    return product.PossuiTabelaResgate === true;
}

var Produtos = data.Simulacao.Produtos.filter(PossuiTabelaResgate);

for (var i = 0; i < Produtos.length; i++) {
    var produto = Produtos[i];

    var tabelaResgate = produto.TabelaResgate;
    var labels = tabelaResgate.map(function (item, i) {
        return item.Tempo;
    });
    var premioData = tabelaResgate.map(function (item, i) {
        return item.Valor;
    });
    var capitalSeguradoData = tabelaResgate.map(function (item, i) {
        return item.Beneficio;
    });
    var reservaData = tabelaResgate.map(function (item, i) {
        return item.ValorResgate;
    });

    new Chart(document.getElementById('rescue-table-chart-' + produto.Id).getContext('2d', { alpha: true }), {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    data: premioData,
                    borderColor: '#0079C2',
                },
                {
                    data: capitalSeguradoData,
                    borderColor: '#75C844',
                },
                {
                    data: reservaData,
                    borderColor: '#FFC400',
                }
            ]
        },
        options: {
            spanGaps: true,
            animation: {
                duration: 0
            },
            hover: {
                animationDuration: 0
            },
            responsiveAnimationDuration: 0,
            legend: {
                display: false,
            },
            scales: {
                xAxes: [{
                    ticks: {
                        stepSize: 5,
                        maxRotation: 0,
                        minRotation: 0
                    },
                    gridLines: {
                        drawOnChartArea: false
                    }
                }],
                yAxes: [{
                    ticks: {
                        beginAtZero: true,
                        callback: function (value, index, values) {
                            return 'R$ ' + value.toFixed(2).replace('.', ',').replace(/(\d)(?=(\d{3})+(?!\d))/g, "$1.");
                        },
                        maxTicksLimit: 6,
                        maxRotation: 0,
                        minRotation: 0
                    },
                    gridLines: {
                        borderDash: [8, 4],
                    }
                }]
            },
            elements: {
                line: {
                    fill: false,
                    tension: 0,
                    stepped: false,
                    borderDash: []
                },
                point: {
                    radius: 0
                }
            },
            plugins: {
                datalabels: false
            },
        }
    });
}

var chartsData = data.Simulacao.chartsData;

var coverageTimeChart = chartsData.coverageTimeChart;
if (coverageTimeChart.show) {
    for (var i = 0; i < coverageTimeChart.data.length; i++) {
        var tempoCoberturaChart = document.getElementById('tempo-cobertura-chart' + i);
        tempoCoberturaChart.height = coverageTimeChart.data[i].length * 80;
        var backgroundColor = coverageTimeChart.data[i].map(function (value, i) {
            return '#0072BB';
        });
        new Chart(tempoCoberturaChart.getContext('2d', { alpha: false }), {
            type: 'horizontalBar',
            data: {
                labels: coverageTimeChart.labels[i],
                datasets: [
                    {
                        backgroundColor: backgroundColor,
                        data: coverageTimeChart.data[i],
                        barThickness: 50
                    },
                ]
            },
            options: {
                scales: {
                    xAxes: [{
                        ticks: {
                            maxRotation: 0,
                            minRotation: 0
                        },
                    }],
                    yAxes: [{
                        ticks: {
                            maxRotation: 0,
                            minRotation: 0
                        },
                    }]
                },
                showLines: false,
                spanGaps: true,
                animation: {
                    duration: 0
                },
                hover: {
                    animationDuration: 0
                },
                responsiveAnimationDuration: 0,
                legend: { display: false },
                scales: {
                    xAxes: [{
                        ticks: {
                            beginAtZero: true,
                            stepSize: 25,
                            max: 100,
                            maxRotation: 0,
                            minRotation: 0
                        },
                        gridLines: {
                            drawOnChartArea: false
                        }
                    }],
                    yAxes: [{
                        ticks: {
                            fontStyle: 'bold',
                            maxRotation: 0,
                            minRotation: 0
                        },
                        gridLines: {
                            drawOnChartArea: false
                        }
                    }]
                },
                elements: {
                    line: {
                        fill: false,
                        tension: 0,
                        stepped: false,
                        borderdash: []
                    },
                    point: {
                        radius: 0
                    }
                },
                plugins: {
                    datalabels: {
                        color: '#FFF',
                        formatter: function (value, context) {
                            return value == 100 ? 'Vitalício' : value + ' anos';
                        },
                        align: 'end',
                        anchor: 'start',
                        font: {
                            size: 14
                        }
                    }
                }
            }
        });
    }
}

var equivalenceChart = chartsData.equivalenceChart;
if (equivalenceChart.show) {
    for (var i = 0; i < equivalenceChart.data.length; i++) {
        var equivalenciaChart = document.getElementById('equivalencia-chart' + i);
        equivalenciaChart.height = equivalenceChart.data[i].length * 80;
        var highestValue = Math.max.apply(null, equivalenceChart.data[i]);
        var backgroundColor = equivalenceChart.data[i].map(function (value, i) {
            return '#0072BB';
        });
        new Chart(equivalenciaChart.getContext('2d', { alpha: false }), {
            type: 'horizontalBar',
            data: {
                labels: equivalenceChart.labels[i],
                datasets: [
                    {
                        backgroundColor: backgroundColor,
                        data: equivalenceChart.data[i],
                        barThickness: 50
                    },
                ]
            },
            options: {
                showLines: false,
                spanGaps: true,
                animation: {
                    duration: 0
                },
                hover: {
                    animationDuration: 0
                },
                responsiveAnimationDuration: 0,
                legend: {
                    display: false
                },
                scales: {
                    xAxes: [{
                        ticks: {
                            beginAtZero: true,
                            maxRotation: 0,
                            minRotation: 0
                        },
                        gridLines: {
                            drawOnChartArea: false
                        }
                    }],
                    yAxes: [{
                        ticks: {
                            fontStyle: 'bold',
                            maxRotation: 0,
                            minRotation: 0
                        },
                        gridLines: {
                            drawOnChartArea: false
                        }
                    }]
                },
                elements: {
                    line: {
                        fill: false,
                        tension: 0,
                        stepped: false,
                        borderDash: []
                    },
                    point: {
                        radius: 0
                    }
                },
                plugins: {
                    datalabels: {
                        color: function (context) {
                            const index = context.dataIndex;
                            const value = context.dataset.data[index];
                            var percentage = value / highestValue;

                            if (percentage < 0.06) {
                                return '#1D1D1D';
                            }

                            return '#fff';
                        },
                        formatter: function (value) {
                            if (!value) {
                                return "";
                            }

                            if (value === 1) {
                                return value + ' mês';
                            }

                            return value + ' meses';
                        },
                        align: 'end',
                        anchor: function (context) {
                            const index = context.dataIndex;
                            const value = context.dataset.data[index];
                            const percentage = value / highestValue;

                            if (percentage < 0.06) {
                                return 'end'
                            }

                            return 'start';
                        },
                        font: {
                            size: 14
                        }
                    }
                }
            }
        });
    }
}

