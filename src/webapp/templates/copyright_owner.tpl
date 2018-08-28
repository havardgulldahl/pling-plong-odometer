{% extends "base.tpl" %}


{% block templates %}
<script type="text/x-template" id="ownership-template">
    <tr>
        <td :class="{loading: !track.ownership.spotify}">
            <i>«[[ track.metadata.title ]]»</i> —
            [[ artists ]] 
            <br><b>Spotify:</b> <span v-if="track.ownership.spotify">[[ copyright ]]</span>
            <br><b>Discogs:</b> <span v-for="label in track.ownership.discogs"> ⇝ <a target=_blank :href="'http://www.discogs.com/label/'+label.id">[[ label.name ]]</a></span>
              <i v-if="track.ownership.spotify &amp;&amp; !track.ownership.discogs" class=translate data-i18n=NOT_FOUND>Not found </i>
        </td>
        <td class=align-middle >
            <div v-if="track.ownership.spotify" >
            <button type="button" 
                    disabled 
                    class="btn active"
                    :class="licenses.style">[[licenses.result]]</button>
            <i v-if="licenses.reason">[[licenses.reason]]</i>
            </div>
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
                updateProgress(1);

            })
            .catch(function(error) {
                inputelement.classList.toggle("loading", false);
                console.error("copyright error: %o", error);
                track.ownership.spotify = {"P" : i18n.PLEASE_SEARCH_MANUALLY()};
                updateProgress(1);
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
        },
        licenses : function() {
            console.log("check licenses: %o", this.track.licenses);
            var status = { "style": "btn-warning",
                           "result": "check",
                           "reason": ""}; // baseline status object 
            var lic, must_check = false, seems_ok = false, reasons = [];
            for(var i=0; i<this.track.licenses.length; i++) {
                lic = this.track.licenses[i]; // shortcut
                if(lic.license_status == "NO") {
                    status["result"] = TEXT_NO;
                    status["style"] = "btn-danger";
                    status["reason"] = lic.source;
                    return status; // one 'no' trumps all other licenses
                }
                if(lic.license_status == "CHECK") {
                    must_check = true;
                    reasons.push(lic.source);
                }
                else if(lic.license_status == "OK") {
                    reasons.push(lic.source);
                    seems_ok = true;
                }
            }
            if(seems_ok && !must_check) {
                // one or more license rules say yes, and none say we must check
                status["result"] = TEXT_OK;
                status["style"] = "btn-success";
                status["reason"] = reasons.join(", ");
            } else {
                // undetermined, or specifically must check
                status["result"] = TEXT_CHECK;
                status["style"] = "btn-warning";
                status["reason"] = reasons.join(", ");
            }
            return status;
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
            // start progressbar
            startProgress(i);

        })
        .catch(function(error) {
            inputelement.classList.toggle("loading", false);
            console.error("copyright error: %o", error);
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
            <div class="col-4">
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