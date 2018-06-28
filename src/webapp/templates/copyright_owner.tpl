{% extends "base.tpl" %}


{% block templates %}
<script type="text/x-template" id="ownership-template">
    <tr>
        <td><i>«[[ track.metadata.title ]]»</i> —
            [[ artists ]] <span v-if="!track.ownership.spotify" class=loading>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span>
            <br><b>Spotify:</b> <span v-if="track.ownership.spotify">[[ copyright ]]</span>
            <br><b>Discogs:</b> <span v-for="label in track.ownership.discogs"> ⇝ <a target=_blank :href="'http://www.discogs.com/label/'+label.id">[[ label.name ]]</a></span>
        </td>
        <td>
            <ul v-if="track.licenses.length > 0">
                <li v-for="lic in track.licenses" :key="lic.id"> [[ lic.source]]: [[lic.license_property]]=[[ lic.license_status ]] ([[ lic.comment ]])</li>
            </ul>
        </td>
    </tr>
</script>
{% endblock templates %}

{% block headscript %}
<script type="text/javascript">

function try_click(el, txt, val) {
    // generate string for link for interactive testing
    var title = i18n.TRY_IT();
    var text = txt.toLowerCase();
    return "<a href=# title='"+title+"' onclick='resolve_manually_delay(document.getElementById(\""+el+"\"));app.ownership=\""+val+"\";'>"+text+"</a>";
}

document.addEventListener("DOMContentLoaded", function(event) {
    document.getElementById("helptext").innerHTML = i18n.OWNERSHIP_HELPTEXT({DMA:try_click("ownership-input", i18n.TRACK(), "NONRE656509HD0001"),
                                                                             SPOTIFY_TRACK:try_click("ownership-input", i18n.TRACK(), "spotify:track:7wxSkft3f6OG3Y3Vysd470"),
                                                                             SPOTIFY_LIST:try_click("ownership-input", i18n.PLAYLIST(), "spotify:user:hgulldahl:playlist:0LZO2ZfDhOw4bV4majJ13N")});
});
</script>
{% endblock headscript %}


{% block docscript %}

Vue.component("ownership-item", {
    props: ["track"],
    delimiters: ["[[", "]]"],
    template: "#ownership-template",
    methods: {
        update_ownership: function() {
            //get copyright, ownership and license info about this track
            var inputelement = this.$el;
            var track = this.track;
            inputelement.classList.toggle("loading", true);
            axios.post("/api/ownership/", track)
            .then(function (response) {
                inputelement.classList.toggle("loading", false);
                // add copyright to ui
                console.log("copyright response: %o", response);
                track.ownership = response.data.ownership;
                // check license
                track.licenses = response.data.licenses;

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
        artists : function() {
            if(this.track.metadata.artists === undefined || this.track.metadata.artists.length === 0) {
                return this.track.metadata.artist;
            } 
            return this.track.metadata.artists.join(", ");
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
      ownership: document.location.search.slice(1), // empty string or query string
      items: []
    },
    created: function() {
        console.log("startup");
        var input = document.getElementById("ownership-input");
        input.value = document.location.search.slice(1); // empty string or query string
        console.log("search: %o", input.value);
        resolve_manually_delay(input);
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
    return true;
}

function resolve_manually(inputelement) {
    // resolve from text input
    var uri, q = inputelement.value;
    app.items = []; // empty list
    if(q.length===0) return; // empty query
    //console.log('resolve form text input %o', q);
    if(q.match(/(NRKO_|NRKT_|NONRO|NONRT|NONRE)[A-Za-z0-9]{12}/)) {
        uri = "/api/trackinfo/DMA/"+encodeURIComponent(q);
    } else if(q.match(/spotify:track:[A-Za-z0-9]{22}/)) { // base62 identifier, spotify track URI
        uri = "/api/trackinfo/spotify/"+encodeURIComponent(q);
    } else if(q.match(/spotify:album:[A-Za-z0-9]{22}/)) { // base62 identifier, spotify album URI
        // spotify:album:40yTsvA7raOkdbeJfC6Hsc
        uri = "/api/albuminfo/spotify/"+encodeURIComponent(q);
    } else if(q.match(/spotify:user:[A-Za-z0-9]+:playlist:[A-Za-z0-9]{22}/)) { // base62 identifier, spotify playlist URI
        uri = "/api/tracklistinfo/spotify/"+encodeURIComponent(q);
    }
    if(uri===undefined) {
        console.warn("uri not recognised");
        return;
    }
    inputelement.classList.toggle("loading", true);
    axios.get(uri)
        .then(function (response) {
            inputelement.classList.toggle("loading", false);
            // add copyright to ui
            console.log("tracklist response: %o", response);
            var tracks = response.data.tracks;
            var t;
            for(var i=0;i<tracks.length;i++) {
                t = tracks[i];
                app.items.push({"metadata":{"title":t.title, "artists":t.artists, "artist":t.artist}, 
                                "ownership": {},
                                "licenses": [],
                                "spotify": {"album_uri": t.album_uri, "uri": t.uri}});
            }
            // add reference to history
            window.history.pushState(null, null, "/copyright_owner?"+q);

        })
        .catch(function(error) {
            inputelement.classList.toggle("loading", false);
            console.error("copyright error: %o", error);
            alertmsg(error, "warning");
        });

    // no known resolver
    return false;
}
{% endblock docscript %}

{% block content %}
<div id=content>
    <form id="ownership-form" class="form" onsubmit="return false">
        <div class="form-row">
            <div class="col-3">
                <input 
                    id=ownership-input 
                    placeholder="Type or paste here" data-i18n-placeholder=type_or_paste_here 
                    class="form-control translate" 
                    type=search 
                    oninput="if(this.value.length>5) {resolve_manually_delay(this);}"
                    autocomplete=off 
                    autocorrect=off 
                    v-model="ownership">
            </div>
            <div class="col-9">
                <label for=ownership-input class="col-form-label text-secondary"> ⇜
                    <span id="helptext" class="text-secondary">Please enter a Spotify or DMA id</span>
                </label>
            </div>
        </div>
    </form>

    <table class="table table-striped table-sm">
        <!-- <col style="width:40%">
        <col style="width:10%"> -->
        <col style="width:70%">
        <col style="width:30%">
        <thead class="thead-dark">
          <tr>
            <th data-i18n=results class=translate>results</th>
            <th data-i18n=license class=translate>license</th>
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
            <td><span style="font-size: 150%;" data-i18n=startinfo_ownership class=translate>To get started: Write or type a Spotify or DMA id above</span></td>
            <td></td>
          </tr>
        </tbody>

    </table>
</div>
{% endblock content %}