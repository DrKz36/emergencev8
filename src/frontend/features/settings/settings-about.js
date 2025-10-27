/**
 * Settings About Module
 * Affiche les informations de version, changelog et crédits
 */

import './settings-about.css';
import { getIcon } from './settings-icons.js';
import versionInfo, { FULL_CHANGELOG } from '../../version.js';
import logoWebpUrl from '../../../../assets/emergence_logo.webp';
import logoPngUrl from '../../../../assets/emergence_logo.png';

class SettingsAbout {
    constructor() {
        this.container = null;
    }

    /**
     * Initialize about module
     */
    init(containerId) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            console.error('About container not found');
            return;
        }

        this.render();
    }

    /**
     * Render about content
     */
    render() {
        this.container.innerHTML = `
            <div class="settings-about">
                ${this.renderVersionInfo()}
                ${this.renderChangelog()}
                ${this.renderModules()}
                ${this.renderCredits()}
            </div>
        `;
    }

    /**
     * Render version information section
     */
    renderVersionInfo() {
        const brandLogoMarkup = `
            <picture class="about-logo-picture">
                <source srcset="${logoWebpUrl}" type="image/webp" />
                <img src="${logoPngUrl}" alt="ÉMERGENCE" class="about-logo" width="120" height="120" loading="lazy" decoding="async" />
            </picture>
        `;

        return `
            <div class="about-section about-version">
                <div class="about-header">
                    ${brandLogoMarkup}
                    <div class="about-header-info">
                        <h2 class="about-title">ÉMERGENCE V8</h2>
                        <p class="about-subtitle">${versionInfo.fullVersion}</p>
                        <div class="about-badges">
                            <span class="about-badge about-badge-phase">${versionInfo.buildPhase}</span>
                            <span class="about-badge about-badge-progress">${versionInfo.completionPercentage}% complété</span>
                            <span class="about-badge about-badge-features">${versionInfo.featuresDisplay} fonctionnalités</span>
                        </div>
                    </div>
                </div>

                <div class="about-info-grid">
                    <div class="about-info-item">
                        <span class="about-info-icon">${getIcon('calendar')}</span>
                        <div class="about-info-content">
                            <span class="about-info-label">Date de build</span>
                            <span class="about-info-value">${versionInfo.versionDate}</span>
                        </div>
                    </div>
                    <div class="about-info-item">
                        <span class="about-info-icon">${getIcon('package')}</span>
                        <div class="about-info-content">
                            <span class="about-info-label">Version</span>
                            <span class="about-info-value">${versionInfo.version}</span>
                        </div>
                    </div>
                    <div class="about-info-item">
                        <span class="about-info-icon">${getIcon('barChart')}</span>
                        <div class="about-info-content">
                            <span class="about-info-label">Phase actuelle</span>
                            <span class="about-info-value">${versionInfo.buildPhase} - ${versionInfo.versionName}</span>
                        </div>
                    </div>
                    <div class="about-info-item">
                        <span class="about-info-icon">${getIcon('checkCircle')}</span>
                        <div class="about-info-content">
                            <span class="about-info-label">Progression</span>
                            <span class="about-info-value">${versionInfo.completionPercentage}% (${versionInfo.featuresDisplay})</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Render changelog section (enriched - 5 latest versions with full details)
     */
    renderChangelog() {
        const fullChangelog = FULL_CHANGELOG || []; // Use enriched changelog (5 versions)

        return `
            <div class="about-section about-changelog">
                <h3 class="about-section-title">
                    ${getIcon('fileText')} Historique des Versions
                </h3>
                <p class="about-section-subtitle">
                    Découvrez les évolutions et améliorations apportées à ÉMERGENCE au fil des versions.
                    Affichage détaillé des 5 dernières révisions avec fonctionnalités complètes.
                </p>

                <div class="changelog-container">
                    ${fullChangelog.map(version => `
                        <div class="changelog-version ${version.version === versionInfo.version ? 'changelog-current' : ''}">
                            <div class="changelog-header">
                                <div class="changelog-title-group">
                                    ${version.version === versionInfo.version ? '<span class="changelog-current-badge">Version actuelle</span>' : ''}
                                    <h4 class="changelog-version-number">${version.version}</h4>
                                    <p class="changelog-version-title">${version.title}</p>
                                </div>
                                <span class="changelog-date">${version.date}</span>
                            </div>

                            <div class="changelog-description">
                                <p>${version.description}</p>
                            </div>

                            <div class="changelog-sections">
                                ${version.sections.map(section => this.renderChangelogSection(section)).join('')}
                            </div>
                        </div>
                    `).join('')}
                </div>

                <div class="changelog-footer">
                    <p class="changelog-footer-text">
                        ${getIcon('info')}
                        Pour consulter l'historique complet, voir le fichier
                        <code>CHANGELOG.md</code> à la racine du projet.
                    </p>
                </div>
            </div>
        `;
    }

    /**
     * Render a single changelog section (features, fixes, quality, impact, files)
     */
    renderChangelogSection(section) {
        const typeBadges = {
            features: 'badge-feature',
            fixes: 'badge-fix',
            quality: 'badge-quality',
            impact: 'badge-impact',
            files: 'badge-files'
        };

        const badgeClass = typeBadges[section.type] || 'badge-default';

        return `
            <div class="changelog-section">
                <h5 class="changelog-section-title">
                    <span class="changelog-section-badge ${badgeClass}">${section.title}</span>
                </h5>
                <div class="changelog-section-content">
                    ${this.renderChangelogSectionItems(section.items, section.type)}
                </div>
            </div>
        `;
    }

    /**
     * Render section items (detailed or simple list)
     */
    renderChangelogSectionItems(items, sectionType) {
        if (!items || items.length === 0) {
            return '<p class="changelog-no-items">Aucun changement</p>';
        }

        // For impact and files sections, render as simple list
        if (sectionType === 'impact' || sectionType === 'files') {
            return `
                <ul class="changelog-simple-list">
                    ${items.map(item => `<li>${item}</li>`).join('')}
                </ul>
            `;
        }

        // For features, fixes, quality sections, render with details
        return `
            <div class="changelog-detailed-items">
                ${items.map(item => `
                    <div class="changelog-detailed-item">
                        <div class="changelog-item-header">
                            <span class="changelog-item-icon">${getIcon('checkCircle')}</span>
                            <strong class="changelog-item-title">${item.title}</strong>
                        </div>
                        <p class="changelog-item-description">${item.description}</p>
                        ${item.file ? `<code class="changelog-item-file">${getIcon('fileText')} ${item.file}</code>` : ''}
                    </div>
                `).join('')}
            </div>
        `;
    }

    /**
     * Render modules section
     */
    renderModules() {
        const modules = [
            { name: 'Home', version: 'v1.0', icon: 'home' },
            { name: 'Cockpit', version: 'v3.0', icon: 'barChart' },
            { name: 'Chat', version: 'v2.5', icon: 'messageCircle' },
            { name: 'Voice', version: 'v1.2', icon: 'mic' },
            { name: 'Memory', version: 'v2.0', icon: 'brain' },
            { name: 'Debate', version: 'v1.5', icon: 'messageSquare' },
            { name: 'Documents', version: 'v1.8', icon: 'fileText' },
            { name: 'References', version: 'v1.0', icon: 'bookmark' },
            { name: 'Threads', version: 'v1.3', icon: 'list' },
            { name: 'Conversations', version: 'v1.4', icon: 'messageCircle' },
            { name: 'Timeline', version: 'v1.1', icon: 'clock' },
            { name: 'Costs', version: 'v1.0', icon: 'dollarSign' },
            { name: 'Preferences', version: 'v1.5', icon: 'user' },
            { name: 'Settings', version: 'v4.0', icon: 'settings' },
            { name: 'Admin', version: 'v1.0', icon: 'shield' }
        ];

        return `
            <div class="about-section about-modules">
                <h3 class="about-section-title">
                    ${getIcon('package')} Modules Installés
                </h3>
                <p class="about-section-subtitle">
                    ${modules.length} modules actifs dans votre installation ÉMERGENCE.
                </p>

                <div class="modules-grid">
                    ${modules.map(module => `
                        <div class="module-card">
                            <span class="module-icon">${getIcon(module.icon)}</span>
                            <div class="module-info">
                                <span class="module-name">${module.name}</span>
                                <span class="module-version">${module.version}</span>
                            </div>
                            <span class="module-status">${getIcon('checkCircle')}</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    /**
     * Render credits section
     */
    renderCredits() {
        return `
            <div class="about-section about-credits">
                <h3 class="about-section-title">
                    ${getIcon('heart')} Crédits & Remerciements
                </h3>

                <div class="credits-content">
                    <div class="credits-main">
                        <h4 class="credits-subtitle">Développement Principal</h4>
                        <p class="credits-text">
                            <strong>Fernando Gonzalez</strong> — Architecte & Développeur Principal
                        </p>
                        <p class="credits-text">
                            ÉMERGENCE V8 est une plateforme multi-agents développée avec passion,
                            combinant les technologies les plus avancées en matière d'IA et d'architecture distribuée.
                        </p>
                    </div>

                    <div class="credits-special">
                        <h4 class="credits-subtitle">${getIcon('star')} Remerciements Spéciaux</h4>
                        <p class="credits-text credits-highlight">
                            À <strong>Marem</strong>, mon épouse extraordinaire, dont le soutien indéfectible,
                            la patience infinie et les encouragements constants ont été essentiels à chaque étape
                            de ce projet ambitieux. Ce travail n'aurait pas été possible sans toi. ❤️
                        </p>
                    </div>

                    <div class="credits-tech">
                        <h4 class="credits-subtitle">Technologies Clés</h4>
                        <div class="tech-tags">
                            <span class="tech-tag">FastAPI</span>
                            <span class="tech-tag">Vite</span>
                            <span class="tech-tag">OpenAI GPT-4</span>
                            <span class="tech-tag">Anthropic Claude</span>
                            <span class="tech-tag">Google Gemini</span>
                            <span class="tech-tag">ChromaDB</span>
                            <span class="tech-tag">WebSocket</span>
                            <span class="tech-tag">Google Cloud Run</span>
                            <span class="tech-tag">Prometheus</span>
                        </div>
                    </div>

                    <div class="credits-guardian">
                        <h4 class="credits-subtitle">${getIcon('shield')} Écosystème Guardian</h4>
                        <p class="credits-text">
                            Ce projet bénéficie d'un écosystème complet d'agents IA autonomes (Anima, Neo, ProdGuardian,
                            Argus, Theia, Nexus, Claude Code) qui assurent la qualité, la documentation, le monitoring
                            et l'optimisation en continu.
                        </p>
                        <p class="credits-text credits-meta">
                            ÉMERGENCE n'est pas seulement une plateforme multi-agents pour les utilisateurs —
                            <strong>c'est le premier projet développé EN COLLABORATION avec une équipe IA autonome</strong>.
                        </p>
                    </div>

                    <div class="credits-footer">
                        <p class="credits-copyright">
                            © 2025 ÉMERGENCE V8 — Tous droits réservés
                        </p>
                        <p class="credits-contact">
                            ${getIcon('mail')} <a href="mailto:gonzalefernando@gmail.com">gonzalefernando@gmail.com</a>
                        </p>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Destroy about module
     */
    destroy() {
        if (this.container) {
            this.container.innerHTML = '';
        }
    }
}

// Export singleton instance
export const settingsAbout = new SettingsAbout();
