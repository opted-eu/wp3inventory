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

        fetch(api + doi, { headers: { 'Accept': 'application/vnd.citationstyles.csl+json, application/x-bibtex' } })
            .then(response => response.text())
            .then(text => resolveDOI(text))
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
    document.getElementById('magic-wand').hidden = true
}


function hideSpinner(button) {
    button.getElementsByClassName('spinner-grow')[0].hidden = true
    button.getElementsByClassName('button-loading')[0].hidden = true
    button.getElementsByClassName('button-text')[0].hidden = false
    document.getElementById('magic-wand').hidden = false
    document.getElementById('magic-error-container').hidden = true

}

function handleError(error, button) {
    button.classList = ['btn btn-danger w-100']
    button.getElementsByClassName('spinner-grow')[0].hidden = true
    button.getElementsByClassName('button-loading')[0].hidden = true
    button.getElementsByClassName('button-text')[0].hidden = false
    button.getElementsByClassName('button-text')[0].innerText = 'Error!'
    document.getElementById('magic-error-container').hidden = false
    console.error(error)
}

function buttonSuccess(button) {
    button.classList = ['btn btn-success w-100']
    button.getElementsByClassName('button-text')[0].innerText = 'Success!'
    document.getElementById('magic-error-container').hidden = true
}

function resolveDOI(text) {

    result = new Array

    // if (headers.get('Content-Type').includes('csl+json')) {

    let json = JSON.parse(text)
    console.log(json)
    result['url'] = json['URL']
    result['doi'] = json['DOI']
    if (Object.keys(json).includes('container-title')) {
        if (typeof json['container-title'] === 'object') {
            result['journal'] = json['container-title'][0]
        } else {
            result['journal'] = json['container-title']
        }
    }

    if (typeof json['title'] === 'object') {
        result['name'] = json['title'][0]
    } else {
        result['name'] = json['title']
    }

    result['title'] = result['name']

    result['paper_kind'] = json['type']

    if (Object.keys(json).includes('created')) {
        if (Object.keys(json.created).includes('date-time')) {
            result['published_date'] = json.created['date-time'].split('-')[0]
        } else {
            result['published_date'] = json.created['date-parts'][0][0]
        }
    } else if (Object.keys(json).includes('issued')) {
        if (Object.keys(json.issued).includes('date-time')) {
            result['published_date'] = json.issued['date-time'].split('-')[0]
        } else {
            result['published_date'] = json.issued['date-parts'][0][0]
        }
    }

    if (Object.keys(json).includes('link')) {
        result['url'] = json['link'][0]['URL']
    }
    let authors = []

    for (let author of json.author) {
        if (Object.keys(author).includes('family')) {
            authors.push(`${author['family']}, ${author['given']}`)
        } else {
            authors.push(author.literal)
        }
    }

    result['authors'] = authors.join(';')

    if (Object.keys(json).includes('abstract')) {
        result['description'] = json.abstract
    }


    // }
    // other parser here

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

    result['title'] = result['name']

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
    result['title'] = package.info['name']
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