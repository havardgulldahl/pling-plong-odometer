{% extends "admin.tpl" %}


{% block templates %}
<script type="text/x-template" id="missing-template">
    <tr>
        <td> <input type=checkbox v-bind:checked=item.done></td>
        <td> [[ formattedTimestamp ]]</td>
        <td> [[ item.filename ]]</td>
        <td> [[ item.recordnumber ]]</td>
        <td> [[ item.musiclibrary ]]</td>
    </tr>
</script>
{% endblock templates %}

{% block docscript %}

Vue.component("missing-item", {
    props: ["item"],
    delimiters: ["[[", "]]"],
    template: "#missing-template",
    methods: {
    },
    computed: {
        formattedTimestamp: function() {
            var options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
            return new Date(this.item.timestamp).toLocaleDateString();
        }
    },
    mounted: function () {
        console.log("mounted %o", this);
    },
  });

var app = new Vue({
    el: '#content',
    data: {
      items: []
    },
    mounted : function() { 
        console.log("startup");
        fetch_missing();  
    },
    delimiters: ["[[", "]]"]
  });

function fetch_missing() {
    axios.get("/api/missing_filenames/")
        .then(function (response) {
            console.log("got missing: %o", response);
            for(var i=0;i<response.data.missing.length;i++) {
                app.items.push(response.data.missing[i]);
            }

        })
        .catch(function(error) {
            console.error("missing error: %o", error);
        });

}
{% endblock docscript %}

{% block admintitle %}<span data-i18n=missingfilenames class=translate>Missing filenames</span>{% endblock  %}


{% block adminpanel %}
<div id=adminpanel>


    <table class="table table-striped table-sm">
        <col style="width:10%">
        <col style="width:10%">
        <col style="width:30%"> 
        <col style="width:30%">
        <col style="width:20%">
        <thead class="thead-dark">
          <tr>
            <th data-i18n=done class=translate>done?</th>
            <th data-i18n=when class=translate>when</th>
            <th data-i18n=filename class=translate>filename</th>
            <th data-i18n=recordnumber class=translate>recordnumber</th>
            <th data-i18n=musiclibrary class=translate>music library</th>
          </tr>
        </thead>
        <tbody id=results-list style="font-size:80%">
          <template v-if="items.length">
          <missing-item v-for="item in items" 
                          v-bind:item="item"
                          v-bind:key="item.id">
          </missing-item>
          </template>
          <tr v-else>
          </tr>
        </tbody>

    </table>
</div>
{% endblock adminpanel %}