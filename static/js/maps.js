// static/js/maps.js
(function () {
  'use strict';

  // ---- Tiles (gratis) ----
  const TILE_URL  = 'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png';
  const TILE_ATTR = '&copy; OpenStreetMap contributors &copy; <a href="https://carto.com/attributions">CARTO</a>';

  window.addTiles = function (map) {
    L.tileLayer(TILE_URL, { subdomains: 'abcd', maxZoom: 20, attribution: TILE_ATTR }).addTo(map);
  };

  // ---- LRU cache simple (mem + localStorage) ----
  const LRU_SIZE = 50;
  const LS_KEY_GC = 'gc_cache_v1';
  const LS_KEY_RC = 'rc_cache_v1';

  const memGC = new Map(); // geocode q -> {lat,lon,props}
  const memRC = new Map(); // reverse "lat,lon" -> props

  function _loadLS(key, mem) {
    try {
      const raw = localStorage.getItem(key);
      if (!raw) return;
      const arr = JSON.parse(raw);
      arr.forEach(([k, v]) => mem.set(k, v));
      // si excede, recorta
      while (mem.size > LRU_SIZE) {
        const firstKey = mem.keys().next().value;
        mem.delete(firstKey);
      }
    } catch {}
  }
  function _saveLS(key, mem) {
    try {
      const arr = Array.from(mem.entries()).slice(-LRU_SIZE);
      localStorage.setItem(key, JSON.stringify(arr));
    } catch {}
  }
  _loadLS(LS_KEY_GC, memGC);
  _loadLS(LS_KEY_RC, memRC);

  function _lruGet(mem, k) {
    if (!mem.has(k)) return null;
    const v = mem.get(k);
    mem.delete(k); mem.set(k, v); // move to recent
    return v;
  }
  function _lruSet(mem, k, v) {
    if (mem.has(k)) mem.delete(k);
    mem.set(k, v);
    while (mem.size > LRU_SIZE) {
      const firstKey = mem.keys().next().value;
      mem.delete(firstKey);
    }
  }

  // ---- Fetch JSON helper ----
  async function jsonFetch(url) {
    const res = await fetch(url, { credentials: 'same-origin', headers: { 'Accept': 'application/json' } });
    if (!res.ok) {
      const err = new Error('HTTP ' + res.status);
      try { err.body = await res.text(); } catch{}
      throw err;
    }
    return res.json();
  }

  // ---- API pública: geocodeAddress / reverseGeocode ----
  window.geocodeAddress = async function (address, focus) {
    const q = (address || '').trim().toLowerCase();
    if (!q) throw new Error('empty_query');

    // 1) cache hit (mem)
    const hitMem = _lruGet(memGC, q);
    if (hitMem) return hitMem;

    // 2) cache hit (localStorage)
    const hitLS = _lruGet(memGC, q); // tras _loadLS ya está en memGC
    if (hitLS) return hitLS; // (realmente cubierto arriba)

    // 3) red
    const params = new URLSearchParams({ q });
    if (focus && typeof focus.lat === 'number' && typeof focus.lon === 'number') {
      params.set('focus_lat', String(focus.lat));
      params.set('focus_lon', String(focus.lon));
    }
    const data = await jsonFetch(`/api/geocode/?${params.toString()}`);
    _lruSet(memGC, q, data);
    _saveLS(LS_KEY_GC, memGC);
    return data;
  };

  window.reverseGeocode = async function (lat, lon) {
    const key = `${Number(lat).toFixed(6)},${Number(lon).toFixed(6)}`;

    const hitMem = _lruGet(memRC, key);
    if (hitMem) return hitMem;

    const data = await jsonFetch(`/api/reverse/?lat=${encodeURIComponent(lat)}&lon=${encodeURIComponent(lon)}`);
    _lruSet(memRC, key, data);
    _saveLS(LS_KEY_RC, memRC);
    return data;
  };

  // ---- Relleno de inputs ----
  window.fillAddressInputs = function (props, mapping) {
    if (!props || !mapping) return;
    const get = k => (props[k] || '').toString();
    const put = (id, v) => { const el = document.getElementById(id); if (el && !el.value) el.value = v; }; // no pisar manual
    put(mapping.calle,   get('street'));
    put(mapping.numero,  get('housenumber'));
    put(mapping.colonia, get('district'));
    put(mapping.ciudad,  get('city'));
    put(mapping.estado,  get('state'));
    put(mapping.cp,      get('postcode'));
  };

  // ---- Debounce opcional para futuros autocompletes ----
  window.debounce = function (fn, wait) {
    let t; return (...args) => { clearTimeout(t); t = setTimeout(() => fn.apply(this, args), wait); };
  };

})();
