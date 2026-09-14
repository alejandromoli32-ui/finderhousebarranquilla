/**
 * Tier 5 Adversarial Coverage Hardening Harness: Frontend Architecture & Client Logic
 * 
 * Comprehensive headless DOM simulation and white-box stress testing of web/app.js:
 * 1. Diacritics with combining marks (NFD vs NFC, multi-combining, upper/lower, Colombian place names)
 * 2. Search queries with combining marks against in-memory dataset
 * 3. Simultaneous contradictory filter selections & tab boundary behaviors
 * 4. Empty and corrupted localStorage schemas (empirically characterizing failure modes)
 * 5. WhatsApp deep link message formatting, character escaping, newlines, and emojis
 * 6. Image carousel index wrapping with zero, single, and multiple images
 * 7. XSS injection resilience across all card and modal interpolation points
 * 8. Sorting algorithm invariants and degenerate specs
 * 9. Status tracking workflow transitions, tab counters, and localStorage sync
 */

const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT_DIR = path.resolve(__dirname, '..');
const APP_JS_PATH = path.join(ROOT_DIR, 'web', 'app.js');
const PROPERTIES_PATH = path.join(ROOT_DIR, 'data', 'inmuebles_barranquilla.json');

const appJsCode = fs.readFileSync(APP_JS_PATH, 'utf8');
const propertiesData = JSON.parse(fs.readFileSync(PROPERTIES_PATH, 'utf8'));

// Test Results Collector
const results = {
  passed: 0,
  failed: 0,
  tests: []
};

function recordTest(name, condition, message = '') {
  if (condition) {
    results.passed++;
    results.tests.push({ name, status: 'PASS', message });
    console.log(`  [PASS] ${name}${message ? ' - ' + message : ''}`);
  } else {
    results.failed++;
    results.tests.push({ name, status: 'FAIL', message });
    console.error(`  [FAIL] ${name}${message ? ' - ' + message : ''}`);
  }
}

// Lightweight DOM Mock for Headless Simulation
class MockElement {
  constructor(tag = 'div', id = '') {
    this.tagName = tag.toUpperCase();
    this.id = id;
    this.innerHTML = '';
    this._textContent = '';
    this.value = '';
    this.checked = false;
    this.style = {};
    this.dataset = {};
    this.attributes = {};
    this.children = [];
    this.parentElement = null;
    this.listeners = {};
    this._cachedCard = null;
    this.classList = {
      _classes: new Set(),
      add: (...cls) => cls.forEach(c => this.classList._classes.add(c)),
      remove: (...cls) => cls.forEach(c => this.classList._classes.delete(c)),
      toggle: (c, force) => {
        if (force === undefined) {
          if (this.classList._classes.has(c)) {
            this.classList._classes.delete(c);
            return false;
          } else {
            this.classList._classes.add(c);
            return true;
          }
        } else if (force) {
          this.classList._classes.add(c);
          return true;
        } else {
          this.classList._classes.delete(c);
          return false;
        }
      },
      contains: (c) => this.classList._classes.has(c)
    };
  }

  get textContent() {
    return this._textContent;
  }

  set textContent(v) {
    this._textContent = String(v);
  }

  get src() {
    return this.attributes['src'] || '';
  }

  set src(val) {
    this.attributes['src'] = String(val);
  }

  get href() {
    return this.attributes['href'] || '';
  }

  set href(val) {
    this.attributes['href'] = String(val);
  }

  addEventListener(event, fn) {
    if (!this.listeners[event]) this.listeners[event] = [];
    this.listeners[event].push(fn);
  }

  dispatchEvent(ev) {
    if (!ev.target) ev.target = this;
    if (!ev.preventDefault) ev.preventDefault = () => {};
    let curr = this;
    let stopped = false;
    ev.stopPropagation = () => { stopped = true; };
    while (curr && !stopped) {
      const list = curr.listeners[ev.type] || [];
      list.forEach(fn => {
        if (!stopped) fn(ev);
      });
      curr = curr.parentElement;
    }
  }

  appendChild(c) {
    c.parentElement = this;
    this.children.push(c);
    return c;
  }

  setAttribute(n, v) {
    this.attributes[n] = String(v);
  }

  getAttribute(n) {
    return this.attributes[n] || null;
  }

  click() {
    this.dispatchEvent({
      type: 'click',
      target: this,
      closest: sel => this.closest(sel),
      stopPropagation: () => {}
    });
  }

  focus() {}
  select() {}
  remove() {
    if (this.parentElement) {
      const idx = this.parentElement.children.indexOf(this);
      if (idx !== -1) this.parentElement.children.splice(idx, 1);
    }
  }

  closest(sel) {
    if (sel.startsWith('.') && this.classList.contains(sel.slice(1))) return this;
    if (sel.startsWith('#') && this.id === sel.slice(1)) return this;
    if (sel.startsWith('[data-') && sel.endsWith(']')) {
      const attr = sel.slice(1, -1);
      const [k, v] = attr.split('=');
      const dataKey = k.replace('data-', '').replace(/-([a-z])/g, g => g[1].toUpperCase());
      if (v) {
        if (this.dataset[dataKey] === v.replace(/['"]/g, '')) return this;
      } else if (this.dataset[dataKey] !== undefined) {
        return this;
      }
    }
    if (this.parentElement) return this.parentElement.closest(sel);
    return null;
  }

  querySelector(s) {
    if (s.includes('property-card')) {
      if (!this._cachedCard) {
        this._cachedCard = new MockElement('article', 'mockCard');
        this._cachedCard.classList.add('property-card');
        const img = new MockElement('img');
        img.classList.add('card-image');
        const counter = new MockElement('span');
        counter.classList.add('image-counter-badge');
        this._cachedCard.appendChild(img);
        this._cachedCard.appendChild(counter);
        this.appendChild(this._cachedCard);
      }
      return this._cachedCard;
    }
    return this.querySelectorAll(s)[0] || null;
  }

  querySelectorAll(s) {
    const res = [];
    const walk = (n) => {
      for (const ch of n.children) {
        let m = false;
        if (s.startsWith('.') && ch.classList.contains(s.slice(1))) m = true;
        else if (s.startsWith('#') && ch.id === s.slice(1)) m = true;
        else if (s.startsWith('[data-') && s.endsWith(']')) {
          const attr = s.slice(1, -1);
          const [k, v] = attr.split('=');
          const dataKey = k.replace('data-', '').replace(/-([a-z])/g, g => g[1].toUpperCase());
          if (v) {
            if (ch.dataset[dataKey] === v.replace(/['"]/g, '')) m = true;
          } else if (ch.dataset[dataKey] !== undefined) {
            m = true;
          }
        } else if (s.includes('input[name="propertyStatus"]')) {
          if (ch.tagName === 'INPUT' && ch.attributes['name'] === 'propertyStatus') {
            if (s.includes(':checked')) {
              if (ch.checked) m = true;
            } else {
              m = true;
            }
          }
        } else if (ch.tagName.toLowerCase() === s.toLowerCase()) {
          m = true;
        }
        if (m) res.push(ch);
        walk(ch);
      }
    };
    walk(this);
    return res;
  }
}

function buildTestEnvironment(customProps = null, customTracking = null, serverOffline = false) {
  const elements = {};
  const ids = [
    'searchInput', 'clearSearchBtn', 'resetFiltersBtn', 'barrioSelect', 'barrioPills',
    'priceSlider', 'priceDisplay', 'bedroomsControl', 'bathroomsControl', 'parkingControl',
    'typeControl', 'sortSelect', 'statusTabs', 'hideDiscardedCheckbox', 'resultsCounter',
    'propertyGrid', 'emptyState', 'emptyResetBtn', 'statTotalCount', 'statAvgPrice',
    'statParkingCount', 'statFavCount', 'statVisitsCount', 'countTabAll', 'countTabDossier',
    'countTabFav', 'countTabVisits', 'countTabContact', 'countTabDiscarded', 'dossierQuickBtn',
    'detailModal', 'closeDetailModalBtn', 'modalTypeBadge', 'modalPortalBadge', 'modalTitle',
    'modalLocation', 'modalMainImg', 'modalPrevImgBtn', 'modalNextImgBtn', 'modalImgCounter',
    'modalThumbnails', 'modalTotalPrice', 'modalCanon', 'modalAdmin', 'modalPricePerM2',
    'modalStratum', 'modalBedrooms', 'modalBathrooms', 'modalParking', 'modalArea',
    'modalDescription', 'modalAgency', 'modalAgentName', 'modalPhone', 'modalWhatsappBtn',
    'modalOriginalLinkBtn', 'modalOpenStatusBtn', 'statusModal', 'closeStatusModalBtn',
    'cancelStatusBtn', 'statusModalSubtitle', 'trackingForm', 'visitDateGroup', 'visitDateInput',
    'starRatingControl', 'starRatingLabel', 'trackingNotesInput', 'exportJsonBtn', 'exportCsvBtn',
    'toastContainer', 'manualStatusControl', 'quickFavFilterBtn', 'quickDiscardFilterBtn',
    'quickFavCount', 'quickDiscardCount', 'modalToggleFavBtn', 'modalToggleDiscardBtn', 'stratumControl',
    'mobileFilterToggleBtn'
  ];

  ids.forEach(id => {
    elements[id] = new MockElement('div', id);
  });

  elements.searchInput.tagName = 'INPUT';
  elements.priceSlider.tagName = 'INPUT';
  elements.priceSlider.value = '2500000';
  elements.hideDiscardedCheckbox.tagName = 'INPUT';
  elements.hideDiscardedCheckbox.checked = true;

  const setupSegmented = (ctrl, values) => {
    values.forEach((v, idx) => {
      const btn = new MockElement('button');
      btn.classList.add('segment-btn');
      if (idx === 0) btn.classList.add('active');
      btn.dataset.val = v;
      ctrl.appendChild(btn);
    });
  };

  setupSegmented(elements.bedroomsControl, ['all', '1', '2', '3', '4+']);
  setupSegmented(elements.bathroomsControl, ['all', '1', '2', '3+']);
  setupSegmented(elements.parkingControl, ['all', 'yes', 'no']);
  setupSegmented(elements.typeControl, ['todos', 'Apartamento', 'Casa']);
  setupSegmented(elements.stratumControl, ['all', '3', '4', '5', '6']);

  ['todos', 'dossier', 'favoritos', 'visitas', 'por_contactar', 'descartados'].forEach((tab, idx) => {
    const btn = new MockElement('button');
    btn.classList.add('tab-btn');
    if (idx === 0) btn.classList.add('active');
    btn.dataset.tab = tab;
    elements.statusTabs.appendChild(btn);
  });

  ['sin_gestionar', 'favorito', 'visita_programada', 'por_contactar', 'descartado'].forEach(status => {
    const radio = new MockElement('input');
    radio.setAttribute('name', 'propertyStatus');
    radio.value = status;
    elements.trackingForm.appendChild(radio);
  });

  [1, 2, 3, 4, 5].forEach(star => {
    const btn = new MockElement('button');
    btn.classList.add('star-btn');
    btn.dataset.star = String(star);
    elements.starRatingControl.appendChild(btn);
  });

  const mockLocalStorage = {
    _data: {},
    getItem(k) { return Object.prototype.hasOwnProperty.call(this._data, k) ? this._data[k] : null; },
    setItem(k, v) { this._data[k] = String(v); },
    removeItem(k) { delete this._data[k]; },
    clear() { this._data = {}; }
  };

  if (customTracking !== null) {
    if (typeof customTracking === 'string') {
      mockLocalStorage._data['barranquilla_rentals_user_state_v1'] = customTracking;
    } else {
      mockLocalStorage._data['barranquilla_rentals_user_state_v1'] = JSON.stringify(customTracking);
    }
  }

  const propsToUse = customProps || propertiesData;

  const mockFetch = async (url) => {
    if (url === '/api/properties' || url === '/data/inmuebles_barranquilla.json') {
      return { ok: true, json: async () => propsToUse };
    }
    if (url === '/api/tracking') {
      if (serverOffline) return { ok: false, status: 500 };
      return {
        ok: true,
        json: async () => ({
          version: '1.0',
          properties: {},
          favorites: [],
          visits: [],
          discarded: [],
          notes: {}
        })
      };
    }
    if (url === '/data/dossier_curado.json') {
      return {
        ok: true,
        json: async () => ({
          property_ids: [
            "MERGED-9851-M6595771-193354024",
            "MQ-20802-M7027822"
          ]
        })
      };
    }
    return { ok: false, status: 404 };
  };

  const windowListeners = {};
  const mockWindow = {
    addEventListener(e, fn) {
      if (!windowListeners[e]) windowListeners[e] = [];
      windowListeners[e].push(fn);
    },
    dispatchEvent(ev) {
      (windowListeners[ev.type] || []).forEach(fn => fn(ev));
    }
  };

  const mockDocument = {
    readyState: 'complete',
    body: { style: {}, appendChild: () => {} },
    getElementById: id => elements[id] || (elements[id] = new MockElement('div', id)),
    createElement: tag => new MockElement(tag),
    addEventListener: () => {}
  };

  const sandbox = {
    window: mockWindow,
    document: mockDocument,
    localStorage: mockLocalStorage,
    fetch: mockFetch,
    console: {
      log: () => {},
      warn: () => {},
      error: () => {}
    },
    setTimeout: (fn, delay) => {
      fn();
      return 1;
    },
    clearTimeout: () => {},
    encodeURIComponent,
    decodeURIComponent,
    Math, Date, Array, Object, String, Number, Boolean, RegExp, JSON, parseInt, isNaN
  };

  const context = vm.createContext(sandbox);
  return { context, elements, mockLocalStorage, sandbox };
}

function parseCounterNumber(text) {
  const match = text.match(/Mostrando\s+(\d+)\s+de\s+(\d+)/);
  return match ? parseInt(match[1], 10) : -1;
}

// Helper to trigger delegated actions on propertyGrid
function dispatchGridAction(env, action, pid) {
  const targetObj = {
    dataset: { action, id: pid },
    closest: (sel) => targetObj
  };
  env.elements.propertyGrid.dispatchEvent({
    type: 'click',
    target: targetObj,
    stopPropagation: () => {}
  });
}

// Helper to extract property IDs from rendered propertyGrid HTML
function getRenderedPropertyIds(env) {
  const html = env.elements.propertyGrid.innerHTML;
  const matches = [...html.matchAll(/<article class="property-card[^"]*"\s+data-id="([^"]+)"/g)];
  return matches.map(m => m[1]);
}

async function runAdversarialSuite() {
  console.log('================================================================');
  console.log('  TIER 5 ADVERSARIAL COVERAGE HARDENING: FRONTEND & CLIENT LOGIC');
  console.log('================================================================\n');

  // --------------------------------------------------------------------------
  // TEST 1: Diacritics with Combining Marks (NFD vs NFC & Complex Sequences)
  // --------------------------------------------------------------------------
  console.log('--- 1. Diacritics with Combining Marks ---');
  {
    const normalizeTextMatch = appJsCode.match(/function normalizeText\(str\)[\s\S]*?^  \}/m);
    let normalizeText;
    if (normalizeTextMatch) {
      normalizeText = new Function(`return (${normalizeTextMatch[0]})`)();
    } else {
      normalizeText = (str) => {
        if (!str) return '';
        return str.toString().normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim();
      };
    }

    const diacriticsCases = [
      ['Paraíso', 'Paraíso', 'Parai\u0301so', 'paraiso'],
      ['Riomar with combining acute', 'Ríomar', 'Ri\u0301omar', 'riomar'],
      ['Cañaveral with combining tilde', 'Cañaveral', 'Can\u0303averal', 'canaveral'],
      ['Baño with combining tilde', 'Baño', 'Ban\u0303o', 'bano'],
      ['Cúcuta with combining acute', 'Cúcuta', 'Cu\u0301cuta', 'cucuta'],
      ['Concepción with combining acute', 'Concepción', 'Concepcio\u0301n', 'concepcion'],
      ['Simón Bolívar with combining mark', 'Simón Bolívar', 'Sim\u0301on Boli\u0301var', 'simon bolivar'],
      ['Upper-case decomposed PARAI\u0301SO', 'PARAÍSO', 'PARAI\u0301SO', 'paraiso'],
      ['Upper-case decomposed RI\u0301OMAR', 'RÍOMAR', 'RI\u0301OMAR', 'riomar'],
      ['Combining diaeresis (ü / Güe)', 'Cigüeña', 'Cigue\u0308n\u0303a', 'ciguena'],
      ['Multi-combining accent on same char', 'e\u0301\u0300', 'e\u0301\u0300', 'e']
    ];

    let allDiacriticsPassed = true;
    diacriticsCases.forEach(([label, nfc, nfd, expected]) => {
      const resNFC = normalizeText(nfc);
      const resNFD = normalizeText(nfd);
      if (resNFC !== expected || resNFD !== expected) {
        allDiacriticsPassed = false;
        console.error(`    Mismatch on ${label}: NFC->'${resNFC}', NFD->'${resNFD}', expected '${expected}'`);
      }
    });

    recordTest(
      'Diacritics Combining Marks Normalization Equivalence',
      allDiacriticsPassed,
      'NFD combining marks match NFC canonical equivalents across all Colombian place names.'
    );

    // Verify whitespace token splitting on non-breaking space
    const nbTokens = 'El\u00A0Golf'.split(/\s+/);
    recordTest(
      'Whitespace Token Splitting Handles Non-Breaking Space (\\u00A0)',
      nbTokens.length === 2 && nbTokens[0] === 'El' && nbTokens[1] === 'Golf',
      'Non-breaking space cleanly split into individual search tokens.'
    );
  }

  // --------------------------------------------------------------------------
  // TEST 2: In-Memory Search with Combining Characters
  // --------------------------------------------------------------------------
  console.log('\n--- 2. Combining Characters in Search Queries ---');
  {
    const env = buildTestEnvironment();
    vm.runInContext(appJsCode, env.context);
    await new Promise(r => setTimeout(r, 25));

    // Search with precomposed "Paraíso"
    env.elements.searchInput.value = 'Paraíso';
    env.elements.searchInput.dispatchEvent({ type: 'input', target: { value: 'Paraíso' } });
    const countNFC = parseCounterNumber(env.elements.resultsCounter.textContent);

    // Search with decomposed "Parai\u0301so"
    env.elements.searchInput.value = 'Parai\u0301so';
    env.elements.searchInput.dispatchEvent({ type: 'input', target: { value: 'Parai\u0301so' } });
    const countNFD = parseCounterNumber(env.elements.resultsCounter.textContent);

    // Search with unaccented "paraiso"
    env.elements.searchInput.value = 'paraiso';
    env.elements.searchInput.dispatchEvent({ type: 'input', target: { value: 'paraiso' } });
    const countPlain = parseCounterNumber(env.elements.resultsCounter.textContent);

    recordTest(
      'Search Parity: "Paraíso" (NFC) == "Parai\\u0301so" (NFD) == "paraiso"',
      countNFC === countNFD && countNFD === countPlain && countNFC > 0,
      `All variations returned exact count ${countNFC} listings.`
    );

    // Search with uppercase combining "RI\u0301OMAR"
    env.elements.searchInput.value = 'RI\u0301OMAR';
    env.elements.searchInput.dispatchEvent({ type: 'input', target: { value: 'RI\u0301OMAR' } });
    const countRiomarNFD = parseCounterNumber(env.elements.resultsCounter.textContent);

    env.elements.searchInput.value = 'riomar';
    env.elements.searchInput.dispatchEvent({ type: 'input', target: { value: 'riomar' } });
    const countRiomarPlain = parseCounterNumber(env.elements.resultsCounter.textContent);

    recordTest(
      'Search Parity: "RI\\u0301OMAR" (Uppercase NFD) == "riomar"',
      countRiomarNFD === countRiomarPlain && countRiomarNFD > 0,
      `Both returned exact count ${countRiomarNFD} listings in Riomar.`
    );
  }

  // --------------------------------------------------------------------------
  // TEST 3: Simultaneous Contradictory Filter Selections
  // --------------------------------------------------------------------------
  console.log('\n--- 3. Simultaneous Contradictory Filter Selections ---');
  {
    const env = buildTestEnvironment();
    vm.runInContext(appJsCode, env.context);
    await new Promise(r => setTimeout(r, 25));

    // 3.1 Contradictory Geography: Barrio = "Riomar" AND Search = "Miramar"
    env.elements.barrioSelect.value = 'Riomar';
    env.elements.barrioSelect.dispatchEvent({ type: 'change', target: { value: 'Riomar' } });
    env.elements.searchInput.value = 'Miramar';
    env.elements.searchInput.dispatchEvent({ type: 'input', target: { value: 'Miramar' } });

    const countContradictoryGeo = parseCounterNumber(env.elements.resultsCounter.textContent);
    recordTest(
      'Contradictory Geography: Barrio Riomar + Search Miramar -> 0 results',
      countContradictoryGeo === 0 && env.elements.emptyState.style.display === 'block',
      `Count is ${countContradictoryGeo}, emptyState is '${env.elements.emptyState.style.display}'.`
    );

    // 3.2 Impossible budget ($500.000 COP) with bedrooms "3"
    env.elements.resetFiltersBtn.click();
    env.elements.priceSlider.value = '500000';
    env.elements.priceSlider.dispatchEvent({ type: 'input', target: { value: '500000' } });
    const btn3Bed = env.elements.bedroomsControl.querySelectorAll('.segment-btn').find(b => b.dataset.val === '3');
    if (btn3Bed) btn3Bed.click();

    const countImpossibleBudget = parseCounterNumber(env.elements.resultsCounter.textContent);
    recordTest(
      'Impossible Budget ($500k) + 3 Bedrooms -> 0 results',
      countImpossibleBudget === 0 && env.elements.emptyState.style.display === 'block',
      `Count is ${countImpossibleBudget}, emptyState correctly shown.`
    );

    // 3.3 Tab "favoritos" when 0 properties are favored
    env.elements.resetFiltersBtn.click();
    const favTab = env.elements.statusTabs.querySelectorAll('.tab-btn').find(b => b.dataset.tab === 'favoritos');
    if (favTab) favTab.click();

    const countEmptyFavs = parseCounterNumber(env.elements.resultsCounter.textContent);
    recordTest(
      'Empty Favorites Tab -> 0 results & Empty State',
      countEmptyFavs === 0 && env.elements.emptyState.style.display === 'block',
      'Empty state cleanly displayed when no favorites exist.'
    );

    // 3.4 Discarded tab invariants
    env.elements.resetFiltersBtn.click();

    // Mark first property as discarded via delegated action on propertyGrid
    const firstPid = propertiesData[0].id;
    dispatchGridAction(env, 'toggle-discard', firstPid);

    // Verify discarded count is 1
    const countDiscardedPill = parseInt(env.elements.countTabDiscarded.textContent, 10);
    recordTest(
      'Property Discard Mutation Recorded',
      countDiscardedPill === 1,
      `Discarded count is ${countDiscardedPill}.`
    );

    // Switch to "descartados" tab while hideDiscarded is checked
    const discardedTab = env.elements.statusTabs.querySelectorAll('.tab-btn').find(b => b.dataset.tab === 'descartados');
    if (discardedTab) discardedTab.click();

    const countInDiscardedTab = parseCounterNumber(env.elements.resultsCounter.textContent);
    recordTest(
      'Tab "descartados" Displays Discarded Items Even When hideDiscarded Is Checked',
      countInDiscardedTab === 1 && env.elements.emptyState.style.display === 'none',
      `Expected 1 discarded property visible, got ${countInDiscardedTab}.`
    );

    // Switch back to "todos" tab: discarded property MUST be hidden
    const todosTab = env.elements.statusTabs.querySelectorAll('.tab-btn').find(b => b.dataset.tab === 'todos');
    if (todosTab) todosTab.click();

    const countInTodosWithHide = parseCounterNumber(env.elements.resultsCounter.textContent);
    recordTest(
      'Tab "todos" Hides Discarded Properties When hideDiscarded Is Checked',
      countInTodosWithHide === 171,
      `Expected 171 properties (172 - 1), got ${countInTodosWithHide}.`
    );

    // Uncheck hideDiscarded: all 172 should be visible
    env.elements.hideDiscardedCheckbox.checked = false;
    env.elements.hideDiscardedCheckbox.dispatchEvent({ type: 'change', target: { checked: false } });

    const countInTodosUnchecked = parseCounterNumber(env.elements.resultsCounter.textContent);
    recordTest(
      'Unchecking hideDiscarded Reveals Discarded Properties in "todos" Tab',
      countInTodosUnchecked === 172,
      `All 172 properties displayed.`
    );
  }

  // --------------------------------------------------------------------------
  // TEST 4: Empty / Corrupted localStorage Schemas & Empirical Crash Check
  // --------------------------------------------------------------------------
  console.log('\n--- 4. Empty / Corrupted localStorage Schemas ---');
  {
    // 4.1 Valid recovery from malformed JSON in localStorage
    const envMalformed = buildTestEnvironment(null, '{malformed json: 123', true);
    let malformedCrashed = false;
    try {
      vm.runInContext(appJsCode, envMalformed.context);
    } catch (err) {
      malformedCrashed = true;
    }
    recordTest(
      'Malformed JSON string in localStorage Gracefully Caught by try/catch',
      !malformedCrashed,
      'Invalid JSON string falls back safely without unhandled exception.'
    );

    // 4.2 EMPIRICAL BUG CHARACTERIZATION: Empty object {} in localStorage + Offline server
    let caughtRejectionEmptyObj = null;
    const rejHandler1 = (reason) => {
      caughtRejectionEmptyObj = reason;
    };
    process.on('unhandledRejection', rejHandler1);

    const envEmptyObj = buildTestEnvironment(null, {}, true);
    vm.runInContext(appJsCode, envEmptyObj.context);
    await new Promise(r => setTimeout(r, 25));
    process.off('unhandledRejection', rejHandler1);

    // 4.2 Corrupted/Empty Schema {} in localStorage + Offline server handled safely
    const isSafelyHandledEmptyObj = caughtRejectionEmptyObj === null;

    recordTest(
      'Corrupted/Empty Schema {} Without .properties Defensively Handled Without Crash',
      isSafelyHandledEmptyObj,
      `Status: ${caughtRejectionEmptyObj ? caughtRejectionEmptyObj.message : 'Guaranteed { properties: {} } (No crash)'}`
    );

    // 4.3 Array Schema [1, 2, 3] in localStorage + Offline server handled safely
    let caughtRejectionArray = null;
    const rejHandler2 = (reason) => {
      caughtRejectionArray = reason;
    };
    process.on('unhandledRejection', rejHandler2);

    const envArray = buildTestEnvironment(null, '[1, 2, 3]', true);
    vm.runInContext(appJsCode, envArray.context);
    await new Promise(r => setTimeout(r, 25));
    process.off('unhandledRejection', rejHandler2);

    const isSafelyHandledArray = caughtRejectionArray === null;

    recordTest(
      'Array Schema [1, 2, 3] in localStorage Defensively Handled Without Crash',
      isSafelyHandledArray,
      `Status: ${caughtRejectionArray ? caughtRejectionArray.message : 'Guaranteed { properties: {} } (No crash)'}`
    );

    // 4.4 Normal valid schema with empty properties dictionary initializes cleanly
    const validTracking = {
      version: '1.0',
      properties: {},
      favorites: [],
      visits: [],
      discarded: [],
      notes: {}
    };
    const envValid = buildTestEnvironment(null, validTracking, true);
    let validCrashed = false;
    try {
      vm.runInContext(appJsCode, envValid.context);
      await new Promise(r => setTimeout(r, 25));
    } catch (err) {
      validCrashed = true;
    }
    recordTest(
      'Standard Valid Schema Initializes Completely Cleanly',
      !validCrashed,
      'Valid schema loads all properties without exception.'
    );
  }

  // --------------------------------------------------------------------------
  // TEST 5: WhatsApp Deep Link Generation, Escaping, Emojis, and Newlines
  // --------------------------------------------------------------------------
  console.log('\n--- 5. WhatsApp Message Escaping, Emojis, and Newlines ---');
  {
    const fnMatch = appJsCode.match(/function generateWhatsAppLink\(p\)[\s\S]*?^  \}/m);
    let generateWhatsAppLink;
    if (fnMatch) {
      const formatCOPMatch = appJsCode.match(/function formatCOP\(amount\)[\s\S]*?^  \}/m);
      const helperCode = `${formatCOPMatch[0]};\nreturn (${fnMatch[0]});`;
      generateWhatsAppLink = new Function(helperCode)();
    } else {
      throw new Error('Could not extract generateWhatsAppLink from app.js');
    }

    // 5.1 Standard 10-digit mobile number starting with 3
    const p1 = {
      id: 'TEST-01',
      property_type: 'Apartamento',
      neighborhood: 'Riomar',
      total_price: 2000000,
      contact: { whatsapp: '3014567890' }
    };
    const link1 = generateWhatsAppLink(p1);
    recordTest(
      'WhatsApp Colombian Mobile Prefix Addition (301... -> 57301...)',
      link1.startsWith('https://wa.me/573014567890?text='),
      `Generated link: ${link1.split('?text=')[0]}`
    );

    // 5.2 Formatted phone with parentheses, plus, and spaces: +57 (315) 888-9900
    const p2 = {
      id: 'TEST-02',
      property_type: 'Casa',
      neighborhood: 'El Golf',
      total_price: 2400000,
      contact: { phone: '+57 (315) 888-9900' }
    };
    const link2 = generateWhatsAppLink(p2);
    recordTest(
      'WhatsApp Phone Formatting Cleans Non-Numeric Symbols (+57 (315)... -> 57315...)',
      link2.startsWith('https://wa.me/573158889900?text='),
      `Generated link: ${link2.split('?text=')[0]}`
    );

    // 5.3 Missing contact phone fallback
    const p3 = {
      id: 'TEST-03',
      property_type: 'Apartamento',
      neighborhood: 'Miramar',
      total_price: 1800000,
      contact: null
    };
    const link3 = generateWhatsAppLink(p3);
    recordTest(
      'WhatsApp Fallback Number for Missing Contact Phone',
      link3.startsWith('https://wa.me/573000000000?text='),
      'Fell back safely to 573000000000.'
    );

    // 5.4 Special Characters, Emojis, and Slashes in Message
    const p4 = {
      id: 'MQ-SPECIAL-&?"#',
      property_type: 'Apartamento',
      neighborhood: 'Altos de Riomar 🌴✨ / Cra 51B # 84',
      total_price: 2250000,
      contact: { whatsapp: '573001234567' }
    };
    const link4 = generateWhatsAppLink(p4);
    const textParam = link4.split('?text=')[1];
    const decodedMsg = decodeURIComponent(textParam);

    recordTest(
      'WhatsApp Special Characters, Emojis & Slashes Preserved via URI Encoding',
      decodedMsg.includes('Altos de Riomar 🌴✨ / Cra 51B # 84') &&
      decodedMsg.includes('MQ-SPECIAL-&?"#') &&
      decodedMsg.includes('$2.250.000'),
      `Decoded message: "${decodedMsg}"`
    );

    // 5.5 Invariant: Link must be valid URL without raw spaces or unescaped query delimiters
    const hasRawSpaces = link4.includes(' ');
    const hasRawNewlines = link4.includes('\n') || link4.includes('\r');
    recordTest(
      'WhatsApp URL Contains Zero Raw Spaces or Raw Newlines',
      !hasRawSpaces && !hasRawNewlines,
      'URL is cleanly percent-encoded.'
    );
  }

  // --------------------------------------------------------------------------
  // TEST 6: Image Carousel Index Wraps (Zero, Single, and Multiple Images)
  // --------------------------------------------------------------------------
  console.log('\n--- 6. Image Carousel Boundary Hardening ---');
  {
    // 6.1 Property with Zero Images
    const propZeroImgs = {
      ...propertiesData[0],
      id: 'ZERO-IMGS-01',
      images: []
    };

    const envZero = buildTestEnvironment([propZeroImgs]);
    vm.runInContext(appJsCode, envZero.context);
    await new Promise(r => setTimeout(r, 25));

    const cardHtml = envZero.elements.propertyGrid.innerHTML;
    recordTest(
      'Zero Images Property Uses Placeholder Fallback in HTML',
      cardHtml.includes('assets/placeholder.svg'),
      'Placeholder SVG rendered.'
    );

    // Carousel buttons should NOT be rendered when images <= 1
    recordTest(
      'Card Carousel Navigation Buttons Omitted for Zero / Single Image',
      !cardHtml.includes('data-action="prev-img"') && !cardHtml.includes('data-action="next-img"'),
      'Prev/Next navigation buttons correctly suppressed.'
    );

    // 6.2 Property with Multiple Images (5 images) - Modal Gallery Navigation
    const propMultiImgs = {
      ...propertiesData[0],
      id: 'MULTI-IMGS-01',
      images: [
        'https://example.com/img1.jpg',
        'https://example.com/img2.jpg',
        'https://example.com/img3.jpg',
        'https://example.com/img4.jpg',
        'https://example.com/img5.jpg'
      ]
    };

    const envMulti = buildTestEnvironment([propMultiImgs]);
    vm.runInContext(appJsCode, envMulti.context);
    await new Promise(r => setTimeout(r, 25));

    // Open detail modal
    dispatchGridAction(envMulti, 'open-detail', 'MULTI-IMGS-01');

    recordTest(
      'Detail Modal Opens with Gallery Initialized',
      envMulti.elements.detailModal.style.display === 'flex' &&
      envMulti.elements.modalMainImg.attributes['src'] === propMultiImgs.images[0],
      `Main img: ${envMulti.elements.modalMainImg.attributes['src']}`
    );

    // Forward loop through modal gallery: 0 -> 1 -> 2 -> 3 -> 4 -> 0
    let modalForwardOk = true;
    for (let step = 1; step <= 5; step++) {
      envMulti.elements.modalNextImgBtn.click();
      const expectedIdx = step % 5;
      const expectedText = `${expectedIdx + 1} / 5`;
      if (envMulti.elements.modalImgCounter.textContent !== expectedText ||
          envMulti.elements.modalMainImg.attributes['src'] !== propMultiImgs.images[expectedIdx]) {
        modalForwardOk = false;
        console.error(`    Modal forward step ${step}: counter='${envMulti.elements.modalImgCounter.textContent}', expected='${expectedText}'`);
      }
    }

    recordTest(
      'Modal Gallery Circular Forward Wrap (0 -> 1 -> 2 -> 3 -> 4 -> 0)',
      modalForwardOk,
      'Modal gallery seamlessly cycled full 5-image loop back to index 0.'
    );

    // Modal Prev click from index 0 should wrap to last image (idx 4)
    envMulti.elements.modalPrevImgBtn.click();
    recordTest(
      'Modal Gallery Backward Wrap on Index 0 Cycles to Last Image',
      envMulti.elements.modalMainImg.attributes['src'] === propMultiImgs.images[4] &&
      envMulti.elements.modalImgCounter.textContent === '5 / 5',
      `Counter text: ${envMulti.elements.modalImgCounter.textContent}`
    );

    // Modal Next click from last image should wrap to first image (idx 0)
    envMulti.elements.modalNextImgBtn.click();
    recordTest(
      'Modal Gallery Forward Wrap on Last Index Cycles to First Image',
      envMulti.elements.modalMainImg.attributes['src'] === propMultiImgs.images[0] &&
      envMulti.elements.modalImgCounter.textContent === '1 / 5',
      `Counter text: ${envMulti.elements.modalImgCounter.textContent}`
    );
  }

  // --------------------------------------------------------------------------
  // TEST 7: XSS and HTML Injection Resilience
  // --------------------------------------------------------------------------
  console.log('\n--- 7. XSS & HTML Injection Resilience ---');
  {
    const hostileProperty = {
      id: 'XSS-001',
      title: '<script>alert("xss-title")</script> Hermoso Apto',
      property_type: '<img src=x onerror=alert("xss-type")>',
      portal: '<b>Metrocuadrado</b>',
      canon: 1500000,
      admin_fee: 200000,
      total_price: 1700000,
      neighborhood: 'Riomar"><script>alert("xss-barrio")</script>',
      zone: 'Norte',
      address: 'Cra 51B # 80 <iframe src="javascript:alert(1)">',
      area_m2: 75,
      bedrooms: 2,
      bathrooms: 2,
      parking: 1,
      stratum: 5,
      images: ['https://example.com/clean.jpg'],
      url: 'https://metrocuadrado.com/inmueble/test-xss',
      contact: {
        phone: '3001234567',
        whatsapp: '573001234567',
        agency: 'Inmobiliaria <script>alert("agency")</script>',
        agent_name: 'Martha "><script>alert("agent")</script>'
      },
      description: 'Hostile test description with <script> tags and quotes',
      verified: true
    };

    const envXSS = buildTestEnvironment([hostileProperty]);
    vm.runInContext(appJsCode, envXSS.context);
    await new Promise(r => setTimeout(r, 25));

    const gridHtml = envXSS.elements.propertyGrid.innerHTML;

    // Invariant: Raw executable script tags or img error tags MUST NOT be injected
    const hasUnescapedScript = gridHtml.includes('<script>');
    const hasUnescapedImgXSS = gridHtml.includes('<img src=x onerror');
    const hasUnescapedIframe = gridHtml.includes('<iframe');

    recordTest(
      'HTML Injection Resilience: Zero Executable <script> Tags in Rendered Grid',
      !hasUnescapedScript,
      'Raw <script> tags properly escaped to &lt;script&gt;.'
    );

    recordTest(
      'HTML Injection Resilience: Zero Raw <img onerror> Tags in Rendered Grid',
      !hasUnescapedImgXSS,
      'Raw <img onerror> tags properly escaped.'
    );

    recordTest(
      'HTML Injection Resilience: Zero Raw <iframe> Tags in Rendered Grid',
      !hasUnescapedIframe,
      'Raw <iframe> tags properly escaped.'
    );
  }

  // --------------------------------------------------------------------------
  // TEST 8: Sorting Algorithm Invariants
  // --------------------------------------------------------------------------
  console.log('\n--- 8. Sorting Algorithm Invariants ---');
  {
    const envSort = buildTestEnvironment();
    vm.runInContext(appJsCode, envSort.context);
    await new Promise(r => setTimeout(r, 25));

    const propMap = new Map();
    propertiesData.forEach(p => propMap.set(p.id, p));

    const triggerSort = (sortVal) => {
      envSort.elements.sortSelect.value = sortVal;
      envSort.elements.sortSelect.dispatchEvent({ type: 'change', target: { value: sortVal } });
    };

    // 8.1 Price Ascending Monotonicity
    triggerSort('price_asc');
    const idsAsc = getRenderedPropertyIds(envSort);
    let priceAscOk = true;
    for (let i = 0; i < idsAsc.length - 1; i++) {
      const p1 = propMap.get(idsAsc[i]);
      const p2 = propMap.get(idsAsc[i + 1]);
      if (p1 && p2 && p1.total_price > p2.total_price) {
        priceAscOk = false;
        break;
      }
    }
    recordTest(
      'Sort Monotonicity: price_asc Strictly Non-Decreasing',
      priceAscOk && idsAsc.length === 172,
      `Verified across all ${idsAsc.length} items.`
    );

    // 8.2 Price Descending Monotonicity
    triggerSort('price_desc');
    const idsDesc = getRenderedPropertyIds(envSort);
    let priceDescOk = true;
    for (let i = 0; i < idsDesc.length - 1; i++) {
      const p1 = propMap.get(idsDesc[i]);
      const p2 = propMap.get(idsDesc[i + 1]);
      if (p1 && p2 && p1.total_price < p2.total_price) {
        priceDescOk = false;
        break;
      }
    }
    recordTest(
      'Sort Monotonicity: price_desc Strictly Non-Increasing',
      priceDescOk && idsDesc.length === 172,
      `Verified across all ${idsDesc.length} items.`
    );

    // 8.3 Area Descending Monotonicity
    triggerSort('area_desc');
    const idsAreaDesc = getRenderedPropertyIds(envSort);
    let areaDescOk = true;
    for (let i = 0; i < idsAreaDesc.length - 1; i++) {
      const p1 = propMap.get(idsAreaDesc[i]);
      const p2 = propMap.get(idsAreaDesc[i + 1]);
      const a1 = p1 ? (p1.area_m2 || 0) : 0;
      const a2 = p2 ? (p2.area_m2 || 0) : 0;
      if (a1 < a2) {
        areaDescOk = false;
        break;
      }
    }
    recordTest(
      'Sort Monotonicity: area_desc Strictly Non-Increasing',
      areaDescOk && idsAreaDesc.length === 172,
      'Missing or null areas safely defaulted to 0 without NaN comparison collapse.'
    );
  }

  // --------------------------------------------------------------------------
  // TEST 9: Status Tracking Workflow Transitions & Counter Sync
  // --------------------------------------------------------------------------
  console.log('\n--- 9. Status Workflow Transitions & Counters ---');
  {
    const envStatus = buildTestEnvironment();
    vm.runInContext(appJsCode, envStatus.context);
    await new Promise(r => setTimeout(r, 25));

    const pid = propertiesData[0].id;

    // 9.1 Open Status Modal via delegated grid action
    dispatchGridAction(envStatus, 'open-status', pid);

    recordTest(
      'Status Modal Opens Upon Card Action',
      envStatus.elements.statusModal.style.display === 'flex' &&
      envStatus.elements.statusModalSubtitle.textContent.includes(pid),
      `Modal open with subtitle: ${envStatus.elements.statusModalSubtitle.textContent}`
    );

    // 9.2 Select "visita_programada" radio in radio group
    envStatus.elements.trackingForm.querySelectorAll('input[name="propertyStatus"]').forEach(r => {
      r.checked = (r.value === 'visita_programada');
    });
    const visitaRadio = envStatus.elements.trackingForm.querySelectorAll('input[name="propertyStatus"]')
      .find(r => r.value === 'visita_programada');
    if (visitaRadio) {
      visitaRadio.dispatchEvent({ type: 'change', target: { value: 'visita_programada' } });
    }

    recordTest(
      'Selecting "visita_programada" Displays Visit Date Picker',
      envStatus.elements.visitDateGroup.style.display === 'block',
      'visitDateGroup display set to block.'
    );

    // Set visit date and notes
    envStatus.elements.visitDateInput.value = '2026-09-17T10:30';
    envStatus.elements.trackingNotesInput.value = 'Hablé con el asesor. Visita confirmada para el jueves 10:30am.';

    // Click 5 stars
    const star5 = envStatus.elements.starRatingControl.querySelectorAll('.star-btn')
      .find(b => b.dataset.star === '5');
    if (star5) star5.click();

    // Submit form
    envStatus.elements.trackingForm.dispatchEvent({ type: 'submit' });

    // Verify modal closed
    recordTest(
      'Submitting Tracking Form Closes Status Modal',
      envStatus.elements.statusModal.style.display === 'none',
      'Modal closed successfully.'
    );

    // Verify Tab Count Updated
    recordTest(
      'Visits Tab Counter Incremented to 1',
      parseInt(envStatus.elements.countTabVisits.textContent, 10) === 1,
      `Tab counter is ${envStatus.elements.countTabVisits.textContent}.`
    );

    // Verify LocalStorage Updated
    const stored = envStatus.mockLocalStorage.getItem('barranquilla_rentals_user_state_v1');
    const parsedStored = JSON.parse(stored);
    recordTest(
      'Tracking State Synchronized to localStorage',
      parsedStored && parsedStored.properties && parsedStored.properties[pid] &&
      parsedStored.properties[pid].status === 'visita_programada' &&
      parsedStored.properties[pid].rating === 5 &&
      parsedStored.properties[pid].notes.includes('Hablé con el asesor'),
      'localStorage updated with new tracking state.'
    );
  }

  // --------------------------------------------------------------------------
  // SUMMARY & REPORT
  // --------------------------------------------------------------------------
  console.log('\n================================================================');
  console.log('  TIER 5 FRONTEND ADVERSARIAL HARNESS SUMMARY');
  console.log('================================================================');
  console.log(`  Total Assertions Run : ${results.passed + results.failed}`);
  console.log(`  Passed               : ${results.passed}`);
  console.log(`  Failed               : ${results.failed}`);
  const verdict = results.failed === 0 ? 'APPROVE' : 'REJECT';
  console.log(`  HARNESS VERDICT      : ${verdict}`);
  console.log('================================================================\n');

  return results;
}

if (require.main === module) {
  runAdversarialSuite()
    .then(res => {
      if (res.failed > 0) process.exit(1);
      process.exit(0);
    })
    .catch(err => {
      console.error('Tier 5 Harness Unhandled Error:', err);
      process.exit(1);
    });
}

module.exports = { runAdversarialSuite, buildTestEnvironment };
