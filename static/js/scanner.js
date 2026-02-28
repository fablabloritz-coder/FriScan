/**
 * FriScan — Module Scanner Webcam
 * Capture d'images via la webcam et envoi au serveur pour décodage.
 */

let cameraStream = null;

async function startCamera() {
    const video = document.getElementById('scanner-video');
    const overlay = document.getElementById('scanner-overlay');
    const btnStart = document.getElementById('btn-start-cam');
    const btnCapture = document.getElementById('btn-capture');
    const btnStop = document.getElementById('btn-stop-cam');

    try {
        // Demander l'accès à la caméra
        cameraStream = await navigator.mediaDevices.getUserMedia({
            video: {
                facingMode: 'environment', // caméra arrière si dispo
                width: { ideal: 1280 },
                height: { ideal: 720 },
            }
        });

        video.srcObject = cameraStream;
        overlay.style.display = 'block';

        btnStart.disabled = true;
        btnCapture.disabled = false;
        btnStop.disabled = false;

        notify('Caméra activée. Placez le code-barres devant la caméra.', 'info');

        // Lancer la détection automatique toutes les 1.5s
        startAutoScan();

    } catch (err) {
        console.error('Erreur caméra:', err);
        if (err.name === 'NotAllowedError') {
            notify('Accès à la caméra refusé. Vérifiez les permissions du navigateur.', 'error');
        } else if (err.name === 'NotFoundError') {
            notify('Aucune caméra détectée.', 'error');
        } else {
            notify('Erreur lors de l\'activation de la caméra.', 'error');
        }
    }
}

function stopCamera() {
    const video = document.getElementById('scanner-video');
    const overlay = document.getElementById('scanner-overlay');
    const btnStart = document.getElementById('btn-start-cam');
    const btnCapture = document.getElementById('btn-capture');
    const btnStop = document.getElementById('btn-stop-cam');

    if (cameraStream) {
        cameraStream.getTracks().forEach(track => track.stop());
        cameraStream = null;
    }

    video.srcObject = null;
    overlay.style.display = 'none';

    btnStart.disabled = false;
    btnCapture.disabled = true;
    btnStop.disabled = true;

    stopAutoScan();
    notify('Caméra arrêtée.', 'info');
}

async function captureAndScan() {
    const video = document.getElementById('scanner-video');
    const canvas = document.getElementById('scanner-canvas');

    if (!cameraStream || video.readyState < 2) {
        notify('La caméra n\'est pas prête.', 'warning');
        return;
    }

    // Capturer l'image
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0);

    // Convertir en blob
    const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', 0.9));
    const formData = new FormData();
    formData.append('file', blob, 'capture.jpg');

    try {
        const res = await fetch(`${API_BASE}/api/scanner/image`, {
            method: 'POST',
            body: formData,
        });

        if (res.status === 422) {
            // Pas de code-barres détecté — normal en mode auto
            return false;
        }

        if (!res.ok) throw new Error();

        const product = await res.json();
        scannedProduct = product;
        displayScannedProduct(product);
        notify(`Code-barres détecté : ${product.barcode}`, 'success');
        stopCamera(); // Arrêter après un scan réussi
        return true;
    } catch (e) {
        // Silencieux en mode auto
        return false;
    }
}


// ════════════ SCAN AUTOMATIQUE ════════════

let autoScanInterval = null;

function startAutoScan() {
    stopAutoScan();
    autoScanInterval = setInterval(async () => {
        const found = await captureAndScan();
        if (found) {
            stopAutoScan();
        }
    }, 1500); // Scan toutes les 1.5 secondes
}

function stopAutoScan() {
    if (autoScanInterval) {
        clearInterval(autoScanInterval);
        autoScanInterval = null;
    }
}
