/**
 * FrigoScan — Module Recettes (recipes.js)
 * Recherche, suggestions, affichage détaillé.
 */

(function () {
    const Recipes = {};
    FrigoScan.Recipes = Recipes;

    document.addEventListener('DOMContentLoaded', () => {
        document.getElementById('btn-recipe-search').addEventListener('click', searchRecipes);
        document.getElementById('recipe-search').addEventListener('keydown', e => {
            if (e.key === 'Enter') searchRecipes();
        });
        document.getElementById('btn-recipe-suggest').addEventListener('click', suggestRecipes);
    });

    async function searchRecipes() {
        const query = document.getElementById('recipe-search').value.trim();
        if (query.length < 2) {
            FrigoScan.toast('Entrez au moins 2 caractères.', 'warning');
            return;
        }
        const data = await FrigoScan.API.get(`/api/recipes/search?q=${encodeURIComponent(query)}`);
        if (data.success) {
            renderRecipes(data.recipes || []);
        }
    }

    let isSuggesting = false;
    async function suggestRecipes() {
        if (isSuggesting) return;
        isSuggesting = true;
        const btn = document.getElementById('btn-recipe-suggest');
        if (btn) { btn.disabled = true; btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Recherche...'; }
        try {
            const data = await FrigoScan.API.get('/api/recipes/suggest?max_results=12&min_score=10');
            if (data.success) {
                if (data.recipes.length === 0) {
                    FrigoScan.toast(data.message || 'Aucune suggestion trouvée.', 'warning');
                }
                renderRecipes(data.recipes || []);
            }
        } finally {
            isSuggesting = false;
            if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fas fa-lightbulb"></i> Suggestions du frigo'; }
        }
    }

    function renderRecipes(recipes) {
        const grid = document.getElementById('recipes-list');
        const empty = document.getElementById('recipes-empty');

        if (recipes.length === 0) {
            grid.innerHTML = '';
            empty.classList.remove('hidden');
            return;
        }
        empty.classList.add('hidden');

        grid.innerHTML = recipes.map((r, idx) => {
            const scoreClass = (r.match_score || 0) >= 70 ? 'high' : (r.match_score || 0) >= 40 ? 'medium' : 'low';
            const scoreHtml = r.match_score !== undefined
                ? `<span class="recipe-card-score ${scoreClass}"><i class="fas fa-bullseye"></i> ${r.match_score}%</span>`
                : '';
            const imgUrl = r.image_url || '';
            const imgHtml = imgUrl
                ? `<img class="recipe-card-img" src="${imgUrl}" alt="${r.title}" onerror="this.style.display='none'">`
                : `<div class="recipe-card-img" style="display:flex;align-items:center;justify-content:center;font-size:3rem;background:var(--bg-hover);">🍳</div>`;

            const prepTime = (r.prep_time || 0) + (r.cook_time || 0);

            return `
                <div class="recipe-card" data-recipe-idx="${idx}">
                    ${imgHtml}
                    <div class="recipe-card-body">
                        <div class="recipe-card-title">${r.title}</div>
                        <div class="recipe-card-meta">
                            ${prepTime ? `<span><i class="fas fa-clock"></i> ${prepTime} min</span>` : ''}
                            <span><i class="fas fa-users"></i> ${r.servings || 4} pers.</span>
                            ${scoreHtml}
                        </div>
                        ${r.missing_ingredients && r.missing_ingredients.length
                            ? `<div style="margin-top:6px;font-size:0.78rem;color:var(--text-muted);">
                                   Manque : ${r.missing_ingredients.slice(0, 3).join(', ')}${r.missing_ingredients.length > 3 ? '...' : ''}
                               </div>`
                            : ''}
                    </div>
                </div>
            `;
        }).join('');

        // Clic sur carte = détail
        grid.querySelectorAll('.recipe-card').forEach(card => {
            card.addEventListener('click', () => {
                const idx = parseInt(card.dataset.recipeIdx);
                showRecipeDetail(recipes[idx]);
            });
        });
    }

    async function showRecipeDetail(recipe) {
        const modal = document.getElementById('recipe-detail-modal');
        const content = document.getElementById('recipe-detail-content');

        let ingredients = [];
        try { ingredients = JSON.parse(recipe.ingredients_json || '[]'); } catch (e) {}

        let tags = [];
        try { tags = JSON.parse(recipe.tags_json || '[]'); } catch (e) {}

        // Charger le contenu du frigo pour vérifier la disponibilité
        let fridgeNames = new Set();
        try {
            const fridgeData = await FrigoScan.API.get('/api/fridge/');
            if (fridgeData.success && fridgeData.items) {
                fridgeData.items.forEach(item => {
                    const name = (item.name || '').toLowerCase().trim();
                    fridgeNames.add(name);
                    name.split(' ').forEach(w => { if (w.length > 2) fridgeNames.add(w); });
                });
            }
        } catch (e) {}

        // Ingrédients basiques qu'on ignore
        const basicIngredients = ["water", "salt", "pepper", "oil", "eau", "sel", "poivre", "huile"];

        const imgHtml = recipe.image_url
            ? `<img src="${recipe.image_url}" alt="${recipe.title}" style="width:100%;max-height:300px;object-fit:cover;border-radius:var(--radius-sm);margin-bottom:16px;">`
            : '';

        // Construire les pills d'ingrédients
        const ingredientPills = ingredients.map(ing => {
            const ingName = (ing.name || '').toLowerCase().trim();
            const isBasic = basicIngredients.some(b => ingName.includes(b));
            let isAvailable = isBasic;
            if (!isBasic) {
                for (const fn of fridgeNames) {
                    if (fn.includes(ingName) || ingName.includes(fn)) { isAvailable = true; break; }
                }
            }
            const cls = isAvailable ? 'ingredient-pill available' : 'ingredient-pill missing';
            const icon = isAvailable ? '<i class="fas fa-check"></i>' : '<i class="fas fa-cart-plus"></i>';
            const measureText = ing.measure ? `${ing.measure} ` : '';
            const addBtn = !isAvailable
                ? ` <button class="btn-add-ingredient" data-name="${(ing.name || '').replace(/"/g, '&quot;')}" title="Ajouter à la liste de courses">+</button>`
                : '';
            return `<span class="${cls}">${icon} ${measureText}${ing.name}${addBtn}</span>`;
        }).join('');

        content.innerHTML = `
            ${imgHtml}
            <h2 style="margin-bottom:12px;">${recipe.title}</h2>
            <div style="display:flex;gap:12px;margin-bottom:16px;flex-wrap:wrap;">
                ${(recipe.prep_time || recipe.cook_time)
                    ? `<span class="badge"><i class="fas fa-clock"></i> Prépa: ${recipe.prep_time || 0}min — Cuisson: ${recipe.cook_time || 0}min</span>`
                    : ''}
                <span class="badge"><i class="fas fa-users"></i> ${recipe.servings || 4} personnes</span>
                ${recipe.match_score !== undefined ? `<span class="badge"><i class="fas fa-bullseye"></i> Compatibilité: ${recipe.match_score}%</span>` : ''}
            </div>
            ${tags.length ? `<div style="margin-bottom:12px;">${tags.map(t => `<span class="badge" style="margin:2px;">${t}</span>`).join('')}</div>` : ''}

            <h3 style="margin-bottom:8px;">Ingrédients</h3>
            <div class="ingredients-pills" style="margin-bottom:16px;">
                ${ingredientPills}
            </div>
            <div style="font-size:0.78rem;color:var(--text-muted);margin-bottom:16px;">
                <span class="ingredient-pill available" style="font-size:0.7rem;padding:2px 6px;"><i class="fas fa-check"></i> Dans le frigo</span>
                <span class="ingredient-pill missing" style="font-size:0.7rem;padding:2px 6px;"><i class="fas fa-cart-plus"></i> Manquant</span>
            </div>

            ${recipe.missing_ingredients && recipe.missing_ingredients.length
                ? `<button class="btn btn-warning btn-add-all-missing" style="margin-bottom:16px;">
                    <i class="fas fa-cart-plus"></i> Ajouter tous les manquants à la liste de courses (${recipe.missing_ingredients.length})
                   </button>`
                : ''}

            <h3 style="margin-bottom:8px;">Instructions</h3>
            <div style="white-space:pre-line;line-height:1.7;">${recipe.instructions || 'Aucune instruction disponible.'}</div>

            ${recipe.source_url ? `<a href="${recipe.source_url}" target="_blank" class="btn btn-secondary" style="margin-top:16px;"><i class="fas fa-external-link-alt"></i> Voir la source</a>` : ''}

            <div style="margin-top:16px;">
                <button class="btn btn-success" onclick="FrigoScan.Recipes.saveRecipe(this)" data-recipe='${JSON.stringify(recipe).replace(/'/g, "&apos;")}'>
                    <i class="fas fa-bookmark"></i> Sauvegarder
                </button>
            </div>
        `;

        modal.classList.remove('hidden');

        // Handlers pour ajout individuel aux courses
        content.querySelectorAll('.btn-add-ingredient').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.stopPropagation();
                const name = btn.dataset.name;
                const res = await FrigoScan.API.post('/api/shopping/', { product_name: name, quantity: 1, unit: 'unité' });
                if (res.success) {
                    FrigoScan.toast(`"${name}" ajouté à la liste de courses`, 'success');
                    btn.parentElement.classList.remove('missing');
                    btn.parentElement.classList.add('available');
                    btn.remove();
                }
            });
        });

        // Handler pour ajout de tous les manquants
        const addAllBtn = content.querySelector('.btn-add-all-missing');
        if (addAllBtn && recipe.missing_ingredients) {
            addAllBtn.addEventListener('click', async () => {
                let added = 0;
                for (const name of recipe.missing_ingredients) {
                    const res = await FrigoScan.API.post('/api/shopping/', { product_name: name, quantity: 1, unit: 'unité' });
                    if (res.success) added++;
                }
                FrigoScan.toast(`${added} ingrédient(s) ajouté(s) à la liste de courses`, 'success');
                addAllBtn.disabled = true;
                addAllBtn.textContent = '✓ Ajoutés';
            });
        }
    }

    Recipes.closeDetail = function () {
        document.getElementById('recipe-detail-modal').classList.add('hidden');
    };

    Recipes.saveRecipe = async function (btn) {
        const recipe = JSON.parse(btn.dataset.recipe);
        const data = await FrigoScan.API.post('/api/recipes/', {
            title: recipe.title,
            ingredients_json: recipe.ingredients_json || '[]',
            instructions: recipe.instructions || '',
            prep_time: recipe.prep_time || 0,
            cook_time: recipe.cook_time || 0,
            servings: recipe.servings || 4,
            source_url: recipe.source_url || '',
            image_url: recipe.image_url || '',
            tags_json: recipe.tags_json || '[]',
            diet_tags_json: recipe.diet_tags_json || '[]',
        });
        if (data.success) {
            FrigoScan.toast('Recette sauvegardée !', 'success');
        }
    };

    // Fermer modal par clic extérieur
    document.addEventListener('click', (e) => {
        const modal = document.getElementById('recipe-detail-modal');
        if (e.target === modal) Recipes.closeDetail();
    });

})();
