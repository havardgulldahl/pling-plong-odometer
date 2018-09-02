{% extends "admin.tpl" %}


{% block templates %}
<script type="text/x-template" id="license-template">
    <tr>
        <td v-bind:title="'@ '+item.timestamp"> [[ item.source ]]</td>
        <td> <i>[[ item.license_property]]</i> <b>[[ item.license_value ]]</b>
            a.k.a: 
            <ul class=list-inline style="display: inline-block">
                <li class=list-inline-item v-for="a in aliases"><i>[[a.alias]]</i></li>
            </ul>
            <input type=text placeholder="Alias" v-model="newAlias" style="width:50px">
            <button style="display: inline-block" 
                    v-on:click="add"
                    class="btn btn-outline-secondary btn-xs">Add</button>
        </td>
        <td> 
            <button type="button" 
                    disabled 
                    :title="sinceString"
                    class="btn active"
                    :class="styleObject">[[item.license_status]]</button>

        </td>
    </tr>
</script>
{% endblock templates %}

{% block docscript %}

Vue.component("license-item", {
    props: {
        item: Object,
        aliases: {
            type: Array,
            default: function() {
                return [];
            }
        }
    },
    data: function() {
        return { newAlias: "" };
    },
    delimiters: ["[[", "]]"],
    template: "#license-template",
    methods: {
        add: function(event) {
            var itm = this.item;
            //console.log("adding %o!", this.newAlias);
            this.aliases.push(this.newAlias);
            this.newAlias = "";
        }
    },
    computed: {
        styleObject: function() {
            return {
                "btn-success": this.item.license_status == "OK",
                "btn-warning": this.item.license_status == "CHECK",
                "btn-danger": this.item.license_status == "NO",
                
            }
        },
        sinceString: function() {
            return i18n.SINCE({SINCE:new Date(this.item.timestamp).toLocaleDateString()});
        }
    },
    mounted: function () {
        var itm = this.item;
        var aliases = this.aliases;
        if(itm.aliases > 0) {
            console.log("look for %i aliases for %s", itm.aliases, itm.license_value);
            axios.get("/api/license_alias/", { 
                params: {
                    property: itm.license_property,
                    value: itm.license_value
                }
            })
                .then(function (response) {
                    console.log("got aliass: %o", response);
                    for(var i=0;i<response.data.aliases.length;i++) {
                        aliases.push(response.data.aliases[i]);
                    }

                })
                .catch(function(error) {
                    console.error("license error: %o", error);
                });

        }
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