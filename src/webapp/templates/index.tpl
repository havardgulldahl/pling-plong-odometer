{% extends "base.tpl" %}

{% block docscript %}
    var fileList = document.getElementById('files-list');

    // add debug ui
    if(document.location.search == "?test") {
        var tbtn = document.createElement('button');
        tbtn.innerText = "Use testfile";
        tbtn.onclick = function(event) {
            event.preventDefault();
            removeChildren(fileList);
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
        reportdialog();
    }

    var createCreditsButton = document.getElementById('create-credits-button');
    createCreditsButton.onclick = function(event) {
        event.preventDefault();
        creditsdialog();
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
            // empty files table
            removeChildren(fileList);
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
    console.log("dragOver");
    // Prevent default select and drag behavior
    ev.preventDefault();
    document.querySelector('body').classList.add('dragover');
    window.setTimeout(function() {
        document.querySelector('body').classList.remove('dragover');
    }, 10000)
  }

  function dragendHandler(ev) {
    console.log("dragEnd");
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

function finishedResolving() {
    // things to do when all metadata is loaded
    var btns = document.querySelectorAll('#file-form button[type="button"]');
    for(var i=0; i<btns.length; i++) {
        btns[i].removeAttribute('disabled');
    }
}

function submit(formData) {
    // send the already prepared form data to the json endpoint for analysis

    // empty the files table
    var fileList = document.getElementById('files-list');
    removeChildren(fileList);
    fileList.innerHTML = "<td class=loading>"+i18n.LOADING_DATA()+"<td><td><td>";
    // Send the Data.
    axios.post("/api/analyze", formData)
    .then(function (response) {
        console.log('got audio response: %o', response.data);
        return formatAudible(response.data.audioclips);
    })
    .catch(function(error) {
        console.error("analysis error: %o", error);
        alertmsg(i18n.ALERTMSG({ERRCODE:"XX", ERRMSG:error}, 'danger'));
    });
}

function report_missing_filename(button) {
    // send missing filename to odometer devs
    console.log("report filename: %o", button);
    var cell = button.parentElement;
    var metadata = cell.metadata;
    var timelinedata = cell.timelinedata;
    console.log("missing metaata : %o", metadata);
    axios.post(timelinedata.add_missing, metadata)
        .then(function (response) {
            var tinglemodal = setupModal();
            tinglemodal.setContent(i18n.THANK_YOU());
            tinglemodal.open();
        })
        .catch(function (error) {
            console.error("missing filename error: %o", error);
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
                <button type="button" disabled class="btn btn-primary translate" id="create-report-button" data-i18n=generate_metadata_report>Generate metadata report</button>
                <button type="button" disabled class="btn btn-primary translate" id="create-credits-button" data-i18n=generate_end_credits>Generate credits</button>
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
            <th class=translate title="Measured in seconds" data-i18n=duration data-i18n-title=measured_in_seconds>audible length</th>
            <th class=translate title="Music library" data-i18n-title=music_library>℗</th>
            <th class=translate data-i18n=metadata id=thead-metadata>metadata</th>
          </tr>
        </thead>
        <tbody id=files-list 
               style="font-size:80%" 
               data-step=2
               data-intro="Når du har lastet inn xml-fila, kommer alle musikksporene automatisk opp her.">
          <tr>
            <td><span style="font-size: 150%;" data-i18n=startinfo class=translate>To get started: Select an XMEML file—exported from Adobe Premiere or Final Cut Pro 7.x. (You may also drop it anywhere in this window).</span> <td><td><td>
          </tr>
        </tbody>

    </table>
    {% endblock content %}