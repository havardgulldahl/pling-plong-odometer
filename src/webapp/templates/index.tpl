{% extends "base.tpl" %}

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