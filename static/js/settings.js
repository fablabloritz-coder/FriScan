/**
 * FrigoScan — Module Réglages (settings.js)
 */

(function () {
    const Settings = {};
    FrigoScan.Settings = Settings;

    // AudioContext partagé pour les aperçus de bip
    let beepCtx = null;
    function getBeepCtx() {
        if (!beepCtx) beepCtx = new (window.AudioContext || window.webkitAudioContext)();
        return beepCtx;
    }

    // Jouer un bip selon le type et le volume
    function playBeepType(type, volume) {
        try {
            const ctx = getBeepCtx();
            const vol = parseFloat(volume) || 0.5;
            const gain = ctx.createGain();
            gain.connect(ctx.destination);
            gain.gain.value = vol;

            if (type === 'standard') {
                const osc = ctx.createOscillator();
                osc.connect(gain);
                osc.frequency.value = 1200;
                osc.start();
                osc.stop(ctx.currentTime + 0.12);
            } else if (type === 'soft') {
                const osc = ctx.createOscillator();
                osc.connect(gain);
                osc.type = 'sine';
                osc.frequency.value = 800;
                osc.start();
                osc.stop(ctx.currentTime + 0.2);
            } else if (type === 'double') {
                const osc1 = ctx.createOscillator();
                osc1.connect(gain);
                osc1.frequency.value = 1200;
                osc1.start();
                osc1.stop(ctx.currentTime + 0.08);
                const osc2 = ctx.createOscillator();
                const gain2 = ctx.createGain();
                gain2.connect(ctx.destination);
                gain2.gain.value = vol;
                osc2.connect(gain2);
                osc2.frequency.value = 1500;
                osc2.start(ctx.currentTime + 0.12);
                osc2.stop(ctx.currentTime + 0.2);
            } else if (type === 'cash') {
                const osc = ctx.createOscillator();
                osc.connect(gain);
                osc.type = 'square';
                osc.frequency.setValueAtTime(523, ctx.currentTime);
                osc.frequency.setValueAtTime(659, ctx.currentTime + 0.08);
                osc.frequency.setValueAtTime(784, ctx.currentTime + 0.16);
                osc.start();
                osc.stop(ctx.currentTime + 0.25);
            }
        } catch (e) { /* audio non supporté */ }
    }

    // Exposer pour scanner.js
    Settings.playBeepType = playBeepType;

    Settings.load = async function () {
        // Attacher les listeners IMMÉDIATEMENT (avant l'API, pour que le bouton save fonctionne même si erreur réseau)
        document.getElementById('btn-save-settings').onclick = saveSettings;
        document.getElementById('btn-clear-fridge').onclick = clearFridge;
        document.getElementById('btn-reset-db').onclick = resetDB;

        // Sliders live (toujours attachés)
        const scanIntervalSlider = document.getElementById('settings-scan-interval');
        scanIntervalSlider.oninput = function () {
            document.getElementById('scan-interval-label').textContent = `${this.value}s`;
        };

        const beepVolumeSlider = document.getElementById('settings-beep-volume');
        beepVolumeSlider.oninput = function () {
            document.getElementById('beep-volume-label').textContent = `${Math.round(this.value * 100)}%`;
        };

        // Aperçu des bips
        document.querySelectorAll('.btn-preview-beep').forEach(btn => {
            btn.onclick = function (e) {
                e.preventDefault();
                e.stopPropagation();
                const type = this.dataset.beep;
                const vol = document.getElementById('settings-beep-volume').value;
                playBeepType(type, vol);
            };
        });

        // Slider taille des icônes
        const iconSizeSlider = document.getElementById('settings-icon-size');
        if (iconSizeSlider) {
            const savedSize = localStorage.getItem('frigoscan-icon-size') || '2.2rem';
            iconSizeSlider.value = parseFloat(savedSize) || 2.2;
            document.getElementById('icon-size-label').textContent = `${iconSizeSlider.value}rem`;
            iconSizeSlider.oninput = function () {
                document.getElementById('icon-size-label').textContent = `${this.value}rem`;
                localStorage.setItem('frigoscan-icon-size', `${this.value}rem`);
            };
        }

        // Charger les données depuis l'API
        const data = await FrigoScan.API.get('/api/settings/');
        if (!data.success) {
            console.warn('FrigoScan: Impossible de charger les réglages depuis le serveur');
            return;
        }
        const s = data.settings;
        console.log('FrigoScan: Réglages chargés depuis le serveur', s);

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
        scanIntervalSlider.value = s.scan_interval || 2;
        document.getElementById('scan-interval-label').textContent = `${s.scan_interval || 2}s`;
        beepVolumeSlider.value = s.scan_beep_volume || 0.5;
        document.getElementById('beep-volume-label').textContent = `${Math.round((s.scan_beep_volume || 0.5) * 100)}%`;
        document.getElementById('settings-scan-beep').checked = s.scan_beep === true || s.scan_beep === 'true';

        // Type de bip
        const beepType = s.beep_type || 'standard';
        const beepRadio = document.querySelector(`input[name="beep-type"][value="${beepType}"]`);
        if (beepRadio) beepRadio.checked = true;

        if (s.default_camera) document.getElementById('settings-default-camera').value = s.default_camera;
        if (s.webcam_resolution) document.getElementById('settings-webcam-resolution').value = s.webcam_resolution;

        // Thème
        const savedTheme = localStorage.getItem('frigoscan-theme') || s.theme || 'light';
        document.documentElement.setAttribute('data-theme', savedTheme);

        // Mettre à jour le localStorage pour les autres modules
        syncToLocalStorage(s);

        // Initialiser l'éditeur d'icônes (à chaque load pour garantir FOOD_DB disponible)
        initIconEditor();
    };

    // Synchroniser les réglages vers localStorage pour les autres modules
    function syncToLocalStorage(settingsObj) {
        try {
            const obj = {};
            for (const [k, v] of Object.entries(settingsObj)) {
                obj[k] = v;
            }
            localStorage.setItem('frigoscan-settings', JSON.stringify(obj));
            localStorage.setItem('frigoscan-nb-persons', settingsObj.nb_persons || '4');
        } catch (e) { /* ignore localStorage errors */ }
    }

    async function saveSettings() {
        const diets = [];
        document.querySelectorAll('#settings-diets input:checked').forEach(cb => diets.push(cb.value));

        const allergens = [];
        document.querySelectorAll('#settings-allergens input:checked').forEach(cb => allergens.push(cb.value));

        // Sauvegarder aussi les exclusions custom
        saveCustomDietExclusions();

        // Récupérer le type de bip sélectionné
        const beepTypeRadio = document.querySelector('input[name="beep-type"]:checked');
        const beepType = beepTypeRadio ? beepTypeRadio.value : 'standard';

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
            { key: 'beep_type', value: beepType },
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

        // Visuel : bouton en mode chargement
        const saveBtn = document.getElementById('btn-save-settings');
        const originalHTML = saveBtn.innerHTML;
        saveBtn.disabled = true;
        saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Enregistrement...';

        const data = await FrigoScan.API.put('/api/settings/bulk', { settings });
        console.log('FrigoScan: Sauvegarde réglages →', data);
        if (data.success) {
            // Animation de succès sur le bouton
            saveBtn.innerHTML = '<i class="fas fa-check"></i> Réglages enregistrés !';
            saveBtn.classList.remove('btn-success');
            saveBtn.classList.add('btn-saved');
            saveBtn.style.background = '#16a34a';
            saveBtn.style.color = '#fff';
            saveBtn.style.transform = 'scale(1.03)';

            FrigoScan.toast('Réglages enregistrés avec succès !', 'success');

            // Sauvegarder en local pour le mode offline
            const settingsObj = {};
            settings.forEach(s => {
                try { settingsObj[s.key] = JSON.parse(s.value); } catch { settingsObj[s.key] = s.value; }
            });
            syncToLocalStorage(settingsObj);

            // Restaurer le bouton après 2s
            setTimeout(() => {
                saveBtn.innerHTML = originalHTML;
                saveBtn.classList.remove('btn-saved');
                saveBtn.classList.add('btn-success');
                saveBtn.style.background = '';
                saveBtn.style.color = '';
                saveBtn.style.transform = '';
                saveBtn.disabled = false;
            }, 2500);
        } else {
            saveBtn.innerHTML = '<i class="fas fa-times"></i> Erreur !';
            saveBtn.style.background = '#dc2626';
            saveBtn.style.color = '#fff';
            setTimeout(() => {
                saveBtn.innerHTML = originalHTML;
                saveBtn.style.background = '';
                saveBtn.style.color = '';
                saveBtn.disabled = false;
            }, 2000);
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
            const currentIcon = catIcons[f.name] || f.emoji;
            const isImage = currentIcon && (currentIcon.startsWith('http') || currentIcon.startsWith('data:') || currentIcon.startsWith('/'));
            const previewHtml = isImage
                ? `<img src="${currentIcon}" alt="${f.name}" style="width:32px;height:32px;object-fit:contain;border-radius:4px;">`
                : `<span style="font-size:1.5rem;">${currentIcon}</span>`;
            return `
                <div class="icon-edit-item">
                    <div class="icon-edit-preview">${previewHtml}</div>
                    <span class="icon-edit-name">${f.name}</span>
                    <div class="icon-edit-controls">
                        <input type="text" class="icon-edit-input" data-cat="${category}" data-name="${f.name}" value="${currentIcon}" placeholder="Emoji ou URL">
                        <label class="btn btn-sm btn-secondary icon-upload-btn" title="Charger une image">
                            <i class="fas fa-image"></i>
                            <input type="file" accept="image/*" class="icon-file-input" data-cat="${category}" data-name="${f.name}" style="display:none;">
                        </label>
                    </div>
                </div>`;
        }).join('');

        // Handlers pour upload d'image
        grid.querySelectorAll('.icon-file-input').forEach(fileInput => {
            fileInput.addEventListener('change', (e) => {
                const file = e.target.files[0];
                if (!file) return;
                if (file.size > 200 * 1024) {
                    FrigoScan.toast('Image trop volumineuse (max 200 Ko).', 'warning');
                    return;
                }
                const reader = new FileReader();
                reader.onload = () => {
                    const dataUrl = reader.result;
                    const cat = fileInput.dataset.cat;
                    const name = fileInput.dataset.name;
                    // Mettre à jour l'input texte
                    const textInput = grid.querySelector(`.icon-edit-input[data-cat="${cat}"][data-name="${name}"]`);
                    if (textInput) textInput.value = dataUrl;
                    // Mettre à jour la preview
                    const item = fileInput.closest('.icon-edit-item');
                    const preview = item.querySelector('.icon-edit-preview');
                    if (preview) preview.innerHTML = `<img src="${dataUrl}" alt="${name}" style="width:32px;height:32px;object-fit:contain;border-radius:4px;">`;
                };
                reader.readAsDataURL(file);
            });
        });
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
        const activeTab = document.querySelector('#icon-edit-tabs .icon-tab-btn.active');
        if (activeTab) Settings.loadIconCategory(activeTab.dataset.cat);
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

    // Initialiser l'éditeur d'icônes avec onglets catégories cliquables
    function initIconEditor() {
        const tabsContainer = document.getElementById('icon-edit-tabs');
        if (!tabsContainer) return;

        const FOOD_DB = FrigoScan.ManualAdd && FrigoScan.ManualAdd.FOOD_DB ? FrigoScan.ManualAdd.FOOD_DB : {};
        const cats = Object.keys(FOOD_DB);

        const CATEGORY_EMOJIS = {
            'fruits': '🍎', 'légumes': '🥕', 'viandes': '🥩', 'poissons': '🐟',
            'produits laitiers': '🧀', 'boulangerie': '🍞', 'boissons': '🍷',
            'féculents': '🌾', 'conserves': '🥫', 'surgelés': '❄️',
            'condiments': '🌶️', 'snacks': '🍪', 'oeufs': '🥚',
            'charcuterie': '🥓', 'autre': '📦'
        };

        tabsContainer.innerHTML = cats.map(c =>
            `<button class="icon-tab-btn btn btn-sm" data-cat="${c}" style="margin:3px;">
                ${CATEGORY_EMOJIS[c] || '📦'} ${c.charAt(0).toUpperCase() + c.slice(1)}
            </button>`
        ).join('');

        tabsContainer.addEventListener('click', (e) => {
            const btn = e.target.closest('.icon-tab-btn');
            if (!btn) return;
            const cat = btn.dataset.cat;

            // Toggle actif
            tabsContainer.querySelectorAll('.icon-tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            Settings.loadIconCategory(cat);
            document.getElementById('icon-edit-actions').classList.remove('hidden');
        });
    }

    // Init au chargement
    document.addEventListener('DOMContentLoaded', () => {
        initCustomDiet();
        initIconEditor();
    });

})();
