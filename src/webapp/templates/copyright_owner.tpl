
{% extends "base.tpl" %}

{% block content %}
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
{% endblock content %}