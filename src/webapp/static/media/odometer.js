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
        var html = translation("i18nHtml");
        if(html) el.innerHTML = DOMPurify.sanitize(html); 
        var intro = translation("i18nIntro");
        if(intro) el.dataset.intro = intro;
    }

    var toggleFeedbackButton = document.getElementById('toggle-feedback');
    toggleFeedbackButton.onclick = function(event) {
        event.preventDefault();
        feedbackdialog();
    }
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

function feedbackdialog() {
    var tinglemodal = setupModal();
    // add another button
    tinglemodal.addFooterBtn(i18n.SUBMIT(), 'tingle-btn tingle-btn--primary', function() {
        var form = document.querySelector(".tingle-modal-box form");
        if("reportValidity" in form && !form.reportValidity()) { // ie doesnt support this
            return false;
        }
        var formData = new FormData(form);
        axios.post("/api/feedback", formData)
            .then(function (response) {
                console.log("feedback response: %o", response);
                alertmsg(i18n.THANK_YOU(), "info");
            })
            .catch(function(error) {
                console.error("feedback error: %o", error);
                alertmsg(i18n.ALERTMSG({ERRCODE:"XX", ERRMSG:error}, 'danger'));
            });
        tinglemodal.close();
    });
    tinglemodal.setContent(document.getElementById("feedback-dialog").innerHTML);
    tinglemodal.open();
}

function check_copyright(button) {
    // check the copyright info of commercial releases
    var cell = button.parentElement;
    var metadata = {"metadata": cell.metadata}; // Trackmetadata from model.py
    var timelinedata = cell.timelinedata; // timeline object from xmeml parser
    console.log("check copyright metadata : %o", metadata);
    var sp = document.createElement('div');
    var dmarights = "<b>DMA</b>: ℗ "+cell.metadata.year+" "+cell.metadata.label;
    sp.innerHTML = dmarights
        +"<br><b>Spotify</b>: <img class=spinner src='/media/spinner.gif'><br><b>Discogs</b>: <img class=spinner src='/media/spinner.gif'>";
    cell.appendChild(sp);

    var xhr = new XMLHttpRequest();
    xhr.open("POST", "/api/ownership/");
    xhr.setRequestHeader("Content-Type", "application/json;charset=UTF-8");
    xhr.onload = function () {
        if (xhr.status === 200) {
            // add copyright to ui

            var response = JSON.parse(xhr.response);
            console.log("copyright response: %o", response);
            var s = dmarights + "<br><b>Spotify</b>: ";
            s += response.ownership.spotify.P || response.ownership.spotify.C;
            s += "<br><b>Discogs</b>: ";
            if(response.ownership.discogs !== null) {
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

