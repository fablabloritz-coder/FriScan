/**
 * FriScan — Application principale (JavaScript)
 * Gestion des onglets, notifications, chargement des données.
 */

const API_BASE = '';

// ════════════════════════ TABS ════════════════════════

document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
        // Désactiver tous les onglets
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

        // Activer l'onglet cliqué
        tab.classList.add('active');
        const tabId = `tab-${tab.dataset.tab}`;
        document.getElementById(tabId).classList.add('active');

        // Charger les données si nécessaire
        if (tab.dataset.tab === 'fridge') loadProducts();
        if (tab.dataset.tab === 'recipes') loadRecipes();
    });
});


// ════════════════════════ NOTIFICATIONS ════════════════════════

function notify(message, type = 'info', duration = 3500) {
    const container = document.getElementById('notifications');
    const el = document.createElement('div');
    el.className = `notification ${type}`;
    el.textContent = message;
    container.appendChild(el);

    setTimeout(() => {
        el.style.opacity = '0';
        el.style.transform = 'translateX(30px)';
        el.style.transition = 'all 0.3s';
        setTimeout(() => el.remove(), 300);
    }, duration);
}


// ════════════════════════ STATS ════════════════════════

async function loadStats() {
    try {
        const res = await fetch(`${API_BASE}/api/products/stats/summary`);
        if (!res.ok) return;
        const data = await res.json();

        document.getElementById('stat-total').textContent = `${data.total_products} produit${data.total_products !== 1 ? 's' : ''}`;
        document.getElementById('stat-expiring').textContent = `${data.expiring_in_3_days} bientôt périmé${data.expiring_in_3_days !== 1 ? 's' : ''}`;
        document.getElementById('stat-expired').textContent = `${data.expired} périmé${data.expired !== 1 ? 's' : ''}`;
    } catch (e) {
        console.error('Erreur chargement stats:', e);
    }
}


// ════════════════════════ PRODUCTS ════════════════════════

let allProducts = [];

async function loadProducts() {
    try {
        const filter = document.getElementById('filter-select')?.value || 'all';
        let url = `${API_BASE}/api/products/`;

        if (filter === 'in_fridge') url += '?in_fridge=true';
        else if (filter === 'expiring') url += '?expiring_soon=3';
        else if (filter === 'expired') url += '?expiring_soon=0';

        const res = await fetch(url);
        if (!res.ok) throw new Error('Erreur serveur');
        allProducts = await res.json();

        renderProducts(allProducts);
        loadStats();
    } catch (e) {
        console.error('Erreur chargement produits:', e);
        notify('Erreur lors du chargement des produits', 'error');
    }
}

function filterProducts() {
    const search = document.getElementById('search-input').value.toLowerCase();
    const filtered = allProducts.filter(p =>
        p.name.toLowerCase().includes(search) ||
        (p.brand && p.brand.toLowerCase().includes(search)) ||
        (p.category && p.category.toLowerCase().includes(search))
    );
    renderProducts(filtered);
}

function renderProducts(products) {
    const container = document.getElementById('products-list');
    const emptyState = document.getElementById('empty-fridge');

    if (products.length === 0) {
        container.innerHTML = '';
        emptyState.classList.remove('hidden');
        return;
    }

    emptyState.classList.add('hidden');
    container.innerHTML = products.map(p => {
        let expiryClass = 'ok';
        let expiryText = 'Pas de date';

        if (p.days_until_expiry !== null) {
            if (p.days_until_expiry < 0) {
                expiryClass = 'danger';
                expiryText = `❌ Périmé depuis ${Math.abs(p.days_until_expiry)} jour(s)`;
            } else if (p.days_until_expiry <= 3) {
                expiryClass = 'warning';
                expiryText = `⚠️ Périme dans ${p.days_until_expiry} jour(s)`;
            } else {
                expiryText = `✅ ${p.days_until_expiry} jours restants`;
            }
        }

        const cardClass = p.days_until_expiry !== null
            ? (p.days_until_expiry < 0 ? 'expired' : (p.days_until_expiry <= 3 ? 'expiring' : ''))
            : '';

        const image = p.image_url
            ? `<img src="${p.image_url}" alt="${p.name}" class="product-image" style="width:60px;height:60px;float:right;margin-left:10px;">`
            : '';

        return `
            <div class="product-card ${cardClass}">
                ${image}
                <div class="card-header">
                    <span class="card-name">${escapeHtml(p.name)}</span>
                    <span class="card-amount">${p.amount}</span>
                </div>
                ${p.brand ? `<div class="card-details">🏷️ ${escapeHtml(p.brand)}</div>` : ''}
                ${p.category ? `<div class="card-details">📂 ${escapeHtml(p.category)}</div>` : ''}
                ${p.quantity ? `<div class="card-details">📦 ${escapeHtml(p.quantity)}</div>` : ''}
                ${p.nutriscore ? `<span class="nutriscore nutriscore-${p.nutriscore}">${p.nutriscore.toUpperCase()}</span>` : ''}
                <div class="card-expiry ${expiryClass}">${expiryText}</div>
                <div class="card-actions">
                    <button class="btn btn-primary" onclick="consumeProduct(${p.id})">
                        ✅ Consommé
                    </button>
                    <button class="btn btn-danger" onclick="deleteProduct(${p.id}, '${escapeHtml(p.name)}')">
                        🗑️
                    </button>
                </div>
            </div>
        `;
    }).join('');
}


// ════════════════════════ CONSUME / DELETE ════════════════════════

async function consumeProduct(id) {
    try {
        const res = await fetch(`${API_BASE}/api/products/${id}/consume`, { method: 'POST' });
        if (!res.ok) throw new Error();
        notify('Produit consommé !', 'success');
        loadProducts();
    } catch (e) {
        notify('Erreur lors de la consommation', 'error');
    }
}

async function deleteProduct(id, name) {
    if (!confirm(`Supprimer "${name}" du frigo ?`)) return;
    try {
        const res = await fetch(`${API_BASE}/api/products/${id}`, { method: 'DELETE' });
        if (!res.ok) throw new Error();
        notify(`"${name}" supprimé`, 'success');
        loadProducts();
    } catch (e) {
        notify('Erreur lors de la suppression', 'error');
    }
}


// ════════════════════════ BARCODE SEARCH ════════════════════════

// Variable globale pour stocker le produit scanné
let scannedProduct = null;

async function searchBarcode() {
    const input = document.getElementById('barcode-input');
    const barcode = input.value.trim();

    if (!barcode) {
        notify('Veuillez entrer un code-barres', 'warning');
        return;
    }

    notify('Recherche en cours...', 'info', 2000);

    try {
        const res = await fetch(`${API_BASE}/api/scanner/barcode`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ barcode }),
        });

        if (res.status === 422) {
            const err = await res.json();
            notify(err.detail, 'error');
            return;
        }

        if (!res.ok) throw new Error();

        scannedProduct = await res.json();
        displayScannedProduct(scannedProduct);
        notify('Produit trouvé !', 'success');
    } catch (e) {
        notify('Erreur lors de la recherche', 'error');
    }
}

function displayScannedProduct(product) {
    const result = document.getElementById('scan-result');
    result.classList.remove('hidden');

    document.getElementById('result-name').textContent = product.name;
    document.getElementById('result-brand').textContent = product.brand ? `🏷️ ${product.brand}` : '';
    document.getElementById('result-category').textContent = product.category ? `📂 ${product.category}` : '';
    document.getElementById('result-quantity').textContent = product.quantity ? `📦 ${product.quantity}` : '';

    const img = document.getElementById('result-image');
    if (product.image_url) {
        img.src = product.image_url;
        img.style.display = 'block';
    } else {
        img.style.display = 'none';
    }

    const nutri = document.getElementById('result-nutriscore');
    if (product.nutriscore) {
        nutri.textContent = `Nutri-Score : ${product.nutriscore.toUpperCase()}`;
        nutri.className = `nutriscore nutriscore-${product.nutriscore}`;
    } else {
        nutri.textContent = '';
        nutri.className = 'nutriscore';
    }

    // Reset date et quantité
    document.getElementById('result-expiry').value = '';
    document.getElementById('result-amount').value = '1';

    // Scroll vers le résultat
    result.scrollIntoView({ behavior: 'smooth', block: 'center' });
}


// ════════════════════════ ADD PRODUCTS ════════════════════════

async function addScannedProduct() {
    if (!scannedProduct) {
        notify('Aucun produit scanné', 'warning');
        return;
    }

    const expiry = document.getElementById('result-expiry').value || null;
    const amount = parseInt(document.getElementById('result-amount').value) || 1;

    const productData = {
        barcode: scannedProduct.barcode,
        name: scannedProduct.name,
        brand: scannedProduct.brand,
        category: scannedProduct.category,
        image_url: scannedProduct.image_url,
        quantity: scannedProduct.quantity,
        nutriscore: scannedProduct.nutriscore,
        expiry_date: expiry,
        amount: amount,
    };

    try {
        const res = await fetch(`${API_BASE}/api/products/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(productData),
        });

        if (!res.ok) throw new Error();

        notify(`"${scannedProduct.name}" ajouté au frigo !`, 'success');
        document.getElementById('scan-result').classList.add('hidden');
        document.getElementById('barcode-input').value = '';
        scannedProduct = null;
        loadStats();
    } catch (e) {
        notify('Erreur lors de l\'ajout', 'error');
    }
}

async function addManualProduct(event) {
    event.preventDefault();

    const name = document.getElementById('manual-name').value.trim();
    if (!name) {
        notify('Veuillez entrer un nom de produit', 'warning');
        return;
    }

    const productData = {
        name: name,
        category: document.getElementById('manual-category').value || null,
        quantity: document.getElementById('manual-quantity').value || null,
        expiry_date: document.getElementById('manual-expiry').value || null,
        amount: parseInt(document.getElementById('manual-amount').value) || 1,
    };

    try {
        const res = await fetch(`${API_BASE}/api/products/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(productData),
        });

        if (!res.ok) throw new Error();

        notify(`"${name}" ajouté au frigo !`, 'success');
        document.getElementById('manual-form').reset();
        document.getElementById('manual-amount').value = '1';
        loadStats();
    } catch (e) {
        notify('Erreur lors de l\'ajout', 'error');
    }
}


// ════════════════════════ RECIPES ════════════════════════

async function loadRecipes() {
    try {
        const res = await fetch(`${API_BASE}/api/recipes/suggestions?max_results=10&min_match=0.3`);
        if (!res.ok) throw new Error();

        const recipes = await res.json();
        renderRecipes(recipes);
    } catch (e) {
        console.error('Erreur chargement recettes:', e);
        notify('Erreur lors du chargement des recettes', 'error');
    }
}

function renderRecipes(recipes) {
    const container = document.getElementById('recipes-list');
    const emptyState = document.getElementById('no-recipes');

    if (recipes.length === 0) {
        container.innerHTML = '';
        emptyState.classList.remove('hidden');
        return;
    }

    emptyState.classList.add('hidden');
    container.innerHTML = recipes.map((r, i) => {
        const scorePercent = Math.round(r.match_score * 100);
        const scoreClass = r.match_score >= 0.7 ? 'high' : (r.match_score >= 0.5 ? 'medium' : '');

        const ingredients = [
            ...r.matched_ingredients.map(ing => `<span class="ingredient-tag matched">✅ ${escapeHtml(ing)}</span>`),
            ...r.missing_ingredients.map(ing => `<span class="ingredient-tag missing">❌ ${escapeHtml(ing)}</span>`),
        ].join('');

        return `
            <div class="recipe-card" id="recipe-${i}">
                <div class="recipe-header">
                    <span class="recipe-name">${escapeHtml(r.name)}</span>
                    <span class="match-score ${scoreClass}">${scorePercent}% match</span>
                </div>
                <div class="recipe-meta">
                    ${r.prep_time ? `⏱️ ${r.prep_time}` : ''}
                    ${r.servings ? ` · 👥 ${r.servings} pers.` : ''}
                </div>
                <div class="ingredient-list">${ingredients}</div>
                <button class="btn-expand" onclick="toggleRecipe(${i})">
                    📖 Voir les instructions
                </button>
                <div class="recipe-instructions">${escapeHtml(r.instructions)}</div>
            </div>
        `;
    }).join('');
}

function toggleRecipe(index) {
    const card = document.getElementById(`recipe-${index}`);
    card.classList.toggle('expanded');
    const btn = card.querySelector('.btn-expand');
    btn.textContent = card.classList.contains('expanded')
        ? '🔼 Masquer les instructions'
        : '📖 Voir les instructions';
}


// ════════════════════════ MODAL ════════════════════════

function closeModal() {
    document.getElementById('product-modal').classList.add('hidden');
}


// ════════════════════════ UTILITIES ════════════════════════

function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

// Détection douchette USB : saisie rapide dans le champ code-barres
let barcodeBuffer = '';
let barcodeTimeout = null;

document.addEventListener('keypress', (e) => {
    // Si on est dans le champ de scan et la saisie est rapide (douchette)
    const input = document.getElementById('barcode-input');
    if (document.activeElement === input) return; // laisser la saisie normale

    // La douchette envoie les caractères très rapidement puis Enter
    if (e.key === 'Enter' && barcodeBuffer.length >= 8) {
        document.getElementById('barcode-input').value = barcodeBuffer;
        searchBarcode();
        barcodeBuffer = '';
        return;
    }

    if (/\d/.test(e.key)) {
        barcodeBuffer += e.key;
        clearTimeout(barcodeTimeout);
        barcodeTimeout = setTimeout(() => { barcodeBuffer = ''; }, 200);
    }
});


// ════════════════════════ AUTOCOMPLÉTION PRODUITS FRAIS ════════════════════════

let acDebounce = null;
let freshProducts = [];           // cache référentiel complet
let selectedFreshProduct = null;  // produit frais sélectionné

/**
 * Appelé à chaque saisie dans le champ nom (ajout manuel).
 * Interroge l'API de recherche de produits frais pour l'autocomplétion.
 */
function onManualNameInput(value) {
    selectedFreshProduct = null;
    hideFreshInfo();

    clearTimeout(acDebounce);
    const query = value.trim();

    if (query.length < 2) {
        hideAutocomplete();
        return;
    }

    acDebounce = setTimeout(async () => {
        try {
            const res = await fetch(`${API_BASE}/api/fresh/search/${encodeURIComponent(query)}`);
            if (!res.ok) return;
            const results = await res.json();
            renderAutocomplete(results);
        } catch (e) {
            console.error('Erreur autocomplétion:', e);
        }
    }, 250);
}

function renderAutocomplete(results) {
    const list = document.getElementById('autocomplete-list');
    if (!results.length) {
        hideAutocomplete();
        return;
    }

    list.innerHTML = results.map((p, i) => `
        <div class="autocomplete-item" onclick="selectFreshProduct(${i})" data-index="${i}">
            <span class="ac-icon">${p.icon}</span>
            <span class="ac-name">${escapeHtml(p.name)}</span>
            <span class="ac-meta">${escapeHtml(p.category)} · ${p.default_expiry_days}j</span>
        </div>
    `).join('');

    // Stocker les résultats pour pouvoir les sélectionner
    list._results = results;
    list.classList.remove('hidden');
}

function selectFreshProduct(index) {
    const list = document.getElementById('autocomplete-list');
    const product = list._results[index];
    if (!product) return;

    selectedFreshProduct = product;

    // Remplir le nom
    document.getElementById('manual-name').value = product.name;

    // Remplir la catégorie
    const catSelect = document.getElementById('manual-category');
    for (let opt of catSelect.options) {
        if (opt.value === product.category) { opt.selected = true; break; }
    }

    // Calculer et remplir la date de péremption par défaut
    const expDate = new Date();
    expDate.setDate(expDate.getDate() + product.default_expiry_days);
    document.getElementById('manual-expiry').value = expDate.toISOString().split('T')[0];

    // Afficher l'info produit frais
    showFreshInfo(product);

    hideAutocomplete();
}

function showFreshInfo(product) {
    const info = document.getElementById('fresh-info');
    document.getElementById('fresh-icon').textContent = product.icon;
    document.getElementById('fresh-msg').textContent =
        `${product.name} — se conserve environ ${product.default_expiry_days} jours (${product.category})`;
    info.classList.remove('hidden');
}

function hideFreshInfo() {
    document.getElementById('fresh-info')?.classList.add('hidden');
}

function hideAutocomplete() {
    document.getElementById('autocomplete-list')?.classList.add('hidden');
}

// Fermer l'autocomplétion quand on clique ailleurs
document.addEventListener('click', (e) => {
    if (!e.target.closest('.autocomplete-wrapper')) {
        hideAutocomplete();
    }
});

// Navigation clavier dans l'autocomplétion
document.addEventListener('keydown', (e) => {
    const list = document.getElementById('autocomplete-list');
    if (!list || list.classList.contains('hidden')) return;
    if (document.activeElement?.id !== 'manual-name') return;

    const items = list.querySelectorAll('.autocomplete-item');
    if (!items.length) return;

    let current = list.querySelector('.autocomplete-item.selected');
    let idx = current ? Array.from(items).indexOf(current) : -1;

    if (e.key === 'ArrowDown') {
        e.preventDefault();
        if (current) current.classList.remove('selected');
        idx = (idx + 1) % items.length;
        items[idx].classList.add('selected');
        items[idx].scrollIntoView({ block: 'nearest' });
    } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        if (current) current.classList.remove('selected');
        idx = idx <= 0 ? items.length - 1 : idx - 1;
        items[idx].classList.add('selected');
        items[idx].scrollIntoView({ block: 'nearest' });
    } else if (e.key === 'Enter') {
        if (idx >= 0) {
            e.preventDefault();
            selectFreshProduct(idx);
        }
    } else if (e.key === 'Escape') {
        hideAutocomplete();
    }
});


// ════════════════════════ GRILLE PRODUITS RAPIDES ════════════════════════

async function loadQuickProducts() {
    try {
        const res = await fetch(`${API_BASE}/api/fresh/`);
        if (!res.ok) return;
        freshProducts = await res.json();

        // Afficher les 20 premiers produits les plus courants
        const grid = document.getElementById('quick-products');
        if (!grid) return;

        const popular = freshProducts.slice(0, 24);
        grid.innerHTML = popular.map((p, i) => `
            <button type="button" class="quick-product-btn" onclick="quickAddProduct(${i})"
                    title="${p.name} (${p.category}, ~${p.default_expiry_days}j)">
                <span class="qp-icon">${p.icon}</span>
                <span class="qp-name">${escapeHtml(p.name)}</span>
            </button>
        `).join('');

        // Stocker pour le clic
        grid._products = popular;
    } catch (e) {
        console.error('Erreur chargement produits rapides:', e);
    }
}

function quickAddProduct(index) {
    const grid = document.getElementById('quick-products');
    const product = grid._products?.[index];
    if (!product) return;

    // Remplir le formulaire
    document.getElementById('manual-name').value = product.name;

    const catSelect = document.getElementById('manual-category');
    for (let opt of catSelect.options) {
        if (opt.value === product.category) { opt.selected = true; break; }
    }

    const expDate = new Date();
    expDate.setDate(expDate.getDate() + product.default_expiry_days);
    document.getElementById('manual-expiry').value = expDate.toISOString().split('T')[0];

    showFreshInfo(product);
    selectedFreshProduct = product;

    // Scroll vers le formulaire
    document.getElementById('manual-form').scrollIntoView({ behavior: 'smooth', block: 'center' });
}


// ════════════════════════ INIT ════════════════════════

document.addEventListener('DOMContentLoaded', () => {
    loadStats();
    loadQuickProducts();
    console.log('🧊 FriScan initialisé');
});
