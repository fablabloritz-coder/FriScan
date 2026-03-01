/**
 * FrigoScan — Module Réglages (settings.js)
 */

(function () {
    const Settings = {};
    FrigoScan.Settings = Settings;

    Settings.load = async function () {
        const data = await FrigoScan.API.get('/api/settings/');
        if (!data.success) return;
        const s = data.settings;

        // Régimes
        const diets = Array.isArray(s.diets) ? s.diets : [];
        document.querySelectorAll('#settings-diets input[type="checkbox"]').forEach(cb => {
            cb.checked = diets.includes(cb.value);
        });

        // Allergènes
        const allergens = Array.isArray(s.allergens) ? s.allergens : [];
        document.querySelectorAll('#settings-allergens input[type="checkbox"]').forEach(cb => {
            cb.checked = allergens.includes(cb.value);
        });

        // Nombre de personnes
        document.getElementById('settings-nb-persons').value = s.nb_persons || 4;
        document.getElementById('settings-shopping-freq').value = s.shopping_frequency || 7;

        // Recettes
        document.getElementById('settings-prefer-dlc').checked = s.recipe_prefer_dlc === true || s.recipe_prefer_dlc === 'true';
        document.getElementById('settings-prefer-seasonal').checked = s.recipe_prefer_seasonal === true || s.recipe_prefer_seasonal === 'true';
        document.getElementById('settings-menu-mode').value = s.menu_mode || 'after_shopping';

        // Scanner
        document.getElementById('settings-scan-interval').value = s.scan_interval || 2;
        document.getElementById('scan-interval-label').textContent = `${s.scan_interval || 2}s`;
        document.getElementById('settings-beep-volume').value = s.scan_beep_volume || 0.5;
        document.getElementById('settings-scan-beep').checked = s.scan_beep === true || s.scan_beep === 'true';
        if (s.default_camera) document.getElementById('settings-default-camera').value = s.default_camera;
        if (s.webcam_resolution) document.getElementById('settings-webcam-resolution').value = s.webcam_resolution;

        // Thème
        const savedTheme = localStorage.getItem('frigoscan-theme') || s.theme || 'light';
        document.documentElement.setAttribute('data-theme', savedTheme);

        // Listeners
        document.getElementById('settings-scan-interval').oninput = function () {
            document.getElementById('scan-interval-label').textContent = `${this.value}s`;
        };

        document.getElementById('btn-save-settings').onclick = saveSettings;
        document.getElementById('btn-clear-fridge').onclick = clearFridge;
        document.getElementById('btn-reset-db').onclick = resetDB;
    };

    async function saveSettings() {
        const diets = [];
        document.querySelectorAll('#settings-diets input:checked').forEach(cb => diets.push(cb.value));

        const allergens = [];
        document.querySelectorAll('#settings-allergens input:checked').forEach(cb => allergens.push(cb.value));

        const settings = [
            { key: 'diets', value: JSON.stringify(diets) },
            { key: 'allergens', value: JSON.stringify(allergens) },
            { key: 'nb_persons', value: document.getElementById('settings-nb-persons').value },
            { key: 'shopping_frequency', value: document.getElementById('settings-shopping-freq').value },
            { key: 'recipe_prefer_dlc', value: String(document.getElementById('settings-prefer-dlc').checked) },
            { key: 'recipe_prefer_seasonal', value: String(document.getElementById('settings-prefer-seasonal').checked) },
            { key: 'menu_mode', value: document.getElementById('settings-menu-mode').value },
            { key: 'scan_interval', value: document.getElementById('settings-scan-interval').value },
            { key: 'scan_beep_volume', value: document.getElementById('settings-beep-volume').value },
            { key: 'scan_beep', value: String(document.getElementById('settings-scan-beep').checked) },
            { key: 'default_camera', value: document.getElementById('settings-default-camera').value },
            { key: 'webcam_resolution', value: document.getElementById('settings-webcam-resolution').value },
            { key: 'theme', value: document.documentElement.getAttribute('data-theme') },
        ];

        // Exclusions du régime personnalisé
        const customSection = document.getElementById('custom-diet-section');
        if (customSection) {
            const exclusions = [];
            customSection.querySelectorAll('input[type="checkbox"]:checked').forEach(cb => exclusions.push(cb.value));
            const keywords = (document.getElementById('custom-diet-keywords')?.value || '').trim();
            if (keywords) {
                keywords.split(',').forEach(k => { const t = k.trim().toLowerCase(); if (t) exclusions.push(t); });
            }
            settings.push({ key: 'custom_exclusions', value: JSON.stringify(exclusions) });
        }

        const data = await FrigoScan.API.put('/api/settings/bulk', { settings });
        if (data.success) {
            FrigoScan.toast('Réglages enregistrés !', 'success');

            // Sauvegarder en local pour le mode offline
            const settingsObj = {};
            settings.forEach(s => {
                try { settingsObj[s.key] = JSON.parse(s.value); } catch { settingsObj[s.key] = s.value; }
            });
            localStorage.setItem('frigoscan-settings', JSON.stringify(settingsObj));
            localStorage.setItem('frigoscan-nb-persons', document.getElementById('settings-nb-persons').value);
        }
    }

    async function clearFridge() {
        const confirmed = await FrigoScan.confirm(
            'Vider le frigo',
            'Êtes-vous sûr de vouloir vider intégralement le frigo ? Cette action est irréversible.'
        );
        if (!confirmed) return;
        const confirmed2 = await FrigoScan.confirm(
            'Confirmation finale',
            'ATTENTION : Tous les produits du frigo seront supprimés. Confirmer ?'
        );
        if (!confirmed2) return;

        const data = await FrigoScan.API.del('/api/fridge/clear/all?confirm=true');
        if (data.success) {
            FrigoScan.toast(data.message, 'success');
        }
    }

    async function resetDB() {
        const confirmed = await FrigoScan.confirm(
            'Réinitialiser',
            'ATTENTION : Toutes les données (frigo, recettes, historique, réglages) seront perdues.'
        );
        if (!confirmed) return;
        const confirmed2 = await FrigoScan.confirm(
            'Dernière chance',
            'Cette action est IRRÉVERSIBLE. Voulez-vous vraiment tout supprimer ?'
        );
        if (!confirmed2) return;

        const data = await FrigoScan.API.post('/api/settings/reset?confirm=true');
        if (data.success) {
            FrigoScan.toast('Application réinitialisée. Rechargement...', 'success');
            setTimeout(() => location.reload(), 1500);
        }
    }

    // Export / Import
    Settings.exportAll = function () {
        window.open('/api/export/all/json', '_blank');
    };

    Settings.exportFridgeCSV = function () {
        window.open('/api/export/fridge/csv', '_blank');
    };

    Settings.backupDB = function () {
        window.open('/api/export/database/backup', '_blank');
    };

    Settings.importData = async function (inputEl) {
        const file = inputEl.files[0];
        if (!file) return;

        const formData = new FormData();
        formData.append('file', file);

        try {
            const resp = await fetch('/api/export/import/json', {
                method: 'POST',
                body: formData,
            });
            const data = await resp.json();
            if (data.success) {
                FrigoScan.toast(data.message || 'Données importées !', 'success');
            } else {
                FrigoScan.toast(data.message || 'Erreur lors de l\'import.', 'error');
            }
        } catch (e) {
            FrigoScan.toast('Erreur lors de l\'import : ' + e.message, 'error');
        }
        inputEl.value = '';
    };

    // ---- Personnalisation des icônes ----
    Settings.loadIconCategory = function (category) {
        const grid = document.getElementById('icon-edit-grid');
        if (!grid || !category) { if (grid) grid.innerHTML = ''; return; }

        // Récupérer la FOOD_DB depuis ManualAdd
        const FOOD_DB = FrigoScan.ManualAdd && FrigoScan.ManualAdd.FOOD_DB ? FrigoScan.ManualAdd.FOOD_DB : {};
        const foods = FOOD_DB[category] || [];
        const customIcons = JSON.parse(localStorage.getItem('frigoscan-custom-icons') || '{}');
        const catIcons = customIcons[category] || {};

        grid.innerHTML = foods.map(f => {
            const currentEmoji = catIcons[f.name] || f.emoji;
            return `
                <div class="icon-edit-item">
                    <input type="text" class="icon-edit-input" data-cat="${category}" data-name="${f.name}" value="${currentEmoji}" maxlength="4">
                    <span class="icon-edit-name">${f.name}</span>
                </div>`;
        }).join('');
    };

    Settings.saveCustomIcons = function () {
        const inputs = document.querySelectorAll('#icon-edit-grid .icon-edit-input');
        const customIcons = JSON.parse(localStorage.getItem('frigoscan-custom-icons') || '{}');

        inputs.forEach(inp => {
            const cat = inp.dataset.cat;
            const name = inp.dataset.name;
            const val = inp.value.trim();
            if (!customIcons[cat]) customIcons[cat] = {};
            if (val) customIcons[cat][name] = val;
        });

        localStorage.setItem('frigoscan-custom-icons', JSON.stringify(customIcons));
        FrigoScan.toast('Icônes personnalisées enregistrées !', 'success');
    };

    Settings.resetCustomIcons = function () {
        localStorage.removeItem('frigoscan-custom-icons');
        const select = document.getElementById('icon-edit-category');
        if (select && select.value) Settings.loadIconCategory(select.value);
        FrigoScan.toast('Icônes réinitialisées.', 'success');
    };

    // ---- Régime personnalisé ----
    function initCustomDiet() {
        const toggle = document.getElementById('diet-custom-toggle');
        const section = document.getElementById('custom-diet-section');
        if (!toggle || !section) return;

        toggle.addEventListener('change', () => {
            section.classList.toggle('hidden', !toggle.checked);
        });

        // Charger les exclusions custom depuis localStorage
        const saved = JSON.parse(localStorage.getItem('frigoscan-custom-exclusions') || '[]');
        section.querySelectorAll('input[type="checkbox"]').forEach(cb => {
            cb.checked = saved.includes(cb.value);
        });

        const customInput = document.getElementById('custom-diet-keywords');
        if (customInput) {
            customInput.value = localStorage.getItem('frigoscan-custom-keywords') || '';
        }
    }

    function saveCustomDietExclusions() {
        const section = document.getElementById('custom-diet-section');
        if (!section) return;

        const exclusions = [];
        section.querySelectorAll('input[type="checkbox"]:checked').forEach(cb => exclusions.push(cb.value));
        localStorage.setItem('frigoscan-custom-exclusions', JSON.stringify(exclusions));

        const customInput = document.getElementById('custom-diet-keywords');
        if (customInput) {
            localStorage.setItem('frigoscan-custom-keywords', customInput.value.trim());
        }
    }

    // Initialiser le sélecteur de catégorie des icônes
    function initIconEditor() {
        const select = document.getElementById('icon-edit-category');
        if (!select) return;

        const FOOD_DB = FrigoScan.ManualAdd && FrigoScan.ManualAdd.FOOD_DB ? FrigoScan.ManualAdd.FOOD_DB : {};
        const cats = Object.keys(FOOD_DB);
        select.innerHTML = '<option value="">— Choisir une catégorie —</option>' +
            cats.map(c => `<option value="${c}">${c.charAt(0).toUpperCase() + c.slice(1)}</option>`).join('');
    }

    // Patch saveSettings pour inclure les exclusions custom
    const originalSaveSettings = saveSettings;
    saveSettings = async function () {
        saveCustomDietExclusions();
        await originalSaveSettings();
    };

    // Init au chargement
    document.addEventListener('DOMContentLoaded', () => {
        initCustomDiet();
        initIconEditor();
    });
