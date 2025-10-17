/**
 * @module features/memory/concept-graph
 * @description Interactive knowledge graph visualization for concepts
 */

const API_BASE = '/api/memory';

async function getAuthHeaders() {
  let token = null;
  try {
    token = sessionStorage.getItem('emergence.id_token') || localStorage.getItem('emergence.id_token');
  } catch (_) {}
  if (!token) {
    try {
      token = sessionStorage.getItem('id_token') || localStorage.getItem('id_token');
    } catch (_) {}
  }

  const headers = {
    'Content-Type': 'application/json',
  };

  const trimmed = typeof token === 'string' ? token.trim() : '';
  if (trimmed) {
    headers['Authorization'] = `Bearer ${trimmed}`;
  }

  return headers;
}

async function getConceptsForGraph() {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_BASE}/concepts/graph`, {
    method: 'GET',
    headers,
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || `HTTP ${response.status}`);
  }

  return response.json();
}

export class ConceptGraph {
  constructor(eventBus, stateManager, options = {}) {
    this.eventBus = eventBus;
    this.state = stateManager;
    this.options = {
      hostId: typeof options.hostId === 'string' ? options.hostId : null,
    };
    this.hostElement = options.hostElement || null;

    this.container = null;
    this.canvas = null;
    this.ctx = null;

    this.nodes = [];
    this.links = [];
    this.isLoading = false;
    this.error = null;

    this.width = 800;
    this.height = 600;
    this.zoom = 1;
    this.offsetX = 0;
    this.offsetY = 0;

    this.isDragging = false;
    this.dragNode = null;
    this.dragStartX = 0;
    this.dragStartY = 0;

    this.hoveredNode = null;
    this.selectedNode = null;

    this._animationFrame = null;
    this._initialized = false;

    // Filters
    this._filterType = 'all'; // 'all', 'high', 'medium', 'low'
    this._filterDate = 'all'; // 'all', 'today', 'week', 'month'
    this._allNodes = [];
    this._allLinks = [];

    this._boundMouseDown = this.handleMouseDown.bind(this);
    this._boundMouseMove = this.handleMouseMove.bind(this);
    this._boundMouseUp = this.handleMouseUp.bind(this);
    this._boundWheel = this.handleWheel.bind(this);
  }

  template() {
    return `
      <div class="concept-graph__inner">
        <header class="concept-graph__header">
          <h3 class="concept-graph__title">Graphe de Connaissances</h3>
          <div class="concept-graph__controls">
            <select class="concept-graph__filter" data-filter="type" title="Filtrer par importance">
              <option value="all">Tous les concepts</option>
              <option value="high">Haute importance (10+)</option>
              <option value="medium">Moyenne (5-9)</option>
              <option value="low">Faible (1-4)</option>
            </select>
            <button class="btn btn--ghost concept-graph__btn" data-action="reset-view">🔄 Vue</button>
            <button class="btn btn--ghost concept-graph__btn" data-action="reload">↻ Recharger</button>
          </div>
        </header>

        <div class="concept-graph__body">
          <p class="concept-graph__error" data-role="graph-error" hidden></p>
          <div class="concept-graph__stats" data-role="graph-stats"></div>
          <div class="concept-graph__canvas-wrapper" data-role="graph-canvas-wrapper">
            <canvas class="concept-graph__canvas" data-role="graph-canvas"></canvas>
          </div>
          <div class="concept-graph__info" data-role="graph-info"></div>
        </div>
      </div>
    `;
  }

  init() {
    this.ensureContainer();
    if (!this.container) return;

    this.bindEvents();
    this._initialized = true;
    this.loadGraph();
  }

  destroy() {
    if (this._animationFrame) {
      cancelAnimationFrame(this._animationFrame);
      this._animationFrame = null;
    }

    if (this.canvas) {
      this.canvas.removeEventListener('mousedown', this._boundMouseDown);
      this.canvas.removeEventListener('mousemove', this._boundMouseMove);
      this.canvas.removeEventListener('mouseup', this._boundMouseUp);
      this.canvas.removeEventListener('wheel', this._boundWheel);
    }

    this._initialized = false;
  }

  ensureContainer() {
    if (this.container) return;

    let host = this.hostElement;
    if (!host && this.options.hostId) {
      host = document.getElementById(this.options.hostId);
    }
    if (!host) return;

    host.classList.add('concept-graph');
    host.innerHTML = this.template();

    this.container = host;
    const canvasWrapper = host.querySelector('[data-role="graph-canvas-wrapper"]');
    this.canvas = host.querySelector('[data-role="graph-canvas"]');

    if (this.canvas && canvasWrapper) {
      this.width = canvasWrapper.clientWidth || 800;
      this.height = canvasWrapper.clientHeight || 600;
      this.canvas.width = this.width;
      this.canvas.height = this.height;
      this.ctx = this.canvas.getContext('2d');
    }

    this.errorContainer = host.querySelector('[data-role="graph-error"]');
    this.infoContainer = host.querySelector('[data-role="graph-info"]');
    this.statsContainer = host.querySelector('[data-role="graph-stats"]');
  }

  bindEvents() {
    if (!this.canvas) return;

    this.canvas.addEventListener('mousedown', this._boundMouseDown);
    this.canvas.addEventListener('mousemove', this._boundMouseMove);
    this.canvas.addEventListener('mouseup', this._boundMouseUp);
    this.canvas.addEventListener('wheel', this._boundWheel, { passive: false });

    const resetBtn = this.container?.querySelector('[data-action="reset-view"]');
    if (resetBtn) {
      resetBtn.addEventListener('click', () => this.resetView());
    }

    const reloadBtn = this.container?.querySelector('[data-action="reload"]');
    if (reloadBtn) {
      reloadBtn.addEventListener('click', () => this.loadGraph());
    }

    const filterType = this.container?.querySelector('[data-filter="type"]');
    if (filterType) {
      filterType.addEventListener('change', (e) => {
        this._filterType = e.target.value;
        this.applyFilters();
      });
    }
  }

  async loadGraph() {
    this.isLoading = true;
    this.error = null;
    this.renderError();

    try {
      const data = await getConceptsForGraph();
      this.processGraphData(data);

      // Check if we have any concepts to display
      if (this._allNodes.length === 0) {
        this.error = 'Aucun concept à afficher pour le moment.\n\nCommencez à utiliser Emergence pour créer votre graphe de connaissances !';
        this.renderError();
        this.renderStats();
      } else {
        this.initializePhysics();
        this.startAnimation();
        this.renderStats();
      }
    } catch (error) {
      console.error('[ConceptGraph] Failed to load graph:', error);

      // Check if it's a 404 - endpoint doesn't exist yet
      if (error.message && error.message.includes('404')) {
        this.error = 'Le graphe de concepts n\'est pas encore disponible. Aucune donnée à afficher.';
      } else if (error.message && error.message.includes('401')) {
        this.error = 'Authentification requise. Veuillez vous reconnecter.';
      } else if (error.message && error.message.includes('429')) {
        // Rate limit hit
        this.error = 'Trop de requêtes. Veuillez réessayer dans quelques instants.';
      } else {
        this.error = error.message || 'Erreur lors du chargement du graphe';
      }

      this.renderError();

      // Set empty data to avoid errors
      this._allNodes = [];
      this._allLinks = [];
      this.nodes = [];
      this.links = [];
      this.renderStats();
    } finally {
      this.isLoading = false;
    }
  }

  processGraphData(data) {
    const concepts = data.concepts || data.nodes || [];
    const relations = data.relations || data.links || [];

    // Create nodes
    this._allNodes = concepts.map((concept, index) => ({
      id: concept.id || concept.concept_id || `concept-${index}`,
      label: concept.concept_text || concept.label || 'Concept',
      count: concept.occurrence_count || 1,
      created_at: concept.created_at || null,
      x: Math.random() * this.width,
      y: Math.random() * this.height,
      vx: 0,
      vy: 0,
      radius: Math.min(30, 10 + Math.sqrt(concept.occurrence_count || 1) * 3),
    }));

    // Create links
    this._allLinks = relations.map((rel) => {
      const source = this._allNodes.find(n => n.id === (rel.source_concept_id || rel.source));
      const target = this._allNodes.find(n => n.id === (rel.target_concept_id || rel.target));

      if (source && target) {
        return { source, target, type: rel.type || 'related' };
      }
      return null;
    }).filter(Boolean);

    this.applyFilters();
  }

  initializePhysics() {
    // Simple force-directed layout initialization
    const centerX = this.width / 2;
    const centerY = this.height / 2;

    this.nodes.forEach((node) => {
      const angle = Math.random() * Math.PI * 2;
      const distance = Math.random() * 200;
      node.x = centerX + Math.cos(angle) * distance;
      node.y = centerY + Math.sin(angle) * distance;
    });
  }

  startAnimation() {
    const animate = () => {
      this.updatePhysics();
      this.render();
      this._animationFrame = requestAnimationFrame(animate);
    };
    animate();
  }

  updatePhysics() {
    const damping = 0.8;
    const repulsion = 5000;
    const attraction = 0.01;

    // Reset forces
    this.nodes.forEach(node => {
      node.vx = 0;
      node.vy = 0;
    });

    // Repulsion between nodes
    for (let i = 0; i < this.nodes.length; i++) {
      for (let j = i + 1; j < this.nodes.length; j++) {
        const dx = this.nodes[j].x - this.nodes[i].x;
        const dy = this.nodes[j].y - this.nodes[i].y;
        const distSq = dx * dx + dy * dy;
        const dist = Math.sqrt(distSq) || 1;

        const force = repulsion / distSq;
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;

        this.nodes[i].vx -= fx;
        this.nodes[i].vy -= fy;
        this.nodes[j].vx += fx;
        this.nodes[j].vy += fy;
      }
    }

    // Attraction along links
    this.links.forEach(link => {
      const dx = link.target.x - link.source.x;
      const dy = link.target.y - link.source.y;
      const dist = Math.sqrt(dx * dx + dy * dy) || 1;

      const force = (dist - 100) * attraction;
      const fx = (dx / dist) * force;
      const fy = (dy / dist) * force;

      link.source.vx += fx;
      link.source.vy += fy;
      link.target.vx -= fx;
      link.target.vy -= fy;
    });

    // Apply velocities
    this.nodes.forEach(node => {
      if (node !== this.dragNode) {
        node.x += node.vx * damping;
        node.y += node.vy * damping;

        // Keep in bounds
        node.x = Math.max(node.radius, Math.min(this.width - node.radius, node.x));
        node.y = Math.max(node.radius, Math.min(this.height - node.radius, node.y));
      }
    });
  }

  render() {
    if (!this.ctx) return;

    this.ctx.clearRect(0, 0, this.width, this.height);
    this.ctx.save();

    // Apply zoom and pan
    this.ctx.translate(this.offsetX, this.offsetY);
    this.ctx.scale(this.zoom, this.zoom);

    // Draw links
    this.links.forEach(link => {
      this.ctx.beginPath();
      this.ctx.moveTo(link.source.x, link.source.y);
      this.ctx.lineTo(link.target.x, link.target.y);
      this.ctx.strokeStyle = 'rgba(148, 163, 184, 0.3)';
      this.ctx.lineWidth = 1;
      this.ctx.stroke();
    });

    // Draw nodes
    this.nodes.forEach(node => {
      const isHovered = node === this.hoveredNode;
      const isSelected = node === this.selectedNode;

      this.ctx.beginPath();
      this.ctx.arc(node.x, node.y, node.radius, 0, Math.PI * 2);

      if (isSelected) {
        this.ctx.fillStyle = 'rgba(56, 189, 248, 0.8)';
      } else if (isHovered) {
        this.ctx.fillStyle = 'rgba(56, 189, 248, 0.5)';
      } else {
        this.ctx.fillStyle = 'rgba(15, 23, 42, 0.9)';
      }
      this.ctx.fill();

      this.ctx.strokeStyle = isSelected || isHovered ? '#38bdf8' : 'rgba(148, 163, 184, 0.5)';
      this.ctx.lineWidth = isSelected || isHovered ? 2 : 1;
      this.ctx.stroke();

      // Draw label
      this.ctx.font = `${isHovered || isSelected ? '12px' : '10px'} sans-serif`;
      this.ctx.fillStyle = '#e2e8f0';
      this.ctx.textAlign = 'center';
      this.ctx.textBaseline = 'middle';
      const maxWidth = node.radius * 2 - 4;
      const text = node.label.length > 15 ? node.label.substring(0, 12) + '...' : node.label;
      this.ctx.fillText(text, node.x, node.y, maxWidth);
    });

    this.ctx.restore();
  }

  handleMouseDown(e) {
    const rect = this.canvas.getBoundingClientRect();
    const x = (e.clientX - rect.left - this.offsetX) / this.zoom;
    const y = (e.clientY - rect.top - this.offsetY) / this.zoom;

    const clickedNode = this.findNodeAt(x, y);

    if (clickedNode) {
      this.dragNode = clickedNode;
      this.dragStartX = x;
      this.dragStartY = y;
      this.selectedNode = clickedNode;
      this.updateInfo();
    } else {
      this.isDragging = true;
      this.dragStartX = e.clientX;
      this.dragStartY = e.clientY;
    }
  }

  handleMouseMove(e) {
    const rect = this.canvas.getBoundingClientRect();
    const x = (e.clientX - rect.left - this.offsetX) / this.zoom;
    const y = (e.clientY - rect.top - this.offsetY) / this.zoom;

    if (this.dragNode) {
      this.dragNode.x = x;
      this.dragNode.y = y;
    } else if (this.isDragging) {
      this.offsetX += e.clientX - this.dragStartX;
      this.offsetY += e.clientY - this.dragStartY;
      this.dragStartX = e.clientX;
      this.dragStartY = e.clientY;
    } else {
      const hoveredNode = this.findNodeAt(x, y);
      if (hoveredNode !== this.hoveredNode) {
        this.hoveredNode = hoveredNode;
        this.canvas.style.cursor = hoveredNode ? 'pointer' : 'default';
        this.updateInfo();
      }
    }
  }

  handleMouseUp() {
    this.isDragging = false;
    this.dragNode = null;
  }

  handleWheel(e) {
    e.preventDefault();
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    this.zoom *= delta;
    this.zoom = Math.max(0.1, Math.min(5, this.zoom));
  }

  findNodeAt(x, y) {
    for (let i = this.nodes.length - 1; i >= 0; i--) {
      const node = this.nodes[i];
      const dx = x - node.x;
      const dy = y - node.y;
      const distSq = dx * dx + dy * dy;
      if (distSq <= node.radius * node.radius) {
        return node;
      }
    }
    return null;
  }

  resetView() {
    this.zoom = 1;
    this.offsetX = 0;
    this.offsetY = 0;
  }

  updateInfo() {
    if (!this.infoContainer) return;

    const node = this.hoveredNode || this.selectedNode;

    if (node) {
      const relatedLinks = this.links.filter(link =>
        link.source === node || link.target === node
      );

      const connections = relatedLinks.length;

      // Get related concepts
      const relatedConcepts = relatedLinks.map(link => {
        const related = link.source === node ? link.target : link.source;
        return `<span class="concept-graph__related-item">${related.label}</span>`;
      }).slice(0, 5); // Show max 5

      const hasMore = relatedLinks.length > 5;

      this.infoContainer.innerHTML = `
        <div class="concept-graph__node-info">
          <h4>${node.label}</h4>
          <p><strong>Occurrences:</strong> ${node.count}</p>
          <p><strong>Connexions:</strong> ${connections}</p>
          ${connections > 0 ? `
            <div class="concept-graph__related">
              <strong>Concepts liés:</strong>
              <div class="concept-graph__related-list">
                ${relatedConcepts.join('')}
                ${hasMore ? `<span class="concept-graph__related-more">+${relatedLinks.length - 5} autres</span>` : ''}
              </div>
            </div>
          ` : ''}
        </div>
      `;
    } else {
      this.infoContainer.innerHTML = '';
    }
  }

  renderError() {
    if (!this.errorContainer) return;

    if (this.error) {
      // Preserve line breaks in error messages
      const lines = this.error.split('\n').filter(line => line.trim());
      this.errorContainer.innerHTML = lines.map(line =>
        `<p style="margin: 0.5em 0;">${this.escapeHtml(line)}</p>`
      ).join('');
      this.errorContainer.hidden = false;
    } else {
      this.errorContainer.innerHTML = '';
      this.errorContainer.hidden = true;
    }
  }

  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  applyFilters() {
    // Filter by type (importance based on count)
    let filteredNodes = [...this._allNodes];

    if (this._filterType !== 'all') {
      filteredNodes = filteredNodes.filter(node => {
        if (this._filterType === 'high') return node.count >= 10;
        if (this._filterType === 'medium') return node.count >= 5 && node.count < 10;
        if (this._filterType === 'low') return node.count < 5;
        return true;
      });
    }

    // Filter links to only include those connecting visible nodes
    const nodeIds = new Set(filteredNodes.map(n => n.id));
    const filteredLinks = this._allLinks.filter(link =>
      nodeIds.has(link.source.id) && nodeIds.has(link.target.id)
    );

    this.nodes = filteredNodes;
    this.links = filteredLinks;

    this.initializePhysics();
    this.renderStats();
  }

  renderStats() {
    if (!this.statsContainer) return;

    const totalNodes = this._allNodes.length;
    const visibleNodes = this.nodes.length;
    const totalLinks = this._allLinks.length;
    const visibleLinks = this.links.length;

    this.statsContainer.innerHTML = `
      <div class="concept-graph__stats-content">
        <span class="concept-graph__stat">
          <strong>${visibleNodes}</strong>/${totalNodes} concepts
        </span>
        <span class="concept-graph__stat">
          <strong>${visibleLinks}</strong>/${totalLinks} relations
        </span>
      </div>
    `;
  }
}
