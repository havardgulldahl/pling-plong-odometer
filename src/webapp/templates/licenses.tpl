{% extends "admin.tpl" %}


{% block templates %}
<script type="text/x-template" id="license-template">
    <tr  v-bind:class="classObject">
        <td v-bind:title="'@ '+item.timestamp"> [[ item.source ]]</td>
        <td> [[ item.license_property]]: [[ item.license_value ]] </td>
        <td> [[ item.comment ]]</td>
    </tr>
</script>
{% endblock templates %}

{% block docscript %}

Vue.component("license-item", {
    props: ["item"],
    delimiters: ["[[", "]]"],
    template: "#license-template",
    methods: {
    },
    computed: {
        classObject: function() {
            return {
                "text-success": this.item.license_status == "green",
                "text-warning": this.item.license_status == "yellow",
                "text-danger": this.item.license_status == "red",
                
            }
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
        fetch_license_rules();  
    },
    delimiters: ["[[", "]]"]
  });

function resolve_manually_delay(inputelement) {
    // add a delay so we dont run this while typing
    if(resolve_manually_delay.tick) {
        window.clearTimeout(resolve_manually_delay.tick);
    }
    resolve_manually_delay.tick = window.setTimeout(function() {
        resolve_manually(inputelement);
    },
    900 );
}

function fetch_license_rules() {
    axios.get("/api/license_rules/")
        .then(function (response) {
            console.log("got licenses: %o", response);
            for(var i=0;i<response.data.rules.length;i++) {
                app.items.push(response.data.rules[i]);
            }

        })
        .catch(function(error) {
            console.error("license error: %o", error);
        });

}
{% endblock docscript %}

{% block admintitle %}<span class=translate data-i18n=licenses>Licenses</span>{% endblock  %}


{% block adminpanel %}
<div id=adminpanel>


    <table class="table table-striped table-sm">
        <!-- <col style="width:40%"> -->
        <col style="width:10%"> 
        <col style="width:60%">
        <col style="width:30%">
        <thead class="thead-dark">
          <tr>
            <th class=translate data-i18n=source>source</th>
            <th class=translate data-i18n=property>property</th>
            <th class=translate data-i18n=status>status</th>
          </tr>
        </thead>
        <tbody id=results-list style="font-size:80%">
          <template v-if="items.length">
          <license-item v-for="item in items" 
                          v-bind:item="item"
                          v-bind:key="item.uuid">
          </license-item>
          </template>
          <tr v-else>
          </tr>
        </tbody>

    </table>
</div>
{% endblock adminpanel %}