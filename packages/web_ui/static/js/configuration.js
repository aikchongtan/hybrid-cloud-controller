// Client-side validation for configuration form

document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('configurationForm');
    const validateButton = document.getElementById('validateButton');
    const submitButton = document.getElementById('submitButton');

    // Field definitions with validation rules
    const fields = {
        cpu_cores: {
            name: 'CPU Cores',
            type: 'integer',
            min: 1,
            required: true
        },
        memory_gb: {
            name: 'Memory',
            type: 'integer',
            min: 1,
            required: true
        },
        instance_count: {
            name: 'Instance Count',
            type: 'integer',
            min: 1,
            required: true
        },
        storage_type: {
            name: 'Storage Type',
            type: 'select',
            options: ['SSD', 'HDD', 'NVME'],
            required: true
        },
        storage_capacity_gb: {
            name: 'Storage Capacity',
            type: 'integer',
            min: 1,
            required: true
        },
        storage_iops: {
            name: 'Storage IOPS',
            type: 'integer',
            min: 1,
            required: false
        },
        bandwidth_mbps: {
            name: 'Bandwidth',
            type: 'integer',
            min: 1,
            required: true
        },
        monthly_data_transfer_gb: {
            name: 'Data Transfer',
            type: 'integer',
            min: 0,
            required: true
        },
        utilization_percentage: {
            name: 'Utilization Percentage',
            type: 'integer',
            min: 0,
            max: 100,
            required: true
        },
        operating_hours_per_month: {
            name: 'Operating Hours',
            type: 'integer',
            min: 0,
            max: 744,
            required: true
        }
    };

    // Clear all error messages
    function clearErrors() {
        Object.keys(fields).forEach(fieldId => {
            const errorElement = document.getElementById(`${fieldId}_error`);
            const inputElement = document.getElementById(fieldId);
            
            if (errorElement) {
                errorElement.style.display = 'none';
                errorElement.textContent = '';
            }
            
            if (inputElement) {
                inputElement.classList.remove('field-error');
                inputElement.classList.remove('is-danger');
            }
        });
    }

    // Display error for a specific field
    function showError(fieldId, message) {
        const errorElement = document.getElementById(`${fieldId}_error`);
        const inputElement = document.getElementById(fieldId);
        
        if (errorElement) {
            errorElement.textContent = message;
            errorElement.style.display = 'block';
        }
        
        if (inputElement) {
            inputElement.classList.add('field-error');
            inputElement.classList.add('is-danger');
        }
    }

    // Validate a single field
    function validateField(fieldId, value) {
        const field = fields[fieldId];
        
        // Check if required
        if (field.required && (value === null || value === undefined || value === '')) {
            return `${field.name} is required`;
        }
        
        // Skip further validation if field is optional and empty
        if (!field.required && (value === null || value === undefined || value === '')) {
            return null;
        }
        
        // Type-specific validation
        if (field.type === 'integer') {
            const numValue = parseInt(value, 10);
            
            if (isNaN(numValue)) {
                return `${field.name} must be a valid number`;
            }
            
            if (!Number.isInteger(numValue)) {
                return `${field.name} must be an integer`;
            }
            
            if (field.min !== undefined && numValue < field.min) {
                return `${field.name} must be at least ${field.min}`;
            }
            
            if (field.max !== undefined && numValue > field.max) {
                return `${field.name} must be at most ${field.max}`;
            }
            
            if (numValue < 0) {
                return `${field.name} must be a positive number`;
            }
        }
        
        if (field.type === 'select') {
            if (field.options && !field.options.includes(value.toUpperCase())) {
                return `${field.name} must be one of: ${field.options.join(', ')}`;
            }
        }
        
        return null;
    }

    // Validate all fields
    function validateForm() {
        clearErrors();
        
        let isValid = true;
        const errors = {};
        
        Object.keys(fields).forEach(fieldId => {
            const inputElement = document.getElementById(fieldId);
            if (!inputElement) return;
            
            const value = inputElement.value.trim();
            const error = validateField(fieldId, value);
            
            if (error) {
                errors[fieldId] = error;
                showError(fieldId, error);
                isValid = false;
            }
        });
        
        return { isValid, errors };
    }

    // Collect form data
    function getFormData() {
        const data = {};
        
        Object.keys(fields).forEach(fieldId => {
            const inputElement = document.getElementById(fieldId);
            if (!inputElement) return;
            
            const value = inputElement.value.trim();
            
            if (fields[fieldId].type === 'integer') {
                data[fieldId] = value ? parseInt(value, 10) : null;
            } else if (fields[fieldId].type === 'select') {
                data[fieldId] = value ? value.toUpperCase() : null;
            } else {
                data[fieldId] = value || null;
            }
        });
        
        return data;
    }

    // Validate button click handler
    validateButton.addEventListener('click', async (e) => {
        e.preventDefault();
        
        // Client-side validation
        const validation = validateForm();
        
        if (!validation.isValid) {
            // Show notification
            showNotification('Please fix the validation errors before proceeding', 'danger');
            return;
        }
        
        // Call API validation endpoint
        const formData = getFormData();
        
        try {
            validateButton.classList.add('is-loading');
            
            // Use relative URL to call Web UI proxy endpoint
            const response = await fetch('/api/configurations/validate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(formData)
            });
            
            const result = await response.json();
            
            if (response.ok && result.valid) {
                showNotification('Configuration is valid! You can now save it.', 'success');
            } else if (result.details) {
                // Display server-side validation errors
                Object.keys(result.details).forEach(fieldId => {
                    showError(fieldId, result.details[fieldId]);
                });
                showNotification('Validation failed. Please check the errors below.', 'danger');
            } else {
                showNotification(result.message || 'Validation failed', 'danger');
            }
        } catch (error) {
            console.error('Validation error:', error);
            showNotification('Unable to validate configuration. Please try again.', 'danger');
        } finally {
            validateButton.classList.remove('is-loading');
        }
    });

    // Form submit handler
    form.addEventListener('submit', (e) => {
        // Client-side validation before submission
        const validation = validateForm();
        
        if (!validation.isValid) {
            e.preventDefault();
            showNotification('Please fix the validation errors before submitting', 'danger');
            return false;
        }
        
        // Show loading state
        submitButton.classList.add('is-loading');
    });

    // Real-time validation on blur
    Object.keys(fields).forEach(fieldId => {
        const inputElement = document.getElementById(fieldId);
        if (!inputElement) return;
        
        inputElement.addEventListener('blur', () => {
            const value = inputElement.value.trim();
            const error = validateField(fieldId, value);
            
            // Clear previous error
            const errorElement = document.getElementById(`${fieldId}_error`);
            if (errorElement) {
                errorElement.style.display = 'none';
                errorElement.textContent = '';
            }
            inputElement.classList.remove('field-error');
            inputElement.classList.remove('is-danger');
            
            // Show new error if any
            if (error) {
                showError(fieldId, error);
            }
        });
    });

    // Helper function to show notifications
    function showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification is-${type}`;
        notification.innerHTML = `
            <button class="delete"></button>
            ${message}
        `;
        
        // Insert at the top of the container
        const container = document.querySelector('.container');
        container.insertBefore(notification, container.firstChild);
        
        // Add delete button handler
        const deleteButton = notification.querySelector('.delete');
        deleteButton.addEventListener('click', () => {
            notification.remove();
        });
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 5000);
        
        // Scroll to top to show notification
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
});
