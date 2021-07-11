// ********************
// Function declaration
// ********************

// Get custom attribute (data-value) from all select and put them in hidden fields
(function($) {
    $.fn.extend({
        inputSelectToHidden: function() {
            return this.change(function() {
                var option = $('option:selected', this).attr('data-value');
                var hidden = $("#" + this.id + "-hidden");
                hidden.val(option);
            })
        }
    });
})(jQuery);

// Load Select options from json api
function getFieldOptions(targetUrl) {
    return new Promise(function(resolve, reject) {
        $.ajax({
            url: targetUrl,
            // beforeSend: function() { $("#new-source").addClass("loading"); },
            success: function(data) {
                resolve(data) // Resolve promise and go to then()
            },
            error: function(err) {
                reject(err) // Reject the promise and go to catch()
            }
        });
    });
}



// Dynamically add select options from data object
function addFieldOptions(fieldOptions, key, selector) {
    fieldOptions[key].forEach(function(item, i) {
        $(selector).append('<option value="' + item.unique_name + '" data-value="' + item.uid + '" data-index="' + i + '">' + item.name + '</option>');

    })
    $(selector).append('<option data-value="new" data-index="99">Other</option>');
};


// Field Visibility Logic
function fieldVisibility(fieldOptions, allNames, el) {

    var value = $(el).find(':selected').val();
    var index = $(el).find(':selected').data('index');

    allNames.hide()
    $('#group-channel-new').hide();
    $('#group-name').show();
    if (index != 99) {
        $('#group-name label').html(fieldOptions.channel[index]['form_name_question']);
        $('#source-name').attr("placeholder", fieldOptions.channel[index]['form_name_placeholder']);
        if ('form_name_helptext' in fieldOptions.channel[index]) {
            $('#name-helptext').html(fieldOptions.channel[index]['form_name_helptext']);
        } else { $('#name-helptext').html("") };
        if ('form_name_addon' in fieldOptions.channel[index]) {
            $('#name-addon').show().html(fieldOptions.channel[index]['form_name_addon']);
        } else { $('#name-addon').hide() };
    } else {
        $('#group-name label').html("What is the name of the news source that you suggest?");
        $('#source-name').attr("placeholder", "");
        $('#name-addon').hide();
    };

    if (value == 'other') {
        $('#group-channel-new').show()
    } else if (value == 'print') {
        $('#group-epaper').show()
    } else if (value == 'transcript') {
        $('#group-transcript-kind').show()
    } else if (value == 'website') {
        $('#group-channel-comments').show()
    }
};

// make form persistent with local storage
function getFormData(f, fID) {
    let data = {
        [fID]: {}
    };
    for (var element of f.elements) {
        if (element.name.length > 0) {
            data[fID][element.name] = element.value;
        }
    }
    return data;
};


// populate form on page load
function populateForm(f, fID) {
    if (localStorage.key(fID)) {
        var savedData = JSON.parse(localStorage.getItem(fID));
        for (var element of f.elements) {
            if (element.name in savedData) {
                element.value = savedData[element.name];
            }
        }

    }
};

// Progress Bar
function setProgressBar(curStep) {
    var percent = parseFloat(100 / steps) * curStep;
    percent = percent.toFixed();
    $("#questionnaire-progress").css("width", percent + "%")
    $("#questionnaire-progress").attr('aria-valuenow', percent + "%")
};


// Main function

$(document).ready(function() {

    // declare constants
    const formId = "new-source";
    const formUrl = location.href;
    const formIdentifier = `${formUrl} ${formId}`;
    var persistentForm = document.querySelector(`#${formId}`)

    // Load Select options from json api
    getFieldOptions('{{ url_for("records.fieldoptions") }}').then(function(data) {
        console.log(data["channel"]);
        // add field options to multiple choice fields
        addFieldOptions(data, 'channel', '#channel-select');

        // handle field visibility / dependency logic
        const allNames = $('#group-name, #group-epaper, #group-channel-comments, #group-transcript-kind')
        allNames.hide()
        $('#channel-select').change(function() {
            let element = $(this);
            fieldVisibility(data, allNames, element);
        });

        // Populate form with locally stored data
        populateForm(persistentForm, formIdentifier);
        $('#channel-select').change();


    }).catch(function(err) {
        // Run this when promise was rejected via reject()
        console.log(err)
    })


    // Get custom attribute (data-value) from all select and put them in hidden fields
    $('select').inputSelectToHidden();

    // persistence: save changes in form
    $("#" + formId).change(function() {
        var data = getFormData(persistentForm, formIdentifier);
        localStorage.setItem(formIdentifier, JSON.stringify(data[formIdentifier]));
    });

    // persistence: clear local storage on "reset"
    $("#reset-form").click(function() {
        localStorage.removeItem(formIdentifier);
    })

    // form progression in multiple steps
    var current = 0,
        current_step, next_step, steps;
    steps = $("fieldset").length;
    $('.next').click(function() {
        current_step = $(this).parent();
        next_step = $(this).parent().next();
        next_step.show();
        current_step.hide();
        setProgressBar(++current);
    });

    $('.prev').click(function() {
        current_step = $(this).parent();
        prev_step = $(this).parent().prev();
        prev_step.show();
        current_step.hide();
        setProgressBar(--current);
    });
    setProgressBar(current);

});

// **************************
// Form Validation on the fly
// **************************

const form = document.getElementById("new-source");
form.noValidate = true;
form.addEventListener('submit', function handleFormSubmit(event) {
    const isValid = form.reportValidity();

    if (isValid) {
        // POST form data to backend with fetch
    }

    event.preventDefault();
});

const visited = [];
for (const field of form.elements) {
    field.addEventListener("invalid", function handleInvalidField(event) {
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
    const errorContainerId = field
        .getAttribute("aria-describedby")
        .split(" ")
        .find((id) => id.includes("feedback"));
    return document.getElementById(errorContainerId);
}

function setFieldValidity(field) {
    if (!field.validity.valid) {
        errorContainer(field).textContent = field.validationMessage;
        field.setAttribute("aria-invalid", "true");
        field.classList.add('is-invalid');
    } else {
        errorContainer(field).textContent = "";
        field.removeAttribute("aria-invalid");
        field.classList.remove('is-invalid');
    }
}