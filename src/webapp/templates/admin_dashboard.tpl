{% extends "admin.tpl" %}


{% block templates %}
{% endblock templates %}

{% block headscript %}
<script src="/media/moment.min.js"></script>
<script src="/media/Chart.min.js"></script>
<script src="/media/chartjs-plugin-datalabels.min.js"></script>
{% endblock headscript %}
{% block docscript %}

// This plugin registers itself globally, meaning that once imported, all charts will display labels. 
// In case you want it enabled only for a few charts, you first need to unregister it globally:
Chart.plugins.unregister(ChartDataLabels);

var app = new Vue({
    el: '#adminpanel',
    data: {
    },
    mounted : function() { 
        console.log("startup");
        function canvas(idel) {
            return document.getElementById(idel).getContext('2d');
        }
        load_charts(canvas("filenameStatsChart"), 
                    canvas("musiclibraryStatsChart"), 
                    canvas("ownershipStatsChart"));
    },
    delimiters: ["[[", "]]"],
    methods: {
    }
  });

function color(idx) {
    let colors = [
        {
        "value":"#6B8E23",
        "css":true,
        "name":"olivedrab"
      },
      {
        "value":"#808000",
        "vga":true,
        "css":true,
        "name":"olive"
      },{
        "value":"#B8860B",
        "css":true,
        "name":"darkgoldenrod"
      },{
        "value":"#FF7F50",
        "css":true,
        "name":"coral"
      },{
        "value":"#FFF5EE",
        "css":true,
        "name":"seashell"
      },{
        "value":"#D2B48C",
        "css":true,
        "name":"tan"
      },{
        "value":"#191970",
        "css":true,
        "name":"midnightblue"
      },{
        "value":"#FF69B4",
        "css":true,
        "name":"hotpink"
      },{
        "value":"#EEA2AD",
        "name":"lightpink 2"
      },{
        "value":"#E066FF",
        "name":"mediumorchid 1"
      }];
      //return colors.filter(function(el) { return el.name == colorName })[0];
      return colors[idx].value;
}

function load_charts(ctxFilenameStats, ctxMusiclibraryStats, ctxOwnershipStats) { 
    console.log("creating all status charts");
    axios.get("/media/status.json")
    .then(function(response) {
        // handle success
        console.log(response);
        create_charts(response.data, ctxFilenameStats, ctxMusiclibraryStats, ctxOwnershipStats);
    }).catch(function(error) {
        // handle fails
        console.error(error);
    });
}

function create_charts(dataseries, ctxFilenameStats, ctxMusiclibraryStats, ctxOwnershipStats) {
    // parse status data
    console.log("dataseries: %o", dataseries);
    const allcolors = {"404": "rgba(255, 99, 132, 0.6)", 
                       "201": "rgba(255, 159, 64, 0.6)", 
                       "400": "rgba(255, 205, 86, 0.6)", 
                       "200": "rgba(75, 192, 192, 0.6)", 
                       "500": "rgba(54, 162, 235, 0.6)", 
                       "OK": "#28a745",
                       "CHECK": "#ffc107",
                       "NO": "#dc3545",
                       "default": "rgba(201, 203, 207, 0.9)"};
            

    var sets = []
    var z = dataseries["activity_7days"]["datasets"];
    for(var k in z) {
        try {
            var kolor = allcolors[k];
        } catch (e) {
            var kolor = allcolors["default"];
        }
        sets.push({
            label: k,
            borderColor: kolor,
            backgroundColor: kolor,
            fill: true,
            data: dataseries["activity_7days"]["datasets"][k],
            tooltip: dataseries["activity_7days"]["tooltips"][k]
        });
    }
    
    console.log("sets: %o", sets);
    // create filename chart
    var myChart = new Chart(ctxFilenameStats, {
        type: 'bar',
        data: {
            labels: dataseries["activity_7days"]["labels"],
            datasets: sets,
        },
        options: {
            responsive: true,
            title: {
                text: i18n.FILENAMES_STATUS_WEEK(),
                display: true
            },
            scales: {
                xAxes: [{
                    stacked: true,
                    fill: true,
                    scaleLabel: {
                        labelString: 'Service'
                    },
                    ticks: {
                        autoSkip: false,
                        min: 0,
                        stepSize: 1
                    }
                }],
                yAxes: [{
                    stacked: false,
                    ticks: {
                        display: false
                    }
                }]
            },
            tooltips: {
                callbacks: {
                    label: function(item, data) {
                        //console.log("lblclb: %o - %o", item, data);
                        var label = "Sum: "+data.datasets[item.datasetIndex].tooltip[item.index];
                        return label;
                    }
                }
            }
        }
    });

    // create music library usage

    var libraryChart = new Chart(ctxMusiclibraryStats, {
        type: 'pie',
        plugins: [ChartDataLabels],
        data: {
            labels: dataseries["activity_7days"]["labels"],
            total_use: dataseries["activity_7days"]["tooltips"]["200"].reduce(function(acc, val) { return acc + val; }, 0),
            datasets: [{
                data: dataseries["activity_7days"]["tooltips"]["200"],
                datalabels: {
                    color: allcolors["default"]
                },
                backgroundColor: function(ctx) {
                    return color(ctx.dataIndex);
                }
            }]
        },
        options: {
            responsive: true,
            title: {
                text: i18n.FILENAMES_STATUS_WEEK(),
                display: true
            },
            tooltips: {
                callbacks: {
                    label: function(item, data) {
                        //console.log("lblclb: %o - %o", item, data);
                        let val = data.datasets[item.datasetIndex].data[item.index];
                        let label = data.labels[item.index] + ": " + val + 
                                " ( " + parseInt( val/data.total_use*100, 10) +" % )";
                        return label;
                    }
                }
            },
            plugins: {
                datalabels: {
                    formatter: function(value, context) {
                        return context.chart.data.labels[context.dataIndex];
                    }
                }
            }

        }
    });

    // create ownersihp status

    var dsets = [];
    for(var dset in dataseries.ownership_resolve_efficiency_hours.datasets) {
        dsets.push({ label: dset, 
                     data:dataseries.ownership_resolve_efficiency_hours.datasets[dset],
                     borderColor: allcolors[dset],
                     backgroundColor: allcolors[dset],
                     type: 'line'
                   });
    }

    var chart = new Chart(ctxOwnershipStats, {
        // The data for our dataset
        data: {
            datasets: dsets
        },

        // Configuration options go here
        options: {
            animation: {
                duration: 750,
            },
            scales: {
                xAxes: [{
                    type: 'time',
                    distribution: 'series',
                    offset: true,
                    ticks: {
                        major: {
                            enabled: true,
                            fontStyle: 'bold'
                        },
                        source: 'data',
                        autoSkip: true,
                        autoSkipPadding: 75,
                        maxRotation: 0,
                        sampleSize: 100
                    }
                }],
                yAxes: [{
                  gridLines: {
                      drawBorder: false
                  },
                  scaleLabel: {
                      display: true,
                      labelString: 'HITS'
                  }
                }]
              },
            title: {
                text: i18n.OWNERSHIP_STATUS_WEEKS(),
                display: true
            }
        }
    });
}




{% endblock docscript %}

{% block admintitle %}<span data-i18n=Dashboard class=translate>Dashboard</span>{% endblock  %}


{% block adminpanel %}
<div id=adminpanel>

    <div class=container>
        <div class=row>
            <div class=col>
                <h3 data-i18n=Filenames class=translate>Filenames</h3>
                <canvas id="filenameStatsChart" width="500" height="500"></canvas>
            </div>
            <div class=col>
                <h3 data-i18n=source class=translate>Source</h3>
                <canvas id="musiclibraryStatsChart" width="500" height="500"></canvas>
            </div>
        </div>
        <div class=row>
            <div class=col>
                <h3 data-i18n=Ownership class=translate>Ownership</h3>
                <canvas id="ownershipStatsChart" width="500" height="500"></canvas>
            </div>
        </div>
    </div>

</div>
{% endblock adminpanel %}