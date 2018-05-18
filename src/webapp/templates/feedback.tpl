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

Vue.component("feedback-item", {
    props: ["item"],
    delimiters: ["[[", "]]"],
    template: "#feedback-template",
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
        fetch_feedback();  
    },
    delimiters: ["[[", "]]"]
  });

function fetch_feedback() {
    axios.get("/api/feedback/")
        .then(function (response) {
            console.log("got feedback: %o", response);
            for(var i=0;i<response.data.rules.length;i++) {
                app.items.push(response.data.rules[i]);
            }

        })
        .catch(function(error) {
            inputelement.classList.toggle("loading", false);
            console.error("license error: %o", error);
        });

}
{% endblock docscript %}

{% block admintitle %}Feedback{% endblock  %}


{% block adminpanel %}
<div id=adminpanel>


    <table class="table table-striped table-sm">
        <!-- <col style="width:40%"> -->
        <col style="width:10%"> 
        <col style="width:60%">
        <col style="width:30%">
        <thead class="thead-dark">
          <tr>
            <th id=thead-source>source</th>
            <th id=thead-property>property</th>
            <th id=thead-status>status</th>
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
            <td></td>
            <td></td>
            <td></td>
          </tr>
        </tbody>

    </table>
</div>
{% endblock adminpanel %}