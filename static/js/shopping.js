/**
 * FrigoScan — Module Liste de courses (shopping.js)
 */

(function () {
    const Shopping = {};
    FrigoScan.Shopping = Shopping;

    let currentItems = []; // Suivi des articles actuels

    Shopping.load = async function () {
        setupListeners();
        await loadList();
    };

    function setupListeners() {
        const addBtn = document.getElementById('btn-shopping-add');
        const addInput = document.getElementById('shopping-add-input');

        addBtn.onclick = addItem;
        addInput.onkeydown = (e) => { if (e.key === 'Enter') addItem(); };

        document.getElementById('btn-shopping-select-all').onclick = selectAll;
        document.getElementById('btn-shopping-deselect-all').onclick = deselectAll;
        document.getElementById('btn-shopping-add-all-fridge').onclick = addAllToFridge;
        document.getElementById('btn-shopping-check-stocks').onclick = checkStocks;
        document.getElementById('btn-shopping-clear-done').onclick = clearPurchased;
        document.getElementById('btn-shopping-clear-all').onclick = clearAll;
    }

    async function loadList() {
        const data = await FrigoScan.API.get('/api/shopping/?show_purchased=true');
        currentItems = data.items || [];
        renderList(currentItems);
    }

    function renderList(items) {
        const list = document.getElementById('shopping-list');
        if (items.length === 0) {
            list.innerHTML = '<div class="empty-state"><i class="fas fa-shopping-cart"></i><p>Liste de courses vide.</p></div>';
            updateAddAllFridgeButton();
            return;
        }

        list.innerHTML = items.map(item => {
            const purchasedClass = item.is_purchased ? 'purchased' : '';
            const sourceLabels = { manual: 'Manuel', stock_alert: 'Stock bas', weekly_menu: 'Menu' };
            return `
                <div class="shopping-item ${purchasedClass}" data-id="${item.id}">
                    <input type="checkbox" class="shopping-item-checkbox" ${item.is_purchased ? 'checked' : ''}
                           data-id="${item.id}"
                           onchange="FrigoScan.Shopping.handleCheckboxChange(${item.id})">
                    <span class="shopping-item-name">${item.product_name}</span>
                    <span class="shopping-item-qty">${item.quantity} ${item.unit}</span>
                    <span class="shopping-item-source">${sourceLabels[item.source] || item.source}</span>
                    <button class="btn btn-success btn-sm" onclick="FrigoScan.Shopping.addToFridge(${item.id}, '${item.product_name.replace(/'/g, "\\'")}', ${item.quantity}, '${item.unit.replace(/'/g, "\\'")}')" title="Ajouter au frigo">
                        <i class="fas fa-door-open"></i>
                    </button>
                    <button class="btn btn-danger btn-sm" onclick="FrigoScan.Shopping.remove(${item.id})">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            `;
        }).join('');

        // Réattacher les handlers sur les checkboxes après les créer
        document.querySelectorAll('.shopping-item-checkbox').forEach(checkbox => {
            checkbox.addEventListener('change', () => {
                updateAddAllFridgeButton();
            });
        });

        updateAddAllFridgeButton();
    }

    async function addItem() {
        const input = document.getElementById('shopping-add-input');
        const name = input.value.trim();
        if (!name) return;

        const data = await FrigoScan.API.post('/api/shopping/', {
            product_name: name,
            quantity: 1,
            unit: 'unité',
            source: 'manual',
        });
        if (data.success) {
            FrigoScan.toast(data.message, 'success');
            input.value = '';
            loadList();
        }
    }

    Shopping.toggle = async function (id) {
        const data = await FrigoScan.API.put(`/api/shopping/${id}/toggle`);
        if (data.success) loadList();
    };

    // Gestion des changements de checkbox
    Shopping.handleCheckboxChange = async function (id) {
        const checkbox = document.querySelector(`.shopping-item-checkbox[data-id="${id}"]`);
        if (checkbox) {
            const data = await FrigoScan.API.put(`/api/shopping/${id}/toggle`);
            if (!data.success) {
                // Reverser si erreur
                checkbox.checked = !checkbox.checked;
            } else {
                updateAddAllFridgeButton();
            }
        }
    };

    // Mettre à jour l'état du bouton "Tout ajouter au frigo"
    function updateAddAllFridgeButton() {
        const addAllBtn = document.getElementById('btn-shopping-add-all-fridge');
        if (!addAllBtn) return;

        const checkboxes = document.querySelectorAll('.shopping-item-checkbox');
        if (checkboxes.length === 0) {
            addAllBtn.classList.add('hidden');
            return;
        }

        const allChecked = Array.from(checkboxes).every(cb => cb.checked);
        if (allChecked) {
            addAllBtn.classList.remove('hidden');
        } else {
            addAllBtn.classList.add('hidden');
        }
    }

    // Sélectionner tous les articles
    function selectAll() {
        document.querySelectorAll('.shopping-item-checkbox:not(:checked)').forEach(checkbox => {
            checkbox.checked = true;
            const id = parseInt(checkbox.dataset.id);
            FrigoScan.Shopping.handleCheckboxChange(id);
        });
        updateAddAllFridgeButton();
    }

    // Désélectionner tous les articles
    function deselectAll() {
        document.querySelectorAll('.shopping-item-checkbox:checked').forEach(checkbox => {
            checkbox.checked = false;
            const id = parseInt(checkbox.dataset.id);
            FrigoScan.Shopping.handleCheckboxChange(id);
        });
        updateAddAllFridgeButton();
    }

    // Ajouter tous les articles sélectionnés au frigo
    async function addAllToFridge() {
        const checkboxes = document.querySelectorAll('.shopping-item-checkbox:checked');
        if (checkboxes.length === 0) {
            FrigoScan.toast('Aucun article à ajouter au frigo.', 'warning');
            return;
        }

        const items = [];
        checkboxes.forEach(checkbox => {
            const id = parseInt(checkbox.dataset.id);
            const item = currentItems.find(i => i.id === id);
            if (item) items.push(item);
        });

        if (items.length === 0) return;

        // Ajouter tous les articles au frigo
        let successCount = 0;
        for (const item of items) {
            try {
                const fridgeData = await FrigoScan.API.post('/api/fridge/', {
                    name: item.product_name,
                    category: 'autre',
                    quantity: parseFloat(item.quantity) || 1,
                    unit: item.unit,
                    dlc: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
                });

                if (fridgeData.success) {
                    // Marquer comme acheté
                    await FrigoScan.API.put(`/api/shopping/${item.id}/toggle`);
                    successCount++;
                }
            } catch (e) {
                console.error(`Erreur pour ${item.product_name}:`, e);
            }
        }

        if (successCount > 0) {
            FrigoScan.toast(`${successCount} article(s) ajouté(s) au frigo !`, 'success');
            loadList();
        } else {
            FrigoScan.toast('Erreur lors de l\'ajout au frigo.', 'error');
        }
    }

    Shopping.remove = async function (id) {
        const data = await FrigoScan.API.del(`/api/shopping/${id}`);
        if (data.success) {
            FrigoScan.toast(data.message, 'success');
            loadList();
        }
    };

    // Ajouter l'article de la liste courses au frigo et le marquer comme acheté
    Shopping.addToFridge = async function (shoppingId, product, quantity, unit) {
        try {
            // Ajouter au frigo
            const fridgeData = await FrigoScan.API.post('/api/fridge/', {
                name: product,
                category: 'autre',
                quantity: parseFloat(quantity) || 1,
                unit: unit,
                dlc: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0], // DLC 7 jours par défaut
            });

            if (fridgeData.success) {
                // Marquer comme acheté
                await FrigoScan.API.put(`/api/shopping/${shoppingId}/toggle`);
                FrigoScan.toast(`"${product}" ajouté au frigo et marqué comme acheté !`, 'success');
                loadList();
            } else {
                FrigoScan.toast('Erreur lors de l\'ajout au frigo.', 'error');
            }
        } catch (e) {
            FrigoScan.toast('Erreur : ' + e.message, 'error');
        }
    };

    async function checkStocks() {
        const data = await FrigoScan.API.post('/api/shopping/check-stocks');
        if (data.success) {
            if (data.count > 0) {
                FrigoScan.toast(`${data.count} alerte(s) de stock bas. Articles ajoutés à la liste.`, 'warning');
            } else {
                FrigoScan.toast('Tous les stocks sont OK.', 'success');
            }
            loadList();
        }
    }

    async function clearPurchased() {
        const data = await FrigoScan.API.del('/api/shopping/clear/purchased');
        if (data.success) {
            FrigoScan.toast(data.message, 'success');
            loadList();
        }
    }

    async function clearAll() {
        const ok = await FrigoScan.confirm('Supprimer liste', 'Vider entièrement la liste de courses ?');
        if (!ok) return;
        const data = await FrigoScan.API.del('/api/shopping/clear/all');
        if (data.success) {
            FrigoScan.toast(data.message, 'success');
            loadList();
        }
    }

})();
