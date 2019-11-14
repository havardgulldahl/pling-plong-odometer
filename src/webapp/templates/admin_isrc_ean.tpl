{% extends "admin.tpl" %}

{% block templates %}
<script type="text/x-template" id="isrc-template">
    <tr>
        <td :class="{loading: !finished_loading_dma}">
             [[ item.dma_id ]]
             <span v-if="dma.title">
                <i>«[[ dma.title ]]»</i> —
                [[ dma.artists ]] 
            </span>
        </td>
        <td>
        ⟿
        </td>
        <td :class="{loading: !finished_loading_isrc}">
            <a v-bind:href="'https://isrcsearch.ifpi.org/#!/search?isrcCode='+item.isrc+'&tab=lookup&showReleases=0&start=0&number=10'">[[ item.isrc ]]</a> 
            <span v-if="isrc.title">
                <i>«[[ isrc.title ]]»</i> —
                [[ formatList(isrc.artists) ]] 
                <a class=spotifylink title="copy spotify uri" v-on:click.prevent="clipboard(isrc.spotify_uri)"></a></span>
            </span>
            <span v-else-if="finished_loading_isrc &amp;&amp; !isrc.title"
                      class="translate text-danger" data-i18n=NOT_FOUND>Not found</span>
        </td>
        <td class=align-middle >
        </td>
    </tr>
</script>
{% endblock templates %}

{% block docscript %}

Vue.component("isrc-item", {
    props: ["item"],
    delimiters: ["[[", "]]"],
    template: "#isrc-template",
    data: function() {
        return { dma: { title: undefined,
                        artists: [],
                        year: undefined},
                 isrc: {title: undefined,
                        artists: [],
                        year: undefined},
                 finished_loading_dma: false,
                 finished_loading_isrc: false 
                }

    },
    methods: {
        getTrackDMA: function() {
            var itm = this;
            axios.get('/api/trackinfo/DMA/' + this.item.dma_id)
            .then(function(response) {
                console.log("got dma: %o", response);
                let record = response.data.tracks[0];
                itm.dma.title = record.title;
                itm.dma.artists = record.artist;
                itm.dma.year = record.year;
                itm.finished_loading_dma = true;
            });

        },
        getTrackISRC: function() {
            //console.log("getting isrc: %o", this.item.isrc);
            var itm = this;
            axios.get('/api/trackinfo/ISRC/' + this.item.isrc)
            .then(function(response) {
                console.log("got isrc: %o", response);
                let record = response.data.tracks[0];
                itm.isrc.title = record.title;
                itm.isrc.artists = record.artists;
                itm.isrc.year = record.year;
                itm.finished_loading_isrc = true;
            });
        },
        formatList: function(some_list) {
            if(!some_list) return '';
            return some_list.join(", ");
        }
    },
    computed: {
        formattedTimestamp: function() {
            var options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
            return new Date(this.item.timestamp).toLocaleDateString();
        }
    },
    mounted: function () {
        console.log("mounted %o", this);
        this.getTrackDMA();
        this.getTrackISRC();
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
                <th>errors</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <th>
                DMA tracks with ISRC codes
                </th>
                <td>[[ stats.totals.isrc_codes ]] 
                    ([[ calcPercent(stats.totals.isrc_codes, stats.totals.all_records) ]] %) </td>
                <td>[[ stats.status.isrc.false || 0]] 
                    ([[ calcPercent(stats.status.isrc.false, stats.totals.isrc_codes) ]] %) </td>
            </tr>
            <tr>
                <th>
                DMA tracks with EAN codes
                </th>
                <td>[[ stats.totals.ean_codes ]] 
                    ([[ stats.totals.ean_codes, stats.totals.all_records ]] %) </td>
                <td>[[ stats.status.ean.false || 0]] 
                    ([[ calcPercent(stats.status.ean.false || 0, stats.totals.ean_codes) ]] %) </td>
            </tr>
        </tbody>
    </table>

    </div>

    <h3>Errors and discrepancies</h3>

    <table class="table table-striped table-sm">
        <col style="width:45%">
        <col style="width:10%">
        <col style="width:45%"> 
        <thead class="thead-dark">
          <tr>
            <th >DMA</th>
            <th></th>
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