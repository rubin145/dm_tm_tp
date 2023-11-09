function submitTitle(uniqueId, titleText, isAI, position) {
    // Use the variable set from the template to decide the form ID
    let formId = isMultiArticleMode ? 'multiArticleForm' : 'titleForm';
    let form = document.getElementById(formId);

    if (!form) {
        console.error("Form with id", formId, "not found");
        return; // Exit the function if the form is not found
    }

    let radioToCheck = form.querySelector(`input[value="${uniqueId}"]`);
    if (radioToCheck) {
        radioToCheck.checked = true;
    } else {
        console.error("Radio input with value", uniqueId, "not found");
        return; // Exit the function if the radio input is not found
    }
    
    let titleTextInput = document.getElementById('titlePreferenceText');
    let titleIsAIInput = document.getElementById('titlePreferenceIsAI');
    let titlePositionInput = document.getElementById('titlePreferencePosition');

    titleTextInput.value = titleText;
    titleIsAIInput.value = isAI;
    titlePositionInput.value = position;

    // Debugging: Log the values before submission
    console.log("Unique ID:", uniqueId);
    console.log("Title Text:", titleText);
    console.log("Is AI:", isAI);
    console.log("Position:", position);

    // Submit the form
    form.submit();
}
