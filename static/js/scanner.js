/**
 * FrigoScan — Module Scanner (scan.js)
 * Scan webcam (html5-qrcode), saisie manuelle, panier temporaire.
 */

(function () {
    const Scanner = {};
    FrigoScan.Scanner = Scanner;

    let html5QrCode = null;
    let isScanning = false;
    let scanCart = [];
    let currentProduct = null;

    // Bip sonore
    function playBeep() {
        try {
            const settings = JSON.parse(localStorage.getItem('frigoscan-settings') || '{}');
            if (settings.scan_beep === false || settings.scan_beep === 'false') return;
            const vol = parseFloat(settings.scan_beep_volume) || 0.5;
            const type = settings.beep_type || 'standard';
            // Utiliser le système de bip centralisé dans settings.js
            if (FrigoScan.Settings && FrigoScan.Settings.playBeepType) {
                FrigoScan.Settings.playBeepType(type, vol);
            } else {
                // Fallback basique
                const ctx = new (window.AudioContext || window.webkitAudioContext)();
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();
                osc.connect(gain);
                gain.connect(ctx.destination);
                osc.frequency.value = 1200;
                gain.gain.value = vol;
                osc.start();
                osc.stop(ctx.currentTime + 0.12);
            }
        } catch (e) { /* silent */ }
    }

    // Init scanner
    Scanner.init = function () {
        setupModeTabs();
        setupManualScan();
        setupCartButtons();
        setupFocusSlider();
        listCameras();
        // Afficher le bouton "Activer la caméra" au lieu d'auto-démarrer
        showStartCameraBtn();
    };

    function showStartCameraBtn() {
        const reader = document.getElementById('scanner-reader');
        if (!reader) return;
        // Ne pas recréer si la caméra tourne déjà
        if (isScanning) return;
        reader.innerHTML = `
            <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:220px;gap:16px;">
                <i class="fas fa-camera" style="font-size:3rem;color:var(--text-muted);"></i>
                <button id="btn-start-camera" class="btn btn-primary btn-lg">
                    <i class="fas fa-video"></i> Activer la caméra
                </button>
                <p style="color:var(--text-muted);font-size:0.82rem;text-align:center;">
                    Autorisez l'accès à la caméra pour scanner les codes-barres
                </p>
            </div>`;
        document.getElementById('btn-start-camera').addEventListener('click', () => {
            reader.innerHTML = '';
            startCamera();
        });
    }

    function setupModeTabs() {
        document.querySelectorAll('[data-scanner-mode]').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('[data-scanner-mode]').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                const mode = btn.dataset.scannerMode;
                document.getElementById('scanner-camera-mode').classList.toggle('hidden', mode !== 'camera');
                document.getElementById('scanner-manual-mode').classList.toggle('hidden', mode !== 'manual');
                if (mode === 'camera') startCamera();
                else stopCamera();
            });
        });
    }

    function setupManualScan() {
        const input = document.getElementById('manual-barcode');
        const btn = document.getElementById('btn-manual-scan');

        btn.addEventListener('click', () => {
            const code = input.value.trim();
            if (code.length >= 4) Scanner.lookupBarcode(code);
            else FrigoScan.toast('Veuillez saisir un code-barres valide.', 'warning');
        });
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') btn.click();
        });
    }

    function setupCartButtons() {
        document.getElementById('btn-add-to-cart').addEventListener('click', addToCart);
        document.getElementById('btn-scan-next').addEventListener('click', resetScanResult);
        document.getElementById('btn-transfer-fridge').addEventListener('click', transferToFridge);
        document.getElementById('btn-clear-cart').addEventListener('click', clearCart);
        document.getElementById('btn-retry-scan').addEventListener('click', () => {
            resetScanResult();
        });
    }

    // Caméras
    async function listCameras() {
        if (typeof Html5Qrcode === 'undefined') return;
        try {
            const devices = await Html5Qrcode.getCameras();
            const select = document.getElementById('scanner-camera-select');
            select.innerHTML = '<option value="">Sélectionner une caméra...</option>';
            devices.forEach(d => {
                const opt = document.createElement('option');
                opt.value = d.id;
                opt.textContent = d.label || `Caméra ${d.id}`;
                select.appendChild(opt);
            });
            select.addEventListener('change', () => {
                if (select.value) startCamera(select.value);
            });
            // Aussi peupler les réglages
            const settingsSelect = document.getElementById('settings-default-camera');
            if (settingsSelect) {
                settingsSelect.innerHTML = '<option value="">Automatique</option>';
                devices.forEach(d => {
                    const opt = document.createElement('option');
                    opt.value = d.id;
                    opt.textContent = d.label || `Caméra ${d.id}`;
                    settingsSelect.appendChild(opt);
                });
            }
        } catch (e) {
            console.warn('Impossible de lister les caméras:', e);
        }
    }

    async function startCamera(cameraId) {
        if (typeof Html5Qrcode === 'undefined') {
            FrigoScan.toast('Bibliothèque de scan non chargée. Mode hors-ligne : utilisez la saisie manuelle.', 'warning');
            return;
        }
        await stopCamera();

        html5QrCode = new Html5Qrcode('scanner-reader');
        const settings = JSON.parse(localStorage.getItem('frigoscan-settings') || '{}');
        const interval = (parseInt(settings.scan_interval) || 2) * 1000;

        const config = {
            fps: Math.round(1000 / interval),
            qrbox: { width: 280, height: 160 },
            aspectRatio: 4 / 3,
        };

        // Essayer d'abord avec le cameraId ou toute caméra disponible
        const attempts = [];
        if (cameraId) {
            attempts.push(cameraId);
        } else {
            // 1) facingMode environment avec focus (mobile)
            attempts.push({ facingMode: 'environment', advanced: [{ focusMode: 'continuous' }] });
            // 2) facingMode environment sans focus
            attempts.push({ facingMode: 'environment' });
            // 3) facingMode user (webcam frontale)
            attempts.push({ facingMode: 'user' });
        }

        let started = false;
        for (const constraints of attempts) {
            try {
                await html5QrCode.start(constraints, config, onScanSuccess, onScanFailure);
                isScanning = true;
                started = true;
                break;
            } catch (e) {
                console.warn('Tentative caméra échouée:', constraints, e.message || e);
                // Recréer l'instance pour la prochaine tentative
                try { await html5QrCode.stop(); } catch (_) {}
                html5QrCode = new Html5Qrcode('scanner-reader');
            }
        }

        if (!started) {
            FrigoScan.toast('Impossible de démarrer la caméra. Vérifiez les permissions ou sélectionnez une caméra.', 'error');
            showStartCameraBtn();
            return;
        }

        // Activer le focus continu + configurer le slider de focus
        try {
            const videoElem = document.querySelector('#scanner-reader video');
            if (videoElem && videoElem.srcObject) {
                const track = videoElem.srcObject.getVideoTracks()[0];
                if (track) {
                    const caps = track.getCapabilities ? track.getCapabilities() : {};
                    // Configurer le slider focus si supporté
                    const focusSlider = document.getElementById('focus-slider');
                    const focusContainer = document.getElementById('focus-control');
                    if (caps.focusDistance && focusSlider && focusContainer) {
                        focusContainer.classList.remove('hidden');
                        focusSlider.min = caps.focusDistance.min;
                        focusSlider.max = caps.focusDistance.max;
                        focusSlider.step = caps.focusDistance.step || 1;
                        focusSlider.value = (caps.focusDistance.min + caps.focusDistance.max) / 2;
                        document.getElementById('focus-value').textContent = 'Auto';
                    } else if (focusContainer) {
                        focusContainer.classList.add('hidden');
                    }
                    // Focus continu par défaut
                    if (caps.focusMode && caps.focusMode.includes('continuous')) {
                        await track.applyConstraints({ advanced: [{ focusMode: 'continuous' }] });
                    }
                }
            }
        } catch (focusErr) { /* Focus non supporté */ }
    }

    // Slider focus
    function setupFocusSlider() {
        const slider = document.getElementById('focus-slider');
        const autoBtn = document.getElementById('btn-focus-auto');
        if (!slider) return;

        slider.addEventListener('input', async () => {
            const val = parseFloat(slider.value);
            document.getElementById('focus-value').textContent = val.toFixed(0);
            try {
                const videoElem = document.querySelector('#scanner-reader video');
                if (videoElem && videoElem.srcObject) {
                    const track = videoElem.srcObject.getVideoTracks()[0];
                    if (track) {
                        await track.applyConstraints({
                            advanced: [{ focusMode: 'manual', focusDistance: val }]
                        });
                    }
                }
            } catch (e) { /* ignore */ }
        });

        if (autoBtn) {
            autoBtn.addEventListener('click', async () => {
                document.getElementById('focus-value').textContent = 'Auto';
                try {
                    const videoElem = document.querySelector('#scanner-reader video');
                    if (videoElem && videoElem.srcObject) {
                        const track = videoElem.srcObject.getVideoTracks()[0];
                        if (track) {
                            await track.applyConstraints({ advanced: [{ focusMode: 'continuous' }] });
                        }
                    }
                } catch (e) { /* ignore */ }
            });
        }
    }

    async function stopCamera() {
        if (html5QrCode && isScanning) {
            try {
                await html5QrCode.stop();
            } catch (e) { /* ignore */ }
            isScanning = false;
        }
    }

    let lastScannedCode = '';
    let lastScanTime = 0;

    function onScanSuccess(decodedText) {
        // Empêcher les scans en double
        const now = Date.now();
        if (decodedText === lastScannedCode && (now - lastScanTime) < 3000) return;
        lastScannedCode = decodedText;
        lastScanTime = now;

        playBeep();
        Scanner.lookupBarcode(decodedText);
    }

    function onScanFailure() { /* silence */ }

    // Recherche produit
    Scanner.lookupBarcode = async function (barcode) {
        document.getElementById('scan-error').classList.add('hidden');
        document.getElementById('scan-result').classList.add('hidden');
        document.getElementById('btn-retry-scan').classList.add('hidden');

        const data = await FrigoScan.API.get(`/api/scan/barcode/${encodeURIComponent(barcode)}`);
        if (data.success && data.product) {
            currentProduct = data.product;
            displayScanResult(data.product);

            // Alerte allergènes
            if (data.product.allergens && data.product.allergens.length) {
                const settings = JSON.parse(localStorage.getItem('frigoscan-settings') || '{}');
                const userAllergens = settings.allergens || [];
                const matched = data.product.allergens.filter(a => userAllergens.includes(a));
                if (matched.length) {
                    FrigoScan.toast(`⚠️ Allergène détecté : ${matched.join(', ')}`, 'warning');
                }
            }
        } else {
            const errDiv = document.getElementById('scan-error');
            errDiv.innerHTML = `<i class="fas fa-exclamation-circle"></i> ${data.message || 'Produit non trouvé.'}
                <br><small>Vous pouvez l'ajouter manuellement via "Ajout manuel".</small>`;
            errDiv.classList.remove('hidden');
            document.getElementById('btn-retry-scan').classList.remove('hidden');
        }
    };

    function displayScanResult(product) {
        const img = document.getElementById('scan-product-img');
        img.src = product.image_url || '';
        img.alt = product.name;
        img.style.display = product.image_url ? 'block' : 'none';

        document.getElementById('scan-product-name').textContent = product.name;
        document.getElementById('scan-product-brand').textContent = product.brand || '';
        document.getElementById('scan-product-category').textContent = product.category || '';

        // Quantité & unité : chercher poids depuis nutrition_json ou product_quantity
        const quantity = product.product_quantity || product.quantity;
        const unitHint = product.quantity_unit || '';
        if (quantity && parseFloat(quantity) > 0) {
            document.getElementById('scan-qty').value = parseFloat(quantity);
            // Deviner l'unité depuis les infos produit
            const unitLower = unitHint.toLowerCase();
            if (unitLower.includes('kg')) document.getElementById('scan-unit').value = 'kg';
            else if (unitLower.includes('ml')) document.getElementById('scan-unit').value = 'mL';
            else if (unitLower.includes('l')) document.getElementById('scan-unit').value = 'L';
            else if (unitLower.includes('g')) document.getElementById('scan-unit').value = 'g';
            document.getElementById('scan-weight-presets-group').style.display = 'none';
        } else {
            document.getElementById('scan-qty').value = 1;
            document.getElementById('scan-unit').value = 'unité';
            // Afficher les poids prédéfinis
            document.getElementById('scan-weight-presets-group').style.display = '';
        }

        // DLC : +7 jours par défaut
        const dlcDate = new Date();
        dlcDate.setDate(dlcDate.getDate() + 7);
        document.getElementById('scan-dlc').value = dlcDate.toISOString().split('T')[0];

        document.getElementById('scan-result').classList.remove('hidden');
    }

    Scanner.setWeight = function (value, unit) {
        document.getElementById('scan-qty').value = value;
        document.getElementById('scan-unit').value = unit;
        // Highlight le bouton sélectionné
        document.querySelectorAll('.weight-btn').forEach(b => b.classList.remove('active'));
        if (event && event.currentTarget) event.currentTarget.classList.add('active');
    };

    Scanner.adjustQty = function (delta) {
        const input = document.getElementById('scan-qty');
        const val = Math.max(0.1, parseFloat(input.value || 1) + delta);
        input.value = Math.round(val * 10) / 10;
    };

    function addToCart() {
        if (!currentProduct) return;
        const item = {
            ...currentProduct,
            product_id: currentProduct.id || null,
            quantity: parseFloat(document.getElementById('scan-qty').value) || 1,
            unit: document.getElementById('scan-unit').value,
            dlc: document.getElementById('scan-dlc').value || null,
        };
        scanCart.push(item);
        updateCartDisplay();
        resetScanResult();
        FrigoScan.toast(`"${item.name}" ajouté au panier.`, 'success');
    }

    function resetScanResult() {
        document.getElementById('scan-result').classList.add('hidden');
        document.getElementById('scan-error').classList.add('hidden');
        document.getElementById('btn-retry-scan').classList.add('hidden');
        document.getElementById('scan-weight-presets-group').style.display = 'none';
        currentProduct = null;
        lastScannedCode = '';
        lastScanTime = 0;
        // Relancer la caméra si on est en mode caméra
        const cameraMode = document.getElementById('scanner-camera-mode');
        if (cameraMode && !cameraMode.classList.contains('hidden')) {
            const select = document.getElementById('scanner-camera-select');
            startCamera(select.value || undefined);
        }
        // Vider le champ code barre manuel
        const manualInput = document.getElementById('manual-barcode');
        if (manualInput) manualInput.value = '';
    }

    function updateCartDisplay() {
        const cartDiv = document.getElementById('scan-cart');
        const itemsDiv = document.getElementById('cart-items');
        const countSpan = document.getElementById('cart-count');

        if (scanCart.length === 0) {
            cartDiv.classList.add('hidden');
            return;
        }

        cartDiv.classList.remove('hidden');
        countSpan.textContent = scanCart.length;

        itemsDiv.innerHTML = scanCart.map((item, idx) => `
            <div class="cart-item">
                <div>
                    <div class="cart-item-name">${item.name}</div>
                    <div class="cart-item-details">${item.quantity} ${item.unit} — DLC: ${item.dlc || 'Non définie'}</div>
                </div>
                <button class="btn btn-danger btn-sm" onclick="FrigoScan.Scanner.removeFromCart(${idx})">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `).join('');
    }

    Scanner.removeFromCart = function (idx) {
        scanCart.splice(idx, 1);
        updateCartDisplay();
    };

    async function transferToFridge() {
        if (scanCart.length === 0) return;
        const items = scanCart.map(item => ({
            product_id: item.product_id,
            name: item.name,
            barcode: item.barcode || '',
            image_url: item.image_url || '',
            category: item.category || 'autre',
            quantity: item.quantity,
            unit: item.unit,
            dlc: item.dlc,
            nutrition_json: item.nutrition_json || '{}',
        }));

        const data = await FrigoScan.API.post('/api/fridge/batch', items);
        if (data.success) {
            FrigoScan.toast(data.message || 'Produits ajoutés au frigo !', 'success');
            scanCart = [];
            updateCartDisplay();
        }
    }

    async function clearCart() {
        const confirmed = await FrigoScan.confirm('Vider le panier', 'Supprimer tous les produits du panier temporaire ?');
        if (confirmed) {
            scanCart = [];
            updateCartDisplay();
        }
    }

})();
