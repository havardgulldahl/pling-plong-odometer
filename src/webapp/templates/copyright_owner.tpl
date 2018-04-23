{% extends "base.tpl" %}


{% block templates %}
<script type="text/x-template" id="ownership-template">
    <tr>
        <td><i>[[ track.metadata.title ]]</i> 
            [[ track.metadata.artist ]] 
            <br><b>Spotify:</b> <span v-if="track.ownership.spotify">[[ track.ownership.spotify.P ]]</span>
            <br><b>Discogs:</b> <span v-for="label in track.ownership.discogs"> ⇝ <a :href="'http://www.discogs.com/label/'+label.id">[[ label.name ]]</a></span>
            <br>Safe to use? <input type=checkbox v-model="track.isSafe" disabled> 
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
        isSafe: function() {
            return false;
        }

    }
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
    console.log('resolve form text input %o', q);
    if(q.match(/(NRKO_|NRKT_|NONRO|NONRT|NONRE)[A-Za-z0-9]{12}/)) {
        //resolve(q, "/resolve/DMA/"+encodeURIComponent(q));
        axios.get("/ownership/DMA/"+encodeURIComponent(q))
            .then(function (response) {
                console.log(response);
                app.items.push({"metadata":response.data.trackinfo, "ownership":response.data.ownership});
            })
            .catch(function (error) {
                console.log(error);
            });
        
    } else if(q.match(/spotify:track:[A-Za-z0-9]{22}/)) { // base62 identifier, spotify URI
        var xhr = new XMLHttpRequest();
        xhr.open("GET", "/ownership/spotify/"+encodeURIComponent(q));
        output.classList.toggle("loading", true);
        output.classList.toggle("text-success", false);
        xhr.onload = function () {
            output.classList.toggle("loading", false);
            if (xhr.status === 200) {
                // add copyright to ui
                var response = JSON.parse(xhr.response);
                console.log("copyright response: %o", response);
                app.items.push(response);
                /*
                var s = "<i>"+response.trackinfo.title+"</i> "+response.trackinfo.artist+"<br><b>Spotify</b>: ";
                s += response.ownership.spotify.P || response.ownership.spotify.C;
                s += "<br><b>Discogs</b>: ";
                if(response.ownership.discogs.length) {
                    var d = response.ownership.discogs;
                    for(var i=0;i<d.length;i++) {
                        s += " ⇝ "+d[i].name;
                    }
                } else {
                    s += i18n.PLEASE_SEARCH_MANUALLY();
                }
                output.classList.toggle("text-success", true);
                output.innerHTML = s;
                */
            } else {
                console.error("copyright error: %o, %o", xhr.status, xhr.response);
                var s = "<br><b>Spotify</b>: "+i18n.PLEASE_SEARCH_MANUALLY()+
                    "<br><b>Discogs</b>: "+i18n.PLEASE_SEARCH_MANUALLY();
                output.innerHTML = s;
            }
        }
        xhr.send();
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