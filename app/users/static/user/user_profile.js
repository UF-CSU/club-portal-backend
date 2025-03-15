document.addEventListener('DOMContentLoaded', () => {
    const editButton = document.querySelector('.edit-button');
    const profileItems = document.querySelectorAll('.profile-item');
    const profileContainer = document.querySelector('.profile-container');

    editButton.addEventListener('click', () => {
        if (editButton.innerText === 'Edit') {
            // Enters edit mode, replaces each span field with an input field
            profileItems.forEach(item => {
                const span = item.querySelector('.field-value');
                if (span) {
                    const label = item.querySelector('.field-label').innerText;
                    const value = span.innerText;
                    const input = document.createElement('input');
                    
                    // If the label is "birthday", the input field is in the date form
                    if (label.toLowerCase().includes('birthday')) {
                        input.type = 'date';
                        input.value = value;
                    } else {
                        input.type = 'text';
                        input.value = value;
                    }
                    // Temporarily store the field label in the input for data retrieval
                    input.setAttribute('data-label', label.toLowerCase());
                    
                    // Replaces the span with the new input field
                    item.replaceChild(input, span);
                }
            });
            editButton.innerText = 'Save';
        } else if (editButton.innerText === 'Save') {
            // Activate Save mode, replaces the data with the input
            const updatedData = {};
            profileItems.forEach(item => {
                const input = item.querySelector('input');
                if (input) {
                    const key = input.getAttribute('data-label') || input.id;
                    updatedData[key] = input.value;
                    
                    const span = document.createElement('span');
                    span.className = 'field-value';
                    span.innerText = input.value;
                    
                    item.replaceChild(span, input);
                }
            });
            console.log('Updated Data:', updatedData);
            alert('Profile updated successfully!');
            editButton.innerText = 'Edit';
        }
    });
});
