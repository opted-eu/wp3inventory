$.typeahead({
    input: '.search-everything',
    order: "desc",
    dynamic: true,
    minLength: 3,
    delay: 500,
    selector: {
        button: "search__everything__button"
    },
    backdrop: {
        "background-color": "#fff"
    },
    template: function(query, item) {
        if (item.channel != null) {
            channel_label = '- {{channel}}'
        } else { channel_label = '' }
        item.type = item.type.filter(function(e) { return e !== 'Entry' })
        return '<span>{{name}}{{tile}} ' + channel_label + '<small"> (Type: {{type}}) <span class="text-muted">(uid: {{uid}})</span></small></span>'
    },
    emptyTemplate: "no result for {{query}}",
    source: {
        name: {
            display: "name",
            href: function(item) {
                if (item.title != null) {
                    item.unique_name = item.uid
                }
                return $SCRIPT_ROOT + "/view/" + item.type.toString().toLowerCase() + '/' + item.unique_name.toString()
            },
            data: [{
                "uid": 0,
                "name": "not found"
            }],
            ajax: function(query) {
                return {
                    type: "GET",
                    url: $SCRIPT_ROOT + "/endpoint/quicksearch",
                    path: "data",
                    data: {
                        q: "{{query}}"
                    }
                }
            }
        }
    },
    callback: {
        // onClick: function(node, a, item, event) {

        // You can do a simple window.location of the item.href
        // alert(JSON.stringify(item));

        // },
        // onSendRequest: function(node, query) {
        //     console.log('request is sent')
        // },
        // onReceiveRequest: function(node, query) {
        //     console.log('request is received')
        // }
    },
    debug: true
});