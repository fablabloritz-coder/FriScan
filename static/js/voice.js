/**
 * FriScan — Module Reconnaissance Vocale
 * Utilise la Web Speech API du navigateur pour dicter les dates limites.
 * Fonctionne dans Chrome, Edge, Safari (pas Firefox).
 */

let recognition = null;
let isListening = false;

/**
 * Démarre la reconnaissance vocale pour remplir un champ date.
 * @param {string} targetInputId - ID du champ input[type=date] à remplir
 */
function startVoiceRecognition(targetInputId) {
    // Vérifier la compatibilité
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        notify('Reconnaissance vocale non supportée par votre navigateur. Utilisez Chrome ou Edge.', 'error');
        return;
    }

    if (isListening) {
        stopVoiceRecognition();
        return;
    }

    recognition = new SpeechRecognition();
    recognition.lang = 'fr-FR';
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.maxAlternatives = 3;

    const statusEl = targetInputId === 'result-expiry'
        ? document.getElementById('voice-status')
        : document.getElementById('voice-status-manual');

    const voiceBtn = event ? event.target.closest('.btn-voice') : null;

    // ══════ UI: mode écoute ══════
    statusEl.classList.remove('hidden');
    statusEl.className = 'voice-status listening';
    statusEl.textContent = '🎤 Écoute en cours... Dites la date (ex: "quinze mars deux mille vingt-six")';
    if (voiceBtn) voiceBtn.classList.add('listening');
    isListening = true;

    recognition.onresult = (event) => {
        let transcript = '';
        for (let i = event.resultIndex; i < event.results.length; i++) {
            transcript = event.results[i][0].transcript;
        }

        statusEl.textContent = `🎤 Entendu : "${transcript}"`;

        // Si le résultat est final, parser la date
        if (event.results[event.results.length - 1].isFinal) {
            const parsedDate = parseFrenchDate(transcript);

            if (parsedDate) {
                document.getElementById(targetInputId).value = parsedDate;
                statusEl.className = 'voice-status success';
                statusEl.textContent = `✅ Date reconnue : ${formatDateFR(parsedDate)}`;
                notify('Date enregistrée par la voix !', 'success');
            } else {
                statusEl.className = 'voice-status error';
                statusEl.textContent = `❌ Date non reconnue : "${transcript}". Réessayez.`;
                notify('Date non reconnue. Essayez à nouveau.', 'warning');
            }

            stopVoiceRecognition(voiceBtn);
        }
    };

    recognition.onerror = (event) => {
        console.error('Erreur vocale:', event.error);
        statusEl.className = 'voice-status error';

        if (event.error === 'no-speech') {
            statusEl.textContent = '❌ Aucune voix détectée. Réessayez.';
        } else if (event.error === 'not-allowed') {
            statusEl.textContent = '❌ Accès au microphone refusé. Vérifiez les permissions.';
        } else {
            statusEl.textContent = `❌ Erreur : ${event.error}`;
        }

        stopVoiceRecognition(voiceBtn);
    };

    recognition.onend = () => {
        isListening = false;
        if (voiceBtn) voiceBtn.classList.remove('listening');
    };

    recognition.start();
}

function stopVoiceRecognition(voiceBtn) {
    if (recognition) {
        recognition.stop();
        recognition = null;
    }
    isListening = false;
    if (voiceBtn) voiceBtn.classList.remove('listening');
}


// ════════════════════════ PARSING DATE FR ════════════════════════

/**
 * Parse une date dictée en français.
 * Exemples supportés :
 *   "quinze mars deux mille vingt-six"
 *   "15 mars 2026"
 *   "le 3 avril 2026"
 *   "03/04/2026"
 *   "3 avril"
 */
function parseFrenchDate(text) {
    if (!text) return null;
    let cleaned = text.toLowerCase().trim();
    cleaned = cleaned.replace(/^le\s+/, '');

    // ══════ Format numérique JJ/MM/AAAA ou JJ-MM-AAAA ══════
    const numMatch = cleaned.match(/(\d{1,2})\s*[\/\-\.]\s*(\d{1,2})\s*[\/\-\.]\s*(\d{2,4})/);
    if (numMatch) {
        let [, day, month, year] = numMatch;
        if (year.length === 2) year = '20' + year;
        return formatDateISO(parseInt(day), parseInt(month), parseInt(year));
    }

    // ══════ Convertir les mots en nombres ══════
    cleaned = wordsToNumbers(cleaned);

    // ══════ Format "JJ mois AAAA" ══════
    const months = {
        'janvier': 1, 'février': 2, 'fevrier': 2, 'mars': 3, 'avril': 4,
        'mai': 5, 'juin': 6, 'juillet': 7, 'août': 8, 'aout': 8,
        'septembre': 9, 'octobre': 10, 'novembre': 11, 'décembre': 12, 'decembre': 12,
    };

    const monthPattern = Object.keys(months).join('|');
    const dateRegex = new RegExp(`(\\d{1,2})\\s+(${monthPattern})\\s*(\\d{4})?`);
    const match = cleaned.match(dateRegex);

    if (match) {
        const day = parseInt(match[1]);
        const month = months[match[2]];
        let year = match[3] ? parseInt(match[3]) : new Date().getFullYear();
        return formatDateISO(day, month, year);
    }

    // ══════ Format mois seul "mars 2026" ══════
    const monthOnlyRegex = new RegExp(`(${monthPattern})\\s*(\\d{4})?`);
    const monthOnly = cleaned.match(monthOnlyRegex);
    if (monthOnly) {
        const month = months[monthOnly[1]];
        const year = monthOnly[2] ? parseInt(monthOnly[2]) : new Date().getFullYear();
        // Par défaut le dernier jour du mois
        const lastDay = new Date(year, month, 0).getDate();
        return formatDateISO(lastDay, month, year);
    }

    return null;
}

/**
 * Convertit les nombres en toutes lettres en chiffres.
 */
function wordsToNumbers(text) {
    const units = {
        'zéro': 0, 'zero': 0, 'un': 1, 'une': 1, 'premier': 1, 'première': 1,
        'deux': 2, 'trois': 3, 'quatre': 4, 'cinq': 5, 'six': 6,
        'sept': 7, 'huit': 8, 'neuf': 9, 'dix': 10, 'onze': 11,
        'douze': 12, 'treize': 13, 'quatorze': 14, 'quinze': 15,
        'seize': 16, 'dix-sept': 17, 'dix sept': 17, 'dix-huit': 18, 'dix huit': 18,
        'dix-neuf': 19, 'dix neuf': 19, 'vingt': 20, 'trente': 30, 'trente et un': 31,
    };

    // Remplacer "deux mille vingt-six" → 2026, etc.
    text = text.replace(/deux mille\s+(\w[\w\s-]*)/g, (match, rest) => {
        rest = rest.trim();
        let num = 2000;
        // Parser le reste
        const parts = rest.split(/[\s-]+/);
        for (const part of parts) {
            if (units[part] !== undefined) {
                num += units[part];
            }
        }
        return num.toString();
    });

    text = text.replace(/mille\s+(\w[\w\s-]*)/g, (match, rest) => {
        rest = rest.trim();
        let num = 1000;
        const parts = rest.split(/[\s-]+/);
        for (const part of parts) {
            if (units[part] !== undefined) {
                num += units[part];
            }
        }
        return num.toString();
    });

    // Remplacer les unités simples (pour les jours)
    // On traite les plus longs d'abord pour éviter les conflits
    const sortedUnits = Object.entries(units).sort((a, b) => b[0].length - a[0].length);
    for (const [word, num] of sortedUnits) {
        const regex = new RegExp(`\\b${word}\\b`, 'g');
        text = text.replace(regex, num.toString());
    }

    return text;
}

function formatDateISO(day, month, year) {
    if (day < 1 || day > 31 || month < 1 || month > 12 || year < 2020 || year > 2100) {
        return null;
    }
    const d = String(day).padStart(2, '0');
    const m = String(month).padStart(2, '0');
    return `${year}-${m}-${d}`;
}

function formatDateFR(isoDate) {
    const months = [
        'janvier', 'février', 'mars', 'avril', 'mai', 'juin',
        'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre',
    ];
    const [y, m, d] = isoDate.split('-').map(Number);
    return `${d} ${months[m - 1]} ${y}`;
}
