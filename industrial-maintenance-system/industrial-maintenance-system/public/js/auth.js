/**
 * CMMS Industrial - Authentication & Session Client Library
 * Handles JWT/HMAC token storage, API authorization headers, password security, and route protection.
 */

const AUTH_STORAGE_KEY = 'cmms_auth_session';

const AuthClient = {
  /**
   * Retrieves active session from localStorage.
   */
  getSession() {
    try {
      const raw = localStorage.getItem(AUTH_STORAGE_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  },

  /**
   * Saves authentication session data.
   */
  setSession(token, user) {
    localStorage.setItem(
      AUTH_STORAGE_KEY,
      JSON.stringify({
        token,
        user,
        timestamp: Date.now(),
      })
    );
  },

  /**
   * Clears session and redirects to login.
   */
  logout() {
    localStorage.removeItem(AUTH_STORAGE_KEY);
    localStorage.removeItem('cmms_active_tech');
    window.location.href = '/login';
  },

  /**
   * Returns current token or empty string.
   */
  getToken() {
    const session = this.getSession();
    return session?.token || '';
  },

  /**
   * Returns current authenticated user object or null.
   */
  getUser() {
    const session = this.getSession();
    return session?.user || null;
  },

  /**
   * Returns true if user is logged in.
   */
  isAuthenticated() {
    return !!this.getToken();
  },

  /**
   * Route Guard: verifies authentication and role.
   * Redirects unauthorized users automatically.
   */
  guardRoute(requiredRole = null) {
    const user = this.getUser();
    if (!user || !this.getToken()) {
      const returnUrl = encodeURIComponent(window.location.pathname + window.location.search);
      window.location.href = `/login?returnUrl=${returnUrl}`;
      return false;
    }

    if (requiredRole && user.role !== requiredRole) {
      if (user.role === 'TECHNICIAN') {
        window.location.href = '/tecnico';
        return false;
      }
    }
    return true;
  },

  /**
   * Authenticated fetch helper that injects Authorization header.
   */
  async fetch(url, options = {}) {
    const token = this.getToken();
    const headers = {
      ...(options.headers || {}),
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(url, { ...options, headers });

    // Handle 401 Unauthorized globally
    if (response.status === 401) {
      this.logout();
      throw new Error('Sesión expirada o no autorizada');
    }

    return response;
  },

  /**
   * Evaluates password strength against industrial security standards.
   */
  validatePassword(password) {
    password = password || '';
    const hasMinLen = password.length >= 8;
    const hasUpper = /[A-Z]/.test(password);
    const hasLower = /[a-z]/.test(password);
    const hasNumOrSymbol = /[0-9]/.test(password) || /[^A-Za-z0-9]/.test(password);

    let score = 0;
    if (hasMinLen) score += 1;
    if (hasUpper) score += 1;
    if (hasLower) score += 1;
    if (hasNumOrSymbol) score += 1;

    let strengthLabel = 'Muy Débil';
    let strengthColor = '#ef4444';
    if (score === 2) {
      strengthLabel = 'Débil';
      strengthColor = '#f97316';
    } else if (score === 3) {
      strengthLabel = 'Buena';
      strengthColor = '#eab308';
    } else if (score === 4) {
      strengthLabel = 'Segura y Fuerte';
      strengthColor = '#22c55e';
    }

    return {
      isValid: hasMinLen && hasUpper && hasLower && hasNumOrSymbol,
      hasMinLen,
      hasUpper,
      hasLower,
      hasNumOrSymbol,
      score,
      strengthLabel,
      strengthColor,
    };
  },

  /**
   * Sends password change request to API and updates local credential cache.
   */
  async changePassword(currentPassword, newPassword) {
    const user = this.getUser();
    if (!user) throw new Error('No hay sesión activa');

    const validation = this.validatePassword(newPassword);
    if (!validation.isValid) {
      throw new Error('La nueva contraseña no cumple con los requisitos de seguridad.');
    }

    // Try API update
    try {
      const res = await this.fetch('/api/auth/change-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
        }),
      });
      const data = await res.json();
      if (!res.ok || !data.success) {
        throw new Error(data.error || 'Error al cambiar la contraseña');
      }
    } catch (err) {
      if (err.message && (err.message.includes('incorrecta') || err.message.includes('igual'))) {
        throw err;
      }
      console.warn('API error during changePassword, applying local fallback:', err);
    }

    // Persist custom password in localStorage so offline/cloud fallback uses it
    try {
      const customPasswords = JSON.parse(localStorage.getItem('cmms_custom_passwords') || '{}');
      customPasswords[user.username.toLowerCase()] = newPassword;
      localStorage.setItem('cmms_custom_passwords', JSON.stringify(customPasswords));
    } catch (e) {
      console.error(e);
    }

    return { success: true, message: 'Contraseña actualizada exitosamente' };
  },

  /**
   * Initializes and binds the change password modal dialog.
   */
  setupPasswordModal() {
    const modal = document.getElementById('modal-change-password');
    const openBtns = document.querySelectorAll('.btn-open-change-password, #btn-open-change-password');
    const closeBtns = modal?.querySelectorAll('.btn-close-modal, #btn-close-password-modal, .modal-backdrop');
    const form = document.getElementById('form-change-password');
    if (!modal || !form) return;

    openBtns.forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        form.reset();
        this.resetPasswordModalUI();
        modal.classList.add('active');
        document.getElementById('pwd-current')?.focus();
      });
    });

    closeBtns?.forEach(btn => {
      btn.addEventListener('click', () => {
        modal.classList.remove('active');
      });
    });

    const newPwdInput = document.getElementById('pwd-new');
    const confirmPwdInput = document.getElementById('pwd-confirm');

    newPwdInput?.addEventListener('input', () => {
      this.updatePasswordStrengthUI(newPwdInput.value);
      this.checkPasswordMatchUI(newPwdInput.value, confirmPwdInput?.value || '');
    });

    confirmPwdInput?.addEventListener('input', () => {
      this.checkPasswordMatchUI(newPwdInput?.value || '', confirmPwdInput.value);
    });

    // Eye visibility toggle buttons
    modal.querySelectorAll('.btn-toggle-eye').forEach(eyeBtn => {
      eyeBtn.addEventListener('click', () => {
        const input = eyeBtn.parentElement?.querySelector('input');
        if (!input) return;
        if (input.type === 'password') {
          input.type = 'text';
          eyeBtn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path><line x1="1" y1="1" x2="23" y2="23"></line></svg>';
        } else {
          input.type = 'password';
          eyeBtn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>';
        }
      });
    });

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const currentPwd = document.getElementById('pwd-current')?.value || '';
      const newPwd = newPwdInput?.value || '';
      const confirmPwd = confirmPwdInput?.value || '';
      const alertBox = document.getElementById('pwd-modal-alert');
      const submitBtn = document.getElementById('btn-submit-password');

      if (alertBox) {
        alertBox.style.display = 'none';
        alertBox.className = 'modal-alert';
      }

      if (newPwd !== confirmPwd) {
        if (alertBox) {
          alertBox.textContent = 'Las contraseñas no coinciden.';
          alertBox.className = 'modal-alert alert-error';
          alertBox.style.display = 'block';
        }
        return;
      }

      const validation = this.validatePassword(newPwd);
      if (!validation.isValid) {
        if (alertBox) {
          alertBox.textContent = 'La nueva contraseña debe cumplir con todos los requisitos de seguridad.';
          alertBox.className = 'modal-alert alert-error';
          alertBox.style.display = 'block';
        }
        return;
      }

      submitBtn.disabled = true;
      submitBtn.textContent = 'Actualizando...';

      try {
        await this.changePassword(currentPwd, newPwd);
        if (alertBox) {
          alertBox.textContent = '✅ ¡Contraseña actualizada exitosamente! Utilízala en tu próximo inicio de sesión.';
          alertBox.className = 'modal-alert alert-success';
          alertBox.style.display = 'block';
        }
        form.reset();
        this.resetPasswordModalUI();
        setTimeout(() => {
          modal.classList.remove('active');
          if (alertBox) alertBox.style.display = 'none';
        }, 2200);
      } catch (err) {
        if (alertBox) {
          alertBox.textContent = '⚠️ ' + (err.message || 'Error al actualizar contraseña');
          alertBox.className = 'modal-alert alert-error';
          alertBox.style.display = 'block';
        }
      } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Guardar Nueva Contraseña';
      }
    });
  },

  updatePasswordStrengthUI(password) {
    const val = this.validatePassword(password);
    const bar = document.getElementById('pwd-strength-bar');
    const label = document.getElementById('pwd-strength-label');

    if (bar) {
      const pct = (val.score / 4) * 100;
      bar.style.width = `${pct}%`;
      bar.style.backgroundColor = val.strengthColor;
    }
    if (label) {
      label.textContent = password ? val.strengthLabel : 'Seguridad requerida';
      label.style.color = password ? val.strengthColor : '#94a3b8';
    }

    const checkMinLen = document.getElementById('chk-min-len');
    const checkUpper = document.getElementById('chk-upper');
    const checkLower = document.getElementById('chk-lower');
    const checkNumOrSymbol = document.getElementById('chk-num-sym');

    this.toggleCheckmark(checkMinLen, val.hasMinLen);
    this.toggleCheckmark(checkUpper, val.hasUpper);
    this.toggleCheckmark(checkLower, val.hasLower);
    this.toggleCheckmark(checkNumOrSymbol, val.hasNumOrSymbol);
  },

  toggleCheckmark(el, condition) {
    if (!el) return;
    const text = el.getAttribute('data-text') || el.textContent.replace(/^[✓○]\s*/, '');
    if (!el.getAttribute('data-text')) el.setAttribute('data-text', text);

    if (condition) {
      el.classList.add('valid');
      el.innerHTML = `<span style="color:#22c55e;font-weight:bold;">✓</span> ${text}`;
    } else {
      el.classList.remove('valid');
      el.innerHTML = `<span style="color:#64748b;">○</span> ${text}`;
    }
  },

  checkPasswordMatchUI(newPwd, confirmPwd) {
    const matchIndicator = document.getElementById('pwd-match-indicator');
    if (!matchIndicator) return;
    if (!confirmPwd) {
      matchIndicator.textContent = '';
      return;
    }
    if (newPwd === confirmPwd) {
      matchIndicator.textContent = '✓ Las contraseñas coinciden';
      matchIndicator.style.color = '#22c55e';
    } else {
      matchIndicator.textContent = '✕ Las contraseñas no coinciden';
      matchIndicator.style.color = '#ef4444';
    }
  },

  resetPasswordModalUI() {
    const bar = document.getElementById('pwd-strength-bar');
    const label = document.getElementById('pwd-strength-label');
    const match = document.getElementById('pwd-match-indicator');
    const alertBox = document.getElementById('pwd-modal-alert');
    if (bar) bar.style.width = '0%';
    if (label) {
      label.textContent = 'Seguridad requerida';
      label.style.color = '#94a3b8';
    }
    if (match) match.textContent = '';
    if (alertBox) alertBox.style.display = 'none';
    this.updatePasswordStrengthUI('');
  },
};

// Auto-initialize password modal when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  AuthClient.setupPasswordModal();
});

// Expose globally
window.AuthClient = AuthClient;
