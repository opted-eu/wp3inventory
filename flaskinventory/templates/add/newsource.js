// rewrite everything without jquery https://tobiasahlin.com/blog/move-from-jquery-to-vanilla-javascript/#selecting-elements

// ********************
// Function declaration
// ********************

// Get custom attribute (data-value) from all select and put them in hidden fields
document.querySelectorAll('select').forEach(function(item) {
    if (document.getElementById(item.id + '-hidden')) {
        item.addEventListener('change', function() {
            document.getElementById(this.id + '-hidden').value = this.options[this.selectedIndex].getAttribute('data-value')
        })
    }
})

var geographicScopeSingle = new Object
var geographicScopeMultiple = new Object
var geographicScopeSubunit = new Object


function addFieldOptionsData(fieldOptions, key, selector, addother = false) {
    var opts = fieldOptions[key] // .sort((a, b) => a.name > b.name ? 1 : -1);
    opts.forEach(function(item, i) {
        let opt = document.createElement('option')
        opt.setAttribute('value', item.uid)
        opt.setAttribute('data-value', item.unique_name)
        opt.setAttribute('data-index', i)
        opt.innerText = item.name
        document.querySelector(selector).append(opt);
    });
    if (addother) {
        let optOther = document.createElement('option')
        optOther.setAttribute('value', 'other')
        optOther.setAttribute('data-value', 'new')
        optOther.setAttribute('data-index', '99')
        optOther.innerText = 'Other'
        document.querySelector(selector).append(optOther);
    }
};

function addFieldOptions(fieldOptions, key, selector, addother, othernames = false, datavalue = true) {
    var opts = fieldOptions[key] // .sort((a, b) => a.name > b.name ? 1 : -1);
    opts.forEach(function(item, i) {
        let opt = document.createElement('option')
        opt.setAttribute('value', item.uid)
        if (datavalue == true) {
            opt.setAttribute('data-value', item.unique_name)
        }
        opt.setAttribute('data-index', i)
        let item_label = item.name
        if (othernames) {
            if ('other_names' in item) {
                item_label += ' (' + item.other_names.join(', ') + ')'
            }
        }
        if ('country' in item) {
            item_label += ' [' + item.country[0]['name'] + ']'
        }
        opt.innerText = item_label
        document.querySelector(selector).append(opt);
    });
    if (addother) {
        let optOther = document.createElement('option')
        optOther.setAttribute('value', 'other')
        optOther.setAttribute('data-value', 'new')
        optOther.setAttribute('data-index', '99')
        optOther.innerText = 'Other'
        document.querySelector(selector).append(optOther);
    }
};

function addLanguages(fieldOptions, key, selector) {
    fieldOptions[key].forEach(function(item, i) {
        let opt = document.createElement('option')
        opt.setAttribute('value', item.code)
        opt.innerText = item.name
        document.querySelector(selector).append(opt);
    });
}

// misc: optional tag for label

const optionalTag = '<span class="text-muted mx-1">(optional)</span>'



function getFieldOptions(targetUrl) {
    return new Promise(function(resolve, reject) {
        fetch(targetUrl)
            .then(data => {
                resolve(data);
            }).catch(error => {
                reject(error)
            })
    });
}

// Field Visibility Logic
function channelVisibility(fieldOptions, allNames, el) {
    var value = el.target.options[el.target.selectedIndex].getAttribute('data-value')
    var index = el.target.options[el.target.selectedIndex].getAttribute('data-index')
    if (index == null) {
        return;
    }
    allNames.forEach((elem) => elem.hidden = true);
    document.getElementById('group-name').hidden = false;

    document.getElementById('name-print-tooltip').hidden = true;
    document.getElementById('name-facebook-tooltip').hidden = true;
    document.getElementById('name-website-tooltip').hidden = true;
    document.getElementById('name-instagram-tooltip').hidden = true;
    document.getElementById('name-twitter-tooltip').hidden = true;
    document.querySelector('#group-audience-size-followers').hidden = true

    if (index != 99) {
        document.querySelector("#name-question").innerText = fieldOptions.channel[index]['form_name_question'];
        document.querySelector("#name").setAttribute("placeholder", fieldOptions.channel[index]['form_name_placeholder'])
        if ('form_name_helptext' in fieldOptions.channel[index]) {
            document.querySelector('#name-helptext').innerText = fieldOptions.channel[index]['form_name_helptext'];
        } else { document.querySelector('#name-helptext').innerText = "" };
        if ('form_name_addon' in fieldOptions.channel[index]) {
            document.querySelector("#name-addon").hidden = false;
            document.querySelector("#name-addon").innerText = fieldOptions.channel[index]['form_name_addon'];
        } else { document.querySelector("#name-addon").hidden = true; };
    } else {

        document.querySelector("#group-name label").innerText = "What is the name of the news source that you suggest?";
        document.querySelector("#name").setAttribute("placeholder", "");
        document.querySelector("#name-addon").hidden = true;
    };

    // Set / Reset certain fields to be required
    document.querySelectorAll('input[name="transcript_kind"').forEach((elem) => {
        elem.removeAttribute('required')
    })

    document.querySelectorAll('input[name="website_allows_comments"]').forEach((elem) => {
        elem.required = false
    });

    document.querySelectorAll('input[name="website_comments_registration_required"]').forEach((elem) => {
        elem.required = false
    });

    document.querySelectorAll('input[name="payment_model"').forEach((elem) => {
        elem.removeAttribute('required')
    });
    document.querySelector("#group-archive-sources-included").hidden = true

    document.querySelectorAll('input[name="channel_epaper"').forEach((elem) => {
        elem.removeAttribute('required');
    })

    document.querySelector("#form-check-contains-ads-1").hidden = false
    document.querySelector("#contains_ads1").required = true
    document.querySelector('label[for="contains_ads1"]').innerHTML = 'Yes, for all audiences'

    document.querySelector("#form-check-contains-ads-2").hidden = false
    document.querySelector("#contains_ads2").required = true
    document.querySelector('label[for="contains_ads2"]').innerHTML = 'Yes, but not for paying users'

    document.querySelector("#form-check-contains-ads-3").hidden = false
    document.querySelector("#contains_ads3").required = true
    document.querySelector('label[for="contains_ads3"]').innerHTML = 'No, not at all'

    document.querySelector("#form-check-contains-ads-4").hidden = false
    document.querySelector("#contains_ads4").required = true
    document.querySelector('label[for="contains_ads4"]').innerHTML = "Don't know"

    if (value == 'print') {
        document.getElementById('name-print-tooltip').hidden = false;
        document.querySelector("#group-epaper").hidden = false;
        document.querySelectorAll('input[name="channel_epaper"').forEach((elem) => {
            elem.setAttribute('required', true);
        })
        document.querySelector("#group-audience-size").hidden = false;
        document.querySelector("#group-source-founded").hidden = false;
        document.querySelector('#source-founded-question').innerHTML = `What year was the print news source founded?`
        document.querySelector("#group-payment-model").hidden = false;
        document.querySelectorAll('input[name="payment_model"').forEach((elem) => {
            elem.setAttribute('required', true);
        })
        document.querySelector("#group-archive-sources-included").hidden = false


    } else if (value == 'transcript') {
        document.querySelector("#group-transcript-kind").hidden = false;
        document.querySelectorAll('input[name="transcript_kind"').forEach((elem) => {
            elem.setAttribute('required', true);
        });
        document.querySelector("#group-source-founded").hidden = false;
        document.querySelector('#source-founded-question').innerHTML = `What year was the radio/TV show or podcast founded?`

        document.querySelector("#group-payment-model").hidden = false;
        document.querySelectorAll('input[name="payment_model"').forEach((elem) => {
            elem.setAttribute('required', true);
            elem.parentElement.hidden = false
        })
        document.querySelector("#group-archive-sources-included").hidden = false


    } else if (value == 'website') {
        document.getElementById('name-website-tooltip').hidden = false;
        document.querySelector("#group-website_allows_comments").hidden = false;
        document.querySelectorAll('input[name="website_allows_comments"]').forEach((elem) => {
            elem.required = true
        });
        document.querySelector("#group-source-founded").hidden = false;
        document.querySelector('#source-founded-question').innerHTML = `What year was the website founded?`
        document.querySelector("#group-payment-model").hidden = false;
        document.querySelectorAll('input[name="payment_model"').forEach((elem) => {
            elem.setAttribute('required', true);
            elem.parentElement.hidden = false
        })
        document.querySelector("#group-archive-sources-included").hidden = false
    } else if (value == 'facebook') {
        document.getElementById('name-facebook-tooltip').hidden = false;
        document.querySelector('#group-source-founded').hidden = false
        document.querySelector('#source-founded-question').innerHTML = `What year was the facebook page created?`
        document.querySelector('#group-audience-size-followers').hidden = false

        document.querySelector('label[for="contains_ads1"]').innerHTML = 'Yes'

        document.querySelector("#form-check-contains-ads-2").hidden = true
        document.querySelector("#contains_ads2").required = false

        document.querySelector('label[for="contains_ads3"]').innerHTML = 'No'

    } else if (value == 'instagram') {
        document.getElementById('name-instagram-tooltip').hidden = false;

        document.querySelector('label[for="contains_ads1"]').innerHTML = 'Yes'

        document.querySelector("#form-check-contains-ads-2").hidden = true
        document.querySelector("#contains_ads2").required = false

        document.querySelector('label[for="contains_ads3"]').innerHTML = 'No'

    } else if (value == 'twitter') {
        document.getElementById('name-twitter-tooltip').hidden = false;

        document.querySelector('label[for="contains_ads1"]').innerHTML = 'Yes'

        document.querySelector("#form-check-contains-ads-2").hidden = true
        document.querySelector("#contains_ads2").required = false

        document.querySelector('label[for="contains_ads3"]').innerHTML = 'No'
    }
};

if (document.querySelector('input[name="special_interest"]')) {
    document.querySelectorAll('input[name="special_interest"]').forEach((elem) => {
        elem.addEventListener("change", function(event) {
            var item = event.target.value;
            if (item == 'no') {
                document.getElementById('group-topical-focus').hidden = true;
                document.getElementById('topical-focus-ts-control').required = false;
                document.getElementById('topical-focus').required = false;

            }
            if (item == 'yes') {
                document.getElementById('group-topical-focus').hidden = false;
                document.getElementById('topical-focus-ts-control').required = true;
                document.getElementById('topical-focus').required = true;
            }
        });
    });
};

if (document.querySelector('#publication-cycle')) {
    document.getElementById('publication-cycle').addEventListener("change", function(event) {
        if (this.value == 'multiple times per week' || this.value == 'weekly') {
            document.getElementById('group-publication-cycle-weekday').hidden = false;

            if (this.value == 'weekly') {
                let weekday = document.querySelectorAll('input[id^="publication-cycle-weekday-"]')
                weekday.forEach((el) => {
                    el.setAttribute('type', 'radio')
                    el.disabled = false
                    el.checked = false
                });

            }
            if (this.value == 'multiple times per week') {
                let weekday = document.querySelectorAll('input[id^="publication-cycle-weekday-"]')
                weekday.forEach((el) => {
                    el.setAttribute('type', 'checkbox')
                    el.disabled = false
                    el.checked = false
                });
            }
        } else {
            document.getElementById('group-publication-cycle-weekday').hidden = true;
        }
    });
};

document.addEventListener('input', (e) => {

    if (e.target.getAttribute('name') == "website_allows_comments")
        if (e.target.value == 'yes') {
            document.getElementById('group-website_comments_registration_required').hidden = false;
        } else {
            document.getElementById('group-website_comments_registration_required').hidden = true;
        };
})

if (document.querySelector('#publication-cycle-weekday-none')) {
    document.getElementById('publication-cycle-weekday-none').addEventListener("change", function(event) {
        if (this.checked && this.type == 'checkbox') {
            document.querySelectorAll('input[name^="publication_cycle_weekday"').forEach((elem) => {
                if (!elem.id.includes('none')) {
                    elem.checked = false
                    elem.disabled = true
                }
            });
        } else {
            document.querySelectorAll('input[name^="publication_cycle_weekday"').forEach((elem) => {
                elem.disabled = false
            });
        }
    })
};

if (document.querySelector('input[name="geographic_scope"]')) {
    document.querySelectorAll('input[name="geographic_scope"]').forEach((elem) => {
        elem.addEventListener("input", function(event) {
            var item = event.target.value;
            if (item == 'multinational') {
                document.getElementById('group-geographic-scope-multiple').hidden = false;
                document.getElementById('group-geographic-scope-single').hidden = true;
                document.getElementById('group-geographic-scope-subunit').hidden = true;

                document.getElementById('geographic-scope-multiple').required = true;
                if (document.getElementById('geographic-scope-multiple-ts-control')) {
                    document.getElementById('geographic-scope-multiple-ts-control').required = true;
                }
                document.getElementById('geographic-scope-single').required = false;
                if (document.getElementById('geographic-scope-single-ts-control')) {
                    document.getElementById('geographic-scope-single-ts-control').required = false;
                }
                document.getElementById('geographic-scope-subunit').required = false;
                if (document.getElementById('geographic-scope-subunit-ts-control')) {
                    document.getElementById('geographic-scope-subunit-ts-control').required = false;
                }
                geographicScopeSingle.clear();
                geographicScopeSubunit.clear();
            } else if (item == 'national') {
                document.getElementById('group-geographic-scope-multiple').hidden = true;
                document.getElementById('group-geographic-scope-single').hidden = false;
                document.getElementById('group-geographic-scope-subunit').hidden = true;

                document.getElementById('geographic-scope-multiple').required = false;
                if (document.getElementById('geographic-scope-multiple-ts-control')) {
                    document.getElementById('geographic-scope-multiple-ts-control').required = false;
                }
                document.getElementById('geographic-scope-single').required = true;
                if (document.getElementById('geographic-scope-single-ts-control')) {
                    document.getElementById('geographic-scope-single-ts-control').required = true;
                    document.getElementById('geographic-scope-single-ts-label').innerText = "What is the national scope?"
                }

                document.getElementById('geographic-scope-subunit').required = false;
                if (document.getElementById('geographic-scope-subunit-ts-control')) {
                    document.getElementById('geographic-scope-subunit-ts-control').required = false;
                    geographicScopeMultiple.clear();
                    geographicScopeSubunit.clear();
                }
            } else if (item == 'subnational') {
                document.getElementById('group-geographic-scope-multiple').hidden = true;
                document.getElementById('group-geographic-scope-single').hidden = false;
                document.getElementById('group-geographic-scope-subunit').hidden = false;

                document.getElementById('geographic-scope-multiple').required = false;
                if (document.getElementById('geographic-scope-multiple-ts-control')) {
                    document.getElementById('geographic-scope-multiple-ts-control').required = false;
                }
                document.getElementById('geographic-scope-single').required = true;
                if (document.getElementById('geographic-scope-single-ts-control')) {
                    document.getElementById('geographic-scope-single-ts-control').required = true;
                    document.getElementById('geographic-scope-single-ts-label').innerText = "To which national context does the subnational unit belong?"
                }

                document.getElementById('geographic-scope-subunit').required = true;
                if (document.getElementById('geographic-scope-single-ts-control')) {
                    document.getElementById('geographic-scope-single-ts-control').required = true;
                }

                geographicScopeMultiple.clear();
            } else {
                document.getElementById('group-geographic-scope-multiple').hidden = true;
                document.getElementById('group-geographic-scope-single').hidden = true;
                document.getElementById('group-geographic-scope-subunit').hidden = true;

                document.getElementById('geographic-scope-multiple').required = false;
                if (document.getElementById('geographic-scope-multiple-ts-control')) {
                    document.getElementById('geographic-scope-multiple-ts-control').required = false;
                }
                document.getElementById('geographic-scope-single').required = false;
                if (document.getElementById('geographic-scope-single-ts-control')) {
                    document.getElementById('geographic-scope-single-ts-control').required = false;
                }

                document.getElementById('geographic-scope-subunit').required = false;
                if (document.getElementById('geographic-scope-single-ts-control')) {
                    document.getElementById('geographic-scope-single-ts-control').required = false;
                }

                geographicScopeSingle.clear();
                geographicScopeMultiple.clear();
                geographicScopeSubunit.clear();
            }
        });
    });
};


// populate form on page load
function populateForm(jsonData) {
    if ('uid' in jsonData) {
        document.getElementById("uid-hidden").value = jsonData["uid"]
    };
    if ('channel' in jsonData) {
        document.getElementById("channel-select").value = jsonData["channel"].uid
        document.getElementById("channel-select-hidden").value = jsonData["channel"].unique_name
    };
    if ('name' in jsonData) {
        document.getElementById("heading-name").innerText = ': ' + jsonData["name"]
    };
    if ("other_names" in jsonData) {
        document.getElementById("other-names").value = jsonData["other_names"].join(",");
    };
    if ("founded" in jsonData) {
        document.getElementById("source-founded").value = jsonData["founded"].split("-")[0]
    };
    if ("payment_model" in jsonData) {
        document.querySelector(`input[name=payment_model][value='${jsonData["payment_model"]}']`).checked = true
    };
    if ("contains_ads" in jsonData) {
        document.querySelector(`input[name=contains_ads][value='${jsonData["contains_ads"]}']`).checked = true
    };
    if ("publishes_org" in jsonData) {
        jsonData["publishes_org"].forEach(function(item) {
            let opt = document.createElement('option')
            opt.setAttribute('value', item.uid)
            opt.innerText = item.name
            opt.selected = true
            document.getElementById("publishes_org").append(opt);
        })
    };
    if ("publishes_person" in jsonData) {
        jsonData["publishes_person"].forEach(function(item) {
            let opt = document.createElement('option')
            opt.setAttribute('value', item.uid)
            opt.innerText = item.name
            opt.selected = true
            document.getElementById("publishes_person").append(opt);
        })
    };
    if ("publication_kind" in jsonData) {
        jsonData["publication_kind"].forEach(function(item) {
            item = item.toLowerCase()
            if (document.querySelector(`#publication-kind option[value='${item}']`)) {
                document.querySelector(`#publication-kind option[value='${item}']`).selected = true
            } else {
                let opt = document.createElement('option')
                opt.setAttribute('value', item)
                opt.innerText = item
                opt.selected = true
                document.getElementById("publication-kind").append(opt);
            }
        })
    };
    if ("special_interest" in jsonData) {
        if (jsonData["special_interest"]) {
            document.getElementById("special_interest2").checked = true
        }
    };
    if ("topical_focus" in jsonData) {
        jsonData["topical_focus"].forEach(function(item) {
            item = item.toLowerCase()
            if (document.querySelector(`#topical-focus option[value='${item}']`)) {
                document.querySelector(`#topical-focus option[value='${item}']`).selected = true
            } else {
                let opt = document.createElement('option')
                opt.setAttribute('value', item)
                opt.innerText = item
                opt.selected = true
                document.getElementById("topical-focus").append(opt);
            }
        })
    };
    if ("publication_cycle" in jsonData) {
        document.getElementById("publication-cycle").value = jsonData["publication_cycle"]
        if ("publication_cycle_weekday" in jsonData) {
            if (jsonData["publication_cycle"] == "weekly") {
                document.getElementById('publication-cycle').dispatchEvent(new Event("change"))
                document.querySelector(`input[name=publication_cycle_weekday][value="${jsonData['publication_cycle_weekday'][0]}"]`).checked = true
            } else if (jsonData["publication_cycle"] == "multiple times per week") {
                document.getElementById('publication-cycle').dispatchEvent(new Event("change"))
                for (item of jsonData["publication_cycle_weekday"]) {
                    document.getElementById(`publication-cycle-weekday-${item}`).checked = true
                }
            }
        }
    };
    if ("geographic_scope" in jsonData) {
        document.querySelector(`input[name=geographic_scope][value='${jsonData["geographic_scope"]}']`).checked = true
        document.querySelector(`input[name=geographic_scope][value='${jsonData["geographic_scope"]}']`).dispatchEvent(new Event("input"))
        let hiddenGeographicScopeCountry = document.getElementById('geographic-scope-countries-hidden')
        if ("country" in jsonData) {
            if (jsonData["geographic_scope"] == "multinational") {
                for (country of jsonData["country"]) {
                    if (document.querySelector(`#geographic-scope-multiple option[value='${country.unique_name}']`)) {
                        document.querySelector(`#geographic-scope-multiple option[value='${country.unique_name}']`).selected = true
                        hiddenGeographicScopeCountry.value += country["uid"] + ","
                    }
                }
                if ("geographic_scope_subunit" in jsonData) {
                    for (subunit of jsonData["geographic_scope_subunit"]) {
                        if (document.querySelector(`#geographic-scope-multiple option[value='${subunit.unique_name}']`)) {
                            document.querySelector(`#geographic-scope-multiple option[value='${subunit.unique_name}']`).selected = true
                            document.getElementById("geographic-scope-subunits-hidden").value += country["uid"] + ","
                        }
                    }
                    hiddenGeographicScopeCountry.value = jsonData["country"][0]["uid"]
                    document.querySelector(`#geographic-scope-single option[value='${jsonData['country'][0]["uid"]}']`).selected = true
                }
            } else if (jsonData["geographic_scope"] == "national") {
                let country = jsonData["country"][0]
                if (document.querySelector(`#geographic-scope-single option[value='${country["uid"]}']`)) {
                    document.querySelector(`#geographic-scope-single option[value='${country["uid"]}']`).selected = true
                    hiddenGeographicScopeCountry.value = country['uid']
                }

            } else if (jsonData["geographic_scope"] == "subnational") {
                if ("geographic_scope_subunit" in jsonData) {
                    for (subunit of jsonData["geographic_scope_subunit"]) {
                        if (document.querySelector(`#geographic-scope-subunit option[value='${subunit.uid}']`)) {
                            document.querySelector(`#geographic-scope-subunit option[value='${subunit.uid}']`).selected = true
                        }
                    }
                    let country = jsonData["country"][0]
                    if (document.querySelector(`#geographic-scope-single option[value='${country["uid"]}']`)) {
                        document.querySelector(`#geographic-scope-single option[value='${country["uid"]}']`).selected = true
                        hiddenGeographicScopeCountry.value = country['uid']
                    }
                }
            }
        }
    };
    if ("languages" in jsonData) {
        for (lang of jsonData["languages"]) {
            document.querySelector(`#languages option[value=${lang}]`).selected = true
        }

    };
    if ("channel_epaper" in jsonData) {
        document.querySelector(`input[name=channel_epaper][value='${jsonData["channel_epaper"]}']`).checked = true
    };
    if ("archives" in jsonData) {
        for (archive of jsonData["archives"]) {
            document.querySelector(`#archive-sources-included option[value='${archive.uid}']`).selected = true
        }
    };
    if ("datasets" in jsonData) {
        for (dataset of jsonData["datasets"]) {
            document.querySelector(`#dataset-sources-included option[value='${dataset.uid}']`).selected = true
        }
    };
    if ("entry_notes" in jsonData) {
        document.getElementById("entry-notes").value = jsonData["entry_notes"]
    };
    if ("related" in jsonData) {
        jsonData["related"].forEach(function(item) {
                let opt = document.createElement('option')
                opt.setAttribute('value', item.uid)
                opt.innerText = item.name + ' (' + item.channel.name + ')'
                opt.selected = true
                document.getElementById("related-sources").append(opt);
            })
            // add self to related
    };
};

// Progress Bar
function setProgressBar(curStep, steps) {
    var percent = parseFloat(100 / steps) * curStep;
    percent = percent.toFixed();
    document.getElementById('questionnaire-progress').style.width = percent + '%'
    document.getElementById('questionnaire-progress').setAttribute('aria-valuenow', percent + '%')
};

// document ready function
var ready = (callback) => {
    if (document.readyState != "loading") callback();
    else document.addEventListener("DOMContentLoaded", callback);
}


ready(() => {

    // declare constants
    const formId = "new-source";
    const formUrl = location.href;
    const formIdentifier = `${formUrl} ${formId}`;
    // var persistentForm = document.querySelector(`#${formId}`)

    // Load Select options from json api
    getFieldOptions('{{ url_for("endpoint.fieldoptions") }}')
        .then(response => response.json())
        .then(function(data) {

            addFieldOptionsData(data, 'channel', '#channel-select');
            addLanguages(data, 'language', '#languages', false);
            addFieldOptions(data, 'country', '#geographic-scope-single', false, false, false);
            addFieldOptions(data, 'subunit', '#geographic-scope-subunit', false, true, false);

            addFieldOptions(data, 'archive', '#archive-sources-included', false, false, false);
            addFieldOptions(data, 'dataset', '#dataset-sources-included', false, false, false);

            // Add field options for Country & Subunit Selection (Multiple Choice)
            var countries = data.country;
            var subunits = data.subunit;
            var multinational = data.multinational
                // Sort values alphabetically
                // countries.sort((a,b) => a.name > b.name ? 1 : -1);
                // subunits.sort((a,b) => a.name > b.name ? 1 : -1);

            var inputGeographicScopeMultiple = document.getElementById('geographic-scope-multiple');

            var optgroupMultinational = document.createElement('optgroup');
            optgroupMultinational.setAttribute('label', 'Multinational Constructs');
            multinational.forEach(function(item, i) {
                let opt = document.createElement('option')
                opt.setAttribute('value', item.unique_name)
                opt.setAttribute('data-uid', item.uid)
                opt.setAttribute('data-type', 'country')
                opt.innerText = item.name
                optgroupMultinational.append(opt)
            });

            var optgroupCountries = document.createElement('optgroup');
            optgroupCountries.setAttribute('label', 'Country');
            countries.forEach(function(item, i) {
                let opt = document.createElement('option')
                opt.setAttribute('value', item.unique_name)
                opt.setAttribute('data-uid', item.uid)
                opt.setAttribute('data-type', 'country')
                opt.innerText = item.name
                optgroupCountries.append(opt)
            });

            var optgroupSubunits = document.createElement('optgroup');
            optgroupSubunits.setAttribute('label', 'Subunit');
            subunits.forEach(function(item, i) {
                let opt = document.createElement('option')
                opt.setAttribute('value', item.unique_name)
                opt.setAttribute('data-uid', item.uid)
                opt.setAttribute('data-type', 'subunit')
                let item_label = item.name
                if ('other_names' in item) {
                    item_label += ' (' + item.other_names.join(', ') + ')'
                }
                if ('country' in item) {
                    item_label += ' [' + item.country[0]['name'] + ']'
                }
                opt.innerText = item_label
                optgroupSubunits.append(opt)
            });

            inputGeographicScopeMultiple.append(optgroupMultinational)
            inputGeographicScopeMultiple.append(optgroupCountries)
            inputGeographicScopeMultiple.append(optgroupSubunits)

            inputGeographicScopeMultiple.addEventListener('change', function() {
                var hiddenGeographicScopeCountry = document.getElementById('geographic-scope-countries-hidden')
                var hiddenGeographicScopeSubunits = document.getElementById('geographic-scope-subunits-hidden')
                var selectedCountries = new Array;
                var selectedSubunits = new Array;
                for (opt of this.selectedOptions) {
                    if (opt.getAttribute('data-type') == 'country') {
                        selectedCountries.push(opt.getAttribute('data-uid'));
                    } else {
                        if (opt.getAttribute('data-uid') === null) {
                            selectedSubunits.push(opt.value);
                        }
                        selectedSubunits.push(opt.getAttribute('data-uid'));
                    }
                }
                hiddenGeographicScopeCountry.value = selectedCountries.join()
                hiddenGeographicScopeSubunits.value = selectedSubunits.join()
            });

            var inputGeographicScopeSingle = document.getElementById('geographic-scope-single')
            inputGeographicScopeSingle.addEventListener('change', function() {
                var hiddenGeographicScopeCountry = document.getElementById('geographic-scope-countries-hidden')
                hiddenGeographicScopeCountry.value = inputGeographicScopeSingle.value
            });

            // get url parameter to pre-fill fields
            var currentUrl = new URL(window.location.href);
            var entry_name = currentUrl.searchParams.get("entry_name");
            document.getElementById('heading-name').innerText = ': ' + entry_name
            document.getElementById('name').value = entry_name

            // Populate form with draft data from embedded json
            var embeddedJSON = document.getElementById('draft') || document.getElementById('existing')
            if (embeddedJSON) {
                embeddedJSON = JSON.parse(embeddedJSON.innerHTML)
                populateForm(embeddedJSON)
            }


            // handle field visibility / dependency logic
            const channelVisibilityFields = document.querySelectorAll('#group-name, #group-epaper, #group-website_allows_comments, #group-website_comments_registration_required, #group-transcript-kind, #group-audience-size, #group-source-founded, #group-payment-model');
            channelVisibilityFields.forEach((elem) => elem.hidden = true);
            document.getElementById('channel-select').addEventListener('change', (element) => {
                    channelVisibility(data, channelVisibilityFields, element);
                })
                // trigger field events from draft
            if (embeddedJSON) {
                document.getElementById('channel-select').dispatchEvent(new Event('change'))
                if (document.getElementById("special_interest2").checked) {
                    document.getElementById("special_interest2").dispatchEvent(new Event("change"))
                }
            }

            // add Tom Select for dynamically loaded data
            var TomSelectCountriesConfig = {
                plugins: ['remove_button'],
                create: true,
                selectOnTab: true,
                onInitialize: function() { // hacky way of forcing the field to be not-validated on load
                    this.input.classList.remove('is-invalid');
                    this.input.removeAttribute("aria-invalid");
                },
                onChange: function() { // invoke validation on change
                    this.sync();
                    if (this.input.validity.valid) {
                        this.wrapper.classList.remove('is-invalid')
                    } else {
                        this.wrapper.classList.add('is-invalid')
                    }
                },
                onItemAdd: function() { // clear input after item was selected
                    this.setTextboxValue();
                    this.refreshOptions();
                }
            };
            var TomSelectCountryConfig = {
                selectOnTab: true,
                onInitialize: function() { // hacky way of forcing the field to be not-validated on load
                    this.input.classList.remove('is-invalid');
                    this.input.removeAttribute("aria-invalid");
                },
                onChange: function() { // invoke validation on change
                    setFieldValidity(this.input)
                    this.sync();
                    if (this.input.validity.valid) {
                        this.wrapper.classList.remove('is-invalid')
                    } else {
                        this.wrapper.classList.add('is-invalid')
                    };
                }
            };

            var TomSelectSubunitConfig = {
                selectOnTab: true,
                create: true,
                onInitialize: function() { // hacky way of forcing the field to be not-validated on load
                    this.input.classList.remove('is-invalid');
                    this.input.removeAttribute("aria-invalid");
                },
                onChange: function() { // invoke validation on change
                    this.sync();
                    if (this.input.validity.valid) {
                        this.wrapper.classList.remove('is-invalid')
                    } else {
                        this.wrapper.classList.add('is-invalid')
                    }
                },
                onItemAdd: function() { // clear input after item was selected
                    this.setTextboxValue();
                    this.refreshOptions();
                }
            };

            geographicScopeSingle = new TomSelect('#geographic-scope-single', TomSelectCountryConfig);
            geographicScopeMultiple = new TomSelect('#geographic-scope-multiple', TomSelectCountriesConfig);
            geographicScopeSubunit = new TomSelect('#geographic-scope-subunit', TomSelectSubunitConfig);


            var TomSelectLanguagesConfig = {
                plugins: ['remove_button'],
                selectOnTab: true,
                onInitialize: function() { // hacky way of forcing the field to be not-validated on load
                    this.input.classList.remove('is-invalid');
                    this.input.removeAttribute("aria-invalid");
                },
                onChange: function() { // invoke validation on change
                    this.sync();
                    if (this.input.validity.valid) {
                        this.wrapper.classList.remove('is-invalid')
                    } else {
                        this.wrapper.classList.add('is-invalid')
                    }
                },
                onItemAdd: function() { // clear input after item was selected
                    this.setTextboxValue();
                    this.refreshOptions();
                }
            };

            const languagesSelect = new TomSelect('#languages', TomSelectLanguagesConfig)

            var TomSelectDatasetConfig = {
                selectOnTab: true,
                plugins: ['remove_button'],
                create: true,
                onItemAdd: function() { // clear input after item was selected
                    this.setTextboxValue();
                    this.refreshOptions();
                }
            }

            const archiveSelect = new TomSelect('#archive-sources-included', TomSelectDatasetConfig)
            const datasetSelect = new TomSelect('#dataset-sources-included', TomSelectDatasetConfig)

            // autocomplete organisation

            var TomSelectOrganisationConfig = {
                plugins: ['remove_button'],
                create: function(input, callback) {
                    var returnData = {
                        value: input,
                        uid: input,
                        unique_name: input,
                        text: input,
                        name: input,
                        country: [
                            { name: 'NEW!' }
                        ]
                    };
                    callback(returnData);
                },
                valueField: 'uid',
                labelField: 'name',
                searchField: 'name',
                delimiter: ',',
                selectOnTab: true,
                // createFilter: function(input) { return input.length >= 3 },
                load: function(query, callback) {
                    if (query.length < 3) return callback();
                    var url = '{{ url_for("endpoint.orglookup") }}?person=false&q=' + encodeURIComponent(query);
                    fetch(url)
                        .then(response => response.json())
                        .then(json => {
                            callback(json.data);
                        }).catch(() => { callback(); });
                },
                render: {
                    option: function(data, escape) {
                        var country_label = ' '
                        if ('country' in data) {
                            country_label = ' (' + escape(data.country[0].name) + ') '
                        };
                        return '<div>' +
                            '<span class="title">' + escape(data.name) + '</span>' +
                            '<small class="text-muted mx-1">' + country_label + '</small>' +
                            '</div>';
                    },
                    item: function(data, escape) {
                        var country_label = ' '
                        if ('country' in data) {
                            country_label = ' (' + escape(data.country[0].name) + ') '
                        };
                        return '<div>' + escape(data.name) + ' <small class="mx-1">' + country_label + '</small></div>';
                    }
                },
                onItemAdd: function() { // clear input after item was selected
                    this.setTextboxValue();
                    this.refreshOptions();
                }
            };
            new TomSelect('#publishes_org', TomSelectOrganisationConfig);

            var TomSelectPersonConfig = {
                plugins: ['remove_button'],
                create: function(input, callback) {
                    var returnData = {
                        value: input,
                        uid: input,
                        unique_name: input,
                        text: input,
                        name: input,
                        country: [
                            { name: 'NEW!' }
                        ]
                    };
                    callback(returnData);
                },
                valueField: 'uid',
                labelField: 'name',
                searchField: 'name',
                delimiter: ',',
                selectOnTab: true,
                // createFilter: function(input) { return input.length >= 3 },
                load: function(query, callback) {
                    if (query.length < 3) return callback();
                    var url = '{{ url_for("endpoint.orglookup") }}?person=true&q=' + encodeURIComponent(query);
                    fetch(url)
                        .then(response => response.json())
                        .then(json => {
                            callback(json.data);
                        }).catch(() => { callback(); });
                },
                render: {
                    option: function(data, escape) {
                        var country_label = ' '
                        if ('country' in data) {
                            country_label = ' (' + escape(data.country[0].name) + ') '
                        };
                        return '<div>' +
                            '<span class="title">' + escape(data.name) + '</span>' +
                            '<small class="text-muted mx-1">' + country_label + '</small>' +
                            '</div>';
                    },
                    item: function(data, escape) {
                        var country_label = ' '
                        if ('country' in data) {
                            country_label = ' (' + escape(data.country[0].name) + ') '
                        };
                        return '<div>' + escape(data.name) + ' <small class="mx-1">' + country_label + '</small></div>';
                    }
                },
                onItemAdd: function() { // clear input after item was selected
                    this.setTextboxValue();
                    this.refreshOptions();
                }
            };
            new TomSelect('#publishes_person', TomSelectPersonConfig);



            var TomSelectOtherNamesConfig = {
                plugins: ['remove_button'],
                selectOnTab: true,
                create: true,
                render: {
                    no_results: function(data, escape) {
                        return '<div></div>';
                    }
                }
            };

            new TomSelect('#other-names', TomSelectOtherNamesConfig);


            var TomSelectPublicationKindConfig = {
                plugins: ['remove_button'],
                create: true,
                selectOnTab: true,
                onInitialize: function() { // hacky way of forcing the field to be not-validated on load
                    this.input.classList.remove('is-invalid');
                    this.input.removeAttribute("aria-invalid");
                },
                onChange: function() { // invoke validation on change
                    setFieldValidity(this.input)
                    this.sync();
                    if (this.input.validity.valid) {
                        this.wrapper.classList.remove('is-invalid')
                    } else {
                        this.wrapper.classList.add('is-invalid')
                    }
                },
            };
            new TomSelect('#publication-kind', TomSelectPublicationKindConfig);

            var TomSelectTopicalFocusConfig = {
                create: true,
                selectOnTab: true,
                onInitialize: function() { // hacky way of forcing the field to be not-validated on load
                    this.input.classList.remove('is-invalid');
                    this.input.removeAttribute("aria-invalid");
                },
                onChange: function() { // invoke validation on change
                    this.sync();
                    if (this.input.validity.valid) {
                        this.wrapper.classList.remove('is-invalid')
                    } else {
                        this.wrapper.classList.add('is-invalid')
                    }
                },
            };

            new TomSelect('#topical-focus', TomSelectTopicalFocusConfig);

            function guessChannel(sourcename) {
                sourcename = sourcename.toLowerCase()

                if (sourcename.includes('facebook')) {
                    return 'facebook'
                } else if (sourcename.includes('instagram')) {
                    return 'instagram'
                } else if (sourcename.includes('telegram')) {
                    return 'telegram'
                } else if (sourcename.includes('twitter')) {
                    return 'twitter'
                } else if (sourcename.includes('vkontakte')) {
                    return 'vkontakte'
                } else if (sourcename.includes('website')) {
                    return 'website'
                } else if (sourcename.includes('print')) {
                    return 'print'
                } else if (sourcename.includes('transcript')) {
                    return 'transcript'
                } else {
                    return false
                }
            };

            // autocomplete related sources

            function createNewSourceField(container, sourceName) {
                var row = document.createElement('div')
                row.classList.add('row', 'mb-3')
                row.id = 'container-' + sourceName
                var label = document.createElement('label')
                label.classList.add('col-sm-2', 'col-form-label')
                label.setAttribute('for', 'newsource_' + sourceName)
                label.innerText = sourceName;
                let guessedChannel = guessChannel(sourceName)
                row.append(label)
                var col = document.createElement('div');
                col.classList.add('col-sm-10');
                var select = document.createElement('select')
                select.classList.add('form-select')
                select.setAttribute('name', 'newsource_' + sourceName)

                // copy options from the first page
                select.innerHTML = document.getElementById('channel-select').innerHTML
                for (option of select) {
                    if (option.getAttribute('data-value') == 'new') {
                        option.remove()
                    }
                    if (option.value) {
                        if (option.value == guessedChannel) {
                            select.value = guessedChannel
                        }

                    }
                }

                // append elements
                col.append(select);
                row.append(col)

                // append to container
                document.getElementById(container).append(row)

            }

            var TomSelectRelatedSourcesConfig = {
                plugins: ['remove_button'],
                create: function(input, callback) {
                    var returnData = {
                        value: input,
                        uid: input,
                        text: input,
                        name: input,
                        country: [
                            { name: 'NEW!' }
                        ],
                        channel: { name: '' }
                    };
                    callback(returnData);
                },
                valueField: 'uid',
                labelField: 'name',
                searchField: 'name',
                delimiter: ',',
                selectOnTab: true,
                onItemAdd: function(input) {
                    // clear input after item was selected
                    this.setTextboxValue();
                    this.refreshOptions();
                    if (!input.startsWith('0x')) {
                        createNewSourceField('group-newrelated-container', input)
                    }
                },
                onItemRemove: function(values) {
                    if (!values.startsWith('0x')) {
                        let el = document.getElementById('container-' + values)
                        el.remove()
                    }
                },
                load: function(query, callback) {
                    if (query.length < 3) return callback();
                    var url = '{{ url_for("endpoint.sourcelookup") }}?q=' + encodeURIComponent(query);
                    fetch(url)
                        .then(response => response.json())
                        .then(json => {
                            callback(json.data);
                        }).catch(() => { callback(); });
                },
                render: {
                    option: function(data, escape) {
                        var channel_label = ' '
                        var channel_icon = ''
                        if (data.channel) {
                            if (data.channel.name) {
                                channel_icon = `<i class="icon-${data.channel.unique_name} color-${data.channel.unique_name} me-2 fa-fw" alt="${data.channel.name}"></i>`
                                channel_label = ' (' + escape(data.channel.name) + ') '
                            }
                        };
                        var country_label = ' '
                        if ("country" in data) {
                            country_label = '<small class="text-muted mx-1"> (' + escape(data.country[0].name) + ')</small>'
                        }
                        return '<div>' +
                            '<span class="title">' + channel_icon + escape(data.name) + channel_label + '</span> ' +
                            country_label +
                            '</div>';
                    },
                    item: function(data, escape) {
                        var channel_label = ' '
                        var channel_icon = ''
                        if (data.channel) {
                            if (data.channel.name) {
                                channel_label = ' (' + escape(data.channel.name) + ') '
                                channel_icon = `<i class="icon-${data.channel.unique_name} color-${data.channel.unique_name} me-2 fa-fw" alt="${data.channel.name}"></i>`
                            }
                        };
                        var country_label = ' '
                        if ("country" in data) {
                            country_label = '<small class="text-muted mx-1"> (' + escape(data.country[0].name) + ')</small>'
                        }
                        return '<div>' + channel_icon + escape(data.name) + channel_label + country_label + '</div>';
                    }
                }
            };
            new TomSelect('#related-sources', TomSelectRelatedSourcesConfig);

            // Hide loading spinner and show form
            document.getElementById('loading-form').hidden = true
            document.getElementById('loading-spinner').hidden = true
            document.getElementById('loading-status').hidden = true
            document.getElementById('new-source').hidden = false

        }).catch(function(err) {
            // Run this when promise was rejected via reject()
            console.log(err)
            document.getElementById('loading-card').classList.add('text-white', 'bg-danger')
            document.getElementById('loading-spinner').setAttribute('style', 'animation: unset;')
            document.getElementById('loading-spinner').classList.remove('text-primary')
            document.getElementById('loading-status').innerText = "Sorry, something went wrong..."
            document.getElementById('loading-status-message').innerText = "Please try to reload this page. If the issue persists, please contact the admins."
        })

    // form progression in multiple steps
    var current = 0;
    var currentStep;
    var nextStep;
    var prevStep
    steps = document.querySelectorAll("fieldset").length;
    document.querySelectorAll('.next').forEach((nextbutton) => {
        nextbutton.addEventListener('click', function() {
            currentStep = nextbutton.parentElement;

            for (field of currentStep.elements) {
                if (!visited.includes(field)) {
                    visited.push(field);
                }
                if (!field.id.includes("ts-control")) {
                    if (field.required) {
                        field.reportValidity();
                        setFieldValidity(field)
                    }
                }

            };
            for (field of currentStep.elements) {
                if (!field.id.includes("ts-control")) {
                    if (!field.validity.valid) {
                        // setFieldValidity(field)
                        return;
                    };
                }
            };
            nextStep = nextbutton.parentElement.nextElementSibling;
            if (nextStep.id == 'section-audience') {
                let audience_size_channels = ['print', 'facebook']
                let channelSelect = document.getElementById('channel-select')
                let selectedChannel = channelSelect.options[channelSelect.selectedIndex].getAttribute('data-value')
                if (!audience_size_channels.includes(selectedChannel)) {
                    nextStep = nextStep.nextElementSibling;
                }
            }
            currentStep.hidden = true;
            nextStep.hidden = false
            document.body.scrollTop = 0; // For Safari
            document.documentElement.scrollTop = 0; // For Chrome, Firefox, IE and Opera

            setProgressBar(++current, steps);

        });

    });

    document.querySelectorAll('.prev').forEach((prevbutton) => {
        prevbutton.addEventListener('click', function() {
            currentStep = prevbutton.parentElement;
            prevStep = prevbutton.parentElement.previousElementSibling;
            if (prevStep.id == 'section-audience') {
                let channelSelect = document.getElementById('channel-select')
                if (channelSelect.options[channelSelect.selectedIndex].getAttribute('data-value') != 'print') {
                    prevStep = prevStep.previousElementSibling;
                }
            }
            currentStep.hidden = true;
            prevStep.hidden = false;
            setProgressBar(--current, steps);
        });
    });
    setProgressBar(current, steps);

});

// validation & submission

const form = document.getElementById("new-source");
form.noValidate = true;

const submitButton = document.getElementById('submit-button')

async function successRedirect(redirect) {
    await new Promise(r => setTimeout(r, 500));
    location.assign(redirect)


}

// button to go back after failed submission

var submitFailButton = document.getElementById('btn-fail-goback')
submitFailButton.addEventListener('click', function() {
    document.getElementById('loading-form').hidden = true
    document.getElementById('loading-card').classList.remove('text-white')
    document.getElementById('loading-card').classList.remove('bg-danger')
    document.getElementById('loading-spinner').hidden = true
    document.getElementById('loading-spinner').removeAttribute('style')
    document.getElementById('loading-spinner').classList.add('text-primary')
    document.getElementById('btn-fail-goback').hidden = true

    document.getElementById('loading-status').innerText = "Processing data..."
    document.getElementById('loading-status-message').innerText = "Please be patient for a short while"
    document.getElementById('loading-status').hidden = true
    document.getElementById('new-source').hidden = false

})

function formResult(success, data) {
    if (success) {

        if ("error" in data) {
            document.getElementById('loading-card').classList.add('text-white', 'bg-danger')
            document.getElementById('loading-spinner').setAttribute('style', 'animation: unset;')
            document.getElementById('loading-spinner').classList.remove('text-primary')
            document.getElementById('loading-status').innerText = "We got a problem"
            document.getElementById('loading-status-message').innerText = data.error
            document.getElementById('btn-fail-goback').hidden = false


        } else {
            document.getElementById('loading-spinner').classList.add('text-success')
            document.getElementById('loading-spinner').classList.remove('text-primary')
            document.getElementById('loading-spinner').hidden = true
            document.getElementById('submit-success-icon').hidden = false
            document.getElementById('loading-status').innerText = "Success!"
            document.getElementById('loading-status-message').innerText = "Everything looks good"
            document.getElementById('btn-viewentry').hidden = false
            document.getElementById('btn-viewentry').setAttribute('href', data.redirect)
            document.getElementById('btn-add-another').hidden = false
        }


    } else {
        document.getElementById('loading-card').classList.add('text-white', 'bg-danger')
        document.getElementById('loading-spinner').setAttribute('style', 'animation: unset;')
        document.getElementById('loading-spinner').classList.remove('text-primary')
        document.getElementById('loading-status').innerText = "Failed"
        document.getElementById('loading-status-message').innerText = "Server not responding!"
        document.getElementById('btn-fail-goback').hidden = false
    }

}

submitButton.addEventListener('click', function handleFormSubmit(event) {
    // var isValid = form.reportValidity();

    // if (isValid) {
    event.preventDefault();
    // POST form data to backend with fetch
    document.getElementById('new-source').hidden = true
    document.getElementById('loading-form').hidden = false
    document.getElementById('loading-spinner').hidden = false
    document.getElementById('loading-status').innerText = "Processing data..."
    document.getElementById('loading-status-message').innerText = "Please be patient for a short while"
    document.getElementById('loading-status').hidden = false
    submitForm('{{ url_for("endpoint.submit") }}', form, formResult);


    // event.preventDefault();
});

const visited = [];
for (const field of form.elements) {
    field.addEventListener("invalid", function handleInvalidField(event) {
        event.preventDefault();
    });

    field.addEventListener("valid", function handleInvalidField(event) {
        setFieldValidity(field);
        event.preventDefault();
    });

    field.addEventListener("blur", function handleFieldBlur() {
        if (!visited.includes(field)) {
            visited.push(field);
        }
        field.checkValidity();
    });

    field.addEventListener("input", function handleFieldInput(event) {
        if (!visited.includes(field)) return;
        setFieldValidity(field);

    });

}

function errorContainer(field) {
    if (field.id.includes("ts-control")) {
        field = document.getElementById(field.id.replace("-ts-control", ""))
    }
    const errorContainerId = field
        .getAttribute("aria-describedby")
        .split(" ")
        .find((id) => id.includes("feedback"));
    return document.getElementById(errorContainerId);
}

function setFieldValidity(field) {
    if (!field.validity.valid) {
        errorContainer(field).textContent = field.validationMessage;
        errorContainer(field).classList.add('invalid-feedback');
        field.setAttribute("aria-invalid", "true");
        field.classList.add('is-invalid');
        if (field.classList.contains('tomselected')) {
            let ts = document.getElementById(field.id + '-ts-control')
            ts.parentElement.parentElement.classList.add('is-invalid');
        }
    } else {
        errorContainer(field).textContent = "";
        errorContainer(field).classList.remove('invalid-feedback');
        field.removeAttribute("aria-invalid");
        field.classList.remove('is-invalid');
        if (field.classList.contains('tomselected')) {
            let ts = document.getElementById(field.id + '-ts-control')
            ts.parentElement.parentElement.classList.remove('is-invalid');
        }
        if (field.type == 'radio') {
            document.querySelectorAll(`input[name=${field.name}]`).forEach(function(el) {
                errorContainer(el).classList.remove('invalid-feedback');
                el.removeAttribute("aria-invalid");
                el.classList.remove('is-invalid');
            });
        };
    }
}


// submit form

function serializeForm(f) {
    var obj = {};
    var formData = new FormData(f);

    var obj = Object.fromEntries(
        Array.from(formData.keys()).map(key => [
            key, formData.getAll(key).length > 1 ?
            formData.getAll(key) : formData.get(key)
        ])
    )

    // remove empty strings
    var obj = Object.fromEntries(Object.entries(obj).filter(([_, v]) => v != ""));

    return obj;
};

function submitForm(endpoint, form, callback) {
    var xhr = new XMLHttpRequest();
    var url = endpoint;
    xhr.open("POST", url, true);
    xhr.setRequestHeader("Content-Type", "application/json");
    xhr.setRequestHeader("X-CSRFToken", csrftoken);
    xhr.onreadystatechange = function() {
        if (xhr.readyState === 4) {
            if (xhr.status === 200) {
                var json = JSON.parse(xhr.responseText);
                console.log(json);
                let success = true
                callback(success, json)
            } else {
                console.log("error", xhr.statusText, xhr.responseText)
                let success = false
                var error = xhr.statusText
                callback(success, error)
            }
        }
    };
    var data = JSON.stringify(serializeForm(form));
    xhr.send(data);

};



// summary at the end

function generateSummary() {

    data = serializeForm(document.getElementById('new-source'));
    console.log("Form submission data:", data)

    prettySummary()

    // var descriptionList = document.createElement('dl')
    // descriptionList.classList.add('row')

    // for (const [key, value] of Object.entries(data)) {
    //     var question = document.createElement('dt');
    //     question.classList.add('col-sm-4');
    //     question.innerText = key;
    //     var answer = document.createElement('dd');
    //     answer.classList.add('col-sm-8');
    //     answer.innerText = value;

    //     descriptionList.append(question)
    //     descriptionList.append(answer)

    // }

    // document.getElementById('summary-container').append(descriptionList);


    // var formFields = document.querySelectorAll('#new-source input, select');
    // for ( var i = 0; i < formFields.length; i++) {

    //     if ( formFields[i].hidden || formFields[i].type == 'button' || formFields[i].id.endsWith('-tomselected') ) {
    //         continue
    //     }

    //     if (formFields[i].type == 'radio' ) {
    //         if (!formFields[i].checked) {
    //             continue
    //         }
    //     }

    //     console.log(formFields[i].id)

    //     var question = document.createElement('dt');
    //     question.classList.add('col-sm-4');
    //     var answer = document.createElement('dd');
    //     answer.classList.add('col-sm-8');

    //     if (formFields[i].type == 'radio') {
    //         question.innerText = document.querySelector('[for="' + formFields[i].name + '"]').innerText
    //     }
    //     else {
    //     question.innerText = document.querySelector('label[for="' + formFields[i].id + '"]').innerText
    //     }
    //     answer.innerText = formFields[i].value

    //     descriptionList.append(question)
    //     descriptionList.append(answer)


    // }



}

function prettySummary() {

    // iterate by type
    // text, select, radio, checkbox, tomselect

    document.querySelectorAll('#summary-container [id^="summary-"]').forEach((el) => el.hidden = true)
    Array.from(form.elements).forEach(function(e) {
        if (e.type == 'text' || e.type == 'number') {
            if (e.value) {
                let summary_element = document.querySelector('#summary-' + e.name.replace('|', '_'))
                if (summary_element) {
                    summary_element.children[1].innerHTML = e.value
                    summary_element.hidden = false
                }
            }
        } else if (e.tagName.toLowerCase() == 'select') {
            if (e.multiple && e.selectedOptions) {
                let summary_element = document.querySelector('#summary-' + e.name.replace('|', '_'))
                if (summary_element) {
                    let selected = []
                    for (opt of e.selectedOptions) { selected.push(opt.innerHTML) }
                    if (selected.length > 0) {
                        summary_element.children[1].innerHTML = selected.join(', ')
                        summary_element.hidden = false
                    }
                }
            } else {
                let summary_element = document.querySelector('#summary-' + e.name.replace('|', '_'))
                if (summary_element) {
                    if (e.value) {
                        summary_element.children[1].innerHTML = e.selectedOptions[0].innerHTML
                        summary_element.hidden = false
                    }
                }
            }
        } else if (e.type == 'radio' && e.checked) {
            let summary_element = document.querySelector('#summary-' + e.name.replace('|', '_'))
            if (summary_element) {
                summary_element.children[1].innerHTML = document.querySelector('[for="' + e.id + '"]').innerHTML
                summary_element.hidden = false
            }

        } else if (e.type == 'checkbox' && e.checked) {
            let summary_element = document.querySelector('#summary-' + e.name.replace('|', '_'))
            if (summary_element) {
                summary_element.children[1].innerHTML = document.querySelector('[for="' + e.id + '"]').innerHTML
                summary_element.hidden = false
            }

        }


    })
}