const editBtn = document.getElementById("editBtn");
const saveBtn = document.getElementById("saveBtn");
const inputs = document.querySelectorAll("input");

if (editBtn) {
    editBtn.addEventListener("click", () => {
        inputs.forEach(input => input.disabled = false);
        saveBtn.style.display = "inline-block";
        editBtn.style.display = "none";
    });
}

// EDIT PROFILE BUTTON
document.getElementById("editProfileBtn")?.addEventListener("click", function () {
    window.location.href = "/edit-profile/";
});

// LOGOUT BUTTON
document.getElementById("logoutBtn")?.addEventListener("click", function () {
    window.location.href = "/logout/";
});

// Floating action buttons on home
document.getElementById("float-raise")?.addEventListener("click", function () {
    window.location.href = "/tickets/create/";
});
document.getElementById("float-services")?.addEventListener("click", function () {
    window.location.href = "/services/";
});
document.getElementById("float-help")?.addEventListener("click", function () {
    window.location.href = "/help-center/";
});

// Hero buttons on home
document.getElementById("hero-raise")?.addEventListener("click", function () {
    window.location.href = "/tickets/create/";
});
document.getElementById("hero-services")?.addEventListener("click", function () {
    window.location.href = "/services/";
});

// Phone number validation on profile edit form
const editProfileForm = document.querySelector('form[action*="edit-profile"]');
if (editProfileForm) {
    const phoneInput = editProfileForm.querySelector('input[name="phone"]');
    if (phoneInput) {
        phoneInput.addEventListener('input', function(e) {
            // Remove any invalid characters except +, -, (, ), space and digits
            let value = e.target.value;
            let cleaned = value.replace(/[^\d+\-\(\)\s]/g, '');
            if (value !== cleaned) {
                e.target.value = cleaned;
                // Show visual feedback
                e.target.setCustomValidity('Please enter a valid phone number');
            } else {
                e.target.setCustomValidity('');
            }
        });
        
        phoneInput.addEventListener('blur', function(e) {
            // Validate on blur
            const phonePattern = /^\+?1?\d{9,15}$|^\+?[\d\s\-()]{9,20}$/;
            if (e.target.value && !phonePattern.test(e.target.value)) {
                e.target.style.borderColor = '#ef4444';
                // Show error message if not already shown
                if (!e.target.nextElementSibling || !e.target.nextElementSibling.classList.contains('phone-error')) {
                    const errorMsg = document.createElement('div');
                    errorMsg.className = 'phone-error';
                    errorMsg.style.color = '#ef4444';
                    errorMsg.style.fontSize = '12px';
                    errorMsg.style.marginTop = '4px';
                    errorMsg.textContent = 'Invalid phone format. Use: +1 555 555 5555, 555-555-5555, or (555) 555-5555';
                    e.target.parentNode.insertBefore(errorMsg, e.target.nextSibling);
                }
            } else {
                e.target.style.borderColor = '';
                const errorMsg = e.target.parentNode.querySelector('.phone-error');
                if (errorMsg) errorMsg.remove();
            }
        });
    }
}
