{% extends "admin.tpl" %}

{% block templates %}
<script type="text/x-template" id="isrc-template">
    <tr>
        <td> [[ item.dma_id ]] -> [[ item.isrc ]]</td>
        <td> [[ item.filename ]]</td>
        <td> [[ item.recordnumber ]]</td>
        <td> [[ item.musiclibrary ]]</td>
    </tr>
</script>
{% endblock templates %}

{% block docscript %}

Vue.component("isrc-item", {
    props: ["item"],
    delimiters: ["[[", "]]"],
    template: "#isrc-template",
    methods: {
    },
    computed: {
        formattedTimestamp: function() {
            var options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
            return new Date(this.item.timestamp).toLocaleDateString();
        }
    },
    mounted: function () {
        console.log("mounted %o", this);
    },
  });

var app = new Vue({
    el: '#content',
    data: {
      items: [],
      stats: {}
    },
    mounted : function() { 
        console.log("startup");
        fetch_isrc_ean_status();
    },
    methods: {
        calcPercent: function(part, whole) {
            console.log("calcPercent %o %o", part, whole);
            return parseInt(part / whole * 100, 10);
        }
    },
    delimiters: ["[[", "]]"]
  });

function fetch_isrc_ean_status() {
    axios.get("/api/isrc_ean_status")
        .then(function (response) {
            console.log("got isrc: %o", response);
            app.stats = response.data.stats;
            for(var i=0;i<response.data.wrong_codes.length;i++) {
                app.items.push(response.data.wrong_codes[i]);
            }

        })
        .catch(function(error) {
            console.error("isrc error: %o", error);
        });

}
{% endblock docscript %}

{% block admintitle %}<span data-i18n=isrc_ean_status class=translate>ISRC &amp; EAN status</span>{% endblock  %}


{% block adminpanel %}
<div id=adminpanel>

    <table>
        <col style="width:70%"> 
        <col style="width:10%">
        <col style="width:10%">
        <col style="width:10%">
        <thead>
            <tr>
                <th></th>
                <th>total</th>
                <th>correct</th>
                <th>false</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <th>
                DMA tracks with ISRC codes
                </th>
                <td>[[ stats.totals.isrc_codes ]] 
                    ([[ calcPercent(stats.totals.isrc_codes, stats.totals.all_records) ]] %) </td>
                <td>[[ stats.status.isrc.true || 0 ]] </td>
                <td>[[ stats.status.isrc.false || 0]] </td>
            </tr>
            <tr>
                <th>
                DMA tracks with EAN codes
                </th>
                <td>[[ stats.totals.ean_codes ]] 
                    ([[ stats.totals.ean_codes, stats.totals.all_records ]] %) </td>
                <td>[[ stats.status.ean.true || 0]] </td>
                <td>[[ stats.status.ean.false || 0]] </td>
            </tr>
        </tbody>
    </table>

    </div>


    <table class="table table-striped table-sm">
        <col style="width:20%">
        <col style="width:40%">
        <col style="width:40%"> 
        <thead class="thead-dark">
          <tr>
            <th >ID</th>
            <th >DMA</th>
            <th >ISRC</th>
          </tr>
        </thead>
        <tbody id=results-list style="font-size:80%">
          <template v-if="items.length">
          <isrc-item v-for="item in items" 
                          v-bind:item="item"
                          v-bind:key="item.id">
          </isrc-item>
          </template>
          <tr v-else>
          </tr>
        </tbody>

    </table>
</div>
{% endblock adminpanel %}