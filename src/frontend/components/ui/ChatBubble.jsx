/**
 * @module components/ui/ChatBubble
 * @description Bulles de chat harmonisées (user + agents) avec gradients métalliques cohérents
 */

export class ChatBubble {
  /**
   * Crée une bulle de chat harmonisée
   * @param {Object} options - Configuration de la bulle
   * @param {string} options.role - 'user' | 'anima' | 'neo' | 'nexus' | 'global' | 'assistant'
   * @param {string} options.content - Contenu HTML de la bulle
   * @param {string} [options.name] - Nom de l'agent/utilisateur
   * @param {string} [options.timestamp] - Timestamp formaté
   * @param {boolean} [options.showActions] - Afficher les actions (copier, etc.)
   * @param {Array} [options.actions] - Actions personnalisées
   * @returns {HTMLElement} - Élément message
   */
  static create({
    role = 'user',
    content = '',
    name = null,
    timestamp = null,
    showActions = true,
    actions = []
  }) {
    const message = document.createElement('div');
    message.className = `chat-message chat-message--${role}`;

    const displayName = name || ChatBubble.getDefaultName(role);
    const time = timestamp || ChatBubble.getCurrentTime();

    const actionsHTML = showActions ? ChatBubble.renderActions(actions) : '';

    message.innerHTML = `
      <div class="chat-message__header">
        <div class="chat-message__meta">
          <span class="chat-message__name">${displayName}</span>
          ${timestamp ? `<span class="chat-message__separator">•</span>
          <span class="chat-message__time">${time}</span>` : ''}
        </div>
        ${actionsHTML}
      </div>
      <div class="chat-message__bubble">
        <div class="chat-message__content">${content}</div>
      </div>
    `;

    return message;
  }

  /**
   * Raccourci pour bulle utilisateur (bleu métallique)
   */
  static user(content, options = {}) {
    return ChatBubble.create({ ...options, role: 'user', content });
  }

  /**
   * Raccourci pour bulle Anima (rose-rouge)
   */
  static anima(content, options = {}) {
    return ChatBubble.create({ ...options, role: 'anima', content });
  }

  /**
   * Raccourci pour bulle Neo (bleu)
   */
  static neo(content, options = {}) {
    return ChatBubble.create({ ...options, role: 'neo', content });
  }

  /**
   * Raccourci pour bulle Nexus (émeraude)
   */
  static nexus(content, options = {}) {
    return ChatBubble.create({ ...options, role: 'nexus', content });
  }

  /**
   * Raccourci pour bulle Global (jaune)
   */
  static global(content, options = {}) {
    return ChatBubble.create({ ...options, role: 'global', content });
  }

  /**
   * Raccourci pour bulle Assistant (gris)
   */
  static assistant(content, options = {}) {
    return ChatBubble.create({ ...options, role: 'assistant', content });
  }

  /**
   * Obtient le nom par défaut selon le rôle
   */
  static getDefaultName(role) {
    const names = {
      user: 'Vous',
      anima: 'Anima',
      neo: 'Neo',
      nexus: 'Nexus',
      global: 'Global',
      assistant: 'Assistant'
    };
    return names[role] || 'Agent';
  }

  /**
   * Retourne le timestamp actuel formaté
   */
  static getCurrentTime() {
    const now = new Date();
    return now.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
  }

  /**
   * Rendu des actions (copier, etc.)
   */
  static renderActions(actions = []) {
    if (actions.length === 0) {
      actions = [
        {
          icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                </svg>`,
          title: 'Copier',
          action: 'copy'
        }
      ];
    }

    const actionsHTML = actions.map(({ icon, title, action }) =>
      `<button class="chat-message__action" data-action="${action}" title="${title}" aria-label="${title}">
        ${icon}
      </button>`
    ).join('');

    return `<div class="chat-message__actions">${actionsHTML}</div>`;
  }
}

/**
 * Styles CSS pour les bulles de chat harmonisées
 * À importer dans votre fichier CSS principal
 */
export const CHAT_BUBBLE_STYLES = `
/* === BULLES DE CHAT HARMONISÉES === */

.chat-message {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  width: var(--bubble-max-width, min(880px, calc(100% - 32px)));
  margin: 0.75rem auto;
  align-items: flex-start;
}

.chat-message--user {
  align-items: flex-end;
}

/* === HEADER === */
.chat-message__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
  width: 100%;
}

.chat-message__meta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.chat-message--user .chat-message__header {
  justify-content: flex-end;
  color: #e0f2fe;
}

.chat-message--anima .chat-message__header { color: #fee2e2; }
.chat-message--neo .chat-message__header { color: #e0f2fe; }
.chat-message--nexus .chat-message__header { color: #dcfce7; }
.chat-message--global .chat-message__header { color: #fef08a; }
.chat-message--assistant .chat-message__header { color: rgba(226, 232, 240, 0.85); }

.chat-message__name {
  font-weight: 700;
}

.chat-message__separator {
  opacity: 0.6;
}

.chat-message__time {
  font-size: 0.75rem;
  letter-spacing: 0.02em;
}

/* === ACTIONS === */
.chat-message__actions {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  color: rgba(226, 232, 240, 0.82);
  flex-shrink: 0;
}

.chat-message__action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: 10px;
  border: 1px solid rgba(148, 163, 184, 0.28);
  background: rgba(15, 23, 42, 0.35);
  color: #e2e8f0;
  padding: 0;
  cursor: pointer;
  transition: all 0.2s ease;
}

.chat-message__action svg {
  width: 16px;
  height: 16px;
}

.chat-message__action:hover {
  background: rgba(30, 41, 59, 0.65);
  border-color: rgba(148, 163, 184, 0.45);
  transform: translateY(-1px);
  box-shadow: 0 12px 24px rgba(15, 23, 42, 0.35);
}

.chat-message__action:disabled {
  opacity: 0.45;
  pointer-events: none;
}

/* === BULLE === */
.chat-message__bubble {
  background: rgba(15, 23, 42, 0.65);
  border: 1px solid rgba(255, 255, 255, 0.10);
  border-radius: var(--bubble-radius, 1.125rem);
  padding: var(--bubble-padding, 0.75rem 1rem);
  color: #e9e9ef;
  line-height: 1.55;
  box-shadow: var(--bubble-shadow, 0 8px 20px rgba(0, 0, 0, 0.25));
  backdrop-filter: blur(14px);
  align-self: flex-start;
  max-width: 100%;
}

/* === BULLES USER (Bleu métallique harmonisé) === */
.chat-message--user .chat-message__bubble {
  background: var(--metal-blue-gradient, linear-gradient(140deg, #60a5fa, #3b82f6, #2563eb));
  border-color: rgba(59, 130, 246, 0.5);
  color: #eff6ff;
  align-self: flex-end;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.4), 0 8px 20px rgba(59, 130, 246, 0.25);
}

/* === BULLES AGENTS (conserver les gradients existants) === */
.chat-message--anima .chat-message__bubble {
  background: linear-gradient(140deg, #be123c, #fb7185);
  border-color: rgba(244, 114, 182, 0.45);
  color: #fff5f7;
}

.chat-message--neo .chat-message__bubble {
  background: linear-gradient(140deg, #1d4ed8, #38bdf8);
  border-color: rgba(59, 130, 246, 0.45);
  color: #eff6ff;
}

.chat-message--nexus .chat-message__bubble {
  background: linear-gradient(140deg, #0f766e, #34d399);
  border-color: rgba(45, 212, 191, 0.45);
  color: #ecfdf5;
}

.chat-message--global .chat-message__bubble {
  background: linear-gradient(140deg, #facc15, #fde047);
  border-color: rgba(250, 204, 21, 0.4);
  color: #1f2937;
}

.chat-message--assistant .chat-message__bubble {
  background: rgba(30, 41, 59, 0.75);
  border-color: rgba(148, 163, 184, 0.28);
  color: #e2e8f0;
}

/* === CONTENU === */
.chat-message__content {
  font-size: 0.95rem;
  line-height: 1.6;
}

.chat-message__content p {
  margin-bottom: 0.75rem;
}

.chat-message__content p:last-child {
  margin-bottom: 0;
}

/* Code blocks */
.chat-message__content pre,
.chat-message__content code {
  font-family: var(--mono, 'Fira Code', monospace);
  font-size: 13px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.10);
  border-radius: 10px;
  padding: 10px;
  overflow: auto;
}

/* === RESPONSIVE === */
@media (max-width: 640px) {
  .chat-message {
    gap: 0.375rem;
    margin: 0.5rem auto;
  }

  .chat-message__header {
    gap: 0.5rem;
  }

  .chat-message__meta {
    font-size: 0.7rem;
  }

  .chat-message__action {
    width: 30px;
    height: 30px;
  }

  .chat-message__action svg {
    width: 14px;
    height: 14px;
  }

  .chat-message__bubble {
    padding: 0.625rem 0.875rem;
  }

  .chat-message__content {
    font-size: 0.875rem;
  }
}
`;
