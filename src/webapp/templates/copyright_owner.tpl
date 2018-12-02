{% extends "base.tpl" %}


{% block templates %}
<script type="text/x-template" id="ownership-template">
    <tr>
        <td :class="{loading: !finished_loading}">
            <i>«[[ track.metadata.title ]]»</i> —
            [[ artists ]] 
            <br><b>Spotify:</b> <span class=spotify v-if="track.ownership.spotify">[[ copyright ]]
                <a class=spotifylink title="copy spotify uri" v-on:click.prevent="clipboard(track.spotify.uri)"></a></span>
                <span v-else class="translate text-danger" data-i18n=NOT_FOUND>Not found</span>
            <br><b>Discogs:</b> 
                <span class=text-muted v-if="track.ownership.spotify">[[ prettycopyright ]]</span> 
                <span v-for="label in track.ownership.discogs"> ⇝ <a target=_blank :href="'http://www.discogs.com/label/'+label.id">[[ label.name ]]</a></span>
                <span v-if="track.ownership.spotify &amp;&amp; !track.ownership.discogs" class="translate text-danger" data-i18n=NOT_FOUND>Not found</span>
        </td>
        <td class=align-middle >
            <div v-if="finished_loading" >
              <button type="button" 
                      disabled 
                      class="btn active"
                      :class="licenses.style">[[licenses.result]]</button>
              <i v-if="licenses.reason">[[licenses.reason]]</i>
              <!-- TODO: reenable this a v-if="track.licenses.result=='CHECK'" href=#>slik sjekker du</a -->
            </div>
            <div v-if="errors">
              <button type="button" 
                      class="btn active btn-danger"
                      v-on:click="update_ownership">Lookup failed. Click to retry</button>

              </button>
	    </div>
        </td>
    </tr>
</script>
{% endblock templates %}

{% block headscript %}
<style type="text/css">
    .spotify .spotifylink {
        visibility: hidden;
    }

    .spotify:hover .spotifylink {
        visibility: visible;
    }
    
    .spotifylink::after {
        background-image: url(/media/icon-link.png);
        background-size: 15px 15px;
        display: inline-block;
        content: "";
	width: 15px;
	height: 15px;
    }

</style>
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

function startProgress(max) {
    // set up a progress bar, with max=max
    //console.log("set up a progress bar, with max=%o", max);
    var parent = document.getElementById("th-license");
    parent.origText = parent.innerText;
    parent.innerHTML = "<progress max="+max+" id=progress value=0 class=align-bottom></progress>";
}

function updateProgress(count) {
    //console.log('updating progress bar with count=%o', count);
    var p = document.getElementById('progress');
    if(!p) return; // progress element is only there with multiple resolves # TODO: FIX THIS
    var newval = parseInt(p.getAttribute('value'))+count;
    if(newval == p.getAttribute('max')) {
        // all resolve tasks are finished, remove progressbar
        //console.log("all resolve tasks are finished, remove progressbar");
        p.parentElement.innerText = p.parentElement.origText;
    } else {
        p.setAttribute('value', newval);
    }
}

function ownershipdialog() {
    var tinglemodal = setupModal();
    var html = document.getElementById("ownership-dialog").innerHTML;

    // add another button
    tinglemodal.addFooterBtn(i18n.DOWNLOAD_AS_FILE(), 'tingle-btn tingle-btn--info', function() {
        // TODO: add html header and date and time
        download(html, "music_ownership.html", "text/html");
        tinglemodal.close();
    });
    tinglemodal.setContent(html);
    tinglemodal.open();
}

</script>
{% endblock headscript %}


{% block docscript %}

var TEXT_OK=i18n.LICENSE_OK();
var TEXT_NO=i18n.LICENSE_NO();
var TEXT_CHECK=i18n.LICENSE_CHECK();

Vue.component("ownership-item", {
    props: ["track"],
    delimiters: ["[[", "]]"],
    template: "#ownership-template",
    data: function() {
        return { errors: false,
                 finished_loading: false 
                };
    },
    methods: {
        update_ownership: function() {
            //get copyright, ownership and license info about this track
            var inputelement = this.$el;
            var track = this.track;
            var that = this;
            inputelement.classList.toggle("loading", true);
            this.finished_loading = false;
            axios.post("/api/ownership/", track)
                .then(function (response) {
                    inputelement.classList.toggle("loading", false);
                    that.set_errors(false);
                    // add copyright to ui
                    //console.log("copyright response: %o", response);
                    track.ownership = response.data.ownership;
                    // check license
                    track.licenses = response.data.licenses;

                    updateProgress(1);
                    that.finished_loading = true;

                })
                .catch(function(error) {
                    inputelement.classList.toggle("loading", false);
                    inputelement.firstChild.classList.toggle("loading", false);
                    console.error("copyright error: %o", error);
                    track.ownership.spotify = {"P" : i18n.PLEASE_SEARCH_MANUALLY()};
                    that.set_errors(true);
                    alertmsg(error);
                    updateProgress(1);
                    that.finished_loading = true;
                });
        },
	set_errors : function(state) {
            //console.log("set errors on %o", this.track);
            return this.errors = state;
        },
	clipboard : function(txt) {
	    console.log("clipboard copy %o", txt);
        var copyElement = document.createElement('input');      
	    copyElement.setAttribute('type', 'text');   
	    copyElement.setAttribute('value', txt);    
	    copyElement = document.body.appendChild(copyElement);   
	    copyElement.select();   
	    document.execCommand('copy');   
	    copyElement.remove();
	    alertmsg(" -"+txt+"- was copied to the clipboard");
        }
    },
    computed: {
        prettycopyright: function() {
            return this.track.ownership.spotify.parsed_label || this.track.ownership.spotify.P || this.track.ownership.spotify.C;
        },
        copyright: function() {
            return this.track.ownership.spotify.P || this.track.ownership.spotify.C;
        },
        artists : function() {
            if(this.track.metadata.artists === undefined || this.track.metadata.artists.length === 0) {
                return this.track.metadata.artist;
            } 
            return this.track.metadata.artists.join(", ");
        },
        licenses : function() {
            //console.log("check licenses: %o", this.track.licenses);
            var lic = this.track.licenses;
            var txtmap = { "NO": TEXT_NO,
                           "CHECK": TEXT_CHECK,
                           "OK": TEXT_OK};
            var stylemap = { "NO": "btn-danger",
                             "CHECK": "btn-warning",
                             "OK": "btn-success"};

            return status = { "style": stylemap[lic.result],
                              "result": txtmap[lic.result],
                              "reason": (lic.reasons && lic.reasons.join(", "))}; 
	    }
    },
    mounted: function () {
        //console.log("mounted %o", this);
        if(isEmpty(this.track.ownership)) { // get ownership details for this object
            this.update_ownership();
        }
    }
  });

var app = new Vue({
    el: '#content',
    data: {
      ownership: document.location.search.slice(1), // empty string or query string
      items: [
        /* mock data for testing 
            { licenses: [],
              spotify: {
                album_uri : "spotify:album:0tgsACxUMuBElueq2YRe1K",
                uri : "spotify:track:7wxSkft3f6OG3Y3Vysd470" 
              },
              metadata: {
                artists : [ "Loyle Carner", "Rebel Kleff"],
                title : "NO CD"
              },
              ownership: {

              }
            }
        */
      ]
    },
    created: function() {
        console.log("startup");
        var input = document.getElementById("ownership-input");
        input.value = document.location.search.slice(1); // empty string or query string
        console.log("search: %o", input.value);
        if(input.value.length>0) {
            resolve_manually_delay(input);
        }
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
    var uri, q = inputelement.value.trim();
    app.items = []; // empty list
    if(q.length===0) return; // empty query
    //console.log('resolve form text input %o', q);
    // normalize urls
    if(q.startsWith("https://open.spotify.com/")) {
        var u = new URL(q);
        q = "spotify" + u.pathname.replace(/\//g, ":");
    }
    if(q.match(/(NRKO_|NRKT_|NONRO|NONRT|NONRE)[A-Za-z0-9]{12}/)) {
        uri = "/api/trackinfo/DMA/"+encodeURIComponent(q);
    } else if(q.match(/spotify:track:[A-Za-z0-9]{22}/)) { // base62 identifier, spotify track URI
        // spotify:track:1oa2KQncbIY0ESKeRdF7xQ
        // https://open.spotify.com/track/1oa2KQncbIY0ESKeRdF7xQ?si=0X_34-_bTum8pNx5YivcJA
        uri = "/api/trackinfo/spotify/"+encodeURIComponent(q);
    } else if(q.match(/spotify:album:[A-Za-z0-9]{22}/)) { // base62 identifier, spotify album URI
        // spotify:album:40yTsvA7raOkdbeJfC6Hsc
        // https://open.spotify.com/album/5MgPPDk6kwQJy548kjal6e?si=ZAkISLSpStWCO4s3JAvODw
        uri = "/api/albuminfo/spotify/"+encodeURIComponent(q);
    } else if(q.match(/spotify:user:[A-Za-z0-9]+:playlist:[A-Za-z0-9]{22}/)) { // base62 identifier, spotify playlist URI
        // https://open.spotify.com/user/jimjemi/playlist/0ebeFbfnBKhWqAHEpSFucn?si=0ahYYjGCQ7yI-BPeUy3rzg
        // spotify:user:jimjemi:playlist:0ebeFbfnBKhWqAHEpSFucn
        uri = "/api/tracklistinfo/spotify/"+encodeURIComponent(q);
    }
    if(uri===undefined) {
        console.warn("uri not recognised");
        alertmsg(i18n.NOT_VALID_FILE_TYPE(), "warning");
        return;
    }
    inputelement.classList.toggle("loading", true);
    axios.get(uri)
        .then(function (response) {
            inputelement.classList.toggle("loading", false);
            // add copyright to ui
            //console.log("tracklist response: %o", response);
            var tracks = response.data.tracks;
            var t;
            for(var i=0;i<tracks.length;i++) {
                if(i==50) {
                    console.warn("max 50 items in playlist");
                    alertmsg(i18n.MAX_50_ITEMS_IN_PLAYLIST(), "warning");
                    break;
                }
                t = tracks[i];
                app.items.push({"metadata":{"title":t.title, "artists":t.artists, "artist":t.artist, "year":t.year}, 
                                "ownership": {},
                                "licenses": [],
                                "spotify": {"album_uri": t.album_uri, "uri": t.uri}});
            }
            // add reference to history
            window.history.pushState(null, null, "/copyright_owner?"+q);
            // start progressbar
            startProgress(i);

        })
        .catch(function(error) {
            inputelement.classList.toggle("loading", false);
            console.error("tracklist error: %o", error);
            alertmsg(error, "warning");
        });

    // no known resolver
    return false;
}

var createReportButton = document.getElementById('generate-ownership-button');
createReportButton.onclick = function(event) {
    event.preventDefault();
    ownershipdialog();
}

{% endblock docscript %}

{% block content %}
<div id=content>
    <form id="ownership-form" class="form" onsubmit="return false">
        <div class="form-row">
            <div class="col-3">
                <input 
                    id=ownership-input 
                    data-intro="Start by typing or pasting a reference from DMA or Spotify."
                    data-i18n-intro="INTRO_OWNERSHIP_INPUT_REFERENCE"
                    data-step=1
                    data-position=right
                    placeholder="Type or paste here" data-i18n-placeholder=type_or_paste_here 
                    class="form-control translate" 
                    type=search 
                    oninput="if(this.value.length>5) {resolve_manually_delay(this);}"
                    autocomplete=off 
                    autocorrect=off 
                    v-model="ownership">
            </div>
            <div class="col-5">
                <label for=ownership-input class="col-form-label text-secondary"> ⇜
                    <span id="helptext" class="text-secondary">Please enter a Spotify or DMA id</span>
                </label>
            </div>
            <div class="col-4"
                 data-step=3
                 class=translate
                 data-i18n-intro="INTRO_OWNERSHIP_REPORT"
                 data-intro="This is where you make the ownership report. You need that for every track you've used.">
                <button type=button class="btn btn-primary translate" 
                        id=generate-ownership-button
                        data-i18n="GENERATE_OWNERSHIP_REPORT">Generate ownership report</button>
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
            <th data-i18n=license class=translate id=th-license>license</th>
          </tr>
        </thead>
        <tbody id=results-list 
               data-step=2
               data-i18n-intro="INTRO_OWNERSHIP_RESULTS_LIST"
               class=translate
               data-intro="The copyright owner of each track will show up in this list."
               style="font-size:80%">
          <template v-if="items.length">
          <ownership-item v-for="(item, index) in items" 
                          v-if="index &lt; 50"
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
<div style="display:none">
    <dialog id="ownership-dialog">

        <h1 class=translate data-i18n="OWNERSHIP_REPORT_TITLE">Ownership report</h1>
        <p class=translate data-i18n-html="OWNERSHIP_REPORT_BODY">
            YOUR HELP IS NEEDED!
            <br>This will become a full bodied report on the current copyright owners 
            of the music you have examined. You can help shape how it looks!
            <br>
            Use the <i>Feedback</i> button and send a message to the Odometer squirrels 
            on what you need from this report. Thanks!
        </p>
    </dialog>
</div>
{% endblock content %}
