function fetchMetaData(button) {

    var platform = document.getElementById('magic-platform').value

    if (!platform) {
        return false
    }

    var identifier = document.getElementById('magic-identifier').value

    if (!identifier) {
        return false
    }

    // clear form
    document.getElementById('form-add-new').reset()

    showSpinner(button)

    if (platform == 'doi') {

        // sanitize identifier string

        doi = identifier.replace("https://doi.org/", "")
        doi = doi.replace("http://doi.org/", "")
        doi = doi.replace("doi.org/", "")

        let api = 'http://doi.org/'

        fetch(api + doi, {headers: {'Accept': 'application/json,application/x-bibtex'}})
            .then(response => response.json())
            .then(json => parseDOI(json))
            .then(result => fillForm(result))
            .then(_ => hideSpinner(button), buttonSuccess(button))
            .catch(error => handleError(error, button))

    } else if (platform == 'arxiv') {

        // sanitize identifier string
        arxiv = identifier.replace('https://arxiv.org/abs/', '')
        arxiv = arxiv.replace('http://arxiv.org/abs/', '')
        arxiv = arxiv.replace('arxiv.org/abs/', '')
        arxiv = arxiv.replace('abs/', '')

        let api = "http://export.arxiv.org/api/query?id_list="

        fetch(api + arxiv)
            .then(response => response.text())
            .then(xml => parseArXiv(xml))
            .then(result => fillForm(result))
            .then(_ => hideSpinner(button), buttonSuccess(button))
            .catch(error => handleError(error, button))

    } else if (platform == 'cran') {

        // sanitize identifier string

        let api = $SCRIPT_ROOT + '/endpoint/cran?package='

        fetch(api + identifier)
            .then(response => response.json())
            .then(result => fillForm(result))
            .then(_ => hideSpinner(button), buttonSuccess(button))
            .catch(error => handleError(error, button))

    } else if (platform == 'python') {
        let api = "https://pypi.org/pypi/"

        fetch(api + identifier + '/json')
            .then(response => response.json())
            .then(json => parsePyPi(json))
            .then(result => fillForm(result))
            .then(_ => hideSpinner(button), buttonSuccess(button))
            .catch(error => handleError(error, button))
    }

};

function fillForm(data) {
    for (let key in data) {
        let field = document.getElementById(key)
        if (field) {
            if (field.multiple) {
                for (let v of data[key]) {
                    document.querySelector(`#${field.id} option[value="${v}"]`).selected = true
                }
            } else {
                field.value = data[key]
            }
            if (field.tomselect) {
                field.tomselect.sync()
            };
        };
    };
};

function showSpinner(button) {
    button.classList = ['btn btn-primary w-100']
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
    button.classList = ['btn btn-danger w-100']
    button.getElementsByClassName('spinner-grow')[0].hidden = true
    button.getElementsByClassName('button-loading')[0].hidden = true
    button.getElementsByClassName('button-text')[0].hidden = false
    button.getElementsByClassName('button-text')[0].innerText = 'Error!'
    console.error(error)
}

function buttonSuccess(button) {
    button.classList = ['btn btn-success w-100']
    button.getElementsByClassName('button-text')[0].innerText = 'Success!'
}

function resolveDOI(res) {

    let text = res.text()

    try {
        let json = JSON.parse(text)
    } catch {
        let bib =  parseBibFile(text)
    }

    if (json) {
        result = parseJSONDOI(json, res.url)
    }
    else if (bib) {
        result = normalizeBib(bib)
    }

    return result

}

function parseJSONDOI(publication, framework) {

    result = new Array()

    if (framework.includes('crosscite.org')) {
        // parse
    }
    else if (framework.includes('crossref.org')) {

        result['url'] = publication.message['url']
        result['doi'] = publication.message['DOI']
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
    }

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

function parsePyPi(package) {

    result = new Array()

    result['name'] = package.info['name']
    result['other_names'] = package.info['summary']
    result['description'] = package.info['description']
    result['url'] = package.info['home_page']
    result['authors'] = package.info['author']
    result['materials'] = []
    for (url in package.info['project_urls']) {
        result['materials'].push(package.info.project_urls[url])
    }

    result['programming_languages'] = ['python']
    result['platform'] = ['windows', 'linux', 'macos']
    return result
}