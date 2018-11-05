{% extends "admin.tpl" %}


{% block templates %}
<script type="text/x-template" id="feedback-template">
    <tr class=item v-bind:class="{'text-muted':item.done}">
        <td> <input type=checkbox v-bind:checked=item.done></td>
        <td> [[ formattedTimestamp ]]</td>
        <td v-bind:class="{'feedback-done':item.done}"> [[ item.message ]]</td>
        <td> [[ item.sender ]]</td>
    </tr>
</script>
{% endblock templates %}

{% block docscript %}

var app = new Vue({
    el: '#adminpanel',
    data: {
      selected_test: [],
      tests: [ { "name": "IFPI reservasjonsliste", "url": "/copyright_owner?"}, 
               { "name": "Analyse XMEML", "url": "/?test"} 
      ]
    },
    mounted : function() { 
        console.log("startup");
        fetch_tests();  
    },
    delimiters: ["[[", "]]"],
    methods: {
        run_test: function() {
            console.log("run_test %o", this.selected_test);
            document.getElementById("testpanel").src = this.selected_test;
        }
    }
  });

function fetch_tests() {
    return; // TODO: implement test fetch
    axios.get("/api/tests/")
        .then(function (response) {
            console.log("got tests: %o", response);
            for(var i=0;i<response.data.tests.length;i++) {
                app.tests.push(response.data.tests[i]);
            }

        })
        .catch(function(error) {
            console.error("tests error: %o", error);
        });

}
{% endblock docscript %}

{% block admintitle %}<span data-i18n=tests class=translate>Tests</span>{% endblock  %}


{% block adminpanel %}
<div id=adminpanel>


    <div class="input-group">
        <div class="input-group-prepend">
            Test: 
        </div>
        <select  v-model="selected_test"> 
            <option v-for="test in tests" v-bind:value="test.url">
                [[ test.name ]] 
            </option>
        </select>
        <div class="input-group-append">
            <button v-on:click="run_test">Run</button>
        </div>
    </div>

    <div class="embed-responsive">
        <iframe id=testpanel class="embed-responsive-item"  src="">

        </iframe>
    </div> 
</div>
{% endblock adminpanel %}