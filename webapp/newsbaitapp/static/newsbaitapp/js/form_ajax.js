$(document).ready(function () {
    $('#userdatafeedback-form').on('submit', function (e) {
        e.preventDefault(); // Prevent the default form submit

        var form = $(this);
        var url = form.data('url'); // Use the data-url attribute
        var messageContainer = $('#form-response-message');
        var retryButton = $('#retry-button');

        // Function to handle the display of the message
        function displayMessage(message, isSuccess) {
            messageContainer.text(message);
            messageContainer.removeClass('alert-danger alert-success')
                .addClass(isSuccess ? 'alert alert-success' : 'alert alert-danger');
            retryButton.before(messageContainer); // Insert the message before the retry button
            messageContainer.show();
        }

        // AJAX call to submit the form data
        $.ajax({
            type: 'POST',
            url: url, // Get the URL from the form data-url attribute
            data: form.serialize(), // Serialize the form data
            success: function (response) {
                // Handle success or failure
                displayMessage(response.message, response.success);
                if (response.success) {
                    $('#userdatafeedback-form').trigger('reset'); // Clear the form
                }
            },
            error: function (xhr, errmsg, err) {
                // Handle error
                console.error(xhr.status + ": " + xhr.responseText);
                displayMessage('An error occurred: ' + errmsg, false);
            }
        });
    });
});

$.ajaxSetup({
    beforeSend: function(xhr, settings) {
        if (!this.crossDomain) {
            xhr.setRequestHeader("X-CSRFToken", $('input[name="csrfmiddlewaretoken"]').val());
        }
    }
});
// ojo no tira errror cuando debería.