{% extends "base.tpl" %}

{% block content %}
<div id=content>


    <div class="container-fluid">
      <div class="row">
        <nav class="col-md-2 d-none d-md-block bg-light sidebar">
          <div class="sidebar-sticky">
            <ul class="nav flex-column">
              <li class="nav-item">
                <a class="nav-link translate" href="/licenses" data-i18n=licenses>
                    Licenses
                </a>
              </li>
              <li class="nav-item">
                <a class="nav-link translate" href="/feedback"  data-i18n=feedback>
                    Feedback
                </a>
              </li>
              <li class="nav-item">
                <a class="nav-link translate" href="/missing_filenames" data-i18n=missingfilenames>
                    Missing file names
                </a>
              </li>
              <li class="nav-item">
                <a class="nav-link translate" href="/isrc_ean_status" data-i18n=isrc_ean_status>
                    ISRC and EAN data health
                </a>
              </li>
              <li class="nav-item">
                <a class="nav-link translate" href="/tests" data-i18n=tests>
                    Tests
                </a>
              </li>
              <li class="nav-item">
                <a class="nav-link translate" href="/dashboard" data-i18n=dashboard>
                    Dashboard
                </a>
              </li>
            </ul>

          </div>
        </nav>

        <main role="main" class="col-md-9 ml-sm-auto col-lg-10 px-4">
          <div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom">
            <h1 class="h2" id=admintitle>{% block admintitle %}{% endblock  %}</h1>
            <!--div class="btn-toolbar mb-2 mb-md-0">
              <div class="btn-group mr-2">
                <button class="btn btn-sm btn-outline-secondary">Share</button>
                <button class="btn btn-sm btn-outline-secondary">Export</button>
              </div>
              <button class="btn btn-sm btn-outline-secondary dropdown-toggle">
                <span data-feather="calendar"></span>
                This week
              </button>
            </div -->
          </div>

{% block adminpanel %}
{% endblock adminpanel %}


        </main>
      </div>
    </div>



</div>
{% endblock content %}
