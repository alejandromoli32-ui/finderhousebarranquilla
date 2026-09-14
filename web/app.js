/**
 * Tracker de Inmuebles en Arriendo - Barranquilla Norte
 * Client-Side Single Page Application Engine (Vanilla ES6+)
 * 
 * Features:
 * - Ultra-fast in-memory tokenized search (< 5ms) with Spanish diacritics stripping
 * - Multi-faceted dynamic filtering (Barrio, Price, Beds, Baths, Parking, Type)
 * - Image carousel with SVG fallback & error handling
 * - Price Breakdown Box (Canon + Admin = Total)
 * - Dual-layer persistence (localStorage 0ms + debounced REST API sync)
 * - WhatsApp deep link generator with prefilled Colombian message
 * - Detail and Status/Notes Modals
 */

(function () {
  'use strict';

  const DEFAULT_DOSSIER_IDS = [
    "MERGED-9851-M6595771-193354024",
    "MQ-20802-M7027822",
    "MQ-18260-M5640703",
    "MQ-9851-M6921994",
    "MQ-9851-M5463984",
    "MERGED-12659-M6046505-194139995",
    "MERGED-13957-M6916787-194065632",
    "MQ-23769-M7006894",
    "MQ-671-M7036862",
    "MQ-9889-M6737523",
    "MQ-671-M5946897",
    "MQ-23769-M7006602",
    "MQ-16553-M6886725",
    "MQ-9851-M6918346",
    "MQ-9851-M6757768"
  ];

  // State Container
  const state = {
    properties: [],
    filteredProperties: [],
    dossierIds: new Set(DEFAULT_DOSSIER_IDS),
    curatedProperties: [],
    tracking: {
      version: '1.0',
      last_updated: null,
      properties: {},
      favorites: [],
      visits: [],
      discarded: [],
      notes: {}
    },
    filters: {
      query: '',
      barrio: 'todos',
      maxPrice: 2500000,
      bedrooms: 'all',
      bathrooms: 'all',
      parking: 'all',
      type: 'todos',
      stratum: 'all',
      statusTab: 'todos',
      hideDiscarded: true,
      sort: 'price_asc'
    },
    cardImageIndices: {},
    modalProperty: null,
    modalImgIndex: 0,
    statusTargetProperty: null,
    pendingSyncTimer: null
  };

  const STORAGE_KEY = 'barranquilla_rentals_user_state_v1';

  // DOM Elements
  const el = {
    searchInput: document.getElementById('searchInput'),
    clearSearchBtn: document.getElementById('clearSearchBtn'),
    resetFiltersBtn: document.getElementById('resetFiltersBtn'),
    barrioSelect: document.getElementById('barrioSelect'),
    barrioPills: document.getElementById('barrioPills'),
    priceSlider: document.getElementById('priceSlider'),
    priceDisplay: document.getElementById('priceDisplay'),
    bedroomsControl: document.getElementById('bedroomsControl'),
    bathroomsControl: document.getElementById('bathroomsControl'),
    parkingControl: document.getElementById('parkingControl'),
    typeControl: document.getElementById('typeControl'),
    stratumControl: document.getElementById('stratumControl'),
    sortSelect: document.getElementById('sortSelect'),
    statusTabs: document.getElementById('statusTabs'),
    hideDiscardedCheckbox: document.getElementById('hideDiscardedCheckbox'),
    resultsCounter: document.getElementById('resultsCounter'),
    propertyGrid: document.getElementById('propertyGrid'),
    emptyState: document.getElementById('emptyState'),
    emptyResetBtn: document.getElementById('emptyResetBtn'),
    mobileFilterToggleBtn: document.getElementById('mobileFilterToggleBtn'),

    // Stats
    statTotalCount: document.getElementById('statTotalCount'),
    statAvgPrice: document.getElementById('statAvgPrice'),
    statParkingCount: document.getElementById('statParkingCount'),
    statFavCount: document.getElementById('statFavCount'),
    statVisitsCount: document.getElementById('statVisitsCount'),

    // Tab Counts
    countTabAll: document.getElementById('countTabAll'),
    countTabDossier: document.getElementById('countTabDossier'),
    countTabFav: document.getElementById('countTabFav'),
    countTabVisits: document.getElementById('countTabVisits'),
    countTabContact: document.getElementById('countTabContact'),
    countTabDiscarded: document.getElementById('countTabDiscarded'),

    // Quick Action
    dossierQuickBtn: document.getElementById('dossierQuickBtn'),

    // Detail Modal
    detailModal: document.getElementById('detailModal'),
    closeDetailModalBtn: document.getElementById('closeDetailModalBtn'),
    modalTypeBadge: document.getElementById('modalTypeBadge'),
    modalPortalBadge: document.getElementById('modalPortalBadge'),
    modalTitle: document.getElementById('modalTitle'),
    modalLocation: document.getElementById('modalLocation'),
    modalMainImg: document.getElementById('modalMainImg'),
    modalPrevImgBtn: document.getElementById('modalPrevImgBtn'),
    modalNextImgBtn: document.getElementById('modalNextImgBtn'),
    modalImgCounter: document.getElementById('modalImgCounter'),
    modalThumbnails: document.getElementById('modalThumbnails'),
    modalTotalPrice: document.getElementById('modalTotalPrice'),
    modalCanon: document.getElementById('modalCanon'),
    modalAdmin: document.getElementById('modalAdmin'),
    modalPricePerM2: document.getElementById('modalPricePerM2'),
    modalStratum: document.getElementById('modalStratum'),
    modalBedrooms: document.getElementById('modalBedrooms'),
    modalBathrooms: document.getElementById('modalBathrooms'),
    modalParking: document.getElementById('modalParking'),
    modalArea: document.getElementById('modalArea'),
    modalDescription: document.getElementById('modalDescription'),
    modalAgency: document.getElementById('modalAgency'),
    modalAgentName: document.getElementById('modalAgentName'),
    modalPhone: document.getElementById('modalPhone'),
    modalWhatsappBtn: document.getElementById('modalWhatsappBtn'),
    modalOriginalLinkBtn: document.getElementById('modalOriginalLinkBtn'),
    modalOpenStatusBtn: document.getElementById('modalOpenStatusBtn'),

    // Status Modal
    statusModal: document.getElementById('statusModal'),
    closeStatusModalBtn: document.getElementById('closeStatusModalBtn'),
    cancelStatusBtn: document.getElementById('cancelStatusBtn'),
    statusModalSubtitle: document.getElementById('statusModalSubtitle'),
    trackingForm: document.getElementById('trackingForm'),
    visitDateGroup: document.getElementById('visitDateGroup'),
    visitDateInput: document.getElementById('visitDateInput'),
    starRatingControl: document.getElementById('starRatingControl'),
    starRatingLabel: document.getElementById('starRatingLabel'),
    trackingNotesInput: document.getElementById('trackingNotesInput'),

    // Exports
    exportJsonBtn: document.getElementById('exportJsonBtn'),
    exportCsvBtn: document.getElementById('exportCsvBtn'),

    // Manual Status & Quick Filters
    manualStatusControl: document.getElementById('manualStatusControl'),
    quickFavFilterBtn: document.getElementById('quickFavFilterBtn'),
    quickDiscardFilterBtn: document.getElementById('quickDiscardFilterBtn'),
    quickFavCount: document.getElementById('quickFavCount'),
    quickDiscardCount: document.getElementById('quickDiscardCount'),
    modalToggleFavBtn: document.getElementById('modalToggleFavBtn'),
    modalToggleDiscardBtn: document.getElementById('modalToggleDiscardBtn'),

    // Toast
    toastContainer: document.getElementById('toastContainer')
  };

  /* ==========================================================================
     TEXT UTILITIES & NORMALIZATION
     ========================================================================== */

  /**
   * Normalizes text for search: removes accents and converts to lowercase.
   * "ñ" is normalized so searching "campina" matches "campiña" and vice-versa.
   */
  function normalizeText(str) {
    if (!str) return '';
    return str
      .toString()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .toLowerCase()
      .trim();
  }

  function formatCOP(amount) {
    if (amount === null || amount === undefined || isNaN(amount)) return '$0';
    return '$' + Math.round(amount).toLocaleString('es-CO');
  }

  function escapeHtml(text) {
    if (!text) return '';
    const map = {
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#039;'
    };
    return text.toString().replace(/[&<>"']/g, m => map[m]);
  }

  /* ==========================================================================
     PERSISTENCE ENGINE (DUAL LAYER)
     ========================================================================== */

  function loadLocalTracking() {
    const defaultTracking = {
      version: '1.0',
      last_updated: null,
      properties: {},
      favorites: [],
      visits: [],
      discarded: [],
      notes: {}
    };
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
          if (!parsed.properties || typeof parsed.properties !== 'object' || Array.isArray(parsed.properties)) {
            parsed.properties = {};
          }
          if (!Array.isArray(parsed.favorites)) parsed.favorites = [];
          if (!Array.isArray(parsed.visits)) parsed.visits = [];
          if (!Array.isArray(parsed.discarded)) parsed.discarded = [];
          if (!parsed.notes || typeof parsed.notes !== 'object' || Array.isArray(parsed.notes)) parsed.notes = {};
          return parsed;
        }
      }
    } catch (e) {
      console.warn('Could not read from localStorage:', e);
    }
    return defaultTracking;
  }

  function saveLocalTracking(tracking) {
    try {
      const target = (tracking && typeof tracking === 'object' && !Array.isArray(tracking)) ? tracking : {};
      const safePayload = {
        version: target.version || '1.0',
        last_updated: target.last_updated || new Date().toISOString(),
        properties: (target.properties && typeof target.properties === 'object' && !Array.isArray(target.properties)) ? target.properties : {},
        favorites: Array.isArray(target.favorites) ? target.favorites : [],
        visits: Array.isArray(target.visits) ? target.visits : [],
        discarded: Array.isArray(target.discarded) ? target.discarded : [],
        notes: (target.notes && typeof target.notes === 'object' && !Array.isArray(target.notes)) ? target.notes : {}
      };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(safePayload));
    } catch (e) {
      console.warn('Could not save to localStorage:', e);
    }
  }

  async function syncTrackingWithServer(immediatePayload = null) {
    try {
      const res = await fetch('/api/tracking', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(immediatePayload || state.tracking)
      });
      if (res.ok) {
        const result = await res.json();
        if (result && result.data) {
          state.tracking = result.data;
          saveLocalTracking(state.tracking);
          updateAllBadgesAndCounters();
        }
      }
    } catch (err) {
      // Offline / file protocol fallback - state is already safely in localStorage
      console.log('Server sync skipped (operating offline or file mode):', err.message);
    }
  }

  function scheduleServerSync(payload = null) {
    // 0ms Optimistic UI updates localStorage
    saveLocalTracking(state.tracking);
    updateAllBadgesAndCounters();

    // Debounced network sync to disk
    if (state.pendingSyncTimer) {
      clearTimeout(state.pendingSyncTimer);
    }
    state.pendingSyncTimer = setTimeout(() => {
      syncTrackingWithServer(payload);
    }, 300);
  }

  function updatePropertyTracking(propertyId, updates) {
    if (!state.tracking || typeof state.tracking !== 'object' || Array.isArray(state.tracking)) {
      state.tracking = {
        version: '1.0',
        last_updated: null,
        properties: {},
        favorites: [],
        visits: [],
        discarded: [],
        notes: {}
      };
    }
    if (!state.tracking.properties || typeof state.tracking.properties !== 'object' || Array.isArray(state.tracking.properties)) {
      state.tracking.properties = {};
    }
    const current = (state.tracking && state.tracking.properties && state.tracking.properties[propertyId]) || {
      status: 'sin_gestionar',
      favorite: false,
      visit_date: null,
      notes: '',
      rating: 0
    };

    const updated = {
      ...current,
      ...updates,
      updated_at: new Date().toISOString()
    };

    if (updated.status === 'favorito') {
      updated.favorite = true;
    }

    state.tracking.properties[propertyId] = updated;

    // Refresh convenience arrays
    const props = (state.tracking && state.tracking.properties) || {};
    state.tracking.favorites = Object.keys(props).filter(
      id => props[id].favorite || props[id].status === 'favorito'
    );
    state.tracking.visits = Object.keys(props).filter(
      id => props[id].status === 'visita_programada'
    );
    state.tracking.discarded = Object.keys(props).filter(
      id => props[id].status === 'descartado'
    );
    state.tracking.notes = {};
    Object.keys(props).forEach(id => {
      if (props[id].notes) {
        state.tracking.notes[id] = props[id].notes;
      }
    });

    scheduleServerSync({
      property_id: propertyId,
      ...updated
    });
  }

  /* ==========================================================================
     DATA INITIALIZATION & INDEXING
     ========================================================================== */

  async function initApp() {
    // 1. Load localStorage tracking as immediate base
    const localTracking = loadLocalTracking();
    if (localTracking && typeof localTracking === 'object' && !Array.isArray(localTracking)) {
      state.tracking = localTracking;
    }
    // Guarantee valid tracking schema with { properties: {} }
    if (!state.tracking || typeof state.tracking !== 'object' || Array.isArray(state.tracking)) {
      state.tracking = {
        version: '1.0',
        last_updated: null,
        properties: {},
        favorites: [],
        visits: [],
        discarded: [],
        notes: {}
      };
    }
    if (!state.tracking.properties || typeof state.tracking.properties !== 'object' || Array.isArray(state.tracking.properties)) {
      state.tracking.properties = {};
    }

    // 2. Load server tracking (source of truth)
    try {
      const trackRes = await fetch('/api/tracking');
      if (trackRes.ok) {
        const serverTracking = await trackRes.json();
        if (serverTracking && typeof serverTracking === 'object' && !Array.isArray(serverTracking) && serverTracking.properties) {
          // Merge: if server has newer or equal, use server
          state.tracking = serverTracking;
          if (!state.tracking.properties || typeof state.tracking.properties !== 'object' || Array.isArray(state.tracking.properties)) {
            state.tracking.properties = {};
          }
          saveLocalTracking(state.tracking);
        }
      }
    } catch (e) {
      console.log('Notice: using local state (offline mode)');
    }

    // 3. Load properties catalogue
    try {
      let propRes = await fetch('/api/properties');
      if (!propRes.ok) {
        propRes = await fetch('/data/inmuebles_barranquilla.json');
      }
      if (propRes.ok) {
        const list = await propRes.json();
        if (Array.isArray(list)) {
          state.properties = list;
        }
      }
    } catch (e) {
      console.error('Failed to load properties list:', e);
    }

    // 3b. Load curated dossier data if available
    try {
      const dosRes = await fetch('/data/dossier_curado.json');
      if (dosRes.ok) {
        const dData = await dosRes.json();
        if (dData && Array.isArray(dData.property_ids) && dData.property_ids.length > 0) {
          state.dossierIds = new Set(dData.property_ids);
          state.curatedProperties = dData.properties || [];
        }
      }
    } catch (e) {
      // Retains DEFAULT_DOSSIER_IDS safely
    }

    // 4. Pre-compute search blobs for < 5ms searches
    state.properties.forEach(p => {
      const parts = [
        p.title || '',
        p.neighborhood || '',
        p.zone || '',
        p.property_type || '',
        p.address || '',
        p.contact?.agency || '',
        p.contact?.agent_name || '',
        p.contact?.phone || '',
        p.contact?.whatsapp || '',
        p.description || '',
        p.id || ''
      ];
      p._searchBlob = normalizeText(parts.join(' '));
    });

    // 5. Populate Barrio Select & Pills
    setupBarrioFilters();

    // 6. Setup Event Listeners
    setupEventListeners();

    // 7. Initial Render
    applyFilters();
    updateAllBadgesAndCounters();

    // 8. Collaborative Live Polling: Check for updates from other users every 25s
    if (typeof window !== 'undefined' && typeof window.setInterval === 'function') {
      window.setInterval(async () => {
        try {
          const res = await fetch('/api/tracking');
          if (res.ok) {
            const remote = await res.json();
            const remoteData = (remote && remote.data) ? remote.data : remote;
            if (remoteData && remoteData.last_updated && remoteData.last_updated !== state.tracking.last_updated) {
              state.tracking = remoteData;
              saveLocalTracking(state.tracking);
              updateAllBadgesAndCounters();
              applyFilters();
            }
          }
        } catch (e) {
          // Offline / silent
        }
      }, 25000);
    }
  }

  function setupBarrioFilters() {
    const barrioMap = new Map();
    state.properties.forEach(p => {
      const b = p.neighborhood || 'Otro';
      barrioMap.set(b, (barrioMap.get(b) || 0) + 1);
    });

    // Sort barrios by listing count descending
    const sortedBarrios = Array.from(barrioMap.entries()).sort((a, b) => b[1] - a[1]);

    // Populate dropdown
    el.barrioSelect.innerHTML = `<option value="todos">Todos los Barrios (${sortedBarrios.length})</option>`;
    sortedBarrios.forEach(([barrio, count]) => {
      const opt = document.createElement('option');
      opt.value = barrio;
      opt.textContent = `${barrio} (${count})`;
      el.barrioSelect.appendChild(opt);
    });

    // Populate top Barrio pills
    const topBarrios = sortedBarrios.slice(0, 10);
    let pillsHtml = `
      <button type="button" class="barrio-pill active" data-barrio="todos">
        Todos <span class="barrio-pill-count">${state.properties.length}</span>
      </button>
    `;
    topBarrios.forEach(([barrio, count]) => {
      pillsHtml += `
        <button type="button" class="barrio-pill" data-barrio="${escapeHtml(barrio)}">
          ${escapeHtml(barrio)} <span class="barrio-pill-count">${count}</span>
        </button>
      `;
    });
    el.barrioPills.innerHTML = pillsHtml;
  }

  /* ==========================================================================
     FILTERING & SEARCH ENGINE (< 5ms)
     ========================================================================== */

  function applyFilters() {
    const {
      query,
      barrio,
      maxPrice,
      bedrooms,
      bathrooms,
      parking,
      type,
      stratum,
      statusTab,
      hideDiscarded,
      sort
    } = state.filters;

    const tokens = query ? normalizeText(query).split(/\s+/).filter(Boolean) : [];

    const filtered = state.properties.filter(p => {
      const tracking = (state.tracking && state.tracking.properties && state.tracking.properties[p.id]) || { status: 'sin_gestionar', favorite: false };

      // 1. Status Tab Filter
      if (statusTab === 'dossier') {
        if (!state.dossierIds || !state.dossierIds.has(p.id)) return false;
      } else if (statusTab === 'favoritos') {
        if (!tracking.favorite && tracking.status !== 'favorito') return false;
      } else if (statusTab === 'visitas') {
        if (tracking.status !== 'visita_programada') return false;
      } else if (statusTab === 'por_contactar') {
        if (tracking.status !== 'por_contactar') return false;
      } else if (statusTab === 'descartados') {
        if (tracking.status !== 'descartado') return false;
      } else {
        // Tab 'todos': hide discarded if checkbox checked
        if (hideDiscarded && tracking.status === 'descartado') {
          return false;
        }
      }

      // 2. Price Filter (Strict <= $2.5M COP ceiling & user max)
      if (p.total_price > maxPrice) return false;

      // 3. Barrio Filter
      if (barrio !== 'todos') {
        if (normalizeText(p.neighborhood) !== normalizeText(barrio)) return false;
      }

      // 4. Property Type Filter
      if (type !== 'todos') {
        if (p.property_type !== type) return false;
      }

      // 5. Bedrooms
      if (bedrooms !== 'all') {
        if (bedrooms === '4+') {
          if (p.bedrooms < 4) return false;
        } else {
          if (p.bedrooms !== parseInt(bedrooms, 10)) return false;
        }
      }

      // 6. Bathrooms
      if (bathrooms !== 'all') {
        if (bathrooms === '3+') {
          if (p.bathrooms < 3) return false;
        } else {
          if (p.bathrooms !== parseInt(bathrooms, 10)) return false;
        }
      }

      // 7. Parking
      if (parking === 'yes' && (!p.parking || p.parking < 1)) return false;
      if (parking === 'no' && p.parking > 0) return false;

      // 8. Stratum Filter
      if (stratum && stratum !== 'all') {
        const sVal = parseInt(stratum, 10);
        if (p.stratum !== sVal) return false;
      }

      // 8. Full-Text Multi-Token Conjunction Search
      if (tokens.length > 0) {
        for (let i = 0; i < tokens.length; i++) {
          if (!p._searchBlob.includes(tokens[i])) {
            return false;
          }
        }
      }

      return true;
    });

    // Sort order
    filtered.sort((a, b) => {
      if (statusTab === 'dossier' && sort === 'price_asc') {
        const arr = DEFAULT_DOSSIER_IDS;
        const iA = arr.indexOf(a.id);
        const iB = arr.indexOf(b.id);
        if (iA !== -1 && iB !== -1) return iA - iB;
      }
      if (sort === 'price_asc') return a.total_price - b.total_price;
      if (sort === 'price_desc') return b.total_price - a.total_price;
      if (sort === 'price_m2_asc') {
        const pm2A = a.area_m2 > 0 ? a.total_price / a.area_m2 : a.total_price;
        const pm2B = b.area_m2 > 0 ? b.total_price / b.area_m2 : b.total_price;
        return pm2A - pm2B;
      }
      if (sort === 'area_desc') return (b.area_m2 || 0) - (a.area_m2 || 0);
      if (sort === 'recent') {
        if (a.verified !== b.verified) return (b.verified ? 1 : 0) - (a.verified ? 1 : 0);
        return (b.id || '').localeCompare(a.id || '');
      }
      return a.total_price - b.total_price;
    });

    state.filteredProperties = filtered;
    renderGrid();
  }

  /* ==========================================================================
     RENDER CARD GRID & CAROUSELS
     ========================================================================== */

  function renderGrid() {
    const list = state.filteredProperties;
    el.resultsCounter.textContent = `Mostrando ${list.length} de ${state.properties.length} inmuebles`;

    if (list.length === 0) {
      el.propertyGrid.innerHTML = '';
      el.emptyState.style.display = 'block';
      return;
    }

    el.emptyState.style.display = 'none';

    let html = '';
    for (let i = 0; i < list.length; i++) {
      html += renderCardHtml(list[i]);
    }
    el.propertyGrid.innerHTML = html;
  }

  function renderCardHtml(p) {
    const tracking = (state.tracking && state.tracking.properties && state.tracking.properties[p.id]) || { status: 'sin_gestionar', favorite: false };
    const isFav = tracking.favorite || tracking.status === 'favorito';
    const isDiscarded = tracking.status === 'descartado';

    const images = (p.images && p.images.length > 0) ? p.images : ['assets/placeholder.svg'];
    const curImgIdx = state.cardImageIndices[p.id] || 0;
    const safeIdx = Math.min(Math.max(0, curImgIdx), images.length - 1);
    const activeImgUrl = images[safeIdx] || 'assets/placeholder.svg';

    // Pricing
    const canonFmt = formatCOP(p.canon);
    const adminFmt = p.admin_fee > 0 ? formatCOP(p.admin_fee) : '<span class="admin-included-tag">Admin Incluida</span>';
    const totalFmt = formatCOP(p.total_price);
    const pricePerM2Fmt = (p.area_m2 && p.area_m2 > 0)
      ? `${formatCOP(Math.round(p.total_price / p.area_m2))}/m²`
      : '';

    // WhatsApp Link
    const waLink = generateWhatsAppLink(p);

    // Status Pill
    let statusPillHtml = '';
    if (tracking.status === 'visita_programada') {
      const visitDateStr = tracking.visit_date
        ? ` · ${formatShortDate(tracking.visit_date)}`
        : '';
      statusPillHtml = `<div class="card-status-pill status-visita">📅 Visita${escapeHtml(visitDateStr)}</div>`;
    } else if (tracking.status === 'por_contactar') {
      statusPillHtml = `<div class="card-status-pill status-contactar">📞 Por contactar</div>`;
    } else if (tracking.status === 'descartado') {
      statusPillHtml = `<div class="card-status-pill status-descartado">🚫 Descartado</div>`;
    }

    // User note snippet
    let noteSnippetHtml = '';
    if (tracking.notes && tracking.notes.trim()) {
      noteSnippetHtml = `<div class="card-note-snippet">📝 ${escapeHtml(tracking.notes)}</div>`;
    }

    return `
      <article class="property-card ${isDiscarded ? 'is-discarded' : ''}" data-id="${escapeHtml(p.id)}">
        <!-- Media Carousel -->
        <div class="card-media-wrapper">
          <img 
            src="${escapeHtml(activeImgUrl)}" 
            alt="${escapeHtml(p.title)}" 
            class="card-image" 
            loading="lazy" 
            onerror="this.onerror=null; this.src='assets/placeholder.svg';"
          >
          
          <!-- Top Badges -->
          <div class="card-top-left-badges">
            <span class="badge badge-teal">${escapeHtml(p.property_type)}</span>
            <span class="badge badge-slate">${escapeHtml(p.portal)}</span>
          </div>

          <div class="card-top-right-actions">
            <button 
              type="button" 
              class="fav-btn ${isFav ? 'is-fav' : ''}" 
              data-action="toggle-fav" 
              data-id="${escapeHtml(p.id)}" 
              title="${isFav ? 'Quitar de Favoritos' : 'Marcar como Favorito'}"
              aria-label="Favorito"
            >
              ★
            </button>
            <button 
              type="button" 
              class="discard-top-btn ${isDiscarded ? 'is-discarded' : ''}" 
              data-action="toggle-discard" 
              data-id="${escapeHtml(p.id)}" 
              title="${isDiscarded ? 'Restaurar inmueble' : 'Descartar inmueble'}"
              aria-label="Descartar"
            >
              ${isDiscarded ? '↩️' : '🗑️'}
            </button>
          </div>

          <!-- Carousel Controls -->
          ${images.length > 1 ? `
            <button type="button" class="carousel-btn prev" data-action="prev-img" data-id="${escapeHtml(p.id)}" aria-label="Foto anterior">‹</button>
            <button type="button" class="carousel-btn next" data-action="next-img" data-id="${escapeHtml(p.id)}" aria-label="Siguiente foto">›</button>
            <span class="image-counter-badge">📷 ${safeIdx + 1} / ${images.length}</span>
          ` : ''}

          <!-- Status Overlay -->
          ${statusPillHtml}
        </div>

        <!-- Body Content -->
        <div class="card-content">
          <div class="card-location-row">
            <span>📍 ${escapeHtml(p.neighborhood)}</span>
            ${p.stratum ? `<span class="stratum-tag">Estrato ${p.stratum}</span>` : ''}
            ${state.dossierIds && state.dossierIds.has(p.id) ? `<span class="stratum-tag" style="background-color: var(--amber-100); color: var(--amber-800); border: 1px solid var(--amber-300); font-weight: 700;">🏆 Top Visita</span>` : ''}
          </div>

          <h3 class="card-title" data-action="open-detail" data-id="${escapeHtml(p.id)}" title="${escapeHtml(p.title)}">
            ${escapeHtml(p.title)}
          </h3>

          <!-- Specs -->
          <div class="card-specs-row">
            <div class="spec-item">
              <span class="spec-icon-label">Hab</span>
              <span class="spec-number">${p.bedrooms ?? 0}</span>
            </div>
            <div class="spec-item">
              <span class="spec-icon-label">Baños</span>
              <span class="spec-number">${p.bathrooms ?? 1}</span>
            </div>
            <div class="spec-item">
              <span class="spec-icon-label">Parq</span>
              <span class="spec-number">${p.parking ?? 0}</span>
            </div>
            <div class="spec-item">
              <span class="spec-icon-label">Área</span>
              <span class="spec-number">${p.area_m2 ? `${p.area_m2}m²` : '-'}</span>
            </div>
          </div>

          <!-- Price Breakdown Box -->
          <div class="price-breakdown-box">
            <div class="price-main-row">
              <span class="price-main-label">Total Mensual:</span>
              <span class="price-main-val">${totalFmt}</span>
            </div>
            <div class="price-desglose-row">
              <span>Canon: ${canonFmt}</span>
              <span>Admin: ${adminFmt}</span>
              ${pricePerM2Fmt ? `<span>${pricePerM2Fmt}</span>` : ''}
            </div>
          </div>

          <!-- Note Snippet -->
          ${noteSnippetHtml}

          <!-- Action Buttons -->
          <div class="card-actions-grid">
            <a href="${escapeHtml(waLink)}" target="_blank" rel="noopener noreferrer" class="btn btn-whatsapp btn-card-action">
              <svg viewBox="0 0 24 24" width="16" height="16"><path fill="currentColor" d="M12.04 2c-5.46 0-9.91 4.45-9.91 9.91 0 1.75.46 3.45 1.32 4.95L2.05 22l5.25-1.38c1.45.79 3.08 1.21 4.74 1.21 5.46 0 9.91-4.45 9.91-9.91 0-2.65-1.03-5.14-2.9-7.01A9.816 9.816 0 0 0 12.04 2zm5.79 14.07c-.24.68-1.4 1.26-1.92 1.34-.5.08-1.14.12-3.32-.78-2.6-1.07-4.29-3.7-4.42-3.87-.13-.18-1.06-1.41-1.06-2.69 0-1.28.67-1.91.91-2.17.24-.26.52-.33.7-.33.18 0 .36 0 .52.01.17.01.4-.06.63.48.24.54.82 2 .89 2.15.07.15.12.33.02.53-.1.2-.15.33-.3.51-.15.17-.32.39-.45.52-.15.15-.31.31-.13.62.18.31.78 1.29 1.68 2.09 1.15 1.02 2.12 1.34 2.43 1.49.31.15.49.13.67-.08.18-.21.78-.91.99-1.22.21-.31.42-.26.7-.16.29.1 1.83.86 2.15 1.02.32.16.53.24.61.37.08.13.08.76-.16 1.44z"/></svg>
              WhatsApp
            </a>

            <a href="${escapeHtml(p.url)}" target="_blank" rel="noopener noreferrer" class="btn btn-outline btn-card-action">
              Ver Anuncio ↗
            </a>

            <div class="card-actions-subrow">
              <button type="button" class="btn btn-secondary btn-card-action" data-action="open-status" data-id="${escapeHtml(p.id)}" style="color: var(--slate-700); background-color: var(--slate-100); border-color: var(--slate-300);" title="Gestionar notas y agendamiento de visita">
                📅 Agendar / Nota
              </button>
              
              <button type="button" class="btn btn-fav-action ${isFav ? 'active' : ''}" data-action="toggle-fav" data-id="${escapeHtml(p.id)}" title="${isFav ? 'Quitar de Favoritos' : 'Marcar como Favorito'}">
                ${isFav ? '★ Favorito' : '☆ Favorito'}
              </button>

              <button type="button" class="btn btn-discard-action ${isDiscarded ? 'active' : ''}" data-action="toggle-discard" data-id="${escapeHtml(p.id)}" title="${isDiscarded ? 'Restaurar inmueble' : 'Descartar inmueble'}">
                ${isDiscarded ? '↩️ Restaurar' : '🗑️ Descartar'}
              </button>
            </div>
          </div>
        </div>
      </article>
    `;
  }

  /* ==========================================================================
     WHATSAPP & CONTACT HELPERS
     ========================================================================== */

  function generateWhatsAppLink(p) {
    let phone = '';
    if (p.contact?.whatsapp) {
      phone = p.contact.whatsapp.replace(/\D/g, '');
    } else if (p.contact?.phone) {
      phone = p.contact.phone.replace(/\D/g, '');
    }

    // Colombian mobile cleanup
    if (phone.length === 10 && phone.startsWith('3')) {
      phone = '57' + phone;
    } else if (phone.length === 12 && phone.startsWith('573')) {
      // already valid
    } else if (!phone) {
      // Fallback
      phone = '573000000000';
    }

    const priceFormatted = formatCOP(p.total_price);
    const msg = `Hola, vi el anuncio del ${p.property_type.toLowerCase()} en ${p.neighborhood} por ${priceFormatted} (Canon + Admin). Estoy interesado en agendar una visita esta semana. ¿Sigue disponible? Ref: ${p.id}`;
    return `https://wa.me/${phone}?text=${encodeURIComponent(msg)}`;
  }

  function formatShortDate(isoString) {
    if (!isoString) return '';
    try {
      const d = new Date(isoString);
      const days = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb'];
      const dayName = days[d.getDay()];
      const dayNum = d.getDate();
      const monthNum = d.getMonth() + 1;
      const hours = d.getHours().toString().padStart(2, '0');
      const mins = d.getMinutes().toString().padStart(2, '0');
      return `${dayName} ${dayNum}/${monthNum} ${hours}:${mins}`;
    } catch (e) {
      return '';
    }
  }

  /* ==========================================================================
     BADGES & STATS SUMMARY
     ========================================================================== */

  function updateAllBadgesAndCounters() {
    const total = state.properties.length;
    let sumTotal = 0;
    let parkCount = 0;

    state.properties.forEach(p => {
      sumTotal += (p.total_price || 0);
      if (p.parking && p.parking > 0) parkCount++;
    });

    const avgPrice = total > 0 ? Math.round(sumTotal / total) : 0;
    const favCount = ((state.tracking && state.tracking.favorites) || []).length;
    const visitsCount = ((state.tracking && state.tracking.visits) || []).length;
    const contactCount = Object.values((state.tracking && state.tracking.properties) || {}).filter(d => d && d.status === 'por_contactar').length;
    const discardedCount = ((state.tracking && state.tracking.discarded) || []).length;

    // Header Stats
    el.statTotalCount.textContent = total;
    el.statAvgPrice.textContent = formatCOP(avgPrice);
    el.statParkingCount.textContent = parkCount;
    el.statFavCount.textContent = favCount;
    el.statVisitsCount.textContent = visitsCount;

    // Tab Counts
    el.countTabAll.textContent = total;
    if (el.countTabDossier) {
      const dossierCount = state.properties.filter(p => state.dossierIds && state.dossierIds.has(p.id)).length || (state.dossierIds ? state.dossierIds.size : 0);
      el.countTabDossier.textContent = dossierCount;
    }
    el.countTabFav.textContent = favCount;
    el.countTabVisits.textContent = visitsCount;
    el.countTabContact.textContent = contactCount;
    el.countTabDiscarded.textContent = discardedCount;

    // Quick filter counters & control sync
    if (el.quickFavCount) el.quickFavCount.textContent = favCount;
    if (el.quickDiscardCount) el.quickDiscardCount.textContent = discardedCount;
    syncStatusControls();
  }

  function syncStatusControls() {
    // 1. Sync tabs
    if (el.statusTabs) {
      el.statusTabs.querySelectorAll('.tab-btn').forEach(b => {
        b.classList.toggle('active', b.dataset.tab === state.filters.statusTab);
      });
    }
    // 2. Sync manual segmented control
    if (el.manualStatusControl) {
      const btns = el.manualStatusControl.querySelectorAll('.segment-btn');
      btns.forEach(b => {
        const val = b.dataset.val;
        if (state.filters.statusTab === 'favoritos') {
          b.classList.toggle('active', val === 'favoritos');
        } else if (state.filters.statusTab === 'descartados') {
          b.classList.toggle('active', val === 'descartados');
        } else if (state.filters.statusTab === 'todos') {
          if (state.filters.hideDiscarded) {
            b.classList.toggle('active', val === 'activos');
          } else {
            b.classList.toggle('active', val === 'todos');
          }
        } else {
          b.classList.remove('active');
        }
      });
    }
    // 3. Sync quick filter chips
    if (el.quickFavFilterBtn) {
      el.quickFavFilterBtn.classList.toggle('active-fav', state.filters.statusTab === 'favoritos');
    }
    if (el.quickDiscardFilterBtn) {
      el.quickDiscardFilterBtn.classList.toggle('active-discard', state.filters.statusTab === 'descartados');
    }
  }

  /* ==========================================================================
     DETAIL MODAL LOGIC
     ========================================================================== */

  function openDetailModal(propertyId) {
    const p = state.properties.find(item => item.id === propertyId);
    if (!p) return;

    state.modalProperty = p;
    state.modalImgIndex = 0;

    const tracking = (state.tracking && state.tracking.properties && state.tracking.properties[p.id]) || { status: 'sin_gestionar', favorite: false };

    el.modalTypeBadge.textContent = p.property_type;
    el.modalPortalBadge.textContent = p.portal;
    el.modalTitle.textContent = p.title;
    el.modalLocation.textContent = `📍 ${p.neighborhood} · ${p.address || ''}`;

    el.modalTotalPrice.textContent = `${formatCOP(p.total_price)} COP`;
    el.modalCanon.textContent = `${formatCOP(p.canon)} COP`;
    el.modalAdmin.textContent = p.admin_fee > 0 ? `${formatCOP(p.admin_fee)} COP` : 'Incluida ($0)';
    el.modalPricePerM2.textContent = p.area_m2 > 0 ? `${formatCOP(Math.round(p.total_price / p.area_m2))}/m²` : '-';
    el.modalStratum.textContent = p.stratum || '-';

    el.modalBedrooms.textContent = p.bedrooms ?? 0;
    el.modalBathrooms.textContent = p.bathrooms ?? 1;
    el.modalParking.textContent = p.parking ?? 0;
    el.modalArea.textContent = p.area_m2 ? `${p.area_m2} m²` : '-';

    el.modalDescription.textContent = p.description || 'Sin descripción adicional.';

    el.modalAgency.textContent = p.contact?.agency || 'Particular / Inmobiliaria';
    el.modalAgentName.textContent = p.contact?.agent_name || 'Asesor Comercial';
    el.modalPhone.textContent = p.contact?.phone || 'No especificado';

    el.modalWhatsappBtn.href = generateWhatsAppLink(p);
    el.modalOriginalLinkBtn.href = p.url;

    const isFav = tracking.favorite || tracking.status === 'favorito';
    const isDiscarded = tracking.status === 'descartado';

    if (el.modalToggleFavBtn) {
      el.modalToggleFavBtn.textContent = isFav ? '★ En Favoritos' : '⭐ Marcar Favorito';
      el.modalToggleFavBtn.classList.toggle('active', isFav);
    }
    if (el.modalToggleDiscardBtn) {
      el.modalToggleDiscardBtn.textContent = isDiscarded ? '↩️ Restaurar Inmueble' : '🗑️ Descartar Inmueble';
      el.modalToggleDiscardBtn.classList.toggle('active', isDiscarded);
    }

    updateModalGallery();

    el.detailModal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
  }

  function closeDetailModal() {
    el.detailModal.style.display = 'none';
    document.body.style.overflow = '';
    state.modalProperty = null;
  }

  function updateModalGallery() {
    const p = state.modalProperty;
    if (!p) return;

    const images = (p.images && p.images.length > 0) ? p.images : ['assets/placeholder.svg'];
    const idx = Math.min(Math.max(0, state.modalImgIndex), images.length - 1);
    state.modalImgIndex = idx;

    el.modalMainImg.src = images[idx];
    el.modalMainImg.onerror = function () {
      this.onerror = null;
      this.src = 'assets/placeholder.svg';
    };

    el.modalImgCounter.textContent = `${idx + 1} / ${images.length}`;

    // Thumbnails
    let thumbsHtml = '';
    images.forEach((img, i) => {
      thumbsHtml += `
        <img 
          src="${escapeHtml(img)}" 
          alt="Miniatura ${i + 1}" 
          class="modal-thumb ${i === idx ? 'active' : ''}" 
          data-thumb-idx="${i}" 
          onerror="this.onerror=null; this.src='assets/placeholder.svg';"
        >
      `;
    });
    el.modalThumbnails.innerHTML = thumbsHtml;
  }

  /* ==========================================================================
     STATUS & NOTES MODAL LOGIC
     ========================================================================== */

  let currentSelectedRating = 0;

  function openStatusModal(propertyId) {
    const p = state.properties.find(item => item.id === propertyId);
    if (!p) return;

    state.statusTargetProperty = p;
    const tracking = (state.tracking && state.tracking.properties && state.tracking.properties[p.id]) || {
      status: 'sin_gestionar',
      favorite: false,
      visit_date: '',
      notes: '',
      rating: 0
    };

    el.statusModalSubtitle.textContent = `ID: ${p.id} · ${p.neighborhood} · ${formatCOP(p.total_price)}`;

    // Set Radio Status
    const radios = el.trackingForm.querySelectorAll('input[name="propertyStatus"]');
    radios.forEach(r => {
      r.checked = (r.value === tracking.status);
    });

    // Visit date
    if (tracking.status === 'visita_programada') {
      el.visitDateGroup.style.display = 'block';
      el.visitDateInput.value = tracking.visit_date || '';
    } else {
      el.visitDateGroup.style.display = 'none';
      el.visitDateInput.value = '';
    }

    // Rating
    currentSelectedRating = tracking.rating || 0;
    renderStarRating(currentSelectedRating);

    // Notes
    el.trackingNotesInput.value = tracking.notes || '';

    el.statusModal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
  }

  function closeStatusModal() {
    el.statusModal.style.display = 'none';
    document.body.style.overflow = '';
    state.statusTargetProperty = null;
  }

  function renderStarRating(rating) {
    const starBtns = el.starRatingControl.querySelectorAll('.star-btn');
    starBtns.forEach(btn => {
      const starVal = parseInt(btn.dataset.star, 10);
      btn.classList.toggle('active', starVal <= rating);
    });

    const labels = ['Sin calificar', '1 - Mala opción', '2 - Regular', '3 - Aceptable', '4 - Muy buena', '5 - ¡Excelente!'];
    el.starRatingLabel.textContent = labels[rating] || 'Sin calificar';
  }

  /* ==========================================================================
     TOAST NOTIFICATIONS
     ========================================================================== */

  function showToast(message, icon = '✓') {
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.innerHTML = `<span>${icon}</span> <span>${escapeHtml(message)}</span>`;
    el.toastContainer.appendChild(toast);

    setTimeout(() => {
      toast.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(10px)';
      setTimeout(() => toast.remove(), 300);
    }, 3200);
  }

  /* ==========================================================================
     EVENT LISTENERS & BINDINGS
     ========================================================================== */

  function setupEventListeners() {
    // 1. Real-time Search Input (Debounced 100ms)
    let searchDebounce = null;
    el.searchInput.addEventListener('input', (e) => {
      const val = e.target.value;
      el.clearSearchBtn.style.display = val ? 'flex' : 'none';
      clearTimeout(searchDebounce);
      searchDebounce = setTimeout(() => {
        state.filters.query = val;
        applyFilters();
      }, 100);
    });

    el.clearSearchBtn.addEventListener('click', () => {
      el.searchInput.value = '';
      el.clearSearchBtn.style.display = 'none';
      state.filters.query = '';
      applyFilters();
      el.searchInput.focus();
    });

    // Keyboard shortcut (Ctrl + K or /) to focus search
    window.addEventListener('keydown', (e) => {
      if ((e.ctrlKey && e.key.toLowerCase() === 'k') || (e.key === '/' && document.activeElement.tagName !== 'INPUT' && document.activeElement.tagName !== 'TEXTAREA')) {
        e.preventDefault();
        el.searchInput.focus();
        el.searchInput.select();
      }
      if (e.key === 'Escape') {
        if (el.detailModal.style.display === 'flex') closeDetailModal();
        if (el.statusModal.style.display === 'flex') closeStatusModal();
      }
    });

    // 2. Barrio Select Dropdown
    el.barrioSelect.addEventListener('change', (e) => {
      const val = e.target.value;
      state.filters.barrio = val;

      // Update active state in quick pills
      const pills = el.barrioPills.querySelectorAll('.barrio-pill');
      pills.forEach(p => {
        p.classList.toggle('active', p.dataset.barrio === val);
      });

      applyFilters();
    });

    // 3. Barrio Quick Pills Click
    el.barrioPills.addEventListener('click', (e) => {
      const pill = e.target.closest('.barrio-pill');
      if (!pill) return;

      const barrio = pill.dataset.barrio;
      state.filters.barrio = barrio;
      el.barrioSelect.value = barrio;

      const pills = el.barrioPills.querySelectorAll('.barrio-pill');
      pills.forEach(p => p.classList.toggle('active', p === pill));

      applyFilters();
    });

    // 4. Price Slider
    el.priceSlider.addEventListener('input', (e) => {
      const val = parseInt(e.target.value, 10);
      state.filters.maxPrice = val;
      el.priceDisplay.textContent = `${formatCOP(val)} COP`;
      applyFilters();
    });

    // 5. Segmented Controls Helper
    function setupSegmented(container, filterKey) {
      container.addEventListener('click', (e) => {
        const btn = e.target.closest('.segment-btn');
        if (!btn) return;

        container.querySelectorAll('.segment-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        state.filters[filterKey] = btn.dataset.val;
        applyFilters();
      });
    }

    setupSegmented(el.bedroomsControl, 'bedrooms');
    setupSegmented(el.bathroomsControl, 'bathrooms');
    setupSegmented(el.parkingControl, 'parking');
    setupSegmented(el.typeControl, 'type');
    if (el.stratumControl) setupSegmented(el.stratumControl, 'stratum');

    // 6. Sort Dropdown
    el.sortSelect.addEventListener('change', (e) => {
      state.filters.sort = e.target.value;
      applyFilters();
    });

    // 7. Status Tabs Click
    el.statusTabs.addEventListener('click', (e) => {
      const btn = e.target.closest('.tab-btn');
      if (!btn) return;

      el.statusTabs.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      state.filters.statusTab = btn.dataset.tab;
      syncStatusControls();
      applyFilters();
    });

    // Manual Status Segmented Control in Filters Grid
    if (el.manualStatusControl) {
      el.manualStatusControl.addEventListener('click', (e) => {
        const btn = e.target.closest('.segment-btn');
        if (!btn) return;

        const val = btn.dataset.val;
        if (val === 'favoritos') {
          state.filters.statusTab = 'favoritos';
        } else if (val === 'descartados') {
          state.filters.statusTab = 'descartados';
        } else if (val === 'activos') {
          state.filters.statusTab = 'todos';
          state.filters.hideDiscarded = true;
          if (el.hideDiscardedCheckbox) el.hideDiscardedCheckbox.checked = true;
        } else {
          state.filters.statusTab = 'todos';
          state.filters.hideDiscarded = false;
          if (el.hideDiscardedCheckbox) el.hideDiscardedCheckbox.checked = false;
        }
        syncStatusControls();
        applyFilters();
      });
    }

    // Mobile Filter Toggle Button
    if (el.mobileFilterToggleBtn) {
      el.mobileFilterToggleBtn.addEventListener('click', () => {
        const grid = document.querySelector('.faceted-grid');
        if (grid) {
          const isExpanded = grid.classList.toggle('mobile-expanded');
          el.mobileFilterToggleBtn.classList.toggle('active', isExpanded);
          el.mobileFilterToggleBtn.setAttribute('aria-expanded', String(isExpanded));
          const chevron = el.mobileFilterToggleBtn.querySelector('.filter-toggle-chevron');
          if (chevron) chevron.textContent = isExpanded ? '▲' : '▼';
        }
      });
    }

    // Quick Filter Buttons in Search Row
    if (el.quickFavFilterBtn) {
      el.quickFavFilterBtn.addEventListener('click', () => {
        if (state.filters.statusTab === 'favoritos') {
          state.filters.statusTab = 'todos';
        } else {
          state.filters.statusTab = 'favoritos';
        }
        syncStatusControls();
        applyFilters();
      });
    }

    if (el.quickDiscardFilterBtn) {
      el.quickDiscardFilterBtn.addEventListener('click', () => {
        if (state.filters.statusTab === 'descartados') {
          state.filters.statusTab = 'todos';
        } else {
          state.filters.statusTab = 'descartados';
        }
        syncStatusControls();
        applyFilters();
      });
    }

    // Modal Favorite & Discard Action Buttons
    if (el.modalToggleFavBtn) {
      el.modalToggleFavBtn.addEventListener('click', () => {
        if (!state.modalProperty) return;
        const pid = state.modalProperty.id;
        const tracking = (state.tracking && state.tracking.properties && state.tracking.properties[pid]) || { favorite: false, status: 'sin_gestionar' };
        const newFav = !tracking.favorite;
        updatePropertyTracking(pid, {
          favorite: newFav,
          status: newFav ? (tracking.status === 'sin_gestionar' ? 'favorito' : tracking.status) : (tracking.status === 'favorito' ? 'sin_gestionar' : tracking.status)
        });
        showToast(newFav ? 'Añadido a Favoritos' : 'Eliminado de Favoritos', newFav ? '⭐' : 'ℹ️');
        applyFilters();
        openDetailModal(pid);
      });
    }

    if (el.modalToggleDiscardBtn) {
      el.modalToggleDiscardBtn.addEventListener('click', () => {
        if (!state.modalProperty) return;
        const pid = state.modalProperty.id;
        const tracking = (state.tracking && state.tracking.properties && state.tracking.properties[pid]) || { status: 'sin_gestionar' };
        const isDiscarded = tracking.status === 'descartado';
        const newStatus = isDiscarded ? 'sin_gestionar' : 'descartado';
        updatePropertyTracking(pid, { status: newStatus });
        showToast(isDiscarded ? 'Inmueble restaurado' : 'Inmueble descartado', isDiscarded ? '↩️' : '🗑️');
        applyFilters();
        openDetailModal(pid);
      });
    }

    // Dossier Quick Button in Header
    if (el.dossierQuickBtn) {
      el.dossierQuickBtn.addEventListener('click', () => {
        if (el.statusTabs) {
          el.statusTabs.querySelectorAll('.tab-btn').forEach(b => {
            b.classList.toggle('active', b.dataset.tab === 'dossier');
          });
        }
        state.filters.statusTab = 'dossier';
        syncStatusControls();
        applyFilters();
        showToast('Mostrando Dossier Curado (Top 15 Visitas Inmediatas)', '🏆');
      });
    }

    // 8. Hide Discarded Toggle
    el.hideDiscardedCheckbox.addEventListener('change', (e) => {
      state.filters.hideDiscarded = e.target.checked;
      syncStatusControls();
      applyFilters();
    });

    // 9. Reset Filters
    function resetAllFilters() {
      state.filters.query = '';
      state.filters.barrio = 'todos';
      state.filters.maxPrice = 2500000;
      state.filters.bedrooms = 'all';
      state.filters.bathrooms = 'all';
      state.filters.parking = 'all';
      state.filters.type = 'todos';
      state.filters.stratum = 'all';
      state.filters.statusTab = 'todos';
      state.filters.hideDiscarded = true;
      state.filters.sort = 'price_asc';

      el.searchInput.value = '';
      el.clearSearchBtn.style.display = 'none';
      el.barrioSelect.value = 'todos';
      el.priceSlider.value = 2500000;
      el.priceDisplay.textContent = '$2.500.000 COP';
      el.sortSelect.value = 'price_asc';
      el.hideDiscardedCheckbox.checked = true;

      // Reset segmented buttons
      [el.bedroomsControl, el.bathroomsControl, el.parkingControl, el.typeControl, el.stratumControl].forEach(c => {
        if (c) {
          const btns = c.querySelectorAll('.segment-btn');
          btns.forEach((b, i) => b.classList.toggle('active', i === 0));
        }
      });

      // Reset pills
      el.barrioPills.querySelectorAll('.barrio-pill').forEach((p, i) => {
        p.classList.toggle('active', i === 0);
      });

      // Reset tabs & status controls
      syncStatusControls();

      applyFilters();
      showToast('Filtros restablecidos');
    }

    el.resetFiltersBtn.addEventListener('click', resetAllFilters);
    el.emptyResetBtn.addEventListener('click', resetAllFilters);

    // 10. Card Delegated Actions (Carousel, Fav, Discard, Modals)
    el.propertyGrid.addEventListener('click', (e) => {
      const target = e.target.closest('[data-action]');
      if (!target) return;

      const action = target.dataset.action;
      const pid = target.dataset.id;
      const prop = state.properties.find(p => p.id === pid);
      if (!prop) return;

      const images = (prop.images && prop.images.length > 0) ? prop.images : ['assets/placeholder.svg'];

      if (action === 'toggle-fav') {
        e.stopPropagation();
        const tracking = (state.tracking && state.tracking.properties && state.tracking.properties[pid]) || { favorite: false, status: 'sin_gestionar' };
        const newFav = !tracking.favorite;
        updatePropertyTracking(pid, {
          favorite: newFav,
          status: newFav ? (tracking.status === 'sin_gestionar' ? 'favorito' : tracking.status) : (tracking.status === 'favorito' ? 'sin_gestionar' : tracking.status)
        });
        showToast(newFav ? 'Añadido a Favoritos' : 'Eliminado de Favoritos', newFav ? '⭐' : 'ℹ️');
        applyFilters();
      } else if (action === 'toggle-discard') {
        e.stopPropagation();
        const tracking = (state.tracking && state.tracking.properties && state.tracking.properties[pid]) || { status: 'sin_gestionar' };
        const isDiscarded = tracking.status === 'descartado';
        const newStatus = isDiscarded ? 'sin_gestionar' : 'descartado';
        updatePropertyTracking(pid, { status: newStatus });
        showToast(isDiscarded ? 'Inmueble restaurado' : 'Inmueble descartado', isDiscarded ? '↩️' : '🗑️');
        applyFilters();
      } else if (action === 'next-img') {
        e.stopPropagation();
        const cur = state.cardImageIndices[pid] || 0;
        state.cardImageIndices[pid] = (cur + 1) % images.length;
        renderSingleCardImage(pid);
      } else if (action === 'prev-img') {
        e.stopPropagation();
        const cur = state.cardImageIndices[pid] || 0;
        state.cardImageIndices[pid] = (cur - 1 + images.length) % images.length;
        renderSingleCardImage(pid);
      } else if (action === 'open-detail') {
        openDetailModal(pid);
      } else if (action === 'open-status') {
        openStatusModal(pid);
      }
    });

    function renderSingleCardImage(pid) {
      const card = el.propertyGrid.querySelector(`.property-card[data-id="${pid}"]`);
      if (!card) return;
      const prop = state.properties.find(p => p.id === pid);
      if (!prop) return;
      const images = (prop.images && prop.images.length > 0) ? prop.images : ['assets/placeholder.svg'];
      const idx = state.cardImageIndices[pid] || 0;

      const img = card.querySelector('.card-image');
      if (img) img.src = images[idx];

      const counter = card.querySelector('.image-counter-badge');
      if (counter) counter.textContent = `📷 ${idx + 1} / ${images.length}`;
    }

    // 11. Modal Gallery Navigation
    el.modalNextImgBtn.addEventListener('click', () => {
      const p = state.modalProperty;
      if (!p) return;
      const images = (p.images && p.images.length > 0) ? p.images : ['assets/placeholder.svg'];
      state.modalImgIndex = (state.modalImgIndex + 1) % images.length;
      updateModalGallery();
    });

    el.modalPrevImgBtn.addEventListener('click', () => {
      const p = state.modalProperty;
      if (!p) return;
      const images = (p.images && p.images.length > 0) ? p.images : ['assets/placeholder.svg'];
      state.modalImgIndex = (state.modalImgIndex - 1 + images.length) % images.length;
      updateModalGallery();
    });

    el.modalThumbnails.addEventListener('click', (e) => {
      const thumb = e.target.closest('.modal-thumb');
      if (!thumb) return;
      state.modalImgIndex = parseInt(thumb.dataset.thumbIdx, 10);
      updateModalGallery();
    });

    el.closeDetailModalBtn.addEventListener('click', closeDetailModal);
    el.detailModal.addEventListener('click', (e) => {
      if (e.target === el.detailModal) closeDetailModal();
    });

    el.modalOpenStatusBtn.addEventListener('click', () => {
      if (state.modalProperty) {
        const id = state.modalProperty.id;
        closeDetailModal();
        openStatusModal(id);
      }
    });

    // 12. Status Modal Events
    el.closeStatusModalBtn.addEventListener('click', closeStatusModal);
    el.cancelStatusBtn.addEventListener('click', closeStatusModal);
    el.statusModal.addEventListener('click', (e) => {
      if (e.target === el.statusModal) closeStatusModal();
    });

    // Toggle visit date picker based on status choice
    el.trackingForm.querySelectorAll('input[name="propertyStatus"]').forEach(r => {
      r.addEventListener('change', (e) => {
        el.visitDateGroup.style.display = (e.target.value === 'visita_programada') ? 'block' : 'none';
      });
    });

    // Star Rating Click
    el.starRatingControl.addEventListener('click', (e) => {
      const star = e.target.closest('.star-btn');
      if (!star) return;
      currentSelectedRating = parseInt(star.dataset.star, 10);
      renderStarRating(currentSelectedRating);
    });

    // Submit Status Form
    el.trackingForm.addEventListener('submit', (e) => {
      e.preventDefault();
      if (!state.statusTargetProperty) return;

      const pid = state.statusTargetProperty.id;
      const selectedStatusRadio = el.trackingForm.querySelector('input[name="propertyStatus"]:checked');
      const status = selectedStatusRadio ? selectedStatusRadio.value : 'sin_gestionar';
      const visitDate = (status === 'visita_programada') ? el.visitDateInput.value : null;
      const notes = el.trackingNotesInput.value.trim();
      const rating = currentSelectedRating;

      updatePropertyTracking(pid, {
        status: status,
        visit_date: visitDate,
        notes: notes,
        rating: rating,
        favorite: (status === 'favorito') ? true : undefined
      });

      closeStatusModal();
      showToast('Seguimiento actualizado con éxito');
      applyFilters();
    });

    // 13. Export Handlers
    el.exportJsonBtn.addEventListener('click', () => {
      const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(state.tracking, null, 2));
      const downloadAnchor = document.createElement('a');
      downloadAnchor.setAttribute('href', dataStr);
      downloadAnchor.setAttribute('download', `user_tracking_barranquilla_${new Date().toISOString().slice(0,10)}.json`);
      document.body.appendChild(downloadAnchor);
      downloadAnchor.click();
      downloadAnchor.remove();
      showToast('Descargando archivo JSON...');
    });

    el.exportCsvBtn.addEventListener('click', () => {
      const props = (state.tracking && state.tracking.properties) || {};
      const rows = [['id', 'barrio', 'tipo', 'precio_total', 'estado', 'favorito', 'fecha_visita', 'calificacion', 'notas']];

      Object.keys(props).forEach(id => {
        const item = props[id];
        const p = state.properties.find(x => x.id === id);
        rows.push([
          id,
          p ? p.neighborhood : '',
          p ? p.property_type : '',
          p ? p.total_price : '',
          item.status || '',
          item.favorite ? 'SI' : 'NO',
          item.visit_date || '',
          item.rating || 0,
          `"${(item.notes || '').replace(/"/g, '""')}"`
        ]);
      });

      const csvContent = '\uFEFF' + rows.map(r => r.join(',')).join('\n');
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `user_tracking_barranquilla_${new Date().toISOString().slice(0,10)}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      showToast('Descargando archivo CSV...');
    });
  }

  // Kickstart Application
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initApp);
  } else {
    initApp();
  }
})();
