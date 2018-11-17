{% extends "admin.tpl" %}


{% block templates %}
<script type="text/x-template" id="feedback-template">
    <tr class=item v-bind:class="{'text-muted':item.done}">
        <td> <input type=checkbox v-bind:checked=item.done></td>
        <td> [[ formattedTimestamp ]]</td>
        <td v-bind:class="{'feedback-done':item.done}"> [[ item.message ]]</td>
        <td> [[ item.sender ]]</td>
    </tr>
</script>
{% endblock templates %}

{% block headscript %}
<script src="/media/Chart.min.js"></script>
{% endblock headscript %}
{% block docscript %}

var app = new Vue({
    el: '#adminpanel',
    data: {
    },
    mounted : function() { 
        console.log("startup");
        var ctxFilenameStats = document.getElementById("filenameStatsChart").getContext('2d');
        var ctxOwnershipStats = document.getElementById("ownershipStatsChart").getContext('2d');
        load_charts(ctxFilenameStats, ctxOwnershipStats);
    },
    delimiters: ["[[", "]]"],
    methods: {
    }
  });

function load_charts(ctxFilenameStats, ctxOwnershipStats) { 
    console.log("creating all status charts");
    axios.get("/media/status.json")
    .then(function(response) {
        // handle success
        console.log(response);
        create_charts(response.data, ctxFilenameStats, ctxOwnershipStats);
    }).catch(function(error) {
        // handle fails
        console.error(error);
    });
}

function create_charts(dataseries, ctxFilenameStats, ctxOwnershipStats) {
    // parse status data
    console.log("dataseries: %o", dataseries);
    const allcolors = {"404": "rgba(255, 99, 132, 0.2)", 
                       "201": "rgba(255, 159, 64, 0.2)", 
                       "400": "rgba(255, 205, 86, 0.2)", 
                       "200": "rgba(75, 192, 192, 0.2)", 
                       "500": "rgba(54, 162, 235, 0.2)", 
                       "OK": "#28a745",
                       "CHECK": "#ffc107",
                       "NO": "#dc3545",
                       "default": "rgba(201, 203, 207, 0.2)"};
            

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
            fill: false,
            data: dataseries["activity_7days"]["datasets"][k],
            tooltip: dataseries["activity_7days"]["tooltips"][k]
        });
    }
    console.log("sets: %o", sets);
    
    // create filename chart
    var myChart = new Chart(ctxFilenameStats, {
        type: "bar",
        data: {
            labels: dataseries["activity_7days"]["labels"],
            datasets: sets,
        },
        options: {
            responsive: false,
            scales: {
                xAxes: [{
                    stacked: true,
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
                    stacked: true,
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

    // create ownersihp status

    var dsets = [];
    for(var dset in dataseries.ownership_resolve_efficiency_hours.datasets) {
        dsets.push({ label: dset, 
                     data:dataseries.ownership_resolve_efficiency_hours.datasets[dset],
                     borderColor: allcolors[dset],
                     backgroundColor: allcolors[dset]
                   });
    }

    var chart = new Chart(ctxOwnershipStats, {
        // The type of chart we want to create
        type: 'line',

        // The data for our dataset
        data: {
            labels: [],
            datasets: dsets
        },

        // Configuration options go here
        options: {
            scales: {
                yAxes: [{
                  stacked: true,
                }]
              },
              animation: {
                duration: 750,
              },
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
                <h3>Filenames</h3>
                <canvas id="filenameStatsChart" width="500" height="500"></canvas>
            </div>
            <div class=col>
                <h3>Ownership</h3>
                <canvas id="ownershipStatsChart" width="500" height="500"></canvas>
            </div>
        </div>
    </div>

</div>
{% endblock adminpanel %}