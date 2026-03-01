/**
 * FrigoScan — Module Recettes (recipes.js)
 * Recherche, suggestions, recettes sauvegardées, affichage détaillé.
 */

(function () {
    const Recipes = {};
    FrigoScan.Recipes = Recipes;

    let savedRecipeTitles = new Set(); // Titres des recettes déjà sauvegardées

    // Parse les mesures d'ingrédients (ex: "200 g", "1/2 cup", "2 tbsp") en {qty, unit}
    function parseMeasure(measure) {
        if (!measure || !measure.trim()) return { qty: 1, unit: 'unité' };
        const m = measure.trim();
        const match = m.match(/^([\d.,/]+)\s*(.*)/);
        if (match) {
            let num = match[1];
            let unitStr = (match[2] || '').trim();
            // Gérer les fractions
            if (num.includes('/')) {
                const parts = num.split('/');
                num = parseFloat(parts[0]) / parseFloat(parts[1]);
            } else {
                num = parseFloat(num.replace(',', '.'));
            }
            if (isNaN(num)) return { qty: 1, unit: m };
            // Normaliser l'unité
            const unitMap = {
                'g': 'g', 'gr': 'g', 'gram': 'g', 'grams': 'g', 'gramme': 'g', 'grammes': 'g',
                'kg': 'kg', 'kilogram': 'kg',
                'ml': 'mL', 'milliliter': 'mL', 'millilitre': 'mL',
                'cl': 'cL', 'centiliter': 'cL', 'centilitre': 'cL',
                'l': 'L', 'liter': 'L', 'litre': 'L', 'litres': 'L',
                'cup': 'cup', 'cups': 'cup',
                'tbsp': 'c. à soupe', 'tablespoon': 'c. à soupe', 'tablespoons': 'c. à soupe',
                'tsp': 'c. à café', 'teaspoon': 'c. à café', 'teaspoons': 'c. à café',
                'oz': 'oz', 'ounce': 'oz', 'ounces': 'oz',
                'lb': 'lb', 'pound': 'lb', 'pounds': 'lb',
                'pièce': 'unité', 'pièces': 'unité', 'piece': 'unité', 'pieces': 'unité',
            };
            const lowerUnit = unitStr.toLowerCase();
            const normalizedUnit = unitMap[lowerUnit] || unitStr || 'unité';
            return { qty: Math.round(num * 10) / 10, unit: normalizedUnit };
        }
        return { qty: 1, unit: m || 'unité' };
    }

    document.addEventListener('DOMContentLoaded', () => {
        document.getElementById('btn-recipe-search').addEventListener('click', searchRecipes);
        document.getElementById('recipe-search').addEventListener('keydown', e => {
            if (e.key === 'Enter') searchRecipes();
        });
        document.getElementById('btn-recipe-suggest').addEventListener('click', suggestRecipes);

        // Onglets recherche / sauvegardées
        document.querySelectorAll('[data-recipe-tab]').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('[data-recipe-tab]').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                const tab = btn.dataset.recipeTab;
                document.getElementById('recipe-tab-search').classList.toggle('hidden', tab !== 'search');
                document.getElementById('recipe-tab-saved').classList.toggle('hidden', tab !== 'saved');
                if (tab === 'saved') loadSavedRecipes();
            });
        });
    });

    // ---- Recettes sauvegardées ----
    async function loadSavedRecipes() {
        const data = await FrigoScan.API.get('/api/recipes/');
        if (!data.success) return;
        const recipes = data.recipes || [];
        savedRecipeTitles = new Set(recipes.map(r => r.title.toLowerCase().trim()));

        const badge = document.getElementById('badge-saved-recipes');
        if (badge) badge.textContent = recipes.length;

        const grid = document.getElementById('saved-recipes-list');
        const empty = document.getElementById('saved-recipes-empty');

        if (recipes.length === 0) {
            grid.innerHTML = '';
            empty.classList.remove('hidden');
            return;
        }
        empty.classList.add('hidden');

        grid.innerHTML = recipes.map((r, idx) => {
            const imgUrl = r.image_url || '';
            const imgHtml = imgUrl
                ? `<img class="recipe-card-img" src="${imgUrl}" alt="${r.title}" onerror="this.style.display='none'">`
                : `<div class="recipe-card-img" style="display:flex;align-items:center;justify-content:center;font-size:3rem;background:var(--bg-hover);">🍳</div>`;
            const prepTime = (r.prep_time || 0) + (r.cook_time || 0);
            return `
                <div class="recipe-card saved-recipe-card" data-saved-idx="${idx}">
                    ${imgHtml}
                    <div class="recipe-card-body">
                        <div class="recipe-card-title">${r.title}</div>
                        <div class="recipe-card-meta">
                            ${prepTime ? `<span><i class="fas fa-clock"></i> ${prepTime} min</span>` : ''}
                            <span><i class="fas fa-users"></i> ${r.servings || 4} pers.</span>
                            <span class="badge" style="background:var(--primary);color:#fff;"><i class="fas fa-bookmark"></i></span>
                        </div>
                    </div>
                    <button class="btn btn-danger btn-sm btn-delete-saved" data-id="${r.id}" title="Supprimer" style="position:absolute;top:8px;right:8px;z-index:2;"
                        onclick="event.stopPropagation(); FrigoScan.Recipes.deleteSaved(${r.id})">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            `;
        }).join('');

        grid.querySelectorAll('.saved-recipe-card').forEach(card => {
            card.addEventListener('click', () => {
                const idx = parseInt(card.dataset.savedIdx);
                showRecipeDetail(recipes[idx]);
            });
        });
    }

    Recipes.deleteSaved = async function (id) {
        const ok = await FrigoScan.confirm('Supprimer', 'Supprimer cette recette sauvegardée ?');
        if (!ok) return;
        const data = await FrigoScan.API.del(`/api/recipes/${id}`);
        if (data.success) {
            FrigoScan.toast('Recette supprimée.', 'success');
            loadSavedRecipes();
        }
    };

    // Charger les titres sauvegardés au démarrage du module (pour filtrer les suggestions)
    async function refreshSavedTitles() {
        try {
            const data = await FrigoScan.API.get('/api/recipes/');
            if (data.success) {
                savedRecipeTitles = new Set((data.recipes || []).map(r => r.title.toLowerCase().trim()));
                const badge = document.getElementById('badge-saved-recipes');
                if (badge) badge.textContent = (data.recipes || []).length;
            }
        } catch (_) {}
    }

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
            // Charger les titres sauvegardés pour filtrer les doublons
            await refreshSavedTitles();
            const data = await FrigoScan.API.get('/api/recipes/suggest?max_results=12&min_score=10');
            if (data.success) {
                // Filtrer les recettes déjà sauvegardées
                let recipes = data.recipes || [];
                recipes = recipes.filter(r => !savedRecipeTitles.has(r.title.toLowerCase().trim()));
                if (recipes.length === 0) {
                    FrigoScan.toast(data.message || 'Aucune nouvelle suggestion trouvée.', 'warning');
                }
                renderRecipes(recipes);
            }
        } finally {
            isSuggesting = false;
            if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fas fa-magic"></i> Suggestions selon mon frigo'; }
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

        // Nombre de personnes depuis les réglages
        const nbPersons = parseInt(localStorage.getItem('frigoscan-nb-persons') || '4');
        const recipeServings = recipe.servings || 4;
        const portionRatio = nbPersons / recipeServings;

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

        // Ajuster les quantités d'ingrédients selon le ratio de portions
        function adjustMeasure(measure) {
            if (!measure || portionRatio === 1) return measure;
            // Extraire le nombre du measure (ex: "200 g", "1/2 cup", "2")
            const numMatch = measure.match(/^([\d.,/]+)\s*(.*)/);
            if (numMatch) {
                let num = numMatch[1];
                const rest = numMatch[2];
                // Gérer les fractions (1/2, 1/4...)
                if (num.includes('/')) {
                    const parts = num.split('/');
                    num = parseFloat(parts[0]) / parseFloat(parts[1]);
                } else {
                    num = parseFloat(num.replace(',', '.'));
                }
                if (!isNaN(num)) {
                    const adjusted = Math.round(num * portionRatio * 10) / 10;
                    return `${adjusted} ${rest}`.trim();
                }
            }
            return measure;
        }

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
            const adjustedMeasure = adjustMeasure(ing.measure);
            const measureText = adjustedMeasure ? `${adjustedMeasure} ` : '';
            const addBtn = !isAvailable
                ? ` <button class="btn-add-ingredient" data-name="${(ing.name || '').replace(/"/g, '&quot;')}" data-measure="${(adjustedMeasure || '').replace(/"/g, '&quot;')}" title="Ajouter à la liste de courses">+</button>`
                : '';
            return `<span class="${cls}">${icon} ${measureText}${ing.name}${addBtn}</span>`;
        }).join('');

        const portionInfo = portionRatio !== 1
            ? `<div style="padding:8px 12px;background:var(--bg-hover);border-radius:var(--radius-sm);margin-bottom:12px;font-size:0.85rem;">
                   <i class="fas fa-info-circle"></i> Quantités ajustées pour <strong>${nbPersons} personnes</strong> (recette originale : ${recipeServings} pers.)
               </div>`
            : '';

        content.innerHTML = `
            ${imgHtml}
            <h2 style="margin-bottom:12px;">${recipe.title}</h2>
            <div style="display:flex;gap:12px;margin-bottom:16px;flex-wrap:wrap;">
                ${(recipe.prep_time || recipe.cook_time)
                    ? `<span class="badge"><i class="fas fa-clock"></i> Prépa: ${recipe.prep_time || 0}min — Cuisson: ${recipe.cook_time || 0}min</span>`
                    : ''}
                <span class="badge"><i class="fas fa-users"></i> ${nbPersons} personnes</span>
                ${recipe.match_score !== undefined ? `<span class="badge"><i class="fas fa-bullseye"></i> Compatibilité: ${recipe.match_score}%</span>` : ''}
            </div>
            ${portionInfo}
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
                const measure = btn.dataset.measure || '';
                const { qty, unit } = parseMeasure(measure);
                const res = await FrigoScan.API.post('/api/shopping/', { product_name: name, quantity: qty, unit: unit });
                if (res.success) {
                    FrigoScan.toast(`"${name}" ajouté à la liste de courses (${qty} ${unit})`, 'success');
                    btn.parentElement.classList.remove('missing');
                    btn.parentElement.classList.add('available');
                    btn.remove();
                }
            });
        });

        // Handler pour ajout de tous les manquants (avec mesures)
        const addAllBtn = content.querySelector('.btn-add-all-missing');
        if (addAllBtn) {
            addAllBtn.addEventListener('click', async () => {
                let added = 0;
                // Récupérer les pills manquants avec leurs mesures
                const missingPills = content.querySelectorAll('.btn-add-ingredient');
                for (const pill of missingPills) {
                    const name = pill.dataset.name;
                    const measure = pill.dataset.measure || '';
                    const { qty, unit } = parseMeasure(measure);
                    const res = await FrigoScan.API.post('/api/shopping/', { product_name: name, quantity: qty, unit: unit });
                    if (res.success) {
                        added++;
                        pill.parentElement.classList.remove('missing');
                        pill.parentElement.classList.add('available');
                        pill.remove();
                    }
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
        // Vérifier si déjà sauvegardée
        if (savedRecipeTitles.has(recipe.title.toLowerCase().trim())) {
            FrigoScan.toast('Cette recette est déjà dans "Mes recettes" !', 'warning');
            return;
        }
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
            FrigoScan.toast('Recette sauvegardée dans "Mes recettes" !', 'success');
            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-check"></i> Sauvegardée';
            btn.classList.remove('btn-success');
            btn.style.background = '#6b7280';
            btn.style.color = '#fff';
            await refreshSavedTitles();
        }
    };

    // Fermer modal par clic extérieur
    document.addEventListener('click', (e) => {
        const modal = document.getElementById('recipe-detail-modal');
        if (e.target === modal) Recipes.closeDetail();
    });

})();
