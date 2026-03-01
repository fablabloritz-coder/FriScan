/**
 * FrigoScan — Module Liste de courses (shopping.js)
 */

(function () {
    const Shopping = {};
    FrigoScan.Shopping = Shopping;

    Shopping.load = async function () {
        setupListeners();
        await loadList();
    };

    function setupListeners() {
        const addBtn = document.getElementById('btn-shopping-add');
        const addInput = document.getElementById('shopping-add-input');

        addBtn.onclick = addItem;
        addInput.onkeydown = (e) => { if (e.key === 'Enter') addItem(); };

        document.getElementById('btn-shopping-check-stocks').onclick = checkStocks;
        document.getElementById('btn-shopping-clear-done').onclick = clearPurchased;
    }

    async function loadList() {
        const data = await FrigoScan.API.get('/api/shopping/?show_purchased=true');
        renderList(data.items || []);
    }

    function renderList(items) {
        const list = document.getElementById('shopping-list');
        if (items.length === 0) {
            list.innerHTML = '<div class="empty-state"><i class="fas fa-shopping-cart"></i><p>Liste de courses vide.</p></div>';
            return;
        }

        list.innerHTML = items.map(item => {
            const purchasedClass = item.is_purchased ? 'purchased' : '';
            const sourceLabels = { manual: 'Manuel', stock_alert: 'Stock bas', weekly_menu: 'Menu' };
            return `
                <div class="shopping-item ${purchasedClass}" data-id="${item.id}">
                    <input type="checkbox" class="shopping-item-checkbox" ${item.is_purchased ? 'checked' : ''}
                           onchange="FrigoScan.Shopping.toggle(${item.id})">
                    <span class="shopping-item-name">${item.product_name}</span>
                    <span class="shopping-item-qty">${item.quantity} ${item.unit}</span>
                    <span class="shopping-item-source">${sourceLabels[item.source] || item.source}</span>
                    <button class="btn btn-danger btn-sm" onclick="FrigoScan.Shopping.remove(${item.id})">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            `;
        }).join('');
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

    Shopping.remove = async function (id) {
        const data = await FrigoScan.API.del(`/api/shopping/${id}`);
        if (data.success) {
            FrigoScan.toast(data.message, 'success');
            loadList();
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

})();
