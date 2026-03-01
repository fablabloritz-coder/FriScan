/**
 * FrigoScan — Module Produits de saison (seasonal.js)
 */

(function () {
    const Seasonal = {};
    FrigoScan.Seasonal = Seasonal;

    const MONTH_NAMES = ['Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
        'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre'];

    let currentMonth = new Date().getMonth() + 1; // 1-12

    Seasonal.load = async function () {
        document.getElementById('btn-season-prev').onclick = () => { currentMonth = currentMonth <= 1 ? 12 : currentMonth - 1; Seasonal.load(); };
        document.getElementById('btn-season-next').onclick = () => { currentMonth = currentMonth >= 12 ? 1 : currentMonth + 1; Seasonal.load(); };

        document.getElementById('seasonal-month').textContent = MONTH_NAMES[currentMonth - 1];

        const data = await FrigoScan.API.get(`/api/seasonal/?month=${currentMonth}`);
        renderSeasonal(data.products || []);
    };

    function renderSeasonal(products) {
        const grid = document.getElementById('seasonal-grid');
        if (products.length === 0) {
            grid.innerHTML = '<div class="empty-state"><i class="fas fa-leaf"></i><p>Aucun produit de saison trouvé pour ce mois.</p></div>';
            return;
        }

        grid.innerHTML = products.map(p => `
            <div class="seasonal-card">
                <span class="seasonal-emoji">${p.emoji || '🌿'}</span>
                <span class="seasonal-name">${p.name}</span>
                <span class="seasonal-category">${p.category || ''}</span>
            </div>
        `).join('');
    }

})();
