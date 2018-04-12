{% extends "base.tpl" %}

{% block docscript %}
    var form = document.getElementById('file-form');
    var fileSelect = document.getElementById('file-select');
    var fileList = document.getElementById('files-list');
    var createReportButton = document.getElementById('create-report-button');
    var createCreditsButton = document.getElementById('create-credits-button');

    // i18n - translate ui
    fileSelect.title = i18n.CHOOSE_TIMELINE_DATA(); 
    document.getElementById("preview").innerText = "⇜ "+i18n.PLEASE_SELECT_FILE(); 
    createReportButton.innerText = i18n.GENERATE_METADATA_REPORT(); 
    createCreditsButton.innerText = i18n.GENERATE_END_CREDITS(); 
    document.getElementById("thead-filename").innerText = i18n.NAME(); 
    document.getElementById("thead-filename").title = i18n.FILENAME(); 
    document.getElementById("thead-duration").innerText = i18n.AUDIBLE_LENGTH(); 
    document.getElementById("thead-duration").title = i18n.MEASURED_IN_SECONDS(); 
    document.getElementById("thead-library").title = i18n.MUSIC_LIBRARY(); 
    document.getElementById("thead-metadata").innerText = i18n.METADATA(); 
    document.getElementById("startinfo").innerHTML = i18n.STARTINFO(); 

    // add debug ui
    if(document.location.search == "?debug") {
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
        var t2btn = document.createElement("button");
        t2btn.innerText = i18n.CHECK_OWNERSHIP();
        t2btn.onclick = function(event) {
            event.preventDefault();
            var tinglemodal = new setupModal();
            tinglemodal.setContent(document.getElementById("ownership-dialog").innerHTML);
            tinglemodal.modalBoxContent.querySelector("h2").innerText = i18n.CHECK_OWNERSHIP_TITLE();
            tinglemodal.modalBoxContent.querySelector("label").innerHTML = i18n.OWNERSHIP_HELPTEXT({DMA: "NONRE674655HD0001", SPOTIFY: "spotify:track:7bKqtOF02nEDUImWZqq5nH"});
            tinglemodal.modalBoxContent.querySelector("input").setAttribute("placeholder", i18n.TYPE_OR_PASTE_HERE());
            tinglemodal.modalBoxContent.querySelector(".card-header").innerText = i18n.RESULTS();
            tinglemodal.open();
            return false;
        }
        document.querySelector('div.col-5').appendChild(t2btn);
    }

    createReportButton.onclick = function(event) {
        event.preventDefault();
        reportdialog();
    }

    createCreditsButton.onclick = function(event) {
        event.preventDefault();
        creditsdialog();
    }

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

{% endblock docscript %}

{% block bodyhandlers %}
    ondrop="dropHandler(event);" 
    ondragover="dragoverHandler(event);" 
    ondragend="dragendHandler(event);"
{% endblock bodyhandlers %}

{% block content %}
    <form id="file-form" class="form" 
          enctype="multipart/form-data" action="/analyze" method="POST">
        <div class="form-row">
            <div class="col-3">
                <input type="file" 
                    class="form-control" 
                    id="file-select" title="Choose timeline data (XMEML)"
                    accept=".xml,text/xml,application/xml"
                    name="xmeml">
            </div>
            <div class="col-5">
                <span id="preview" class="text-secondary">Please select a file</span>
            </div>
            <div class="col-4">
                <button type="button" disabled class="btn btn-primary" id="create-report-button">Generate metadata report</button>
                <button type="button" disabled class="btn btn-primary" id="create-credits-button">Generate credits</button>
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
            <th title="File name" id=thead-filename>name</th>
            <th title="Measured in seconds" id=thead-duration>audible length</th>
            <th title="Music library" id=thead-library>℗</th>
            <th id=thead-metadata>metadata</th>
          </tr>
        </thead>
        <tbody id=files-list style="font-size:80%">
          <tr>
            <td id=startinfo>To get started: Select an XMEML file—exported from Adobe Premiere or Final Cut Pro 7.x. <br>(You may also drop it anywhere in this window). <td><td><td>
          </tr>
        </tbody>

    </table>
    {% endblock content %}