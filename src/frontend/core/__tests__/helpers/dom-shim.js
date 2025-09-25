const globalScope = typeof globalThis !== 'undefined' ? globalThis : global;

function ensureDocument() {
  if (typeof globalScope.document !== 'undefined') return;
  const noop = () => {};
  const classList = { add: noop, remove: noop, contains: () => false };
  const body = {
    appendChild: noop,
    removeChild: noop,
    querySelector: () => null,
    querySelectorAll: () => [],
    classList,
  };
  const createElement = () => ({
    setAttribute: noop,
    removeAttribute: noop,
    appendChild: noop,
    removeChild: noop,
    querySelector: () => null,
    querySelectorAll: () => [],
    classList: { add: noop, remove: noop },
    style: {},
    hidden: false,
  });

  globalScope.document = {
    getElementById: () => null,
    getElementsByClassName: () => [],
    querySelector: () => null,
    querySelectorAll: () => [],
    createElement,
    addEventListener: noop,
    removeEventListener: noop,
    body,
    documentElement: body,
  };
}

function ensureWindow() {
  if (typeof globalScope.window !== 'undefined') return;
  const noop = () => {};
  globalScope.window = {
    addEventListener: noop,
    removeEventListener: noop,
    dispatchEvent: noop,
    CustomEvent: globalScope.CustomEvent,
    location: { hostname: 'localhost' },
    localStorage: {
      getItem: () => null,
      setItem: noop,
      removeItem: noop,
    },
    sessionStorage: {
      getItem: () => null,
      setItem: noop,
      removeItem: noop,
    },
    matchMedia: () => ({ matches: false, addEventListener: noop, removeEventListener: noop }),
  };
}

function ensureNavigator() {
  if (typeof globalScope.navigator !== 'undefined') return;
  Object.defineProperty(globalScope, 'navigator', {
    configurable: true,
    enumerable: false,
    writable: true,
    value: {
      language: 'fr-FR',
      languages: ['fr-FR'],
      userAgent: 'node-test',
      platform: 'node',
    },
  });
}

ensureDocument();
ensureWindow();
ensureNavigator();
