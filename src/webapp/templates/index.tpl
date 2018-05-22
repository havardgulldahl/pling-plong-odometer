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
                    class="form-control translate" 
                    id="file-select" 
                    title="Choose timeline data (XMEML)" data-i18n-title=choose_timeline_data
                    accept=".xml,text/xml,application/xml"
                    name="xmeml">
            </div>
            <div class="col-5">
                <label for=id-select id="preview" class="text-secondary col-form-label">⇜ <span class=translate data-i18n=please_select_file>Please select a file</span> </label>
            </div>
            <div class="col-4">
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
            <th class=translate data-i18n=metadata>metadata</th>
          </tr>
        </thead>
        <tbody id=files-list style="font-size:80%">
          <tr>
            <td><span style="font-size: 150%;" data-i18n=startinfo class=translate>To get started: Select an XMEML file—exported from Adobe Premiere or Final Cut Pro 7.x. (You may also drop it anywhere in this window).</span> <td><td><td>
          </tr>
        </tbody>

    </table>
    {% endblock content %}