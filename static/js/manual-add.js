/**
 * FrigoScan — Module Ajout Manuel (manual-add.js)
 * Catégories, grille d'aliments, saisie libre, presets.
 */

(function () {
    const ManualAdd = {};
    FrigoScan.ManualAdd = ManualAdd;

    let selectedCategory = '';
    let selectedFood = null;

    // Base d'aliments par catégorie
    const FOOD_DB = {
        fruits: [
            { name: 'Pomme', emoji: '🍎', dlc_days: 14 },
            { name: 'Banane', emoji: '🍌', dlc_days: 7 },
            { name: 'Orange', emoji: '🍊', dlc_days: 14 },
            { name: 'Fraise', emoji: '🍓', dlc_days: 5 },
            { name: 'Raisin', emoji: '🍇', dlc_days: 7 },
            { name: 'Poire', emoji: '🍐', dlc_days: 10 },
            { name: 'Pêche', emoji: '🍑', dlc_days: 5 },
            { name: 'Citron', emoji: '🍋', dlc_days: 21 },
            { name: 'Kiwi', emoji: '🥝', dlc_days: 14 },
            { name: 'Mangue', emoji: '🥭', dlc_days: 7 },
            { name: 'Ananas', emoji: '🍍', dlc_days: 5 },
            { name: 'Cerise', emoji: '🍒', dlc_days: 5 },
            { name: 'Melon', emoji: '🍈', dlc_days: 7 },
            { name: 'Pastèque', emoji: '🍉', dlc_days: 7 },
            { name: 'Abricot', emoji: '🟠', dlc_days: 5 },
            { name: 'Prune', emoji: '🟣', dlc_days: 7 },
            { name: 'Clémentine', emoji: '🍊', dlc_days: 14 },
        ],
        légumes: [
            { name: 'Tomate', emoji: '🍅', dlc_days: 7 },
            { name: 'Carotte', emoji: '🥕', dlc_days: 21 },
            { name: 'Salade', emoji: '🥬', dlc_days: 5 },
            { name: 'Courgette', emoji: '🥒', dlc_days: 10 },
            { name: 'Poivron', emoji: '🫑', dlc_days: 10 },
            { name: 'Oignon', emoji: '🧅', dlc_days: 30 },
            { name: 'Ail', emoji: '🧄', dlc_days: 30 },
            { name: 'Haricots verts', emoji: '🫘', dlc_days: 5 },
            { name: 'Brocoli', emoji: '🥦', dlc_days: 7 },
            { name: 'Champignon', emoji: '🍄', dlc_days: 5 },
            { name: 'Épinard', emoji: '🥬', dlc_days: 5 },
            { name: 'Chou-fleur', emoji: '🥦', dlc_days: 7 },
            { name: 'Pomme de terre', emoji: '🥔', dlc_days: 30 },
            { name: 'Aubergine', emoji: '🍆', dlc_days: 7 },
            { name: 'Poireau', emoji: '🥬', dlc_days: 10 },
            { name: 'Artichaut', emoji: '🌿', dlc_days: 7 },
            { name: 'Concombre', emoji: '🥒', dlc_days: 7 },
            { name: 'Radis', emoji: '🔴', dlc_days: 7 },
            { name: 'Betterave', emoji: '🟣', dlc_days: 14 },
            { name: 'Navet', emoji: '⚪', dlc_days: 14 },
            { name: 'Céleri', emoji: '🥬', dlc_days: 10 },
            { name: 'Fenouil', emoji: '🌿', dlc_days: 7 },
            { name: 'Petits pois', emoji: '🟢', dlc_days: 3 },
        ],
        viandes: [
            { name: 'Poulet', emoji: '🍗', dlc_days: 3 },
            { name: 'Bœuf', emoji: '🥩', dlc_days: 3 },
            { name: 'Porc', emoji: '🥓', dlc_days: 3 },
            { name: 'Agneau', emoji: '🐑', dlc_days: 3 },
            { name: 'Dinde', emoji: '🦃', dlc_days: 3 },
            { name: 'Veau', emoji: '🥩', dlc_days: 3 },
            { name: 'Steak haché', emoji: '🍔', dlc_days: 2 },
            { name: 'Saucisse', emoji: '🌭', dlc_days: 5 },
            { name: 'Canard', emoji: '🦆', dlc_days: 3 },
            { name: 'Lapin', emoji: '🐇', dlc_days: 3 },
        ],
        poissons: [
            { name: 'Saumon', emoji: '🐟', dlc_days: 2 },
            { name: 'Thon', emoji: '🐟', dlc_days: 2 },
            { name: 'Cabillaud', emoji: '🐟', dlc_days: 2 },
            { name: 'Crevette', emoji: '🦐', dlc_days: 2 },
            { name: 'Sardine', emoji: '🐟', dlc_days: 2 },
            { name: 'Truite', emoji: '🐟', dlc_days: 2 },
            { name: 'Moule', emoji: '🦪', dlc_days: 1 },
            { name: 'Maquereau', emoji: '🐟', dlc_days: 2 },
            { name: 'Dorade', emoji: '🐟', dlc_days: 2 },
            { name: 'Bar', emoji: '🐟', dlc_days: 2 },
        ],
        'produits laitiers': [
            { name: 'Lait', emoji: '🥛', dlc_days: 7 },
            { name: 'Yaourt', emoji: '🥛', dlc_days: 14 },
            { name: 'Fromage', emoji: '🧀', dlc_days: 14 },
            { name: 'Beurre', emoji: '🧈', dlc_days: 30 },
            { name: 'Crème fraîche', emoji: '🥛', dlc_days: 10 },
            { name: 'Fromage blanc', emoji: '🥛', dlc_days: 14 },
            { name: 'Camembert', emoji: '🧀', dlc_days: 21 },
            { name: 'Emmental râpé', emoji: '🧀', dlc_days: 14 },
            { name: 'Mozzarella', emoji: '🧀', dlc_days: 7 },
            { name: 'Comté', emoji: '🧀', dlc_days: 30 },
        ],
        boulangerie: [
            { name: 'Pain', emoji: '🍞', dlc_days: 3 },
            { name: 'Baguette', emoji: '🥖', dlc_days: 1 },
            { name: 'Pain de mie', emoji: '🍞', dlc_days: 7 },
            { name: 'Croissant', emoji: '🥐', dlc_days: 2 },
            { name: 'Brioche', emoji: '🍞', dlc_days: 5 },
            { name: 'Pain complet', emoji: '🍞', dlc_days: 5 },
        ],
        boissons: [
            { name: 'Eau', emoji: '💧', dlc_days: 365 },
            { name: 'Jus d\'orange', emoji: '🧃', dlc_days: 7 },
            { name: 'Lait', emoji: '🥛', dlc_days: 7 },
            { name: 'Soda', emoji: '🥤', dlc_days: 90 },
            { name: 'Bière', emoji: '🍺', dlc_days: 180 },
            { name: 'Vin', emoji: '🍷', dlc_days: 365 },
            { name: 'Café', emoji: '☕', dlc_days: 180 },
            { name: 'Thé', emoji: '🍵', dlc_days: 365 },
        ],
        féculents: [
            { name: 'Pâtes', emoji: '🍝', dlc_days: 365 },
            { name: 'Riz', emoji: '🍚', dlc_days: 365 },
            { name: 'Semoule', emoji: '🌾', dlc_days: 365 },
            { name: 'Quinoa', emoji: '🌾', dlc_days: 365 },
            { name: 'Boulgour', emoji: '🌾', dlc_days: 365 },
            { name: 'Lentilles', emoji: '🟤', dlc_days: 365 },
            { name: 'Pois chiches', emoji: '🟡', dlc_days: 365 },
            { name: 'Haricots secs', emoji: '🫘', dlc_days: 365 },
        ],
        conserves: [
            { name: 'Tomates pelées', emoji: '🥫', dlc_days: 730 },
            { name: 'Maïs', emoji: '🌽', dlc_days: 730 },
            { name: 'Haricots verts', emoji: '🥫', dlc_days: 730 },
            { name: 'Petits pois', emoji: '🥫', dlc_days: 730 },
            { name: 'Thon en boîte', emoji: '🥫', dlc_days: 730 },
            { name: 'Sardines', emoji: '🥫', dlc_days: 730 },
            { name: 'Soupe', emoji: '🥫', dlc_days: 365 },
            { name: 'Compote', emoji: '🥫', dlc_days: 365 },
        ],
        surgelés: [
            { name: 'Pizza surgelée', emoji: '🍕', dlc_days: 180 },
            { name: 'Frites surgelées', emoji: '🍟', dlc_days: 180 },
            { name: 'Légumes surgelés', emoji: '🥦', dlc_days: 180 },
            { name: 'Poisson surgelé', emoji: '🐟', dlc_days: 180 },
            { name: 'Glace', emoji: '🍨', dlc_days: 180 },
            { name: 'Fruits surgelés', emoji: '🍓', dlc_days: 180 },
        ],
        condiments: [
            { name: 'Sel', emoji: '🧂', dlc_days: 3650 },
            { name: 'Poivre', emoji: '🌶️', dlc_days: 730 },
            { name: 'Huile d\'olive', emoji: '🫒', dlc_days: 365 },
            { name: 'Vinaigre', emoji: '🍶', dlc_days: 730 },
            { name: 'Moutarde', emoji: '🟡', dlc_days: 365 },
            { name: 'Ketchup', emoji: '🍅', dlc_days: 180 },
            { name: 'Mayonnaise', emoji: '🥚', dlc_days: 90 },
            { name: 'Sauce soja', emoji: '🍶', dlc_days: 365 },
            { name: 'Herbes de Provence', emoji: '🌿', dlc_days: 730 },
            { name: 'Curry', emoji: '🟡', dlc_days: 730 },
            { name: 'Paprika', emoji: '🔴', dlc_days: 730 },
            { name: 'Sucre', emoji: '🍬', dlc_days: 3650 },
            { name: 'Farine', emoji: '🌾', dlc_days: 365 },
        ],
        snacks: [
            { name: 'Biscuits', emoji: '🍪', dlc_days: 90 },
            { name: 'Chocolat', emoji: '🍫', dlc_days: 180 },
            { name: 'Chips', emoji: '🥨', dlc_days: 60 },
            { name: 'Céréales', emoji: '🥣', dlc_days: 180 },
            { name: 'Barres de céréales', emoji: '🍫', dlc_days: 180 },
            { name: 'Confiture', emoji: '🍯', dlc_days: 365 },
            { name: 'Miel', emoji: '🍯', dlc_days: 730 },
            { name: 'Nutella', emoji: '🍫', dlc_days: 365 },
        ],
        oeufs: [
            { name: 'Oeufs (x6)', emoji: '🥚', dlc_days: 28 },
            { name: 'Oeufs (x12)', emoji: '🥚', dlc_days: 28 },
            { name: 'Oeufs de caille', emoji: '🥚', dlc_days: 21 },
        ],
        charcuterie: [
            { name: 'Jambon', emoji: '🥓', dlc_days: 7 },
            { name: 'Saucisson', emoji: '🌭', dlc_days: 21 },
            { name: 'Pâté', emoji: '🍖', dlc_days: 7 },
            { name: 'Lardons', emoji: '🥓', dlc_days: 7 },
            { name: 'Bacon', emoji: '🥓', dlc_days: 7 },
            { name: 'Rosette', emoji: '🌭', dlc_days: 21 },
            { name: 'Chorizo', emoji: '🌭', dlc_days: 21 },
            { name: 'Rillettes', emoji: '🍖', dlc_days: 7 },
        ],
        autre: [
            { name: 'Tofu', emoji: '🟫', dlc_days: 7 },
            { name: 'Beurre de cacahuète', emoji: '🥜', dlc_days: 180 },
            { name: 'Houmous', emoji: '🟡', dlc_days: 7 },
            { name: 'Sauce tomate', emoji: '🍅', dlc_days: 14 },
        ],
    };

    // Initialisation des listeners
    document.addEventListener('DOMContentLoaded', () => {
        // Clic sur catégorie
        document.querySelectorAll('.category-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                selectedCategory = btn.dataset.cat;
                showFoodGrid(selectedCategory);
            });
        });

        // Retour aux catégories
        document.getElementById('btn-back-categories').addEventListener('click', () => {
            document.getElementById('food-grid-container').classList.add('hidden');
            document.getElementById('manual-detail-form').classList.add('hidden');
            document.getElementById('category-grid').classList.remove('hidden');
        });

        // Ajout libre
        document.getElementById('btn-add-custom-food').addEventListener('click', () => {
            const name = document.getElementById('custom-food-name').value.trim();
            if (!name) { FrigoScan.toast('Entrez un nom de produit.', 'warning'); return; }
            showDetailForm({ name, emoji: '📦', dlc_days: 7 });
            document.getElementById('custom-food-name').value = '';
        });

        // Confirmer ajout
        document.getElementById('btn-manual-add-confirm').addEventListener('click', confirmAdd);
        document.getElementById('btn-manual-cancel').addEventListener('click', () => {
            document.getElementById('manual-detail-form').classList.add('hidden');
            document.getElementById('food-grid-container').classList.remove('hidden');
        });
    });

    function showFoodGrid(category) {
        document.getElementById('category-grid').classList.add('hidden');
        document.getElementById('manual-detail-form').classList.add('hidden');
        const container = document.getElementById('food-grid-container');
        container.classList.remove('hidden');

        document.getElementById('selected-category-title').textContent =
            category.charAt(0).toUpperCase() + category.slice(1);

        const grid = document.getElementById('food-grid');
        const foods = FOOD_DB[category] || [];
        grid.innerHTML = foods.map(f => `
            <button class="food-btn" data-food='${JSON.stringify(f).replace(/'/g, "&apos;")}'>
                <span class="food-emoji">${f.emoji}</span>
                <span>${f.name}</span>
            </button>
        `).join('');

        grid.querySelectorAll('.food-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const food = JSON.parse(btn.dataset.food);
                showDetailForm(food);
            });
        });
    }

    function showDetailForm(food) {
        selectedFood = food;
        document.getElementById('food-grid-container').classList.add('hidden');
        document.getElementById('manual-detail-form').classList.remove('hidden');
        document.getElementById('manual-product-name').textContent = `${food.emoji || ''} ${food.name}`;
        document.getElementById('manual-qty').value = 1;
        document.getElementById('manual-unit').value = 'unité';

        // DLC estimée
        const dlcDate = new Date();
        dlcDate.setDate(dlcDate.getDate() + (food.dlc_days || 7));
        document.getElementById('manual-dlc').value = dlcDate.toISOString().split('T')[0];
    }

    ManualAdd.setQty = function (val) {
        document.getElementById('manual-qty').value = val;
    };

    ManualAdd.adjustQty = function (delta) {
        const input = document.getElementById('manual-qty');
        const val = Math.max(0.1, parseFloat(input.value || 1) + delta);
        input.value = Math.round(val * 10) / 10;
    };

    async function confirmAdd() {
        if (!selectedFood) return;

        const item = {
            name: selectedFood.name,
            category: selectedCategory || 'autre',
            quantity: parseFloat(document.getElementById('manual-qty').value) || 1,
            unit: document.getElementById('manual-unit').value,
            dlc: document.getElementById('manual-dlc').value || null,
            nutrition_json: '{}',
        };

        const data = await FrigoScan.API.post('/api/fridge/', item);
        if (data.success) {
            FrigoScan.toast(`"${item.name}" ajouté au frigo !`, 'success');
            // Retour à la grille
            document.getElementById('manual-detail-form').classList.add('hidden');
            document.getElementById('food-grid-container').classList.remove('hidden');
            selectedFood = null;
        }
    }

})();
