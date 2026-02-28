// =====================================
// FriScan - Application Principale v2.0
// Interface Tactile - Surface Pro
// =====================================

const API_URL = '';
let allProducts = [];
let freshProducts = [];
let currentFilter = 'all';
let scannedProductData = null;
let currentPresetQty = { scan: null, manual: null };

// ========== SETTINGS ==========
const DEFAULT_SETTINGS = {
    expiryDays: 3,
    diets: [],
    scanInterval: 2.0
};

function getSettings() {
    try {
        const s = JSON.parse(localStorage.getItem('friscan_settings'));
        return { ...DEFAULT_SETTINGS, ...s };
    } catch { return { ...DEFAULT_SETTINGS }; }
}

function saveSettings(settings) {
    localStorage.setItem('friscan_settings', JSON.stringify(settings));
}

function loadSettingsUI() {
    const s = getSettings();
    const slider = document.getElementById('expiry-days-slider');
    const scanSlider = document.getElementById('scan-interval-slider');
    if (slider) { slider.value = s.expiryDays; updateExpiryDays(s.expiryDays); }
    if (scanSlider) { scanSlider.value = s.scanInterval; updateScanInterval(s.scanInterval); }
    // Diet buttons
    document.querySelectorAll('.diet-option').forEach(btn => {
        if (s.diets.includes(btn.dataset.diet)) btn.classList.add('active');
        else btn.classList.remove('active');
    });
}

function updateExpiryDays(val) {
    const v = parseInt(val);
    document.getElementById('expiry-days-value').textContent = v + ' jours';
    const s = getSettings();
    s.expiryDays = v;
    saveSettings(s);
}

function updateScanInterval(val) {
    const v = parseFloat(val);
    document.getElementById('scan-interval-value').textContent = v.toFixed(1) + 's';
    const s = getSettings();
    s.scanInterval = v;
    saveSettings(s);
}

function toggleDiet(btn) {
    btn.classList.toggle('active');
    const s = getSettings();
    s.diets = [...document.querySelectorAll('.diet-option.active')].map(b => b.dataset.diet);
    saveSettings(s);
}

// ========== FULLSCREEN ==========
function toggleFullscreen() {
    if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen().catch(() => {});
        document.body.classList.add('fullscreen-mode');
    } else {
        document.exitFullscreen().catch(() => {});
        document.body.classList.remove('fullscreen-mode');
    }
}

document.addEventListener('fullscreenchange', () => {
    const btn = document.getElementById('fullscreen-btn');
    if (document.fullscreenElement) {
        btn.innerHTML = '\u2716';
        document.body.classList.add('fullscreen-mode');
    } else {
        btn.innerHTML = '\u26F6';
        document.body.classList.remove('fullscreen-mode');
    }
});

// ========== TABS ==========
function initTabs() {
    document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            tab.classList.add('active');
            document.getElementById('tab-' + tab.dataset.tab).classList.add('active');
            if (tab.dataset.tab === 'fridge') loadProducts();
            if (tab.dataset.tab === 'recipes') loadRecipes();
            if (tab.dataset.tab === 'settings') loadSettingsUI();
        });
    });
}

// ========== NOTIFICATIONS ==========
function showNotification(message, type = 'info') {
    const container = document.getElementById('notifications');
    const n = document.createElement('div');
    n.className = 'notification ' + type;
    n.textContent = message;
    container.appendChild(n);
    setTimeout(() => { n.style.opacity = '0'; setTimeout(() => n.remove(), 300); }, 3000);
}

// ========== QUANTITY STEPPER ==========
function stepAmount(id, delta) {
    const el = document.getElementById(id);
    let val = parseInt(el.textContent) || 1;
    val = Math.max(1, val + delta);
    el.textContent = val;
}

function setPresetQty(context, preset) {
    currentPresetQty[context] = preset;
    // Toggle active class
    const parent = (context === 'scan')
        ? document.querySelector('#scan-result .quantity-presets')
        : document.querySelector('#tab-manual .quantity-presets');
    if (parent) {
        parent.querySelectorAll('.qty-preset-btn').forEach(b => b.classList.remove('active'));
        parent.querySelectorAll('.qty-preset-btn').forEach(b => {
            if (b.textContent.trim() === preset) b.classList.add('active');
        });
    }
}

// ========== FRESH PRODUCTS & QUICK ADD ==========
async function loadFreshProducts() {
    try {
        const res = await fetch(API_URL + '/api/fresh-products');
        freshProducts = await res.json();
        renderQuickProducts();
        renderCategoryFilter();
    } catch (e) { console.error('Fresh products error:', e); }
}

function renderCategoryFilter() {
    const container = document.getElementById('category-filter');
    if (!container) return;
    const categories = [...new Set(freshProducts.map(p => p.category))];
    container.innerHTML = '<button class="cat-filter-btn active" onclick="filterQuickProducts(\'all\', this)">Tous</button>';
    categories.forEach(cat => {
        const icon = freshProducts.find(p => p.category === cat)?.icon || '';
        container.innerHTML += '<button class="cat-filter-btn" onclick="filterQuickProducts(\'' + cat + '\', this)">' + icon + ' ' + cat + '</button>';
    });
}

function filterQuickProducts(cat, btn) {
    document.querySelectorAll('.cat-filter-btn').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');
    renderQuickProducts(cat === 'all' ? null : cat);
}

function renderQuickProducts(categoryFilter = null) {
    const grid = document.getElementById('quick-products-grid');
    if (!grid) return;
    let products = freshProducts;
    if (categoryFilter) products = products.filter(p => p.category === categoryFilter);
    grid.innerHTML = '';
    products.forEach(p => {
        grid.innerHTML += '<button class="quick-product-btn" onclick="quickAddProduct(\'' + p.name.replace(/'/g, "\\'") + '\')">' +
            '<span class="qp-icon">' + p.icon + '</span>' +
            '<span class="qp-name">' + p.name + '</span></button>';
    });
}

async function quickAddProduct(name) {
    const fresh = freshProducts.find(p => p.name === name);
    if (!fresh) return;
    const expiryDate = new Date();
    expiryDate.setDate(expiryDate.getDate() + (fresh.default_expiry_days || 7));
    const product = {
        name: fresh.name,
        category: fresh.category,
        expiry_date: expiryDate.toISOString().split('T')[0],
        amount: 1
    };
    try {
        const res = await fetch(API_URL + '/api/products', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(product)
        });
        if (res.ok) {
            showNotification(fresh.icon + ' ' + name + ' ajoute !', 'success');
            loadProducts();
        } else {
            showNotification('Erreur ajout', 'error');
        }
    } catch (e) { showNotification('Erreur reseau', 'error'); }
}

// ========== AUTOCOMPLETE ==========
function initAutocomplete() {
    const input = document.getElementById('manual-name');
    const list = document.getElementById('autocomplete-list');
    if (!input || !list) return;

    input.addEventListener('input', () => {
        const val = input.value.toLowerCase().trim();
        if (val.length < 2) { list.classList.add('hidden'); return; }
        const matches = freshProducts.filter(p =>
            p.name.toLowerCase().includes(val) ||
            p.keywords.some(k => k.toLowerCase().includes(val))
        ).slice(0, 8);
        if (matches.length === 0) { list.classList.add('hidden'); return; }
        list.innerHTML = '';
        matches.forEach(m => {
            const item = document.createElement('div');
            item.className = 'autocomplete-item';
            item.innerHTML = '<span class="ac-icon">' + m.icon + '</span><div><div class="ac-name">' + m.name + '</div><div class="ac-meta">' + m.category + ' - DLC ' + m.default_expiry_days + 'j</div></div>';
            item.addEventListener('click', () => selectFreshProduct(m));
            list.appendChild(item);
        });
        list.classList.remove('hidden');
    });

    document.addEventListener('click', (e) => {
        if (!e.target.closest('.autocomplete-wrapper')) list.classList.add('hidden');
    });
}

function selectFreshProduct(product) {
    document.getElementById('manual-name').value = product.name;
    document.getElementById('autocomplete-list').classList.add('hidden');
    // Set category
    const catSelect = document.getElementById('manual-category');
    for (let i = 0; i < catSelect.options.length; i++) {
        if (catSelect.options[i].value === product.category) { catSelect.selectedIndex = i; break; }
    }
    // Set default expiry
    const expiryDate = new Date();
    expiryDate.setDate(expiryDate.getDate() + (product.default_expiry_days || 7));
    document.getElementById('manual-expiry').value = expiryDate.toISOString().split('T')[0];
    // Show info
    const info = document.getElementById('fresh-info');
    info.innerHTML = product.icon + ' <strong>' + product.name + '</strong> - DLC par defaut : ' + product.default_expiry_days + ' jours';
    info.classList.remove('hidden');
}

// ========== BARCODE SEARCH ==========
async function searchBarcode() {
    const barcode = document.getElementById('barcode-input').value.trim();
    if (!barcode) { showNotification('Entrez un code-barres', 'warning'); return; }
    try {
        showNotification('Recherche...', 'info');
        const res = await fetch(API_URL + '/api/barcode/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ barcode })
        });
        const data = await res.json();
        if (data.found) {
            displayScannedProduct(data.product);
        } else {
            showNotification('Produit non trouve dans OpenFoodFacts', 'warning');
        }
    } catch (e) { showNotification('Erreur de recherche', 'error'); }
}

function displayScannedProduct(product) {
    scannedProductData = product;
    document.getElementById('scan-name').textContent = product.name || 'Produit inconnu';
    document.getElementById('scan-brand').textContent = product.brand ? 'Marque: ' + product.brand : '';
    document.getElementById('scan-category').textContent = product.category ? 'Cat: ' + product.category : '';
    document.getElementById('scan-qty-info').textContent = product.quantity || '';

    const img = document.getElementById('scan-img');
    if (product.image_url) { img.src = product.image_url; img.style.display = 'block'; }
    else { img.style.display = 'none'; }

    const ns = document.getElementById('scan-nutriscore');
    if (product.nutriscore) {
        ns.innerHTML = '<span class="nutriscore nutriscore-' + product.nutriscore + '">Nutri-Score ' + product.nutriscore.toUpperCase() + '</span>';
    } else { ns.innerHTML = ''; }

    document.getElementById('scan-result').classList.remove('hidden');
    document.getElementById('scan-amount').textContent = '1';
    currentPresetQty.scan = null;
}

async function addScannedProduct() {
    if (!scannedProductData) return;
    const expiry = document.getElementById('scan-expiry').value;
    if (!expiry) { showNotification('Indiquez la date de peremption', 'warning'); return; }
    const amount = parseInt(document.getElementById('scan-amount').textContent) || 1;
    const notes = currentPresetQty.scan ? currentPresetQty.scan : '';
    const product = {
        name: scannedProductData.name || 'Produit scanne',
        barcode: scannedProductData.barcode || '',
        category: scannedProductData.category || 'Autre',
        expiry_date: expiry,
        amount: amount,
        brand: scannedProductData.brand || '',
        image_url: scannedProductData.image_url || '',
        nutriscore: scannedProductData.nutriscore || '',
        notes: notes
    };
    try {
        const res = await fetch(API_URL + '/api/products', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(product)
        });
        if (res.ok) {
            showNotification('Produit ajoute au frigo !', 'success');
            document.getElementById('scan-result').classList.add('hidden');
            document.getElementById('barcode-input').value = '';
            scannedProductData = null;
            loadProducts();
        } else { showNotification('Erreur ajout', 'error'); }
    } catch (e) { showNotification('Erreur reseau', 'error'); }
}

// ========== MANUAL ADD ==========
async function addManualProduct() {
    const name = document.getElementById('manual-name').value.trim();
    if (!name) { showNotification('Entrez un nom de produit', 'warning'); return; }
    const category = document.getElementById('manual-category').value;
    const expiry = document.getElementById('manual-expiry').value;
    const amount = parseInt(document.getElementById('manual-amount').textContent) || 1;
    const notes = currentPresetQty.manual ? currentPresetQty.manual : '';
    if (!expiry) { showNotification('Indiquez la date de peremption', 'warning'); return; }
    const product = {
        name: name,
        category: category,
        expiry_date: expiry,
        amount: amount,
        notes: notes
    };
    try {
        const res = await fetch(API_URL + '/api/products', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(product)
        });
        if (res.ok) {
            showNotification('Produit ajoute !', 'success');
            document.getElementById('manual-name').value = '';
            document.getElementById('manual-expiry').value = '';
            document.getElementById('manual-amount').textContent = '1';
            document.getElementById('fresh-info').classList.add('hidden');
            currentPresetQty.manual = null;
            document.querySelectorAll('#tab-manual .qty-preset-btn').forEach(b => b.classList.remove('active'));
            loadProducts();
        } else { showNotification('Erreur ajout', 'error'); }
    } catch (e) { showNotification('Erreur reseau', 'error'); }
}

// ========== PRODUCTS (FRIDGE) ==========
async function loadProducts() {
    try {
        const settings = getSettings();
        let url = API_URL + '/api/products';
        const params = [];
        if (currentFilter === 'expiring') params.push('expiring_soon=' + settings.expiryDays);
        if (currentFilter === 'expired') params.push('expired=true');
        if (params.length) url += '?' + params.join('&');
        const res = await fetch(url);
        allProducts = await res.json();
        renderProducts();
        updateStats();
    } catch (e) { console.error('Load error:', e); }
}

function renderProducts() {
    const grid = document.getElementById('products-grid');
    const empty = document.getElementById('empty-fridge');
    const searchVal = (document.getElementById('search-input')?.value || '').toLowerCase();
    let products = allProducts;
    if (searchVal) products = products.filter(p => p.name.toLowerCase().includes(searchVal));
    if (products.length === 0) {
        grid.innerHTML = '';
        empty.classList.remove('hidden');
        return;
    }
    empty.classList.add('hidden');
    const settings = getSettings();
    grid.innerHTML = products.map(p => {
        const days = daysUntilExpiry(p.expiry_date);
        let status = 'ok', statusClass = '';
        if (days < 0) { status = 'expire'; statusClass = 'expired'; }
        else if (days <= settings.expiryDays) { status = 'bientot'; statusClass = 'expiring'; }
        const expiryText = days < 0 ? 'Expire depuis ' + Math.abs(days) + 'j' :
            days === 0 ? 'Expire aujourd\'hui !' :
            days <= settings.expiryDays ? 'Expire dans ' + days + 'j' :
            'OK - ' + days + ' jours restants';
        const expiryClass = days < 0 ? 'danger' : days <= settings.expiryDays ? 'warning' : 'ok';
        return '<div class="product-card ' + statusClass + '">' +
            '<div class="card-header"><div class="card-name">' + p.name + '</div>' +
            '<div class="card-amount">' + (p.amount || 1) + '</div></div>' +
            '<div class="card-details">' + (p.category || '') + (p.notes ? ' - ' + p.notes : '') + '</div>' +
            '<div class="card-details">' + formatDate(p.expiry_date) + '</div>' +
            '<div class="card-expiry ' + expiryClass + '">' + expiryText + '</div>' +
            '<div class="card-actions">' +
            '<button class="btn btn-secondary" onclick="consumeProduct(' + p.id + ')">-1</button>' +
            '<button class="btn btn-danger" onclick="deleteProduct(' + p.id + ')">Suppr</button>' +
            '</div></div>';
    }).join('');
}

function setFilter(filter, btn) {
    currentFilter = filter;
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');
    loadProducts();
}

async function consumeProduct(id) {
    try {
        await fetch(API_URL + '/api/products/' + id + '/consume', { method: 'POST' });
        showNotification('Produit consomme', 'success');
        loadProducts();
    } catch (e) { showNotification('Erreur', 'error'); }
}

async function deleteProduct(id) {
    try {
        await fetch(API_URL + '/api/products/' + id, { method: 'DELETE' });
        showNotification('Produit supprime', 'success');
        loadProducts();
    } catch (e) { showNotification('Erreur', 'error'); }
}

async function confirmClearAll() {
    if (!confirm('Supprimer TOUS les produits du frigo ?')) return;
    try {
        for (const p of allProducts) {
            await fetch(API_URL + '/api/products/' + p.id, { method: 'DELETE' });
        }
        showNotification('Frigo vide !', 'success');
        loadProducts();
    } catch (e) { showNotification('Erreur', 'error'); }
}

// ========== STATS ==========
async function updateStats() {
    try {
        const res = await fetch(API_URL + '/api/products/stats/summary');
        const stats = await res.json();
        document.getElementById('stat-total').textContent = '\ud83d\udce6 ' + (stats.total || 0) + ' produits';
        document.getElementById('stat-expiring').textContent = '\u26a0\ufe0f ' + (stats.expiring_soon || 0) + ' bientot';
        document.getElementById('stat-expired').textContent = '\u274c ' + (stats.expired || 0) + ' expires';
    } catch (e) {}
}

// ========== RECIPES ==========
async function loadRecipes() {
    try {
        const settings = getSettings();
        let url = API_URL + '/api/recipes/suggestions?max_results=12&min_match=0.2&prioritize_expiring=true';
        // Diet filter from dropdown or settings
        const dietDropdown = document.getElementById('diet-filter');
        let diet = dietDropdown ? dietDropdown.value : '';
        if (!diet && settings.diets.length > 0) {
            diet = settings.diets.join(',');
        }
        if (diet) url += '&diet=' + encodeURIComponent(diet);
        url += '&expiry_days=' + settings.expiryDays;
        const res = await fetch(url);
        const recipes = await res.json();
        renderRecipes(recipes);
    } catch (e) {
        console.error('Recipes error:', e);
        document.getElementById('recipes-grid').innerHTML = '';
        document.getElementById('empty-recipes')?.classList.remove('hidden');
    }
}

function renderRecipes(recipes) {
    const grid = document.getElementById('recipes-grid');
    const empty = document.getElementById('empty-recipes');
    if (!recipes || recipes.length === 0) {
        grid.innerHTML = '';
        empty?.classList.remove('hidden');
        return;
    }
    empty?.classList.add('hidden');
    grid.innerHTML = recipes.map(r => {
        const pct = Math.round((r.match_score || 0) * 100);
        const scoreClass = pct >= 70 ? 'high' : pct >= 40 ? 'medium' : '';
        const dietTags = (r.diet_tags || []).map(t => '<span class="diet-tag">' + t + '</span>').join('');
        const matched = (r.matched_ingredients || []).map(i => '<span class="ingredient-tag matched">\u2713 ' + i + '</span>').join('');
        const missing = (r.missing_ingredients || []).map(i => '<span class="ingredient-tag missing">' + i + '</span>').join('');
        return '<div class="recipe-card">' +
            '<div class="recipe-header"><div class="recipe-name">' + r.name + '</div>' +
            '<span class="match-score ' + scoreClass + '">' + pct + '%</span></div>' +
            '<div class="recipe-meta">\u23f1 ' + (r.prep_time || '?') + ' min | \ud83c\udf7d ' + (r.servings || '?') + ' pers.</div>' +
            (dietTags ? '<div class="recipe-tags">' + dietTags + '</div>' : '') +
            '<div class="ingredient-list">' + matched + missing + '</div>' +
            '<div class="recipe-instructions">' + (r.instructions || '') + '</div>' +
            '<button class="btn-expand" onclick="this.parentElement.classList.toggle(\'expanded\')">Voir la recette</button>' +
            '</div>';
    }).join('');
}

// ========== HELPERS ==========
function daysUntilExpiry(dateStr) {
    if (!dateStr) return 999;
    const expiry = new Date(dateStr + 'T00:00:00');
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    return Math.ceil((expiry - today) / 86400000);
}

function formatDate(dateStr) {
    if (!dateStr) return '';
    const d = new Date(dateStr + 'T00:00:00');
    return d.toLocaleDateString('fr-FR', { day: 'numeric', month: 'short', year: 'numeric' });
}

// ========== USB SCANNER DETECTION ==========
let usbBuffer = '';
let usbTimer = null;

document.addEventListener('keypress', (e) => {
    // USB scanners fire rapid keypress events
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') return;
    if (e.key === 'Enter' && usbBuffer.length >= 8) {
        const barcode = usbBuffer;
        usbBuffer = '';
        document.getElementById('barcode-input').value = barcode;
        searchBarcode();
        return;
    }
    usbBuffer += e.key;
    clearTimeout(usbTimer);
    usbTimer = setTimeout(() => { usbBuffer = ''; }, 200);
});

// ========== SEARCH ==========
function initSearch() {
    const input = document.getElementById('search-input');
    if (input) {
        input.addEventListener('input', () => renderProducts());
    }
}

// ========== INIT ==========
document.addEventListener('DOMContentLoaded', () => {
    initTabs();
    initSearch();
    initAutocomplete();
    loadSettingsUI();
    loadFreshProducts();
    loadProducts();

    // Fullscreen button
    document.getElementById('fullscreen-btn')?.addEventListener('click', toggleFullscreen);
});
