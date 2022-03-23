function fetchMetaData(button) {

    var platform = document.getElementById('platform').value

    if (!platform) {
        return false
    }

    var identifier = document.getElementById('identifier').value

    if (!identifier) {
        return false
    }

    showSpinner(button)

    if (platform == 'doi') {

        let api = 'https://api.crossref.org/works/'

        fetch(api + identifier)
            .then(response => response.json())
            .then(json => parseDOI(json))
            .then(result => fillForm(result))
            .then(_ => hideSpinner(button), buttonSuccess(button))
            .catch(error => handleError(error, button))

    } else if (platform == 'arxiv') {

        let api = "http://export.arxiv.org/api/query?id_list="

        fetch(api + identifier)
            .then(response => response.text())
            .then(xml => parseArXiv(xml))
            .then(result => fillForm(result))
            .then(_ => hideSpinner(button), buttonSuccess(button))
            .catch(error => handleError(error, button))

    } else if (platform == 'cran') {

        let api = 'https://crandb.r-pkg.org/'

        fetch(api + identifier, { mode: 'no-cors' })
            .then(response => response.json())
            .then(json => parseCRAN(json))
            .then(result => fillForm(result))
            .then(_ => hideSpinner(button), buttonSuccess(button))
            .catch(error => handleError(error, button))

    }

};

function fillForm(data) {
    for (let key in data) {
        let field = document.getElementById(key)
        if (field) {
            field.value = data[key]
            if (field.tomselect) {
                field.tomselect.sync()
            };
        };
    };
};

function showSpinner(button) {
    button.classList = ['btn btn-primary']
    button.getElementsByClassName('spinner-grow')[0].hidden = false
    button.getElementsByClassName('button-loading')[0].hidden = false
    button.getElementsByClassName('button-text')[0].hidden = true
}


function hideSpinner(button) {
    button.getElementsByClassName('spinner-grow')[0].hidden = true
    button.getElementsByClassName('button-loading')[0].hidden = true
    button.getElementsByClassName('button-text')[0].hidden = false
}

function handleError(error, button) {
    button.classList = ['btn btn-danger']
    button.getElementsByClassName('spinner-grow')[0].hidden = true
    button.getElementsByClassName('button-loading')[0].hidden = true
    button.getElementsByClassName('button-text')[0].hidden = false
    button.getElementsByClassName('button-text')[0].innerText = 'Error!'
    console.error(error)
}

function buttonSuccess(button) {
    button.classList = ['btn btn-success']
    button.getElementsByClassName('button-text')[0].innerText = 'Success!'
}

function parseDOI(publication) {
    result = new Array()
    result['url'] = publication.message['url']
    if (typeof publication.message['container-title'] === 'object') {
        result['journal'] = publication.message['container-title'][0]
    } else {
        result['journal'] = publication.message['container-title']
    }

    if (typeof publication.message['title'] === 'object') {
        result['name'] = publication.message['title'][0]
    } else {
        result['name'] = publication.message['title']
    }

    result['paper_kind'] = publication.message['type']

    result['published_date'] = publication.message.created['date-time'].split('-')[0]


    result['url'] = publication.message['link'][0]['URL']

    let authors = []

    for (let author of publication.message.author) {
        authors.push(`${author['family']}, ${author['given']}`)
    }

    result['authors'] = authors.join(';')

    return result

}

function parseArXiv(xml) {

    let parser = new DOMParser()

    let publication = parser.parseFromString(xml, 'text/xml')

    let total_result = publication.getElementsByTagName('opensearch:totalResults')[0].innerHTML
    if (!total_result) {
        total_result = publication.getElementsByTagName('opensearch:totalresults')[0].innerHTML
    }

    if (parseInt(total_result) < 1) {
        return false
    }

    publication = publication.getElementsByTagName('entry')[0]

    let result = new Array()

    result['arxiv'] = publication.getElementsByTagName('id')[0].innerHTML

    result['url'] = result['arxiv']

    result['name'] = publication.getElementsByTagName('title')[0].innerHTML

    let authors = []

    for (author of publication.getElementsByTagName('author')) {
        let author_raw = author.getElementsByTagName('name')[0].innerHTML
        author_raw = author_raw.split(' ')
        author_name = author_raw.pop() + ', ' + author_raw.join(" ")
        authors.push(author_name)
    }
    result['authors'] = authors.join(';')

    result['published_date'] = publication.getElementsByTagName('published')[0].innerHTML.split('-')[0]

    result['description'] = publication.getElementsByTagName('summary')[0].innerHTML.trim()

    return result
}

function parseCRAN(package) {

    result = new Array()

    result['name'] = package['Package']
    result['description'] = package['Description']
    result['other_names'] = package['Title']
    result['url'] = package['URL']
    result['programming_languages'] = 'r'

    return result
}