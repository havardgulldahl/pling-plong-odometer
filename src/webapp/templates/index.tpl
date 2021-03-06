{% extends "base.tpl" %}


{% block templates %}
<script type="text/x-template" id="audible-template">
    <tr>
        <td class="filename" :class="{loading: loading, 'text-success':track.resolvable}"> [[ track.clipname ]]</td> <!-- filename -->
        <td class="duration">[[ duration() ]]</td> <!-- duration -->
        <td class="service">  <!-- service selectior -->
            <template v-if="track.music_services.length && !force_select_service">
                <a v-on:click="force_select_service = true;" href="#">[[ track.music_services[0] ]]</a>
            </template>
            <template v-else>
                <select v-model="resolve_using_music_service" 
                        v-on:change="override_music_service()"
                        xclass="form-control form-control-sm">
                    <option disabled value="null">Søk opp i:</option>
                    <option v-for="service in this.$all_music_services" v-bind:value="service">[[ service ]]</option>
                </select>
            </template>
            <template v-if="unknown_track && track.resolvable">
                <button v-on:click="add_missing()"
                        role=button
                        data-i18n-title=report_missing_filename
                        class="translate btn btn-outline-secondary btn-xs">＋</button>
            </template>
        <td class="metadata" :class="{'text-white': errors, 'bg-danger':errors}"> 
            <template v-if="track.metadata !== null">
                <template v-if="track.metadata.productionmusic">
                    <i> [[ track.metadata.copyright ]] </i> ℗ <b> [[ track.metadata.label ]] </b>
                </template>
                <template v-else>
                    <i>[[ track.metadata.title]]</i> [[ track.metadata.artist]] ℗ <b>[[ track.metadata.label]]</b> [[ track.metadata.year]]
                </template>
            </template>
            <span v-else-if="errors">
                [[ errors ]]
            </span>
            <span v-else-if="!track.resolvable" class=text-muted>
                [[ i18n_unknown() ]]
            </span>
            <span v-else class=text-muted> [[ i18n_getting_metadata() ]]</span>
        </td> <!-- track metadata-->
    </tr>
</script>
<script type="text/x-template" id="audible-report-template">
    <div>
        <dt>Title</dt><dd>[[ title() ]]</dd>
        <div v-if="track.metadata && track.metadata.identifier">
            <dt>Track identifier:</dt><dd> [[ track.metadata.identifier ]]</dd>
        </div>
        <div v-if="track.metadata && track.metadata.artist">
            <dt>Artist:</dt><dd> [[ track.metadata.artist ]] </dd>
        </div>
        <div v-if="track.metadata && track.metadata.albumname">
            <dt>Album name:</dt><dd> [[ track.metadata.albumname ]] </dd>
        </div>
        <div v-if="track.metadata && track.metadata.lyricist">
            <dt>Lyricist:</dt><dd> [[ track.metadata.lyricist ]] </dd>
        </div>
        <div v-if="track.metadata && track.metadata.composer">
            <dt>Composer:</dt><dd> [[ track.metadata.composer ]] </dd>
        </div>
        <div v-if="track.metadata && track.metadata.label">
            <dt>Label:</dt><dd> [[ track.metadata.label ]] </dd>
        </div>
        <div v-if="track.metadata && track.metadata.recordnumber">
            <dt>Recordnumber:</dt><dd> [[ track.metadata.recordnumber ]] </dd>
        </div>
        <div v-if="track.metadata && track.metadata.copyright">
            <dt>Copyright owner:</dt><dd> [[ track.metadata.copyright ]] </dd>
        </div>
        <div v-if="track.metadata && track.metadata.year && track.metadata.year !== -1">
            <dt>Released year:</dt><dd> [[ track.metadata.year ]]</dd>
        </div>
        <div v-if="track.metadata">
            <dt>Music Library:</dt><dd>[[ track.metadata.musiclibrary ]]</dd>
        </div>
        <br>
        <b>[[ i18n_seconds_in_total() ]]</b>
        <hr>
    </div>
</script>
<script type="text/x-template" id="audible-credits-template">
    <div v-if="track.metadata">
        <div v-if="track.metadata.productionmusic">
            <i> [[ track.metadata.copyright ]] </i>
        </div>
        <div v-else>
            <i>[[ track.metadata.title]]</i> [[ track.metadata.artist]] ℗ <b>[[ track.metadata.label]]</b> [[ track.metadata.year]]
        </div>
    </div>
</script>
{% endblock templates %}

{% block docscript %}

Vue.component("audible-item", {
    props: ["track"],
    delimiters: ["[[", "]]"],
    template: "#audible-template",
    data: function() {
        return { errors: false,
                 unknown_track: null,
                 loading: false,
                 resolve_using_music_service: null,
                 force_select_service: false
         };
    },
    created: function () {
        //console.log("created %o", this);
        if(this.track.music_services.length > 0) {
            // update detected music service
            this.resolve_using_music_service = this.track.music_services[0];
        }
        // set initial known state
        this.unknown_track = !this.track.resolvable;
        if(this.track.metadata === null) { // get metadata for this object
            this.update_metadata();
        }
    },
    methods: {
        update_metadata: function(override) {
            let force_resolve = override || false;
            // get metadata from api and update this object
            if(!force_resolve && !this.track.resolvable) {
                // cant resolve this track
                //console.log("This trak cannot be resolved: %s", clip.track.clipname);
                return false;
            }
            var clip = this;
            // get metadata url, use the overridden music service or detected music service
            // fall back to default
            var url = clip.track.resolve[clip.resolve_using_music_service] || 
                    clip.track.resolve_other.replace("{music_service}", clip.resolve_using_music_service);
            //console.log("update_metadata for %s from %o", clip.track.clipname, url);
            clip.loading = true;
            axios.get(url)
            .then(function (response) {
                clip.track.metadata = response.data.metadata;
                clip.loading = false;
                if(force_resolve) {
                    // we have overridden the autodetection and gotten a result
                    // update model to reflect this
                    clip.track.resolvable = true;
                    clip.track.music_services[0] = clip.resolve_using_music_service;
                }
                app.finished_tracks += 1;
            })
            .catch(function(error) {
                console.error("metadta error: %o", error);
                clip.errors = error.message;
                clip.loading = false;
                app.finished_tracks += 1;
            });
        }, 
        duration: function() {
            // from odometer.js import formatDuration
            return formatDuration(this.track.audible_length) + "s";
        },
        add_missing: function() {
            // 
            //console.log("music_service_missing %o", this);
            axios.post(this.track.add_missing, data={'item':this.track.clipname})
            .then(function(response) {
                var tinglemodal = setupModal();
                tinglemodal.setContent(i18n.THANK_YOU());
                tinglemodal.open();
                //alertmsg(i18n.THANK_YOU(), "success");
            });
        },
        override_music_service: function() {
            //console.log("override music service: %o", this.resolve_using_music_service);
            let override = true;
            app.tracks_to_resolve += 1;
            this.update_metadata(override);

        },
        i18n_getting_metadata: function() {
            return i18n.GETTING_METADATA();
        },
        i18n_unknown: function() {
            return i18n.UNKNOWN();
        }
    }
});

Vue.component("audible-report-item", {
    props: ["track"],
    delimiters: ["[[", "]]"],
    template: "#audible-report-template",
    methods: {
        title: function() {
            return (this.track.metadata !== null) ? this.track.metadata.title : this.track.clipname;
        },
        i18n_seconds_in_total: function() {
            return i18n.SECONDS_IN_TOTAL({SECONDS:formatDuration(this.track.audible_length)});
        }
    }
});

Vue.component("audible-credits-item", {
    props: ["track"],
    delimiters: ["[[", "]]"],
    template: "#audible-credits-template"
});

var app = new Vue({
    el: '#content',
    data: {
      items: [ ],
      all_tracks: false,
      tracks_to_resolve: 0,
      finished_tracks: 0
    },
    created: function() {
        console.log("Odometer startup");
    },
    delimiters: ["[[", "]]"],
    computed: {
        reportitems: function() {
            // filter through items[] and return the ones that should be included in the report
            var self = this;
            if(self.all_tracks) {
                return self.items;  // return everything
            }
            return self.items.filter(function (item) {
                //console.log("filtering item %o", item);
                return item.resolvable;
            });
        },
        creditsitems: function() {
            // filter through items[] and return the ones that should be included in the credits list
            var self = this;
            var _holders = [];
            return self.items.filter(function (item) {
                if(!item.resolvable || !item.metadata) {
                    return false;
                }
                if(item.metadata.productionmusic===true) {
                    if(_holders.indexOf(item.metadata.copyright) === -1) { // only register once per copyright holder
                        _holders.push(item.metadata.copyright);
                        return true;
                    }
                } else {
                    return true;
                }
            });
        }
    }
  });


    // add debug ui
    if(document.location.search == "?test") {
        var tbtn = document.createElement('button');
        tbtn.innerText = "Use testfile";
        tbtn.onclick = function(event) {
            event.preventDefault();
            document.getElementById('preview').validFile = {name:'testfile',
                                                            lastModifiedDate: new Date()};
            var formData = new FormData();
            formData.append('usetestfile', '1');
            submit(formData);
            return false;
        }
        document.querySelector('div.col-5').appendChild(tbtn);
    }
    var createReportButton = document.getElementById('create-report-button');
    createReportButton.onclick = function(event) {
        event.preventDefault();
        var preview = document.getElementById('preview');
        var filedate = preview.validFile.lastModifiedDate || new Date();
        var filename = preview.validFile.name;
        var html = '<p><code>'+i18n.GENERATED_FROM({FILENAME:filename,
            DATESTRING:filedate.toLocaleString()})+'</code>';
        var tinglemodal = setupModal();
        // add another button
        tinglemodal.addFooterBtn(i18n.DOWNLOAD_AS_FILE(), 'tingle-btn tingle-btn--info', function() {
            // TODO: add html header and date and time
            html = html + document.getElementById("report-tracks").innerHTML;
            download(html, "music_metadata_"+filename+".html", "text/html");
            tinglemodal.close();
        });
        tinglemodal.setContent(html + document.getElementById("report-dialog").innerHTML);
        tinglemodal.open();
    }

    var createCreditsButton = document.getElementById('create-credits-button');
    createCreditsButton.onclick = function(event) {
        event.preventDefault();
        var tinglemodal = setupModal();
        tinglemodal.setContent(document.getElementById("credits-dialog").innerHTML);
        tinglemodal.open();
    }

    var fileSelect = document.getElementById('file-select');
    fileSelect.onchange = function(event) {
        // react to file select changes
        // based on public domain code from https://developer.mozilla.org/en-US/docs/Web/HTML/Element/input/file
        var curFiles = fileSelect.files;
        var preview = document.getElementById('preview');
        if(curFiles.length === 0) {
          preview.innerHTML = "<b>"+i18n.NO_FILES_SELECTED()+"</b>";
        } else {
            var chosenFile = curFiles[0];
            if(!validFileType(chosenFile)) {
                preview.innerText = i18n.NOT_VALID_FILE_TYPE();
                preview.setAttribute('class', 'text-danger');
                // clear any previous file info
                preview.validFile = null;
            } else {
                preview.innerText = i18n.FILE_OK({FILESIZE: returnFileSize(chosenFile.size)});
                preview.setAttribute('title', i18n.FULL_FILE_NAME({FILENAME: chosenFile.name}));
                preview.setAttribute('class', 'text-success');
                // Keep the file info around as a javascript object
                preview.validFile = chosenFile;
                // Create a new FormData object.
                var formData = new FormData();
                // Add the file to the request.
                formData.append('xmeml', chosenFile, chosenFile.name);
                submit(formData)
            }
        }
    }


function dropHandler(ev) {
    // handle a dropped file
    ev.preventDefault();
    document.querySelector('body').classList.remove('dragover');
    // If dropped items aren't files, reject them
    var dt = ev.dataTransfer;
    var preview = document.getElementById('preview');
    var chosenFile;
    // Create a new FormData object.
    if (dt.items) {
        // Use DataTransferItemList interface to access the file(s)
        chosenFile = dt.items[0].getAsFile();
    } else {
        // Use DataTransfer interface to access the file(s)
        chosenFile = dt.files[0];
    }
    if(validFileType(chosenFile)) {
        preview.innerText = slug(chosenFile.name, 25) + ' OK – ' + returnFileSize(chosenFile.size);
        preview.setAttribute('title', i18n.FULL_FILE_NAME({FILENAME:chosenFile.name}));
        preview.setAttribute('class', 'text-success');
        document.getElementById('file-select').value = "";
        // Keep the file info around as a javascript object
        preview.validFile = chosenFile;
        var formData = new FormData();
        formData.append('xmeml', chosenFile, chosenFile.name);
        submit(formData);
    } else {
        alertmsg(i18n.NOT_VALID_FILE_TYPE(), "danger");
        // Clear any previous file info|
        preview.validFile = null;
    }
  }

  function dragoverHandler(ev) {
    //console.log("dragOver");
    // Prevent default select and drag behavior
    ev.preventDefault();
    document.querySelector('body').classList.add('dragover');
    window.setTimeout(function() {
        document.querySelector('body').classList.remove('dragover');
    }, 10000)
  }

  function dragendHandler(ev) {
    //console.log("dragEnd");
    document.querySelector('body').classList.remove('dragover');
    // Remove all of the drag data
    var dt = ev.dataTransfer;
    if (dt.items) {
      // Use DataTransferItemList interface to remove the drag data
      for (var i = 0; i < dt.items.length; i++) {
        dt.items.remove(i);
      }
    } else {
      // Use DataTransfer interface to remove the drag data
      ev.dataTransfer.clearData();
    }
  }

function submit(formData) {
    // send the already prepared form data to the json endpoint for analysis
    var is_resolvable = function(itm) {
        return itm.resolvable;
    };

    // Send the Data.
    axios.post("/api/analyze", formData)
    .then(function (response) {
        //console.log('got audio response: %o', response.data);
        app.items = response.data.audioclips.map(function(clip) {
            clip.metadata = null; // this is where we put the Trackmetadata structure later
            return clip;
        });
        //startProgress((app.items.filter(is_resolvable)).length);
        app.tracks_to_resolve = (app.items.filter(is_resolvable)).length;
        // reset counter
        app.finished_tracks = 0;
    })
    .catch(function(error) {
        console.error("analysis error: %o", error);
        alertmsg(i18n.ALERTMSG({ERRCODE:"XX", ERRMSG:error}, 'danger'));
    });
}

{% endblock docscript %}

{% block bodyhandlers %}
    ondrop="dropHandler(event);" 
    ondragover="dragoverHandler(event);" 
    ondragend="dragendHandler(event);"
{% endblock bodyhandlers %}

{% block content %}
<div id=content>
    <form id="file-form" class="form" 
          enctype="multipart/form-data" action="/api/analyze" method="POST">
        <div class="form-row">
            <div class="col-3">
                <input type="file" 
                    data-intro="Start med å laste opp en xml-fil fra Premiere her."
                    data-position="right"
                    data-step=1
                    class="form-control translate" 
                    id="file-select" 
                    title="Choose timeline data (XMEML)" data-i18n-title=choose_timeline_data
                    accept=".xml,text/xml,application/xml"
                    name="xmeml">
            </div>
            <div class="col-5">
                <label for=id-select id="preview" class="text-secondary col-form-label">⇜ <span class=translate data-i18n=please_select_file>Please select a file</span> </label>
            </div>
            <div class="col-4"
                 data-step=3
                 data-intro="Så kan du lage rapport eller rulletekst med disse knappene">
                <button type="button" 
                        v-bind:disabled="tracks_to_resolve == 0 || finished_tracks != tracks_to_resolve"
                        class="btn btn-primary translate" 
                        id="create-report-button" 
                        data-i18n=generate_metadata_report>Generate metadata report</button>
                <button type="button" 
                        v-bind:disabled="tracks_to_resolve == 0 || finished_tracks != tracks_to_resolve"
                        class="btn btn-primary translate" 
                        id="create-credits-button" 
                        data-i18n=generate_end_credits>Generate credits</button>
            </div>
        </div>
    </form>

    <table class="table table-striped table-sm">
        <col style="width:40%">
        <col style="width:10%">
        <col style="width:10%">
        <col style="width:60%">
        <thead class="thead-dark">
          <tr>
            <th class=translate title="File name" data-i18n=name data-i18n-title=filename>name</th>
            <th class=translate title="Measured in seconds" 
                data-i18n=duration data-i18n-title=measured_in_seconds 
                style="text-align: right">audible length</th>
            <th class=translate title="Music library" data-i18n-title=music_library>℗</th>
            <th>
                <template v-if="finished_tracks == tracks_to_resolve">
                    <span class=translate data-i18n=metadata id=thead-metadata>metadata</span>
                </template>
                <template v-else>
                    <progress id=progress 
                              v-bind:value="finished_tracks"
                              class=align-bottom 
                              v-bind:max="tracks_to_resolve"
                    >
                </template>
            </th>
          </tr>
        </thead>
        <tbody id=files-list 
               style="font-size:80%" 
               data-step=2
               data-intro="Når du har lastet inn xml-fila, kommer alle musikksporene automatisk opp her.">
            <template v-if="items.length">
            <audible-item v-for="item in items" 
                          v-bind:key="item.clipname"
                          v-bind:track="item">
            </audible-item>
            </template>
            <tr v-else>
                <td><span style="font-size: 150%;" data-i18n=startinfo class=translate>To get started: Select an XMEML file—exported from Adobe Premiere or Final Cut Pro 7.x. (You may also drop it anywhere in this window).</span> <td><td><td>
            </tr>
        </tbody>

    </table>
    <div style="display: none">
        <dialog id=report-dialog>
            <div class="form-check" style="display: none">
                <input class="form-check-input" type="checkbox" value="" id="check_all_tracks" model="all_tracks">
                <label class="form-check-label" for="defaultCheck1">
                    Include all audio tracks: [[ all_tracks ]]
                </label>
            </div>
            <div id=report-tracks>
                <audible-report-item v-for="item in reportitems"
                    v-bind:key="item.clipname"
                    v-bind:track="item">
                </audible-report-item>
            </div>
        </dialog>
        <dialog id=credits-dialog>
            <div id=credits-tracks>
                <audible-credits-item v-for="item in creditsitems"
                    v-bind:key="item.clipname"
                    v-bind:track="item">
                </audible-credits-item>
            </div>
        </dialog>
    </div>
 </div>   
 {% endblock content %}