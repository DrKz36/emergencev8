/**
 * Change Password Modal
 * Modal pour changer son mot de passe
 */

export class ChangePasswordModal {
    constructor(eventBus, apiClient, userEmail = null) {
        this.eventBus = eventBus;
        this.apiClient = apiClient;
        this.userEmail = userEmail;
        this.modal = null;
    }

    /**
     * Show the change password modal
     */
    show() {
        // Create modal element
        this.modal = document.createElement('div');
        this.modal.className = 'change-password-overlay';

        const defaultEmail = this.userEmail || '';

        this.modal.innerHTML = `
            <div class="change-password-modal">
                <div class="change-password-header">
                    <h2>Réinitialiser mon mot de passe</h2>
                    <button class="change-password-close" aria-label="Fermer">×</button>
                </div>
                <div class="change-password-body">
                    <p class="change-password-intro">
                        Pour sécuriser votre compte, nous allons vous envoyer un email de vérification.
                        Cliquez sur le lien dans l'email pour créer un nouveau mot de passe.
                    </p>
                    <form id="change-password-form" class="change-password-form">
                        <div class="form-group">
                            <label for="email">Adresse email</label>
                            <input
                                type="email"
                                id="email"
                                name="email"
                                class="form-input"
                                placeholder="votre@email.com"
                                value="${defaultEmail}"
                                required
                                autocomplete="email"
                            />
                            <small class="form-hint">Nous enverrons un lien de réinitialisation à cette adresse</small>
                        </div>
                        <div class="form-error" id="form-error" style="display: none;"></div>
                        <div class="form-success" id="form-success" style="display: none;"></div>
                    </form>
                </div>
                <div class="change-password-footer">
                    <button type="button" class="btn-cancel">Annuler</button>
                    <button type="submit" form="change-password-form" class="btn-submit">
                        Envoyer le lien
                    </button>
                </div>
            </div>
        `;

        // Append to body
        document.body.appendChild(this.modal);

        // Add styles if not already present
        this.injectStyles();

        // Attach event listeners
        this.attachEventListeners();

        // Focus trap
        this.setupFocusTrap();
    }

    /**
     * Hide the modal
     */
    hide() {
        if (this.modal) {
            this.modal.remove();
            this.modal = null;
        }
    }

    /**
     * Inject CSS styles
     */
    injectStyles() {
        if (document.getElementById('change-password-styles')) {
            return;
        }

        const style = document.createElement('style');
        style.id = 'change-password-styles';
        style.textContent = `
            .change-password-overlay {
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0, 0, 0, 0.7);
                backdrop-filter: blur(4px);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 999999;
                padding: 1rem;
                animation: fadeIn 0.3s ease;
            }

            @keyframes fadeIn {
                from { opacity: 0; }
                to { opacity: 1; }
            }

            .change-password-modal {
                background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 16px;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
                max-width: 500px;
                width: 100%;
                max-height: 90vh;
                overflow-y: auto;
                animation: slideUp 0.4s ease;
            }

            @keyframes slideUp {
                from { transform: translateY(30px); opacity: 0; }
                to { transform: translateY(0); opacity: 1; }
            }

            .change-password-header {
                padding: 1.5rem 2rem;
                border-bottom: 1px solid rgba(255, 255, 255, 0.1);
                position: relative;
            }

            .change-password-header h2 {
                font-size: 1.5rem;
                font-weight: 600;
                color: #e2e8f0;
                margin: 0;
            }

            .change-password-close {
                position: absolute;
                top: 1rem;
                right: 1rem;
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
                color: #e2e8f0;
                width: 32px;
                height: 32px;
                border-radius: 8px;
                font-size: 1.5rem;
                line-height: 1;
                cursor: pointer;
                transition: all 0.2s;
            }

            .change-password-close:hover {
                background: rgba(255, 255, 255, 0.2);
                border-color: rgba(255, 255, 255, 0.3);
            }

            .change-password-body {
                padding: 2rem;
            }

            .change-password-intro {
                color: #cbd5e1;
                line-height: 1.6;
                margin: 0 0 1.5rem 0;
            }

            .change-password-form {
                display: flex;
                flex-direction: column;
                gap: 1.25rem;
            }

            .form-group {
                display: flex;
                flex-direction: column;
                gap: 0.5rem;
            }

            .form-group label {
                color: #e2e8f0;
                font-weight: 500;
                font-size: 0.9rem;
            }

            .form-input {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 0.75rem 1rem;
                color: #e2e8f0;
                font-size: 1rem;
                transition: all 0.2s;
            }

            .form-input:focus {
                outline: none;
                border-color: rgba(59, 130, 246, 0.5);
                background: rgba(255, 255, 255, 0.08);
            }

            .form-input::placeholder {
                color: rgba(203, 213, 225, 0.4);
            }

            .form-hint {
                color: #94a3b8;
                font-size: 0.8rem;
            }

            .form-error {
                background: rgba(239, 68, 68, 0.1);
                border: 1px solid rgba(239, 68, 68, 0.3);
                border-radius: 8px;
                padding: 0.75rem 1rem;
                color: #fca5a5;
                font-size: 0.9rem;
            }

            .form-success {
                background: rgba(34, 197, 94, 0.1);
                border: 1px solid rgba(34, 197, 94, 0.3);
                border-radius: 8px;
                padding: 0.75rem 1rem;
                color: #86efac;
                font-size: 0.9rem;
            }

            .change-password-footer {
                padding: 1.5rem 2rem;
                border-top: 1px solid rgba(255, 255, 255, 0.1);
                display: flex;
                gap: 0.75rem;
                justify-content: flex-end;
            }

            .btn-cancel,
            .btn-submit {
                padding: 0.6rem 1.2rem;
                border-radius: 8px;
                font-size: 0.95rem;
                font-weight: 500;
                cursor: pointer;
                transition: all 0.2s;
                border: none;
            }

            .btn-cancel {
                background: rgba(255, 255, 255, 0.1);
                color: #cbd5e1;
                border: 1px solid rgba(255, 255, 255, 0.2);
            }

            .btn-cancel:hover {
                background: rgba(255, 255, 255, 0.15);
                border-color: rgba(255, 255, 255, 0.3);
            }

            .btn-submit {
                background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
                color: white;
                border: 1px solid rgba(59, 130, 246, 0.5);
                box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
            }

            .btn-submit:hover:not(:disabled) {
                background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
                box-shadow: 0 6px 16px rgba(59, 130, 246, 0.4);
            }

            .btn-submit:disabled {
                opacity: 0.6;
                cursor: not-allowed;
            }

            @media (max-width: 640px) {
                .change-password-modal {
                    max-width: 100%;
                    margin: 0;
                    border-radius: 0;
                    max-height: 100vh;
                }

                .change-password-header,
                .change-password-body,
                .change-password-footer {
                    padding: 1.25rem;
                }

                .change-password-footer {
                    flex-direction: column-reverse;
                }

                .btn-cancel,
                .btn-submit {
                    width: 100%;
                }
            }
        `;

        document.head.appendChild(style);
    }

    /**
     * Attach event listeners
     */
    attachEventListeners() {
        if (!this.modal) return;

        const closeBtn = this.modal.querySelector('.change-password-close');
        const cancelBtn = this.modal.querySelector('.btn-cancel');
        const form = this.modal.querySelector('#change-password-form');

        // Close handlers
        const handleClose = () => {
            this.hide();
        };

        closeBtn?.addEventListener('click', handleClose);
        cancelBtn?.addEventListener('click', handleClose);

        // Form submission
        form?.addEventListener('submit', async (e) => {
            e.preventDefault();
            await this.handleSubmit(e.target);
        });

        // Close on overlay click
        this.modal.addEventListener('click', (e) => {
            if (e.target === this.modal) {
                handleClose();
            }
        });

        // Close on Escape key
        const escapeHandler = (e) => {
            if (e.key === 'Escape') {
                handleClose();
                document.removeEventListener('keydown', escapeHandler);
            }
        };
        document.addEventListener('keydown', escapeHandler);
    }

    /**
     * Handle form submission
     */
    async handleSubmit(form) {
        const email = form.querySelector('#email').value;
        const errorEl = form.querySelector('#form-error');
        const successEl = form.querySelector('#form-success');
        const submitBtn = form.querySelector('.btn-submit');

        // Clear previous messages
        errorEl.style.display = 'none';
        successEl.style.display = 'none';

        // Validate email
        if (!email || !email.includes('@')) {
            errorEl.textContent = 'Veuillez entrer une adresse email valide.';
            errorEl.style.display = 'block';
            return;
        }

        // Disable submit button
        submitBtn.disabled = true;
        submitBtn.textContent = 'Envoi en cours...';

        try {
            const response = await fetch('/api/auth/request-password-reset', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    email: email,
                }),
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'Erreur lors de l\'envoi du lien.');
            }

            // Success
            successEl.textContent = data.message || 'Un email avec un lien de réinitialisation vous a été envoyé.';
            successEl.style.display = 'block';

            // Close modal after 3 seconds
            setTimeout(() => {
                this.hide();
            }, 3000);

        } catch (error) {
            errorEl.textContent = error.message || 'Une erreur est survenue.';
            errorEl.style.display = 'block';
            submitBtn.disabled = false;
            submitBtn.textContent = 'Envoyer le lien';
        }
    }

    /**
     * Setup focus trap for accessibility
     */
    setupFocusTrap() {
        if (!this.modal) return;

        const focusableElements = this.modal.querySelectorAll(
            'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );

        const firstElement = focusableElements[0];
        const lastElement = focusableElements[focusableElements.length - 1];

        firstElement?.focus();

        const trapFocus = (e) => {
            if (e.key !== 'Tab') return;

            if (e.shiftKey) {
                if (document.activeElement === firstElement) {
                    e.preventDefault();
                    lastElement?.focus();
                }
            } else {
                if (document.activeElement === lastElement) {
                    e.preventDefault();
                    firstElement?.focus();
                }
            }
        };

        this.modal.addEventListener('keydown', trapFocus);
    }
}
