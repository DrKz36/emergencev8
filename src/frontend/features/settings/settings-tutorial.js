/**
 * Settings Tutorial Module (static)
 * Fournit les guides et ressources documentaires sans tutoriel interactif.
 */

import { SettingsIcons, getIcon } from './settings-icons.js';
import { TUTORIAL_GUIDES } from '../../components/tutorial/tutorialGuides.js';

export class SettingsTutorial {
    constructor() {
        this.container = null;
    }

    async init(containerId) {
        this.container = typeof containerId === 'string'
            ? document.getElementById(containerId)
            : containerId;

        if (!this.container) {
            console.warn('[SettingsTutorial] container not found', containerId);
            return;
        }

        this.render();
    }

    render() {
        const guides = Array.isArray(TUTORIAL_GUIDES) ? TUTORIAL_GUIDES : [];
        const cards = guides.map((guide) => {
            const title = this.escapeHtml(guide.title || guide.id || 'Guide');
            const summary = this.escapeHtml(guide.summary || guide.description || '');
            return `
                <article class="tutorial-guide-card" data-guide-id="${this.escapeHtml(guide.id || '')}">
                    <div class="tutorial-guide-card__icon">${guide.icon ?? '📘'}</div>
                    <div class="tutorial-guide-card__content">
                        <h4>${title}</h4>
                        <p>${summary}</p>
                    </div>
                </article>
            `;
        }).join('');

        this.container.innerHTML = `
            <section class="settings-tutorial">
                <header class="settings-header">
                    <h2>${getIcon('book', 'header-icon')} Guides & tutoriels</h2>
                    <p class="header-description">
                        Le tutoriel interactif a été retiré. Consulte la documentation statique directement depuis la section « À propos » ou via le guide détaillé ci-dessous.
                    </p>
                </header>

                <div class="tutorial-static-actions">
                    <a class="btn-open-doc" href="/docs/TUTORIAL_SYSTEM.md" target="_blank" rel="noopener">
                        <span class="btn-icon">${SettingsIcons.bookOpen}</span>
                        Ouvrir le tutoriel complet (documentation)
                    </a>
                </div>

                <div class="tutorial-guides-list">
                    ${cards || '<p class="tutorial-empty">Aucun guide supplémentaire n\'est disponible pour le moment.</p>'}
                </div>
            </section>
        `;
    }

    escapeHtml(value) {
        return String(value ?? '').replace(/[&<>"']/g, (match) => {
            switch (match) {
                case '&': return '&amp;';
                case '<': return '&lt;';
                case '>': return '&gt;';
                case '"': return '&quot;';
                case "'": return '&#39;';
                default: return match;
            }
        });
    }

    destroy() {
        if (this.container) {
            this.container.innerHTML = '';
            this.container = null;
        }
    }
}

export const settingsTutorial = new SettingsTutorial();