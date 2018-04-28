{% extends "base.tpl" %}


{% block templates %}
<script type="text/x-template" id="ownership-template">
    <tr>
        <td><i>«[[ track.metadata.title ]]»</i> —
            [[ track.metadata.artist ]] <span v-if="!track.ownership.spotify" class=loading>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span>
            <br><b>Spotify:</b> <span v-if="track.ownership.spotify">[[ copyright ]]</span>
            <br><b>Discogs:</b> <span v-for="label in track.ownership.discogs"> ⇝ <a :href="'http://www.discogs.com/label/'+label.id">[[ label.name ]]</a></span>
            <br>Safe to use? <input type=checkbox v-model="isLicensed" disabled> 
        </td>
    </tr>
</script>
{% endblock templates %}

{% block docscript %}

Vue.component("ownership-item", {
    props: ["track"],
    delimiters: ["[[", "]]"],
    template: "#ownership-template",
    methods: {
        update_ownership: function() {
            //console.log("update %o spotify", this);
            var inputelement = this.$el;
            var track = this.track;
            inputelement.classList.toggle("loading", true);
            axios.get("/ownership/spotify/"+encodeURIComponent(track.spotify.uri))
            .then(function (response) {
                inputelement.classList.toggle("loading", false);
                // add copyright to ui
                console.log("copyright response: %o", response);
                track.ownership = response.data.ownership;
            })
            .catch(function(error) {
                inputelement.classList.toggle("loading", false);
                console.error("copyright error: %o", error);
                track.ownership.spotify = {"P" : i18n.PLEASE_SEARCH_MANUALLY()};
            });
        }
    },
    computed: {
        copyright: function() {
            return this.track.ownership.spotify.P || this.track.ownership.spotify.C;
        },
        isLicensed: {
            get: function() {
                return false;
            }
        }
    },
    mounted: function () {
        //console.log("mounted %o", this);
        if(isEmpty(this.track.ownership)) { // get ownership details for this object
            this.update_ownership();
        }
    },
  });

var app = new Vue({
    el: '#content',
    data: {
      ownership: 'Hello Vue!',
      items: []
    },
    delimiters: ["[[", "]]"]
  });

function resolve_manually_delay(inputelement) {
    // add a delay so we dont run this while typing
    if(resolve_manually_delay.tick) {
        window.clearTimeout(resolve_manually_delay.tick);
    }
    resolve_manually_delay.tick = window.setTimeout(function() {
        resolve_manually(inputelement);
    },
    900 );
}

function resolve_manually(inputelement) {
    // resolve from text input
    var q = inputelement.value;
    app.items = []; // empty list
    console.log('resolve form text input %o', q);
    if(q.match(/(NRKO_|NRKT_|NONRO|NONRT|NONRE)[A-Za-z0-9]{12}/)) {
        inputelement.classList.toggle("loading", true);
        axios.get("/ownership/DMA/"+encodeURIComponent(q))
            .then(function (response) {
                console.log(response);
                inputelement.classList.toggle("loading", false);
                app.items.push({"metadata":response.data.trackinfo, "ownership":response.data.ownership});
            })
            .catch(function (error) {
                console.log(error);
            });
        
    } else if(q.match(/spotify:track:[A-Za-z0-9]{22}/)) { // base62 identifier, spotify track URI
        inputelement.classList.toggle("loading", true);
        //inputelement.classList.toggle("text-success", false);
        axios.get("/ownership/spotify/"+encodeURIComponent(q))
            .then(function (response) {
                inputelement.classList.toggle("loading", false);
                // add copyright to ui
                console.log("copyright response: %o", response);
                app.items.push({"metadata":response.data.trackinfo, "ownership":response.data.ownership});
            })
            .catch(function(error) {
                inputelement.classList.toggle("loading", false);
                console.error("copyright error: %o, %o", error, error);
                var s = "<br><b>Spotify</b>: "+i18n.PLEASE_SEARCH_MANUALLY()+
                    "<br><b>Discogs</b>: "+i18n.PLEASE_SEARCH_MANUALLY();
                output.innerHTML = s;
            })
    } else if(q.match(/spotify:user:[a-z]+:playlist:[A-Za-z0-9]{22}/)) { // base62 identifier, spotify playlist URI
        inputelement.classList.toggle("loading", true);
        axios.get("/tracklist/spotify/"+encodeURIComponent(q))
            .then(function (response) {
                inputelement.classList.toggle("loading", false);
                // add copyright to ui
                console.log("tracklist response: %o", response);
                var tracks = response.data.tracks;
                var t;
                for(var i=0;i<tracks.length;i++) {
                    t = tracks[i];
                    app.items.push({"metadata":{"title":t.title, "artist":t.artist}, 
                                    "ownership": {},
                                    "spotify": {"album_uri": t.album_uri, "uri": t.uri}});
                }

            })
            .catch(function(error) {
                inputelement.classList.toggle("loading", false);
                throw(error);
            });
    }
    // no known resolver
    return false;
}
{% endblock docscript %}

{% block content %}
<div id=content>
    <form id="ownership-form" class="form" onsubmit="return false">
        <div class="form-row">
            <div class="col-3">
                <input id=ownership-input placeholder="Type or paste here" class=form-control 
                    type=search oninput="if(this.value.length>5) {resolve_manually_delay(this);}"
                    autocomplete=off autocorrect=off v-model="ownership">
            </div>
            <div class="col-9">
                <span id="helptext" class="text-secondary">Please enter a Spotify or DMA id</span>
                <a href=# onclick="document.getElementById('ownership-input').value='NONRE656509HD0001'">Try it</a>
            </div>
        </div>
    </form>

    <table class="table table-striped table-sm">
        <!-- <col style="width:40%">
        <col style="width:10%">
        <col style="width:10%"> -->
        <col style="width:100%">
        <thead class="thead-dark">
          <tr>
            <th id=thead-results>results</th>
          </tr>
        </thead>
        <tbody id=results-list style="font-size:80%">
          <template v-if="items.length">
          <ownership-item v-for="item in items" 
                          v-bind:track="item"
                          v-bind:key="item.original_query">
          </ownership-item>
          </template>
          <tr v-else>
            <td><b>To get started: Write or type a Spotify or DMA id above</b></td>
          </tr>
        </tbody>

    </table>
</div>
{% endblock content %}