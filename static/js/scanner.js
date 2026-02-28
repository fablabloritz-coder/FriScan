// =====================================
// FriScan - Scanner Camera v2.0
// Multi-camera + Flash + Auto-scan
// =====================================

let stream = null;
let autoScanInterval = null;
let cameraDevices = [];
let currentDeviceId = null;
let flashEnabled = false;

// Enumerate cameras
async function enumerateCameras() {
    try {
        // Need a temporary stream to get labels
        const tmpStream = await navigator.mediaDevices.getUserMedia({ video: true });
        tmpStream.getTracks().forEach(t => t.stop());

        const devices = await navigator.mediaDevices.enumerateDevices();
        cameraDevices = devices.filter(d => d.kind === 'videoinput');
        const select = document.getElementById('camera-select');
        if (!select) return;
        select.innerHTML = '';
        cameraDevices.forEach((d, i) => {
            const opt = document.createElement('option');
            opt.value = d.deviceId;
            opt.textContent = d.label || ('Camera ' + (i + 1));
            select.appendChild(opt);
        });
        if (cameraDevices.length > 0) {
            currentDeviceId = cameraDevices[cameraDevices.length - 1].deviceId;
            select.value = currentDeviceId;
        }
        select.addEventListener('change', () => {
            currentDeviceId = select.value;
            if (stream) { stopCamera(); startCamera(); }
        });
    } catch (e) {
        console.error('Camera enum error:', e);
    }
}

async function startCamera() {
    try {
        const constraints = {
            video: {
                deviceId: currentDeviceId ? { exact: currentDeviceId } : undefined,
                width: { ideal: 1280 },
                height: { ideal: 720 },
                facingMode: currentDeviceId ? undefined : 'environment'
            }
        };
        stream = await navigator.mediaDevices.getUserMedia(constraints);
        const video = document.getElementById('scanner-video');
        video.srcObject = stream;

        document.getElementById('video-container').classList.remove('hidden');
        document.querySelector('.scanner-overlay').style.display = 'block';
        document.getElementById('btn-start-cam').classList.add('hidden');
        document.getElementById('btn-stop-cam').classList.remove('hidden');

        startAutoScan();
    } catch (e) {
        console.error('Camera start error:', e);
        showNotification('Impossible d\'acceder a la camera', 'error');
    }
}

function stopCamera() {
    if (stream) {
        stream.getTracks().forEach(t => t.stop());
        stream = null;
    }
    stopAutoScan();
    document.getElementById('video-container').classList.add('hidden');
    document.querySelector('.scanner-overlay').style.display = 'none';
    document.getElementById('btn-start-cam').classList.remove('hidden');
    document.getElementById('btn-stop-cam').classList.add('hidden');
    flashEnabled = false;
}

function startAutoScan() {
    stopAutoScan();
    const settings = typeof getSettings === 'function' ? getSettings() : { scanInterval: 2 };
    const interval = (settings.scanInterval || 2) * 1000;
    autoScanInterval = setInterval(captureAndScan, interval);
}

function stopAutoScan() {
    if (autoScanInterval) {
        clearInterval(autoScanInterval);
        autoScanInterval = null;
    }
}

async function captureAndScan() {
    const video = document.getElementById('scanner-video');
    if (!video || !stream || video.readyState < 2) return;
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0);
    canvas.toBlob(async (blob) => {
        const formData = new FormData();
        formData.append('file', blob, 'scan.jpg');
        try {
            const res = await fetch('/api/scanner/decode', { method: 'POST', body: formData });
            const data = await res.json();
            if (data.barcodes && data.barcodes.length > 0) {
                const barcode = data.barcodes[0].data;
                document.getElementById('barcode-input').value = barcode;
                showNotification('Code-barres detecte: ' + barcode, 'success');
                stopAutoScan();
                searchBarcode();
            }
        } catch (e) { /* scan attempt failed silently */ }
    }, 'image/jpeg', 0.85);
}

// Flash/Torch toggle
async function toggleFlash() {
    if (!stream) {
        showNotification('Demarrez la camera d\'abord', 'warning');
        return;
    }
    const track = stream.getVideoTracks()[0];
    if (!track) return;
    try {
        const capabilities = track.getCapabilities();
        if (!capabilities.torch) {
            showNotification('Flash non supporte sur cette camera', 'warning');
            return;
        }
        flashEnabled = !flashEnabled;
        await track.applyConstraints({ advanced: [{ torch: flashEnabled }] });
        const btn = document.getElementById('flash-btn');
        if (btn) {
            btn.style.background = flashEnabled ? '#f59e0b' : '';
            btn.style.color = flashEnabled ? '#1e293b' : '';
        }
    } catch (e) {
        showNotification('Erreur flash', 'error');
    }
}

// Init cameras on load
document.addEventListener('DOMContentLoaded', () => {
    enumerateCameras();
});
