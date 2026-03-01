/**
 * FrigoScan — Module Menu de la semaine (menus.js)
 */

(function () {
    const Menus = {};
    FrigoScan.Menus = Menus;

    const DAYS = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche'];
    const MEAL_LABELS = { breakfast: 'Petit-déj', lunch: 'Déjeuner', dinner: 'Dîner', snack: 'Goûter' };

    let currentWeekStart = getMonday(new Date());

    function getMonday(d) {
        const date = new Date(d);
        const day = date.getDay();
        const diff = date.getDate() - day + (day === 0 ? -6 : 1);
        date.setDate(diff);
        return date.toISOString().split('T')[0];
    }

    function shiftWeek(offset) {
        const d = new Date(currentWeekStart);
        d.setDate(d.getDate() + offset * 7);
        currentWeekStart = d.toISOString().split('T')[0];
        Menus.load();
    }

    Menus.load = async function () {
        document.getElementById('btn-menu-prev').onclick = () => shiftWeek(-1);
        document.getElementById('btn-menu-next').onclick = () => shiftWeek(1);
        document.getElementById('btn-generate-menu-fridge').onclick = () => generateMenu('fridge');
        document.getElementById('btn-generate-menu-scratch').onclick = () => generateMenu('scratch');
        document.getElementById('btn-clear-menu').onclick = clearWeekMenu;

        const weekDate = new Date(currentWeekStart);
        const options = { day: 'numeric', month: 'long', year: 'numeric' };
        document.getElementById('menu-week-label').textContent =
            `Semaine du ${weekDate.toLocaleDateString('fr-FR', options)}`;

        const data = await FrigoScan.API.get(`/api/menus/?week_start=${currentWeekStart}`);
        renderMenu(data.menu || []);
    };

    function renderMenu(entries) {
        const grid = document.getElementById('menu-grid');

        // Organiser par jour
        const byDay = {};
        for (let i = 0; i < 7; i++) byDay[i] = {};
        entries.forEach(e => {
            byDay[e.day_of_week] = byDay[e.day_of_week] || {};
            byDay[e.day_of_week][e.meal_type] = e;
        });

        grid.innerHTML = DAYS.map((dayName, idx) => {
            const meals = byDay[idx] || {};
            const mealTypes = ['lunch', 'dinner'];
            const mealsHtml = mealTypes.map(mt => {
                const entry = meals[mt];
                return `
                    <div class="menu-meal">
                        <span class="menu-meal-type">${MEAL_LABELS[mt] || mt}</span>
                        <span class="menu-meal-recipe">${entry ? entry.recipe_title : '—'}</span>
                        ${entry && entry.id ? `<button class="btn btn-danger btn-sm" onclick="FrigoScan.Menus.removeEntry(${entry.id})"><i class="fas fa-times"></i></button>` : ''}
                    </div>
                `;
            }).join('');

            return `
                <div class="menu-day-card">
                    <h4><i class="fas fa-calendar-day"></i> ${dayName}</h4>
                    ${mealsHtml}
                </div>
            `;
        }).join('');
    }

    async function generateMenu(mode) {
        const nbPersons = parseInt(localStorage.getItem('frigoscan-nb-persons') || '4');
        const modeLabel = mode === 'fridge' ? 'selon le frigo' : 'de zéro';
        FrigoScan.toast(`Génération du menu ${modeLabel} en cours...`, 'info');

        const data = await FrigoScan.API.post(
            `/api/menus/generate?week_start=${currentWeekStart}&servings=${nbPersons}&mode=${mode}`
        );
        if (data.success) {
            FrigoScan.toast(data.message || 'Menu généré !', 'success');
            Menus.load();
        }
    }

    async function clearWeekMenu() {
        const ok = await FrigoScan.confirm('Vider le menu', 'Supprimer tout le menu de cette semaine ?');
        if (!ok) return;
        const data = await FrigoScan.API.del(`/api/menus/week/${currentWeekStart}`);
        if (data.success) {
            FrigoScan.toast('Menu vidé.', 'success');
            Menus.load();
        }
    }

    Menus.removeEntry = async function (entryId) {
        const data = await FrigoScan.API.del(`/api/menus/${entryId}`);
        if (data.success) {
            FrigoScan.toast('Entrée supprimée.', 'success');
            Menus.load();
        }
    };

})();
