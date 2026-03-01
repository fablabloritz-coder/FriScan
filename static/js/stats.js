/**
 * FrigoScan — Module Statistiques (stats.js)
 */

(function () {
    const Stats = {};
    FrigoScan.Stats = Stats;

    Stats.load = async function () {
        const periodEl = document.getElementById('stats-period-select');
        periodEl.onchange = () => Stats.load();
        const days = parseInt(periodEl.value) || 30;

        const data = await FrigoScan.API.get(`/api/stats/summary?days=${days}`);
        if (data.success) renderStats(data, days);
    };

    function renderStats(data, days) {
        const container = document.getElementById('stats-content');

        // Top KPIs
        let html = `
            <div class="stat-card">
                <h4><i class="fas fa-utensils"></i> Consommés</h4>
                <div class="stat-number" style="color:var(--success);">${data.total_consumed}</div>
                <div class="stat-label">produit(s) en ${days} jours</div>
            </div>
            <div class="stat-card">
                <h4><i class="fas fa-trash"></i> Gaspillés</h4>
                <div class="stat-number" style="color:var(--danger);">${data.total_wasted}</div>
                <div class="stat-label">produit(s) périmés/jetés</div>
            </div>
        `;

        // Top produits
        if (data.top_products && data.top_products.length) {
            const maxCount = data.top_products[0].count;
            html += `<div class="stat-card">
                <h4><i class="fas fa-fire"></i> Top produits</h4>
                ${data.top_products.map(p => {
                    const pct = Math.round((p.count / maxCount) * 100);
                    return `
                        <div class="stat-bar-container">
                            <div class="stat-bar-label">
                                <span>${p.product_name}</span>
                                <span>${p.count}x</span>
                            </div>
                            <div class="stat-bar"><div class="stat-bar-fill green" style="width:${pct}%"></div></div>
                        </div>
                    `;
                }).join('')}
            </div>`;
        }

        // Par catégorie
        if (data.by_category && data.by_category.length) {
            const maxCat = Math.max(...data.by_category.map(c => c.count));
            html += `<div class="stat-card">
                <h4><i class="fas fa-tags"></i> Par catégorie</h4>
                ${data.by_category.map(c => {
                    const pct = Math.round((c.count / maxCat) * 100);
                    return `
                        <div class="stat-bar-container">
                            <div class="stat-bar-label">
                                <span>${c.category || 'autre'}</span>
                                <span>${c.count}</span>
                            </div>
                            <div class="stat-bar"><div class="stat-bar-fill" style="width:${pct}%"></div></div>
                        </div>
                    `;
                }).join('')}
            </div>`;
        }

        // Par jour de la semaine
        if (data.by_day_of_week && data.by_day_of_week.length) {
            const maxDay = Math.max(...data.by_day_of_week.map(d => d.count));
            html += `<div class="stat-card">
                <h4><i class="fas fa-calendar-week"></i> Par jour</h4>
                ${data.by_day_of_week.map(d => {
                    const pct = maxDay > 0 ? Math.round((d.count / maxDay) * 100) : 0;
                    return `
                        <div class="stat-bar-container">
                            <div class="stat-bar-label">
                                <span>${d.day_name}</span>
                                <span>${d.count}</span>
                            </div>
                            <div class="stat-bar"><div class="stat-bar-fill orange" style="width:${pct}%"></div></div>
                        </div>
                    `;
                }).join('')}
            </div>`;
        }

        // Par mois
        if (data.by_month && data.by_month.length) {
            const maxMonth = Math.max(...data.by_month.map(m => m.count));
            html += `<div class="stat-card">
                <h4><i class="fas fa-chart-bar"></i> Par mois</h4>
                ${data.by_month.map(m => {
                    const pct = maxMonth > 0 ? Math.round((m.count / maxMonth) * 100) : 0;
                    return `
                        <div class="stat-bar-container">
                            <div class="stat-bar-label">
                                <span>${m.month}</span>
                                <span>${m.count}</span>
                            </div>
                            <div class="stat-bar"><div class="stat-bar-fill" style="width:${pct}%"></div></div>
                        </div>
                    `;
                }).join('')}
            </div>`;
        }

        container.innerHTML = html;
    }

})();
