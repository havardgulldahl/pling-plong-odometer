<!DOCTYPE html>
<html lang=no>
<head>
    <meta charset="utf-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Pling Plong Odometer Online</title>

<link rel="stylesheet" href="/media/bootstrap.min.css" integrity="sha256-QUyqZrt5vIjBumoqQV0jM8CgGqscFfdGhN+nVCqX0vc=" crossorigin="anonymous">
<link rel="stylesheet" href="/media/tingle.min.css" >
<link rel="stylesheet" href="/media/odometer.css" >
<script type="text/javascript" src="/media/tingle.min.js"></script>
<script type="text/javascript" src="/media/i18n.js"></script>
<script type="text/javascript" src="/media/messageformat.min.js"></script>
<script type="text/javascript" src="/media/odometer.js"></script>

<script type="text/javascript">

var languagecode = "no-NO"; // TODO: update this dynamically
var i18n = new MessageFormat(languagecode).compile(messages)[languagecode];
const all_music_services = ["DMA", "ExtremeMusic", "UprightMusic", "AUX", "ApolloMusic", "UniPPM", "WarnerChappell"]; // TOOD: get this dynamically/lazily

</script>

</head>
<body
    ondrop="dropHandler(event);" 
    ondragover="dragoverHandler(event);" 
    ondragend="dragendHandler(event);">

        <nav class="navbar navbar-expand-lg navbar-light bg-light">
                <a class="navbar-brand" href="#">♫ ♪ Odometer <span class=beta title="Some things may break">BETA</span></a>
                <button class="navbar-toggler" type="button" data-toggle="collapse" data-target="#navbarNavAltMarkup" aria-controls="navbarNavAltMarkup" aria-expanded="false" aria-label="Toggle navigation">
                  <span class="navbar-toggler-icon"></span>
                </button>
                <div class="collapse navbar-collapse" id="navbarNavAltMarkup">
                  <div class="navbar-nav">
                    <a class="nav-item nav-link active" href="#" id=navbar-analysis>Analysis <span class="sr-only">(current)</span></a>
                    <a class="nav-item nav-link disabled" href="#" id=navbar-help>Help</a>
                    <a class="nav-item nav-link" href="/doc" title="JSON REST API documentation (swagger)" id=navbar-api>API</a>
                    <a class="nav-item nav-link" href="#" title="" onclick="statusdialog()" id=navbar-status>Status</a>
                  </div>
                </div>
              </nav>

    <div id=alertmsg class="fade show alert" role="alert" hidden>
    </div>

    {% block content %}{% endblock %}

    <button id=toggle-feedback>Feedback</button>
    <div style="display:none">
    <dialog id=feedback-dialog>
        <form onsubmit="return false;" method=POST action=/feedback>
            <div class="form-group">
                <label for=feedback-email>E-mail</label>:
                <input id=feedback-email name=sender type=email placeholder="If you want us to get in touch" class="form-control" >
            </div>
            <div class="form-check">
                <input id=feedback-check disabled name=include_xmeml type=checkbox class=form-check-input>
                <label for=feedback-check>Include xml</label>?
            </div>
            <div class="form-group">
                <label for=feedback-text>Feedback</label>:
                <textarea id=feedback-text name=text rows=3 style="width:99%"></textarea>
            </div>

        </form>
    </dialog>
    <dialog id=status-dialog>
        <h2>Status</h2>
        <canvas id="statusChart" width="400" height="400"></canvas>
    </dialog>
    <dialog id=ownership-dialog>
        <h2>Look up ownership of commercial releases</h2>
        <form onsubmit="return false">
        <div class=form-group>
            <label for=ownership-input></label>
            <input id=ownership-input placeholder="Type or paste here" class=form-control 
                type=search oninput="if(this.value.length>5) {resolve_manually_delay(this);}"
                autocomplete=off autocorrect=off>
            <div class="card">
                <div class="card-header">
                    Results
                </div>
                <div class="card-body">
                    <p class="card-text">...</p>
                </div>
            </div>
        </div>

        </form>
    </dialog>
    </div>

<script type="text/javascript">
main()
</script>
<footer><a href="https://github.com/havardgulldahl/pling-plong-odometer/releases/tag/★" title="$Format:%ci$">Odometer ★</a></footer>
</body>

</html>