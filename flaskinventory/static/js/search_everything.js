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
            let ch = item.channel.toLowerCase()
            channel_label = `<i class="icon-${ch} color-${ch} me-2 fa-fw" alt="{{channel}}"></i>`
        } else { channel_label = '' }
        if (item.doi != null) {
            identifier = '<span class="text-muted">(DOI: {{doi}})</span>'
        } else if (item.arxiv != null) {
            identifier = '<span class="text-muted">(arXiv: {{arxiv}})</span>'
        } else {
            identifier = ''
        }
        item.type = item.type.filter(function(e) { return e !== 'Entry' })
        return '<span>' + channel_label + '{{name}}<small> (Type: {{type}}) ' + identifier + '</small></span>'
    },
    emptyTemplate: "no result for {{query}}",
    source: {
        name: {
            display: ["name", "arxiv", "doi", "title"],
            href: function(item) {
                if (item.title != null) {
                    item.unique_name = item.uid
                }
                item.type = item.type.filter(function(e) { return e !== 'Entry' })
                return $SCRIPT_ROOT + "/view/" + item.type.toString().toLowerCase() + '/uid/' + item.uid.toString()
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