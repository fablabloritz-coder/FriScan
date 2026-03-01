/**
 * FrigoScan — Module Frigo (fridge.js)
 * Affichage, filtres, tri, actions sur le contenu du frigo.
 */

(function () {
    const Fridge = {};
    FrigoScan.Fridge = Fridge;

    let currentFilter = 'all';
    let currentSort = 'added_at';

    Fridge.load = async function () {
        setupListeners();
        await loadItems();
    };

    function setupListeners() {
        // Filtres
        document.querySelectorAll('#view-fridge .filter-tabs .tab-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('#view-fridge .filter-tabs .tab-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                currentFilter = btn.dataset.filter;
                loadItems();
            });
        });

        // Tri
        const sortEl = document.getElementById('fridge-sort');
        sortEl.addEventListener('change', () => {
            currentSort = sortEl.value;
            loadItems();
        });
    }

    async function loadItems() {
        let url = `/api/fridge/?sort=${currentSort}`;
        if (currentFilter === 'soon') url += '&filter_dlc=soon';
        else if (currentFilter === 'expired') url += '&filter_dlc=expired';

        const data = await FrigoScan.API.get(url);
        if (!data.success) return;

        const list = document.getElementById('fridge-list');
        const empty = document.getElementById('fridge-empty');

        if (data.items.length === 0) {
            list.innerHTML = '';
            empty.classList.remove('hidden');
            return;
        }

        empty.classList.add('hidden');

        // Si tri par catégorie, regrouper avec des en-têtes
        if (currentSort === 'category') {
            const CATEGORY_EMOJIS = {
                'fruits': '🍎', 'légumes': '🥕', 'viandes': '🥩', 'poissons': '🐟',
                'produits laitiers': '🧀', 'boulangerie': '🍞', 'boissons': '🍷',
                'féculents': '🌾', 'conserves': '🥫', 'surgelés': '❄️',
                'condiments': '🌶️', 'snacks': '🍪', 'oeufs': '🥚',
                'charcuterie': '🥓', 'autre': '📦'
            };
            const groups = {};
            data.items.forEach(item => {
                const cat = (item.category || 'autre').toLowerCase();
                if (!groups[cat]) groups[cat] = [];
                groups[cat].push(item);
            });

            let html = '';
            for (const [cat, items] of Object.entries(groups)) {
                const emoji = CATEGORY_EMOJIS[cat] || '📦';
                const catName = cat.charAt(0).toUpperCase() + cat.slice(1);
                html += `<div class="fridge-category-header">
                    <span class="fridge-category-emoji">${emoji}</span>
                    <span class="fridge-category-name">${catName}</span>
                    <span class="fridge-category-count">${items.length} produit${items.length > 1 ? 's' : ''}</span>
                </div>`;
                html += items.map(item => renderItem(item)).join('');
            }
            list.innerHTML = html;
        } else if (currentSort === 'dlc') {
            // Tri DLC : séparer les groupes (périmé, bientôt, ok)
            const expired = data.items.filter(i => i.dlc_status === 'expired');
            const soon = data.items.filter(i => i.dlc_status === 'soon');
            const ok = data.items.filter(i => i.dlc_status !== 'expired' && i.dlc_status !== 'soon');

            let html = '';
            if (expired.length) {
                html += `<div class="fridge-category-header fridge-header-expired">
                    <span class="fridge-category-emoji">⚠️</span>
                    <span class="fridge-category-name">Périmés</span>
                    <span class="fridge-category-count">${expired.length}</span>
                </div>`;
                html += expired.map(item => renderItem(item)).join('');
            }
            if (soon.length) {
                html += `<div class="fridge-category-header fridge-header-soon">
                    <span class="fridge-category-emoji">⏰</span>
                    <span class="fridge-category-name">Bientôt périmés</span>
                    <span class="fridge-category-count">${soon.length}</span>
                </div>`;
                html += soon.map(item => renderItem(item)).join('');
            }
            if (ok.length) {
                html += `<div class="fridge-category-header fridge-header-ok">
                    <span class="fridge-category-emoji">✅</span>
                    <span class="fridge-category-name">OK</span>
                    <span class="fridge-category-count">${ok.length}</span>
                </div>`;
                html += ok.map(item => renderItem(item)).join('');
            }
            list.innerHTML = html;
        } else {
            list.innerHTML = data.items.map(item => renderItem(item)).join('');
        }

        // Attacher les événements
        list.querySelectorAll('[data-action]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const action = btn.dataset.action;
                const id = parseInt(btn.dataset.id);
                handleAction(action, id);
            });
        });
    }

    function renderItem(item) {
        const dlcClass = item.dlc_status === 'soon' ? 'dlc-soon' : item.dlc_status === 'expired' ? 'dlc-expired' : '';
        let dlcBadge = '';
        if (item.dlc) {
            if (item.dlc_status === 'expired') {
                dlcBadge = `<span class="dlc-badge expired"><i class="fas fa-skull-crossbones"></i> Périmé (${Math.abs(item.dlc_days_left)}j)</span>`;
            } else if (item.dlc_status === 'soon') {
                dlcBadge = `<span class="dlc-badge soon"><i class="fas fa-clock"></i> ${item.dlc_days_left}j restant(s)</span>`;
            } else {
                dlcBadge = `<span class="dlc-badge ok"><i class="fas fa-check"></i> ${item.dlc_days_left}j</span>`;
            }
        }

        const imgHtml = item.image_url
            ? `<img class="fridge-item-img" src="${item.image_url}" alt="${item.name}" onerror="this.style.display='none'">`
            : `<div class="fridge-item-img" style="display:flex;align-items:center;justify-content:center;font-size:1.4rem;">🧊</div>`;

        return `
            <div class="fridge-item ${dlcClass}">
                ${imgHtml}
                <div class="fridge-item-info">
                    <div class="fridge-item-name">${item.name}</div>
                    <div class="fridge-item-meta">
                        <span>${item.quantity} ${item.unit}</span>
                        <span class="badge">${item.category || 'autre'}</span>
                        ${dlcBadge}
                    </div>
                </div>
                <div class="fridge-item-actions">
                    <button class="btn btn-success btn-sm" data-action="consume" data-id="${item.id}" title="Consommé">
                        <i class="fas fa-utensils"></i>
                    </button>
                    <button class="btn btn-warning btn-sm" data-action="extend" data-id="${item.id}" title="Prolonger DLC (+3j)">
                        <i class="fas fa-calendar-plus"></i>
                    </button>
                    <button class="btn btn-danger btn-sm" data-action="delete" data-id="${item.id}" title="Supprimer">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        `;
    }

    async function handleAction(action, id) {
        switch (action) {
            case 'consume': {
                const data = await FrigoScan.API.post(`/api/fridge/${id}/consume?user_name=Famille`);
                if (data.success) {
                    FrigoScan.toast(data.message, 'success');
                    if (data.stock_alert) {
                        FrigoScan.toast(data.stock_alert.message, 'warning');
                    }
                    loadItems();
                }
                break;
            }
            case 'extend': {
                const data = await FrigoScan.API.post(`/api/fridge/${id}/extend-dlc?days=3`);
                if (data.success) {
                    FrigoScan.toast(data.message, 'success');
                    loadItems();
                }
                break;
            }
            case 'delete': {
                const confirmed = await FrigoScan.confirm('Supprimer', 'Retirer ce produit du frigo ?');
                if (confirmed) {
                    const data = await FrigoScan.API.del(`/api/fridge/${id}`);
                    if (data.success) {
                        FrigoScan.toast(data.message, 'success');
                        loadItems();
                    }
                }
                break;
            }
        }
    }

})();
