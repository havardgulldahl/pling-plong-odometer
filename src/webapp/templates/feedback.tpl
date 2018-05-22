{% extends "admin.tpl" %}


{% block templates %}
<script type="text/x-template" id="feedback-template">
    <tr>
        <td> <input type=checkbox v-bind:checked=item.done></td>
        <td> [[ formattedTimestamp ]]</td>
        <td> [[ item.message ]]</td>
        <td> [[ item.sender ]]</td>
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
        fetch_feedback();  
    },
    delimiters: ["[[", "]]"]
  });

function fetch_feedback() {
    axios.get("/api/feedback/")
        .then(function (response) {
            console.log("got feedback: %o", response);
            for(var i=0;i<response.data.feedback.length;i++) {
                app.items.push(response.data.feedback[i]);
            }

        })
        .catch(function(error) {
            console.error("feedback error: %o", error);
        });

}
{% endblock docscript %}

{% block admintitle %}<span data-i18n=feedback class=translate>Feedback</span>{% endblock  %}


{% block adminpanel %}
<div id=adminpanel>


    <table class="table table-striped table-sm">
        <col style="width:10%">
        <col style="width:20%"> 
        <col style="width:50%">
        <col style="width:20%">
        <thead class="thead-dark">
          <tr>
            <th data-i18n=done class=translate>done?</th>
            <th data-i18n=when class=translate>when</th>
            <th data-i18n=message class=translate>message</th>
            <th data-i18n=sender class=translate>sender</th>
          </tr>
        </thead>
        <tbody id=results-list style="font-size:80%">
          <template v-if="items.length">
          <feedback-item v-for="item in items" 
                          v-bind:item="item"
                          v-bind:key="item.public_id">
          </feedback-item>
          </template>
          <tr v-else>
          </tr>
        </tbody>

    </table>
</div>
{% endblock adminpanel %}