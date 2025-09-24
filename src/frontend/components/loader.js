/**
 * @module ui/loader
 * @description Gestionnaire d'animations de chargement
 */

import { ANIMATIONS, TIMEOUTS } from '../shared/constants.js';

const { CLASSES: ANIMATION_CLASSES } = ANIMATIONS;
const { ANIMATION_EXIT, LOADER_MINIMUM_VISIBLE } = TIMEOUTS;

class LoaderManager {
  constructor() {
    this.loaders = new Map();
    this.globalLoader = null;
    this.init();
  }

  /**
   * Initialize global loader
   */
  init() {
    // Create global loader container
    const container = document.createElement('div');
    container.className = 'global-loader';
    container.innerHTML = `
      <div class="global-loader__spinner">
        <div class="spinner spinner--large"></div>
      </div>
    `;
    document.body.appendChild(container);
    this.globalLoader = container;
  }

  /**
   * Show global loader
   * @param {string} message
   */
  showGlobal(message = '') {
    this.globalLoader.classList.add('global-loader--visible');
    
    if (message) {
      let messageEl = this.globalLoader.querySelector('.global-loader__message');
      if (!messageEl) {
        messageEl = document.createElement('div');
        messageEl.className = 'global-loader__message';
        this.globalLoader.querySelector('.global-loader__spinner').appendChild(messageEl);
      }
      messageEl.textContent = message;
    }
  }

  /**
   * Hide global loader
   */
  hideGlobal() {
    this.globalLoader.classList.remove('global-loader--visible');
  }

  /**
   * Show loader on element
   * @param {HTMLElement|string} target
   * @param {Object} options
   * @returns {string} Loader ID
   */
  show(target, {
    size = 'medium',
    overlay = true,
    message = '',
    blur = false
  } = {}) {
    const element = typeof target === 'string' 
      ? document.querySelector(target) 
      : target;
      
    if (!element) return null;
    
    // Generate ID
    const id = `loader-${Date.now()}`;
    
    // Create loader
    const loader = document.createElement('div');
    loader.className = 'element-loader';
    if (overlay) loader.classList.add('element-loader--overlay');
    if (blur) loader.classList.add('element-loader--blur');
    
    let html = `<div class="spinner spinner--${size}"></div>`;
    if (message) {
      html += `<div class="element-loader__message">${message}</div>`;
    }
    
    loader.innerHTML = html;
    
    // Position loader
    const position = window.getComputedStyle(element).position;
    if (position === 'static') {
      element.style.position = 'relative';
    }
    
    // Add loader
    element.appendChild(loader);
    
    // Disable element
    element.classList.add('loading');
    if (element.tagName === 'BUTTON' || element.tagName === 'INPUT') {
      element.disabled = true;
    }
    
    // Store loader data
    this.loaders.set(id, {
      element,
      loader,
      originalPosition: position
    });
    
    return id;
  }

  /**
   * Hide loader
   * @param {string} id
   */
  hide(id) {
    const data = this.loaders.get(id);
    if (!data) return;
    
    const { element, loader, originalPosition } = data;
    
    // Remove loader
    loader.remove();
    
    // Restore element
    element.classList.remove('loading');
    if (originalPosition === 'static') {
      element.style.position = '';
    }
    if (element.tagName === 'BUTTON' || element.tagName === 'INPUT') {
      element.disabled = false;
    }
    
    // Clean up
    this.loaders.delete(id);
  }

  /**
   * Show skeleton loader
   * @param {HTMLElement|string} target
   * @param {Object} options
   */
  skeleton(target, {
    lines = 3,
    animate = true
  } = {}) {
    const element = typeof target === 'string' 
      ? document.querySelector(target) 
      : target;
      
    if (!element) return;
    
    element.innerHTML = '';
    
    for (let i = 0; i < lines; i++) {
      const line = document.createElement('div');
      line.className = 'skeleton-line';
      if (animate) line.classList.add('skeleton-line--animated');
      
      // Vary widths
      const widths = ['100%', '80%', '90%', '70%', '85%'];
      line.style.width = widths[i % widths.length];
      
      element.appendChild(line);
    }
  }

  /**
   * Progress loader
   * @param {HTMLElement|string} target
   * @param {Object} options
   * @returns {Object} Progress controller
   */
  progress(target, {
    message = 'Chargement...',
    showPercentage = true
  } = {}) {
    const element = typeof target === 'string' 
      ? document.querySelector(target) 
      : target;
      
    if (!element) return null;
    
    // Create progress loader
    const loader = document.createElement('div');
    loader.className = 'progress-loader';
    
    let html = '<div class="progress-loader__bar">';
    html += '<div class="progress-loader__fill"></div>';
    html += '</div>';
    
    if (message || showPercentage) {
      html += '<div class="progress-loader__info">';
      if (message) html += `<span class="progress-loader__message">${message}</span>`;
      if (showPercentage) html += '<span class="progress-loader__percentage">0%</span>';
      html += '</div>';
    }
    
    loader.innerHTML = html;
    element.appendChild(loader);
    
    const fill = loader.querySelector('.progress-loader__fill');
    const percentage = loader.querySelector('.progress-loader__percentage');
    
    // Return controller
    return {
      update(value) {
        const percent = Math.min(100, Math.max(0, value));
        fill.style.width = `${percent}%`;
        if (percentage) percentage.textContent = `${Math.round(percent)}%`;
      },
      
      complete() {
        this.update(100);
        setTimeout(() => {
          loader.classList.add(ANIMATION_CLASSES.FADE_OUT);
          setTimeout(() => loader.remove(), ANIMATION_EXIT);
        }, LOADER_MINIMUM_VISIBLE);
      },
      
      error(message = 'Erreur') {
        loader.classList.add('progress-loader--error');
        if (loader.querySelector('.progress-loader__message')) {
          loader.querySelector('.progress-loader__message').textContent = message;
        }
      }
    };
  }

  /**
   * Dots animation loader
   * @param {HTMLElement|string} target
   * @returns {Function} Stop function
   */
  dots(target) {
    const element = typeof target === 'string' 
      ? document.querySelector(target) 
      : target;
      
    if (!element) return () => {};
    
    const originalText = element.textContent;
    let dots = 0;
    
    const interval = setInterval(() => {
      dots = (dots + 1) % 4;
      element.textContent = originalText + '.'.repeat(dots);
    }, 500);
    
    return () => {
      clearInterval(interval);
      element.textContent = originalText;
    };
  }
}

// Export singleton instance
export const loader = new LoaderManager();

// Also export for custom usage
export { LoaderManager };

