// odometer.js

function secs2timestring(duration) {
    // takes an integer of seconds, responds with a "mm:ss" timestring
    var mins = parseInt(duration / 60);
    var secs = duration % 60;
    return mins.toString() + ":" + secs.toString();
}

function slug(s, len) {
    // make sure text is not longer than len (default: 15) and return with ellipsis
    len = len || 15;
    if(s.length < len) return s;
    return s.substr(0, len-1) + "…";
}

// ucs-2 string to base64 encoded ascii
function utoa(str) {
    return window.btoa(unescape(encodeURIComponent(str)));
}
// base64 encoded ascii to ucs-2 string
function atou(str) {
    return decodeURIComponent(escape(window.atob(str)));
}

// check if an object is empty -- https://stackoverflow.com/a/34491966
function isEmpty(obj) {
    for (var x in obj) { if (obj.hasOwnProperty(x))  return false; }
    return true;
 }

function formatDuration(numbr) {
    // retun all duration numbers the same way and formatted according to locale
    // TODO: get locale dynamically (with translations)
    return numbr.toLocaleString("no", {"minimumIntegerDigits":1, "minimumFractionDigits":2});
}

function removeChildren(node) {
    while(node.hasChildNodes()) {
        node.removeChild(node.firstChild);
    }
}

function startProgress(max) {
   //console.log('creating progress bar with max=%o', max);
   document.getElementById('thead-metadata').innerHTML = "<progress id=progress value=0 class=align-bottom max="+max+"></progress>";
}

function updateProgress(val) {
    //console.log('updating progress bar with val=%o', val);
    var p = document.getElementById('progress');
    if(!p) return; // progress element is only there with multiple resolves # TODO: FIX THIS
    var newval = parseInt(p.getAttribute('value'))+val;
    if(newval == p.getAttribute('max')) {
        // all resolve tasks are finished, remove progressbar
        p.parentElement.innerText = i18n.METADATA();
        finishedResolving();
    } else {
        p.setAttribute('value', newval);
    }
}

function returnFileSize(number) {
    if(number < 1024) {
      return number + 'bytes';
    } else if(number > 1024 && number < 1048576) {
      return (number/1024).toFixed(1) + 'KB';
    } else if(number > 1048576) {
      return (number/1048576).toFixed(1) + 'MB';
    }
}

var fileTypes = [
    'text/xml',
    'application/xml'
  ]
  
function validFileType(file) {
    for(var i = 0; i < fileTypes.length; i++) {
        if(file.type === fileTypes[i]) {
        return true;
        }
    }
    return false;
}

function setupModal() {
    // create empty modal for later
    tinglemodal = new tingle.modal({
        footer: true,
        stickyFooter: true,
        closeLabel: i18n.CLOSE(),
        closeMethods: ['overlay', 'button', 'escape'],
    });
    // add a button
    tinglemodal.addFooterBtn(i18n.CLOSE(), 'tingle-btn tingle-btn--primary', function() {
    // here goes some logic
        tinglemodal.close();
    });
    return tinglemodal;

}
function main() {
    // i18n - translate ui
    var translatestrings = document.querySelectorAll(".translate");
    function translation(key) {
        // get [key] from data-i18n* and return translation
        try {
            var i18nkey = (el.dataset[key]).toUpperCase();
            //console.log("with key %o", i18nkey);
            return i18n[i18nkey]();
        } catch(e) {
            //console.error(e);
            return false;
        }
    }
    for (var i=0; i<translatestrings.length; i++) {
        var el = translatestrings[i];
        //console.log("translating element %o ...", el);
        var txt = translation("i18n");
        if(txt) el.innerText = txt;
        var title = translation("i18nTitle");
        if(title) el.title = title;
        var placeholder = translation("i18nPlaceholder");
        if(placeholder) el.placeholder = placeholder;
    }

    var toggleFeedbackButton = document.getElementById('toggle-feedback');
    toggleFeedbackButton.onclick = function(event) {
        event.preventDefault();
        feedbackdialog();
    }


}

function resolveAll() {
    // resolve all resolvable tracks
    var resolvables = document.querySelectorAll('#files-list .metadata.resolvable'); 
    startProgress(resolvables.length);
    var url, resolver, clipname;
    for (var i = 0; i < resolvables.length; i++) {
        resolveClip(resolvables[i].getAttribute("id"));
    }
}

function resolveClip(metadatacell_id) {
    // (manually) gather all the details from the dom and resolve() a clip 
    var cell = document.getElementById(metadatacell_id);
    var resolver = cell.previousSibling.firstChild.value;
    var url = cell.timelinedata.resolve[resolver];
    if(url===undefined) {
        // odometer doesnt recognise this clip, we must force it
        var url = cell.timelinedata.resolve_other.replace("{music_service}", resolver);
        cell.classList.add('resolve-overridden');
    } else {
        cell.classList.remove('resolve-overridden');
    }
    var clipname = cell.timelinedata.clipname;
    //console.log("resolveClip: %o %o->%o", clipname, resolver, url);
    resolve(clipname, url)
}

function submit(formData) {
    // send the already prepared form data to the json endpoint for analysis
    // Set up the request.
    var xhr = new XMLHttpRequest();
    // Open the connection.
    xhr.open('POST', '/api/analyze', true);

    // Set up a handler for when the request finishes.
    xhr.onload = function () {
        if (xhr.status === 200) {
            // File(s) uploaded.
            var audio = JSON.parse(xhr.response);
            console.log('got audio response: %o', audio);
            return formatAudible(audio["audioclips"]);
        } else {
            alertmsg(i18n.ALERTMSG({ERRCODE:xhr.status, ERRMSG:xhr.statusText}, 'danger'));
        }
    };
    var fileList = document.getElementById('files-list');
    // empty the files table
    removeChildren(fileList);
    fileList.innerHTML = "<td>"+i18n.LOADING_DATA()+"<td><td><td>";
    // Send the Data.
    xhr.send(formData);
}

function formatMusicServicesDropdown(music_services, metadatacell_id) {
    // get a list of music services and return a html string of a <select> element
    var s = "<select size=1 onchange=\"resolveClip('"+metadatacell_id+"')\">";
    var possible_services = all_music_services.slice(0); //make a copy
    var suggested = "<optgroup label='"+i18n.RECOGNISED()+"'>";
    if(music_services.length == 0){
        suggested = suggested+"<option selected disabled>"+i18n.UNKNOWN()+"</option>";
    } else {
        for(var i=0;i<music_services.length;i++){
            suggested = suggested+"<option>"+music_services[i]+"</option>";
            possible_services.splice(possible_services.indexOf(music_services[i]), 1); // remove from that list
        }
    }
    var possible = "<optgroup label='"+i18n.OTHERS()+"'>";
    for(var j=0;j<possible_services.length;j++) {
        possible = possible + "<option>"+possible_services[j]+"</option>";
    }
    return s+suggested+possible+"</select>";

}
function formatAudible(audible) {
    // get a json document of the audio file structure of the parsed xml and render it
    var fileList = document.getElementById('files-list');
    // empty the files table
    removeChildren(fileList);

    var tr, elm, c, r, secs, services;

    for(var i=0; i<audible.length; i++) {
        tr = document.createElement('tr');
        elm = audible[i];
        c = elm.clipname;
        r = elm.resolve;
        secs = elm.audible_length;
        services = formatMusicServicesDropdown(elm.music_services, "o-"+utoa(c));
        tr.innerHTML = "<td>"+c+"<td class=duration>"+formatDuration(secs)+"s<td>"+services+"<td class=metadata id='o-"+utoa(c)+"'>";
        // keep the info around as a javascript object
        tr.lastChild.timelinedata = elm;
        if(elm.resolvable) {
           tr.firstChild.classList.add('text-success');
           tr.lastChild.classList.add('resolvable');
        }
        fileList.appendChild(tr);
    }
    resolveAll();
}

function resolve(clipname, url) {
    // get a clipname and an url, and parse the JSON contents into a metadata string
    // Set up the request.
    var xhr = new XMLHttpRequest();
    // Open the connection.
    xhr.open('GET', url, true);

    var output = document.getElementById('o-'+utoa(clipname));  // find the metadata cell of the correct row
    // Set up a handler for when the request finishes.
    output.innerText = i18n.GETTING_METADATA();
    // clear any previous state 
    output.classList.toggle("has-metadata", false);
    output.classList.toggle("bg-danger", false);
    output.classList.toggle("text-white", false);
    output.classList.toggle("text-success", false);
    output.classList.toggle("loading", true);

    xhr.onload = function () {
        output.classList.toggle("loading", false);
        if (xhr.status === 200) {
            // File(s) uploaded.
            var response = JSON.parse(xhr.response);
            console.log('got response %o', response);
            var md = response['metadata'];
            output.classList.add('has-metadata', 'text-success');
            output.metadata = md;
            if(md.productionmusic === true) {
                output.innerHTML = md.copyright+" ℗ <b>"+md.label+"</b>";
            } else {
                output.innerHTML = "<i>"+md.title+"</i> "+md.artist
                        + " <button type=button onclick='check_copyright(this)' class='btn btn-success btn-xs' title='"+i18n.CHECK_COPYRIGHT()+"'>℗</a>";
            }
            if(output.classList.contains('resolve-overridden')) {
                // this is the result of a manual overridden resolve, i.e. filename should've been 
                // recognised, but wasn't
                // add some ui to report missing filename
                output.innerHTML = output.innerHTML + " <button type=button onclick='report_missing_filename(this)' class='btn btn-success btn-xs' title='"+i18n.REPORT_MISSING_FILENAME()+"'>＋＋＋</a>"; }
        } else if(xhr.status === 400) {
            // server had issues with our request
            var response = JSON.parse(xhr.response);
            console.log('got error response %o', response);
            var e = response['error'];
            output.classList.add('text-white', 'bg-danger');
            output.innerHTML = '<b>'+e.type+'</b>: '+e.args;

        } else {
            console.error("server returned %o -> %o", xhr.status, xhr.statusText);
            output.innerHTML = '<i>'+xhr.statusText+'</i>';
            output.classList.add('text-white', 'bg-danger');
        }
        updateProgress(+1);
    };

    // Send 
    xhr.send();
}

function alertmsg(msg, errortype) {
    // flash a message to the #alertmsg elemnt. Errortype one of [warning, danger, info, success, primary]
    // https://getbootstrap.com/docs/4.0/components/alerts/
    var e = document.getElementById('alertmsg');
    var etype = errortype || 'warning';
    e.innerText = msg;
    e.classList.add('alert-'+etype);
    e.hidden=false;
    window.setTimeout(function() {e.hidden=true; 
                                e.classList.remove('alert-'+etype); 
                                e.innerText='';}, 
                            4500);
}

function creditsdialog() {
    // pop up  a dialog suitable for copy-paste into end credits
    var metadatarows = document.querySelectorAll('td.has-metadata');
    var s = "";
    var _holders = [];
    for(var i=0; i<metadatarows.length; i++) {
        var md = metadatarows[i].metadata;
        if(md.title===undefined) { continue }
        if(md.productionmusic===true) {
            if(_holders.indexOf(md.copyright) === -1) { // only register once per copyright holder
                s = s + "<i>"+md.copyright+"</i><br>"// <br>℗ <b>"+md.label+"</b><br>";
                _holders.push(md.copyright);
            }
        } else {
            s = s + "<i>"+md.title+"</i> "+md.artist+" <br>℗ <b>"+md.label+"</b> "+md.year+" <br>";
        }
    }
    console.log('got credits: %o', s);
    var tinglemodal = setupModal();
    tinglemodal.setContent('<h1>'+i18n.END_CREDITS()+'</h1>'+s);
    tinglemodal.open();
}

function runsheetdialog() {
    // pop up a run sheet dialog, listing each track by inpoint on timeline on timeline
    var metadatarows = document.querySelectorAll('td.has-metadata');
    var preview = document.getElementById('preview');
    var s = "<h1>"+i18n.REPORT_HEADER_TIMELINE()+"</h1>";
    s = s + '<p><code>'+i18n.FULL_FILE_NAME({FILENAME:preview.validFile.name})+'</code>';
    s = s + '<table cellpadding=10><tr>';
    s = s + '<th>'+i18n.IN()+'</th>';
    s = s + '<th>'+i18n.OUT()+'</th>';
    s = s + '<th>'+i18n.DURATION()+'</th>';
    s = s + '<th>'+i18n.CLIP_DETAILS()+'</th>';
    s = s + '</tr>';
    var reportrows = []; // this is where we keep the generated text of each report row
    for(var i=0; i<metadatarows.length; i++) {
        var md = metadatarows[i].metadata;
        var td = metadatarows[i].timelinedata;
        console.log("got timelinedata: %o", td);
        var t;
        if(md.title===undefined) {// TODO: let people choose ordinary files also 
            t = td.filename; 
        } else {
            t = '\u00ab'+md.title+'\u00bb \u2117 '+td.musiclibrary
            //_t = u'\u00ab%(title)s\u00bb \u2117 %(musiclibrary)s' % vars(r.metadata)
        }
        if(md.productionmusic===true) {
            if(_labels.indexOf(md.label) === -1) { // only register once per label
                s = s + "<i>"+md.copyright+"</i> ℗ <b>"+md.label+"</b><br>";
            }
        } else {
            s = s + "<i>"+md.title+"</i> "+md.artist+" ℗ <b>"+md.label+"</b> "+md.year+" <br>";
        }
    }
    console.log('got credits: %o', s);
    var tinglemodal = setupModal();
    tinglemodal.setContent('<h1>End credits</h1>'+s);
    tinglemodal.open();
}

function reportdialog() {
    // pop up a prf report, detailing the metadata details
    var metadatarows = document.querySelectorAll('td.has-metadata');
    var reportrows = []; // this is where we keep the generated text of each report row
    for(var i=0; i<metadatarows.length; i++) {
        var md = metadatarows[i].metadata;
        var td = metadatarows[i].timelinedata;
        console.log("got timelinedata: %o", td);
        var t = md.title || td.title;// TODO: let people choose ordinary files also 
        var _s = "<div><dt>Title:</dt><dd>"+t+"</dd>";
        if(md.identifier)
            _s = _s + "<dt>Track identifier:</dt><dd>"+md.identifier+"</dd>";
        if(md.artist)
            _s = _s + "<dt>Artist:</dt><dd>"+md.artist+"</dd>";
        if(md.albumname)
            _s = _s + "<dt>Album name:</dt><dd>"+md.albumname+"</dd>";
        if(md.lyricist)
            _s = _s + "<dt>Lyricist:</dt><dd>"+md.lyricist+"</dd>";
        if(md.composer)
            _s = _s + "<dt>Composer:</dt><dd>"+md.composer+"</dd>";
        if(md.label)
            _s = _s + "<dt>Label:</dt><dd>"+md.label+"</dd>";
        if(md.recordnumber)
            _s = _s + "<dt>Recordnumber:</dt><dd>"+md.recordnumber+"</dd>";
        if(md.copyright)
            _s = _s + "<dt>Copyright owner:</dt><dd>"+md.copyright+"</dd>";
        if(md.year && md.year !== -1)
            _s = _s + "<dt>Released year:</dt><dd>"+md.year+"</dd>";
        _s = _s + "<dt>Music Library:</dt><dd>"+md.musiclibrary+"</dd>";
        
        _s = _s + "<br><b>"+i18n.SECONDS_IN_TOTAL({SECONDS:formatDuration(td.audible_length)})+"</b></div><hr>";
        reportrows.push(_s);
    }
    var preview = document.getElementById('preview');
    var html = '<p><code>'+i18n.GENERATED_FROM({FILENAME:preview.validFile.name, 
                 DATESTRING:preview.validFile.lastModifiedDate.toLocaleString()})+'</code>';
    html = html + reportrows.join("\n");
    var tinglemodal = setupModal();
    // add another button
    tinglemodal.addFooterBtn(i18n.DOWNLOAD_AS_FILE(), 'tingle-btn tingle-btn--info', function() {
        // TODO: add html header and date and time
        download(html, "music_metadata.html", "text/html");
        tinglemodal.close();
    });
    tinglemodal.setContent("<h1>"+i18n.REPORT_HEADER_PRF()+"</h1>"+html);
    tinglemodal.open();
}

function feedbackdialog() {
    var tinglemodal = setupModal();
    // add another button
    tinglemodal.addFooterBtn(i18n.SUBMIT(), 'tingle-btn tingle-btn--primary', function() {
        var form = document.querySelector(".tingle-modal-box form");
        var formData = new FormData(form);
        axios.post("/api/feedback", formData)
            .then(function (response) {
                console.log("feedback response: %o", response);
                alertmsg(i18n.THANK_YOU(), "info");
            })
            .catch(function(error) {
                console.error("feedback error: %o", error);
                alertmsg(i18n.ALERTMSG({ERRCODE:"XX", ERRMSG:xhr.statusText}, 'danger'));
            });
            tinglemodal.close();
    });
    tinglemodal.setContent(document.getElementById("feedback-dialog").innerHTML);
    tinglemodal.open();
}

function report_missing_filename(button) {
    // send missing filename to odometer devs
    console.log("report filename: %o", button);
    var cell = button.parentElement;
    var metadata = cell.metadata;
    var timelinedata = cell.timelinedata;
    console.log("missing metaata : %o", metadata);
    var xhr = new XMLHttpRequest();
    xhr.open("POST", timelinedata.add_missing);
    xhr.setRequestHeader("Content-type", "application/json;charset=utf-8");
    xhr.onload = function () {
        if (xhr.status === 200) {
            // open dialog to thank for adding missing metadata / filename
            var tinglemodal = setupModal();
            tinglemodal.setContent(i18n.THANK_YOU());
            tinglemodal.open();
        } else {
            console.error("missing filename error: %o, %o", xhr.status, xhr.response);
        }
    }
    xhr.send(JSON.stringify(metadata));
}

function check_copyright(button) {
    // check the copyright info of commercial releases
    var cell = button.parentElement;
    var metadata = cell.metadata; // Trackmetadata from model.py
    var timelinedata = cell.timelinedata; // timeline object from xmeml parser
    console.log("check copyright metadata : %o", metadata);
    var sp = document.createElement('div');
    var dmarights = "<b>DMA</b>: ℗ "+metadata.year+" "+metadata.label;
    sp.innerHTML = dmarights
        +"<br><b>Spotify</b>: <img class=spinner src='/media/spinner.gif'><br><b>Discogs</b>: <img class=spinner src='/media/spinner.gif'>";
    cell.appendChild(sp);

    var xhr = new XMLHttpRequest();
    //xhr.open("GET", "/ownership/metadata/"+encodeURIComponent(JSON.stringify(metadata)));
    xhr.open("POST", "/api/ownership/metadata");
    xhr.setRequestHeader("Content-Type", "application/json;charset=UTF-8");
    xhr.onload = function () {
        if (xhr.status === 200) {
            // add copyright to ui

            var response = JSON.parse(xhr.response);
            console.log("copyright response: %o", response);
            var s = dmarights + "<br><b>Spotify</b>: ";
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
            sp.innerHTML = s;
        } else {
            console.error("copyright error: %o, %o", xhr.status, xhr.response);
            var s = dmarights + "<br><b>Spotify</b>: "+i18n.PLEASE_SEARCH_MANUALLY()+
                "<br><b>Discogs</b>: "+i18n.PLEASE_SEARCH_MANUALLY();
            sp.innerHTML = s;
        }
        // remove button, clear ui
        button.remove();
    }
    xhr.send(JSON.stringify(metadata));
}

function statusdialog() {
    // set up dialog with live status, graphs, etc

    //const allcolors = ['#ff6384', '#36a2eb', '#ffce56', '#4bc0c0', '#9966ff'];
    const allcolors = {"404": "rgba(255, 99, 132, 0.2)", 
                       "201": "rgba(255, 159, 64, 0.2)", 
                       "400": "rgba(255, 205, 86, 0.2)", 
                       "200": "rgba(75, 192, 192, 0.2)", 
                       "500": "rgba(54, 162, 235, 0.2)", 
                       "default": "rgba(201, 203, 207, 0.2)"};
            

    // set up dialog
    var tinglemodal = setupModal();
    tinglemodal.setContent(document.getElementById("status-dialog").innerHTML);

    // load graph library
    var head = document.head || document.getElementsByTagName("head")[0];
    var scr = document.createElement("script");
    scr.type = "text\/javascript";
    scr.onload = function() {
        // script library is loaded, now get data
        var xhr = new XMLHttpRequest();
        xhr.open("GET", "/media/status.json");
        xhr.onload = function () {
        if (xhr.status === 200) {
            // parse status data
            var dataseries = JSON.parse(xhr.responseText);
            console.log("dataseries: %o", dataseries);
            document.querySelector(".tingle-modal-box__content h2").innerHTML = i18n.STATUS_GRAPH_7DAYS({TIMESTAMP:dataseries.timestamp});
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

            
            // create chart
            var ctx = document.getElementById("statusChart");
            var myChart = new Chart(ctx, {
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
        } else {
            console.error("chart data error: %o, %o", xhr.status, xhr.response);
        }
        }
        xhr.send();
        tinglemodal.open();
    };
    head.appendChild(scr);
    scr.src = "/media/Chart.min.js";
}

function download(content, filename, contentType) {
    console.log('downloading metadata sheet');
    if(!contentType) contentType = 'application/octet-stream';
    var a = document.createElement('a');
    var blob = new Blob([content], {'type':contentType});
    a.href = window.URL.createObjectURL(blob);
    a.download = filename;
    a.style.display = 'none';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(a.href); // free memory
}
/*
clips = defaultdict(list)
for r in self.itercheckedrows():
    if r.metadata.title is None:
        # not resolved, use file name
        _t = repr(r.audioname)
    else:
        _t = u'\u00ab%(title)s\u00bb \u2117 %(musiclibrary)s' % vars(r.metadata)
    for sc in r.subclips:
        _s = '<tr><td><code>%s</code></td><td><code>%s</code></td>' % (sc['in'], sc['out'])
        _s += '<td>%06.2f\"</td>' % (sc['durationsecs'])
        _s += '<td>%s</td>' % _t
        _s += "</tr>"
        clips[sc['in']].append(_s)
# sort all clips by inpoint
inpoints = list(clips.keys())
inpoints.sort()
s = s + "".join(["".join(clips[inpoint]) for inpoint in inpoints])
s = s + '</table>'
*/
function finishedResolving() {
    // things to do when all metadata is loaded
    var btns = document.querySelectorAll('#file-form button[type="button"]');
    for(var i=0; i<btns.length; i++) {
        btns[i].removeAttribute('disabled');
    }
}