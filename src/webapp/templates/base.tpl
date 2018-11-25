<!DOCTYPE html>
<html lang=no>
<head>
    <meta charset="utf-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Pling Plong Odometer Online</title>

<link rel="stylesheet" href="/media/bootstrap.min.css" integrity="sha384-MCw98/SFnGE8fJT3GXwEOngsV7Zt27NXFoaoApmYm81iuXoPkFOJwJ8ERdknLPMO" crossorigin="anonymous">
<link rel="stylesheet" href="/media/tingle.min.css" >
<link rel="stylesheet" href="/media/introjs.min.css" >
<link rel="stylesheet" href="/media/odometer.css" >
<script type="text/javascript" src="/media/tingle.min.js"></script>
<script type="text/javascript" src="/media/i18n.js"></script>
<script type="text/javascript" src="/media/messageformat.min.js"></script>
<script type="text/javascript" src="/media/promise.polyfill.min.js"></script>
<script type="text/javascript" src="/media/axios.min.js"></script>
<script type="text/javascript" src="/media/purify.min.js"></script>
<script type="text/javascript" src="/media/intro.min.js"></script>
<script type="text/javascript" 
        {% if app['debugmode'] %}
        src="/media/vue.js"
        {% else %}
        src="/media/vue.min.js"
        {% endif %}
        ></script>
<script type="text/javascript" src="/media/odometer.js"></script>

{% block templates %}{% endblock templates %}

<script type="text/javascript">

var languagecode = "no-NO"; // TODO: update this dynamically
var i18n = new MessageFormat(languagecode).compile(messages)[languagecode];
const all_music_services = ["DMA", "ExtremeMusic", "UprightMusic", "AUX", "ApolloMusic", "UniPPM"]; // TOOD: get this dynamically/lazily

</script>


{% block headscript %}{% endblock headscript %}

</head>
<body
{% block bodyhandlers %}{% endblock bodyhandlers %}
    >
        <nav class="navbar navbar-expand-lg navbar-light bg-light">
                <a class="navbar-brand" href="/">♫ ♪ Odometer <span class=beta title="Some things may break">BETA</span></a>
                <button class="navbar-toggler" type="button" data-toggle="collapse" data-target="#navbarNavAltMarkup" aria-controls="navbarNavAltMarkup" aria-expanded="false" aria-label="Toggle navigation">
                  <span class="navbar-toggler-icon"></span>
                </button>
                <div class="collapse navbar-collapse" id="navbarNavAltMarkup">
                  <div class="navbar-nav">
                    <a class="nav-item nav-link {% if app["active_page"] == "analysis" %} active {% endif %} translate" href="/" data-i18n=analysis id=navbar-analysis>Analysis</a>
                    <a class="nav-item nav-link {% if app["active_page"] == "ownership" %} active {% endif %} translate" href="/copyright_owner" data-i18n=check_ownership id=navbar-ownership>Ownership</a>
                    <a class="nav-item nav-link translate" href="#" onclick="introJs().setOptions({nextLabel: i18n.NEXT(), skipLabel: i18n.SKIP(), prevLabel: i18n.PREVIOUS(), doneLabel: i18n.DONE()}).start()" data-i18n=help>Help</a>
                    <a class="nav-item nav-link translate" href="/api/doc" title="JSON REST API (swagger)" data-i18n=api>API</a>
                  </div>
                </div>
              </nav>

    <div id=alertmsg class="fade show alert" role="alert" hidden>
    </div>

    {% block content %}{% endblock %}

    <button id=toggle-feedback>Feedback</button>
    <div style="display:none">
    <dialog id=feedback-dialog>
        <form onsubmit="return false;" method=POST action=/feedback novalidate>
            <div class="form-group">
                <label for=feedback-email class=translate data-i18n=email>E-mail</label>:
                <input id=feedback-email 
                       name=sender 
                       type=email 
                       placeholder="If you want us to get in touch" data-i18n-placeholder=if_you_want_us_to_get_in_touch
                       class="form-control translate" >
            </div>
            <!-- div class="form-check">
                <input id=feedback-check disabled name=include_xmeml type=checkbox class=form-check-input>
                <label for=feedback-check class=translate data-i18n=include_xml>Include xml</label>?
            </div -->
            <div class="form-group">
                <label for=feedback-text class=translate data-i18n=feedback>Feedback</label>:
                <textarea id=feedback-text name=text rows=3 style="width:99%" required></textarea>
            </div>

        </form>
    </dialog>
    <dialog id=status-dialog>
        <h2>Status</h2>
        <canvas id="statusChart" width="400" height="400"></canvas>
    </dialog>
    </div>

<script type="text/javascript">
main()
{% block docscript %}{% endblock docscript %}
</script>
<footer><a href="https://github.com/havardgulldahl/pling-plong-odometer/releases/tag/★" title="$Format:%ci$">Odometer ★</a></footer>
</body>

</html>