/**
 * FrigoScan — Module Dictée Vocale (voice.js)
 * Reconnaissance vocale pour les dates (DLC).
 * Supporte : "quatre février deux mille vingt-six", "4 2 2026", "04/02/2026", etc.
 */

(function () {
    const Voice = {};
    FrigoScan.Voice = Voice;

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    // Mapping texte → nombre
    const WORD_NUMBERS = {
        'zéro': 0, 'zero': 0,
        'un': 1, 'une': 1, 'premier': 1, 'première': 1,
        'deux': 2, 'deuxième': 2,
        'trois': 3, 'troisième': 3,
        'quatre': 4, 'quatrième': 4,
        'cinq': 5, 'cinquième': 5,
        'six': 6, 'sixième': 6,
        'sept': 7, 'septième': 7,
        'huit': 8, 'huitième': 8,
        'neuf': 9, 'neuvième': 9,
        'dix': 10, 'dixième': 10,
        'onze': 11, 'douze': 12, 'treize': 13, 'quatorze': 14, 'quinze': 15,
        'seize': 16, 'dix-sept': 17, 'dix sept': 17, 'dix-huit': 18, 'dix huit': 18,
        'dix-neuf': 19, 'dix neuf': 19,
        'vingt': 20, 'vingt et un': 21, 'vingt-et-un': 21,
        'vingt-deux': 22, 'vingt deux': 22, 'vingt-trois': 23, 'vingt trois': 23,
        'vingt-quatre': 24, 'vingt quatre': 24, 'vingt-cinq': 25, 'vingt cinq': 25,
        'vingt-six': 26, 'vingt six': 26, 'vingt-sept': 27, 'vingt sept': 27,
        'vingt-huit': 28, 'vingt huit': 28, 'vingt-neuf': 29, 'vingt neuf': 29,
        'trente': 30, 'trente et un': 31, 'trente-et-un': 31,
    };

    const MONTH_NAMES = {
        'janvier': 1, 'février': 2, 'fevrier': 2, 'mars': 3, 'avril': 4,
        'mai': 5, 'juin': 6, 'juillet': 7, 'août': 8, 'aout': 8,
        'septembre': 9, 'octobre': 10, 'novembre': 11, 'décembre': 12, 'decembre': 12,
    };

    // Convertit "deux mille vingt-six" → 2026, etc.
    function parseSpokenNumber(text) {
        text = text.trim().toLowerCase();

        // Si c'est déjà un nombre
        const direct = parseInt(text, 10);
        if (!isNaN(direct)) return direct;

        // Lookup direct
        if (WORD_NUMBERS[text] !== undefined) return WORD_NUMBERS[text];

        // "deux mille vingt-six" → 2000 + 26
        let total = 0;
        const parts = text.replace(/-/g, ' ').split(/\s+/);
        let i = 0;
        while (i < parts.length) {
            const word = parts[i];
            if (word === 'mille') {
                total = (total || 1) * 1000;
                i++;
            } else if (word === 'cent') {
                total = (total || 1) * 100;
                i++;
            } else if (word === 'et') {
                i++;
            } else {
                // Try two-word combos
                let found = false;
                if (i + 1 < parts.length) {
                    const twoWord = parts[i] + ' ' + parts[i + 1];
                    if (WORD_NUMBERS[twoWord] !== undefined) {
                        total += WORD_NUMBERS[twoWord];
                        i += 2;
                        found = true;
                    }
                }
                if (!found) {
                    if (WORD_NUMBERS[word] !== undefined) {
                        total += WORD_NUMBERS[word];
                    } else {
                        const num = parseInt(word, 10);
                        if (!isNaN(num)) total += num;
                    }
                    i++;
                }
            }
        }
        return total || NaN;
    }

    /**
     * Parse une date dictée en français → "YYYY-MM-DD"
     * Exemples : "quatre février deux mille vingt-six", "4 2 2026", "le 04/02/2026"
     */
    function parseSpokenDate(spoken) {
        let text = spoken.toLowerCase().trim()
            .replace(/le\s+/g, '')
            .replace(/[.,!?]/g, '')
            .replace(/\//g, ' ')
            .replace(/-/g, ' ');

        let day = null, month = null, year = null;

        // Chercher un nom de mois
        for (const [name, num] of Object.entries(MONTH_NAMES)) {
            if (text.includes(name)) {
                month = num;
                // Séparer autour du nom de mois
                const idx = text.indexOf(name);
                const before = text.substring(0, idx).trim();
                const after = text.substring(idx + name.length).trim();

                day = parseSpokenNumber(before);
                year = parseSpokenNumber(after);
                break;
            }
        }

        // Si pas de nom de mois, essayer format numérique "4 2 2026" ou "04 02 2026"
        if (month === null) {
            const nums = text.split(/\s+/).map(w => parseSpokenNumber(w)).filter(n => !isNaN(n));
            if (nums.length >= 3) {
                day = nums[0];
                month = nums[1];
                year = nums[2];
            } else if (nums.length === 2) {
                // Jour + mois, année courante
                day = nums[0];
                month = nums[1];
                year = new Date().getFullYear();
            }
        }

        if (!day || !month || isNaN(day) || isNaN(month)) return null;

        // Année : si < 100, ajouter 2000
        if (!year || isNaN(year)) year = new Date().getFullYear();
        if (year < 100) year += 2000;

        // Validation basique
        if (day < 1 || day > 31 || month < 1 || month > 12) return null;

        return `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
    }

    /**
     * Lance la reconnaissance vocale et remplit le champ DLC.
     * @param {string} inputId - L'id du champ date cible
     */
    Voice.listenDLC = function (inputId) {
        if (!SpeechRecognition) {
            FrigoScan.toast('Reconnaissance vocale non supportée par ce navigateur.', 'error');
            return;
        }

        const btn = event.currentTarget;
        const icon = btn.querySelector('i');

        // Si déjà en écoute, arrêter
        if (btn.dataset.listening === 'true') {
            btn._recognition?.abort();
            return;
        }

        const recognition = new SpeechRecognition();
        recognition.lang = 'fr-FR';
        recognition.interimResults = false;
        recognition.maxAlternatives = 3;
        recognition.continuous = false;
        btn._recognition = recognition;

        // UI
        btn.dataset.listening = 'true';
        icon.className = 'fas fa-circle-notch fa-spin';
        btn.classList.add('listening');
        FrigoScan.toast('🎤 Dictez la date (ex: "quatre février deux mille vingt-six")...', 'info');

        recognition.onresult = function (e) {
            let parsed = null;
            // Essayer chaque alternative
            for (let i = 0; i < e.results[0].length; i++) {
                const transcript = e.results[0][i].transcript;
                console.log('Voice transcript:', transcript);
                parsed = parseSpokenDate(transcript);
                if (parsed) break;
            }

            if (parsed) {
                document.getElementById(inputId).value = parsed;
                const dateObj = new Date(parsed);
                const display = dateObj.toLocaleDateString('fr-FR', { day: 'numeric', month: 'long', year: 'numeric' });
                FrigoScan.toast(`📅 DLC : ${display}`, 'success');
            } else {
                FrigoScan.toast('Impossible de comprendre la date. Réessayez en disant par exemple "quatre février deux mille vingt-six".', 'warning');
            }
        };

        recognition.onerror = function (e) {
            if (e.error === 'no-speech') {
                FrigoScan.toast('Aucune parole détectée. Réessayez.', 'warning');
            } else if (e.error === 'not-allowed') {
                FrigoScan.toast('Microphone non autorisé. Vérifiez les permissions du navigateur.', 'error');
            } else {
                FrigoScan.toast('Erreur de reconnaissance vocale : ' + e.error, 'error');
            }
        };

        recognition.onend = function () {
            btn.dataset.listening = 'false';
            icon.className = 'fas fa-microphone';
            btn.classList.remove('listening');
        };

        recognition.start();
    };

})();
