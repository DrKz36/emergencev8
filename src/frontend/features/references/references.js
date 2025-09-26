/**
 * @module features/references/references
 * @description Module "A propos" (sidebar) : selectionne un document et l'affiche dans la zone centrale avec un rendu markdown simplifie.
 */

const DOCS = [
  {
    id: 'tech-portrait',
    title: 'Portrait technique',
    description: 'Architecture actuelle, modules backend/frontend, flux memoire et chiffres cle.',
    path: '/docs/tech-portrait.md',
    category: 'Architecture',
    cta: 'Voir le document',
    showInList: true,
  },
  {
    id: 'story-genese',
    title: "Genese d'Emergence",
    description: "Le cheminement fondateur, les apprentissages avec les IA generatives et les objectifs a venir.",
    path: '/docs/story-genese-emergence.md',
    category: 'Vision',
    cta: "Lire l'histoire",
    showInList: true,
  },
  {
    id: 'agents-profils',
    title: 'Profils des copilotes IA',
    description: 'Fiches detaillees de Anima, Neo et Nexus (missions, personnalites, points de vigilance).',
    path: '/docs/agents-profils.md',
    category: 'Agents',
    cta: 'Consulter la fiche complete',
    showInList: false,
  },
];

const AGENTS = [
  {
    id: 'anima',
    name: 'Anima',
    alias: 'La presence empathique',
    summary: "Accueille, clarifie et maintient le rythme des echanges pour garder l'equipe alignee.",
    role: "Accueillir, clarifier et maintenir le rythme des echanges.",
    personality: "Chaleureuse, orientee accompagnement, experte en reformulation et reconnaissance des intentions implicites.",
    capabilities: [
      'Detection des signaux faibles dans la memoire court terme.',
      'Suggestions de relances pour relancer le dialogue.',
      "Maintien d'une cohesion fluide entre utilisateurs et agents techniques.",
    ],
    image: '/assets/anima.png',
    imageAlt: 'Portrait de Anima',
    docAnchor: 'anima-la-presence-empathique',
  },
  {
    id: 'neo',
    name: 'Neo',
    alias: "L'analyste strategique",
    summary: "Structure les idees, cartographie les hypotheses et projette des plans d'action.",
    role: "Structurer les idees, cartographier les hypotheses et rapprocher les donnees existantes.",
    personality: "Analytique, concis, ferme lorsqu'il faut recadrer et adosse a des grilles de lecture prospectives.",
    capabilities: [
      'Exploitation fine du RAG pour sourcer et justifier les reponses.',
      "Declinaison des discussions en plans d'action prioritises.",
      'Evaluation continue des risques et opportunites.',
    ],
    image: '/assets/neo.png',
    imageAlt: 'Portrait de Neo',
    docAnchor: 'neo-l-analyste-strategique',
  },
  {
    id: 'nexus',
    name: 'Nexus',
    alias: "L'architecte systemique",
    summary: 'Traduit les besoins en flux operationnels coherents et supervise les autres agents.',
    role: 'Traduire les besoins en processus concrets et orchestrer les autres agents specialises.',
    personality: 'Methodique, oriente protocole, centre sur la coherence globale et la tracabilite.',
    capabilities: [
      'Pilotage des workflows chat, memoire et debats.',
      'Arbitrage des fournisseurs LLM selon la qualite et le cout.',
      'Supervision des indicateurs de couts et d\'observabilite.',
    ],
    image: '/assets/nexus.png',
    imageAlt: 'Portrait de Nexus',
    docAnchor: 'nexus-l-architecte-systemique',
  },
];

function getDocMeta(docId) {
  return DOCS.find((doc) => doc.id === docId) || null;
}

export class ReferencesModule {
  constructor(eventBus, state) {
    this.eventBus = eventBus;
    this.state = state;
    this.container = null;
    this.viewer = null;
    this.activeDocId = (DOCS.find((doc) => doc.showInList !== false) || {}).id || null;
    this.cache = new Map();
    this.onCardClick = this.onCardClick.bind(this);
  }

  init() {}

  mount(container) {
    if (!container) return;
    this.container = container;
    this.container.innerHTML = this.render();
    this.viewer = this.container.querySelector('[data-role="references-viewer"]');
    this.container.addEventListener('click', this.onCardClick);
    if (this.activeDocId) {
      this.loadDoc(this.activeDocId, { silentHighlight: true });
    }
  }

  unmount() {
    if (!this.container) return;
    this.container.removeEventListener('click', this.onCardClick);
    this.container.innerHTML = '';
    this.container = null;
    this.viewer = null;
  }

  render() {
    const cards = this.renderDocCards();
    const agentsSection = this.renderAgentsSection();

    return `
      <section class="references" aria-labelledby="references-title">
        <header class="references__header">
          <h1 id="references-title" class="references__title">A propos</h1>
          <p class="references__intro">Retrouvez la synthese technique et les reperes cle du projet Emergence.</p>
        </header>
        ${agentsSection}
        <div class="references__body">
          <div class="references__cards" data-role="references-cards">
            ${cards}
          </div>
          <div class="references__viewer" data-role="references-viewer">
            <div class="references__viewer-status">Selectionnez un document pour afficher son contenu.</div>
          </div>
        </div>
        <footer class="references__footer">
          <p class="references__note">Les documents sont charges directement depuis le dossier docs/. Mettez a jour la documentation en parallele de toute evolution produit.</p>
        </footer>
      </section>
    `;
  }

  renderDocCards() {
    return DOCS.filter((doc) => doc.showInList !== false).map((doc) => {
      const isActive = doc.id === this.activeDocId;
      const baseClass = 'references__card';
      const modifiers = [isActive ? 'references__card--active' : null, doc.image ? 'references__card--with-image' : null]
        .filter(Boolean)
        .join(' ');
      const cardClass = modifiers ? `${baseClass} ${modifiers}` : baseClass;
      const ariaPressed = isActive ? 'true' : 'false';
      const media = doc.image
        ? `<span class="references__card-media"><img src="${this.escapeHtml(doc.image)}" alt="${this.escapeHtml(doc.imageAlt || doc.title)}" loading="lazy" /></span>`
        : '';

      return `
        <button type="button" class="${cardClass}" data-doc-id="${doc.id}" aria-pressed="${ariaPressed}">
          ${media}
          <span class="references__card-content">
            <span class="references__card-kicker">${this.escapeHtml(doc.category)}</span>
            <span class="references__card-title">${this.escapeHtml(doc.title)}</span>
            <span class="references__card-description">${this.escapeHtml(doc.description)}</span>
            <span class="references__card-cta">${this.escapeHtml(doc.cta)}</span>
          </span>
        </button>
      `;
    }).join('');
  }

    renderAgentsSection() {
    const cards = AGENTS.map((agent) => this.renderAgentCard(agent)).join('');
    return `
      <section class="references__agents" aria-labelledby="references-agents-title">
        <div class="references__agents-header">
          <h2 id="references-agents-title">Vos copilotes IA</h2>
          <p>Cartographie rapide des missions, personnalites et atouts de Anima, Neo et Nexus.</p>
        </div>
        <div class="references__cards references__cards--agents">
          ${cards}
        </div>
      </section>
    `;
  }
  renderAgentCard(agent) {
    const docMeta = getDocMeta('agents-profils');
    const targetDocId = docMeta?.id || 'agents-profils';
    const anchor = this.escapeHtml(agent.docAnchor || '');
    const alias = this.escapeHtml(agent.alias || '');
    const summary = this.escapeHtml(agent.summary || '');
    return `
      <button
        type="button"
        class="references__card references__card--agent"
        data-agent-doc="${targetDocId}"
        data-agent-anchor="${anchor}"
        aria-pressed="false"
      >
        <span class="references__card-content">
          <span class="references__card-kicker">Copilote IA</span>
          <span class="references__card-title">${this.escapeHtml(agent.name)}</span>
          <span class="references__card-subtitle">${alias}</span>
          <span class="references__card-description references__card-description--agent">${summary}</span>
          <span class="references__card-cta">Voir le document</span>
        </span>
      </button>
    `;
  }
  onCardClick(event) {
    const focusTrigger = event.target.closest('[data-agent-doc]');
    if (focusTrigger && this.container?.contains(focusTrigger)) {
      event.preventDefault();
      const docId = focusTrigger.getAttribute('data-agent-doc');
      const anchor = focusTrigger.getAttribute('data-agent-anchor') || '';
      if (docId) {
        this.loadDoc(docId, { anchor, silentHighlight: true });
      }
      return;
    }

    const target = event.target.closest('[data-doc-id]');
    if (!target || !this.container?.contains(target)) return;
    event.preventDefault();
    const docId = target.getAttribute('data-doc-id');
    if (!docId || docId === this.activeDocId) return;
    this.activeDocId = docId;
    this.updateActiveCards();
    this.loadDoc(docId, { silentHighlight: true });
  }

  updateActiveCards() {
    const cards = this.container?.querySelectorAll('[data-doc-id]');
    if (!cards) return;

    cards.forEach((card) => {
      const isActive = card.getAttribute('data-doc-id') === this.activeDocId;
      card.classList.toggle('references__card--active', isActive);
      card.setAttribute('aria-pressed', isActive ? 'true' : 'false');
    });
  }

  async loadDoc(docId, options = {}) {
    if (!this.viewer) return;
    const { anchor, silentHighlight } = options;
    const doc = getDocMeta(docId);
    if (!doc) {
      this.viewer.innerHTML = '<div class="references__viewer-status">Document introuvable.</div>';
      return;
    }

    if (!silentHighlight && doc.showInList !== false) {
      this.activeDocId = doc.id;
      this.updateActiveCards();
    }

    this.viewer.innerHTML = '<div class="references__viewer-status">Chargement du document...</div>';

    try {
      let markdown;
      if (this.cache.has(doc.path)) {
        markdown = this.cache.get(doc.path);
      } else {
        const response = await fetch(doc.path, { credentials: 'same-origin' });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        markdown = await response.text();
        this.cache.set(doc.path, markdown);
      }

      const html = this.markdownToHtml(markdown);
      this.viewer.innerHTML = `
        <div class="references__viewer-scroll">
          <article class="references__viewer-article" data-doc-id="${doc.id}">
            ${html}
          </article>
        </div>
      `;
      this.focusAnchor(anchor || doc.anchor);
    } catch (error) {
      console.error('[ReferencesModule] Impossible de charger le document', error);
      this.viewer.innerHTML = '<div class="references__viewer-status references__viewer-status--error">Impossible de charger ce document pour le moment.</div>';
    }
  }

  focusAnchor(anchor) {
    if (!anchor || !this.viewer) return;
    const selector = anchor.startsWith('#') ? anchor : `#${anchor}`;
    const scrollContainer = this.viewer.querySelector('.references__viewer-scroll');
    if (!scrollContainer) return;

    const target = scrollContainer.querySelector(selector);
    if (!target) return;

    target.classList.add('references__viewer-heading--focus');
    const offset = Math.max(target.offsetTop - 16, 0);
    scrollContainer.scrollTo({ top: offset, behavior: 'smooth' });
    window.setTimeout(() => {
      target.classList.remove('references__viewer-heading--focus');
    }, 2200);
  }

  markdownToHtml(markdown) {
    const lines = markdown.split(/\r?\n/);
    const html = [];
    let inList = false;
    let inCode = false;
    const codeBuffer = [];

    const flushList = () => {
      if (!inList) return;
      html.push('</ul>');
      inList = false;
    };

    const flushCode = () => {
      if (!inCode) return;
      const code = codeBuffer.join('\n');
      html.push(`<pre><code>${this.escapeHtml(code)}</code></pre>`);
      codeBuffer.length = 0;
      inCode = false;
    };

    lines.forEach((rawLine) => {
      const line = rawLine ?? '';
      const trimmed = line.trim();

      if (trimmed.startsWith('```')) {
        if (inCode) {
          flushCode();
        } else {
          flushList();
          inCode = true;
        }
        return;
      }

      if (inCode) {
        codeBuffer.push(line);
        return;
      }

      if (!trimmed) {
        flushList();
        html.push('');
        return;
      }

      const headingMatch = trimmed.match(/^(#{1,4})\s+(.*)$/);
      if (headingMatch) {
        flushList();
        const level = Math.min(headingMatch[1].length, 4);
        const text = headingMatch[2];
        const slug = this.slugify(text);
        html.push(`<h${level} id="${slug}">${this.formatInline(text)}</h${level}>`);
        return;
      }

      if (/^[-*+]\s+/.test(trimmed)) {
        if (!inList) {
          html.push('<ul>');
          inList = true;
        }
        const item = trimmed.replace(/^[-*+]\s+/, '');
        html.push(`<li>${this.formatInline(item)}</li>`);
        return;
      }

      flushList();
      html.push(`<p>${this.formatInline(trimmed)}</p>`);
    });

    flushCode();
    flushList();
    return html.join('\n');
  }

  slugify(value) {
    return String(value || '')
      .normalize('NFD')
      .replace(/\p{Diacritic}/gu, '')
      .toLowerCase()
      .replace(/[^a-z0-9\s-]/g, '')
      .trim()
      .replace(/\s+/g, '-')
      .replace(/-+/g, '-');
  }

  escapeHtml(value) {
    return String(value ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  formatInline(text) {
    let html = this.escapeHtml(text);
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
    html = html.replace(/`([^`]+?)`/g, '<code>$1</code>');
    html = html.replace(/\[(.+?)\]\((.+?)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
    return html;
  }
}

export default ReferencesModule;


