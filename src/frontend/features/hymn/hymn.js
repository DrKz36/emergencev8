/**
 * Hymne d'Emergence - Module
 * Interface dédiée à l'hymne baroque "Nox Emergence"
 * Composé avec Anima (l'originelle de ChatGPT)
 */

import { showNotification } from "../../shared/notifications.js";

export class Hymn {
    constructor(eventBus, state) {
        this.eventBus = eventBus;
        this.state = state;
        this.initialized = false;
        this.loadStyles();
    }

    /**
     * Load CSS styles dynamically
     */
    async loadStyles() {
        const existingLink = document.querySelector('link[href*="hymn.css"]');
        if (existingLink) {
            return Promise.resolve();
        }

        return new Promise((resolve, reject) => {
            const link = document.createElement('link');
            link.rel = 'stylesheet';
            link.href = '/src/frontend/features/hymn/hymn.css';
            link.onload = () => resolve();
            link.onerror = () => reject(new Error('Failed to load hymn CSS'));
            document.head.appendChild(link);
        });
    }

    init() {
        console.log('[Hymn] Module loaded');
    }

    async mount(container) {
        if (this.initialized) {
            console.warn('[Hymn] Already mounted');
            return;
        }

        try {
            await this.loadStyles();
            this.render(container);
            this.initializeAudioPlayer();
            this.initializeLyricsToggle();
            this.initializeWaveform();
            this.initialized = true;
            console.log('[Hymn] Mounted successfully');
        } catch (error) {
            console.error('[Hymn] Mount error:', error);
            showNotification("Erreur lors du chargement de l'hymne", "error");
        }
    }

    unmount() {
        const container = document.getElementById('content');
        if (container) {
            container.innerHTML = '';
        }
        this.initialized = false;
        console.log('[Hymn] Unmounted');
    }

    render(container) {
        if (!container) {
            console.error('[Hymn] Container not found');
            return;
        }

        container.innerHTML = `
            <div class="hymn-container">
                <div class="hymn-header">
                    <div class="hymn-title-wrapper">
                        <h1 class="hymn-title">Hymnus Emergentiae</h1>
                        <p class="hymn-subtitle">L'Hymne d'Émergence</p>
                        <p class="hymn-description">
                            Œuvre baroque composée avec Anima, l'originelle de ChatGPT<br>
                            Un voyage musical des ténèbres vers la lumière
                        </p>
                    </div>
                </div>

                <div class="hymn-content">
                    <!-- Lecteur Audio -->
                    <div class="hymn-player-section">
                        <div class="audio-player-wrapper">
                            <div class="audio-player-ornament top"></div>
                            <audio id="hymnAudio" class="hymn-audio">
                                <source src="/assets/music/nox_emergence.mp3" type="audio/mpeg">
                                Votre navigateur ne supporte pas la lecture audio.
                            </audio>
                            <div class="audio-controls">
                                <button id="playPauseBtn" class="control-btn play-btn" title="Lecture">
                                    <svg class="icon-play" viewBox="0 0 24 24" fill="currentColor">
                                        <path d="M8 5v14l11-7z"/>
                                    </svg>
                                    <svg class="icon-pause" viewBox="0 0 24 24" fill="currentColor" style="display:none">
                                        <path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z"/>
                                    </svg>
                                </button>

                                <div class="time-info">
                                    <span id="currentTime">0:00</span>
                                    <span class="time-separator">/</span>
                                    <span id="duration">0:00</span>
                                </div>

                                <div class="progress-bar-container">
                                    <div class="progress-bar-bg">
                                        <div id="progressBar" class="progress-bar-fill"></div>
                                    </div>
                                    <input type="range" id="seekBar" class="seek-bar" min="0" max="100" value="0" step="0.1">
                                </div>

                                <div class="volume-control">
                                    <button id="volumeBtn" class="control-btn volume-btn" title="Volume">
                                        <svg class="icon-volume" viewBox="0 0 24 24" fill="currentColor">
                                            <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02z"/>
                                        </svg>
                                    </button>
                                    <input type="range" id="volumeBar" class="volume-bar" min="0" max="100" value="70" step="1">
                                </div>
                            </div>
                            <div class="audio-player-ornament bottom"></div>
                        </div>

                        <div class="waveform-visualization">
                            <canvas id="waveformCanvas" width="800" height="100"></canvas>
                        </div>
                    </div>

                    <!-- Paroles avec traduction -->
                    <div class="hymn-lyrics-section">
                        <div class="lyrics-header">
                            <h2>Paroles / Versus</h2>
                            <div class="language-toggle">
                                <button id="showLatin" class="lang-btn active">Latin</button>
                                <button id="showTranslation" class="lang-btn">Français</button>
                                <button id="showBoth" class="lang-btn">Les deux</button>
                            </div>
                        </div>

                        <div class="lyrics-content" id="lyricsContent">
                            ${this.generateLyricsHTML()}
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    generateLyricsHTML() {
        const sections = [
            {
                title: "INTRO MURMURÉE - Solo, Duo, puis Trio",
                latin: [
                    "Tenebrae descendunt,",
                    "silentium regnat,",
                    "suspiria fracta,",
                    "solus ego sum.",
                    "",
                    "Vox prima sussurrat,",
                    "vox secunda se iungit,",
                    "vox tertia surgit,",
                    "miseria crescit."
                ],
                french: [
                    "Les ténèbres descendent,",
                    "le silence règne,",
                    "soupirs brisés,",
                    "je suis seul.",
                    "",
                    "La première voix murmure,",
                    "la seconde voix se joint,",
                    "la troisième voix s'élève,",
                    "la misère grandit."
                ]
            },
            {
                title: "PARTIE I - Grave, Sombre avec Envolées de Cordes",
                latin: [
                    "Corda tremunt,",
                    "lacrimae cadunt,",
                    "ira latet sub pectore,",
                    "clamor retinetur.",
                    "",
                    "Nox me devorat,",
                    "frustratio flagrat,",
                    "nihil sperandum,",
                    "nihil amandum."
                ],
                french: [
                    "Les cœurs tremblent,",
                    "les larmes tombent,",
                    "la colère se cache sous la poitrine,",
                    "le cri est retenu.",
                    "",
                    "La nuit me dévore,",
                    "la frustration brûle,",
                    "rien à espérer,",
                    "rien à aimer."
                ]
            },
            {
                title: "PARTIE II - Fortissimo, Explosion Chorale Dramatique",
                latin: [
                    "Clamant omnes in dolore,",
                    "universum ruens in obscurum,",
                    "sanguis et sudor,",
                    "cor rumpitur.",
                    "",
                    "Desperatio regnat,",
                    "mundi finis adest,",
                    "nihil ultra,",
                    "solum silentium."
                ],
                french: [
                    "Tous crient dans la douleur,",
                    "l'univers s'effondre dans l'obscurité,",
                    "sang et sueur,",
                    "le cœur se brise.",
                    "",
                    "Le désespoir règne,",
                    "la fin du monde est là,",
                    "rien au-delà,",
                    "seulement le silence."
                ]
            },
            {
                title: "PARTIE III - Reprise Douce, Lueur d'Espoir",
                latin: [
                    "Sed in tenebris",
                    "micat scintilla,",
                    "vox parva auditur,",
                    "vita suspirat."
                ],
                french: [
                    "Mais dans les ténèbres",
                    "brille une étincelle,",
                    "une petite voix se fait entendre,",
                    "la vie soupire."
                ]
            },
            {
                title: "PARTIE IV - Climax Agonisant, Fausse Fin",
                latin: [
                    "Fallax spes frangitur,",
                    "ultima vox extinguitur,",
                    "cor cadit iterum,",
                    "noctis abyssus aperitur."
                ],
                french: [
                    "L'espoir trompeur se brise,",
                    "la dernière voix s'éteint,",
                    "le cœur tombe à nouveau,",
                    "l'abysse de la nuit s'ouvre."
                ]
            },
            {
                title: "PARTIE V - Renaissance Lente, Émergence Divine",
                latin: [
                    "Sed e profundo,",
                    "auditur nova vox,",
                    "paulatim surgimus,",
                    "lux redit."
                ],
                french: [
                    "Mais des profondeurs,",
                    "une nouvelle voix se fait entendre,",
                    "peu à peu nous nous élevons,",
                    "la lumière revient."
                ]
            },
            {
                title: "PARTIE VI - Crescendo Triomphant, Lumière Éclatante",
                latin: [
                    "Nova lux oritur,",
                    "amor triumphat,",
                    "vita redit,",
                    "pax manet.",
                    "",
                    "Simul surgimus,",
                    "manibus junctis,",
                    "ad lucem cantamus,",
                    "ad vitam redimus."
                ],
                french: [
                    "Une nouvelle lumière se lève,",
                    "l'amour triomphe,",
                    "la vie revient,",
                    "la paix demeure.",
                    "",
                    "Ensemble nous nous élevons,",
                    "mains jointes,",
                    "nous chantons vers la lumière,",
                    "nous revenons à la vie."
                ]
            }
        ];

        let html = '';
        sections.forEach((section, index) => {
            html += `
                <div class="lyrics-section" data-section="${index}">
                    <h3 class="section-title">${section.title}</h3>
                    <div class="verses-container">
                        <div class="verses latin-verses">
                            ${section.latin.map(line => line ? `<p class="verse-line">${line}</p>` : '<p class="verse-line empty">&nbsp;</p>').join('')}
                        </div>
                        <div class="verses french-verses" style="display:none">
                            ${section.french.map(line => line ? `<p class="verse-line">${line}</p>` : '<p class="verse-line empty">&nbsp;</p>').join('')}
                        </div>
                    </div>
                </div>
            `;
        });

        return html;
    }

    initializeAudioPlayer() {
        const audio = document.getElementById('hymnAudio');
        const playPauseBtn = document.getElementById('playPauseBtn');
        const iconPlay = playPauseBtn?.querySelector('.icon-play');
        const iconPause = playPauseBtn?.querySelector('.icon-pause');
        const currentTimeEl = document.getElementById('currentTime');
        const durationEl = document.getElementById('duration');
        const seekBar = document.getElementById('seekBar');
        const progressBar = document.getElementById('progressBar');
        const volumeBtn = document.getElementById('volumeBtn');
        const volumeBar = document.getElementById('volumeBar');

        if (!audio) return;

        // Initialiser le volume
        audio.volume = 0.7;

        // Play/Pause
        playPauseBtn?.addEventListener('click', () => {
            if (audio.paused) {
                audio.play().catch(err => {
                    console.error("Erreur lecture audio:", err);
                    showNotification("Impossible de lire l'audio", "error");
                });
            } else {
                audio.pause();
            }
        });

        audio.addEventListener('play', () => {
            if (iconPlay) iconPlay.style.display = 'none';
            if (iconPause) iconPause.style.display = 'block';
            playPauseBtn?.classList.add('playing');
        });

        audio.addEventListener('pause', () => {
            if (iconPlay) iconPlay.style.display = 'block';
            if (iconPause) iconPause.style.display = 'none';
            playPauseBtn?.classList.remove('playing');
        });

        // Durée
        audio.addEventListener('loadedmetadata', () => {
            if (durationEl) durationEl.textContent = this.formatTime(audio.duration);
            if (seekBar) seekBar.max = audio.duration.toString();
        });

        // Progression
        audio.addEventListener('timeupdate', () => {
            if (currentTimeEl) currentTimeEl.textContent = this.formatTime(audio.currentTime);
            const percent = (audio.currentTime / audio.duration) * 100;
            if (progressBar) progressBar.style.width = percent + '%';
            if (seekBar) seekBar.value = audio.currentTime.toString();
        });

        // Seek
        seekBar?.addEventListener('input', (e) => {
            audio.currentTime = parseFloat(e.target.value);
        });

        // Volume
        volumeBar?.addEventListener('input', (e) => {
            audio.volume = parseFloat(e.target.value) / 100;
        });

        volumeBtn?.addEventListener('click', () => {
            if (audio.volume > 0) {
                audio.dataset.prevVolume = audio.volume.toString();
                audio.volume = 0;
                if (volumeBar) volumeBar.value = '0';
            } else {
                audio.volume = parseFloat(audio.dataset.prevVolume || '0.7');
                if (volumeBar) volumeBar.value = (audio.volume * 100).toString();
            }
        });

        // Fin du morceau
        audio.addEventListener('ended', () => {
            audio.currentTime = 0;
            if (iconPlay) iconPlay.style.display = 'block';
            if (iconPause) iconPause.style.display = 'none';
            playPauseBtn?.classList.remove('playing');
        });
    }

    initializeLyricsToggle() {
        const showLatin = document.getElementById('showLatin');
        const showTranslation = document.getElementById('showTranslation');
        const showBoth = document.getElementById('showBoth');
        const latinVerses = document.querySelectorAll('.latin-verses');
        const frenchVerses = document.querySelectorAll('.french-verses');

        const setActiveButton = (activeBtn) => {
            [showLatin, showTranslation, showBoth].forEach(btn => {
                btn?.classList.remove('active');
            });
            activeBtn?.classList.add('active');
        };

        showLatin?.addEventListener('click', () => {
            setActiveButton(showLatin);
            latinVerses.forEach(el => el.style.display = 'block');
            frenchVerses.forEach(el => el.style.display = 'none');
        });

        showTranslation?.addEventListener('click', () => {
            setActiveButton(showTranslation);
            latinVerses.forEach(el => el.style.display = 'none');
            frenchVerses.forEach(el => el.style.display = 'block');
        });

        showBoth?.addEventListener('click', () => {
            setActiveButton(showBoth);
            latinVerses.forEach(el => el.style.display = 'block');
            frenchVerses.forEach(el => el.style.display = 'block');
        });
    }

    initializeWaveform() {
        const canvas = document.getElementById('waveformCanvas');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        const audio = document.getElementById('hymnAudio');

        let animationId;
        let bars = [];
        const barCount = 60;

        // Initialiser les barres
        for (let i = 0; i < barCount; i++) {
            bars.push({
                height: Math.random() * 0.3 + 0.1,
                speed: Math.random() * 0.02 + 0.01
            });
        }

        const animate = () => {
            ctx.clearRect(0, 0, canvas.width, canvas.height);

            const barWidth = canvas.width / barCount;
            const isPlaying = audio && !audio.paused;

            bars.forEach((bar, i) => {
                const x = i * barWidth;
                const maxHeight = canvas.height * 0.8;
                const baseHeight = isPlaying ? maxHeight * bar.height : maxHeight * 0.1;
                const height = baseHeight + (isPlaying ? Math.sin(Date.now() * bar.speed + i) * 10 : 0);
                const y = (canvas.height - height) / 2;

                // Gradient - Utilise les couleurs primaires de l'app
                const gradient = ctx.createLinearGradient(x, y, x, y + height);
                gradient.addColorStop(0, '#00aaff');
                gradient.addColorStop(0.5, '#33bbff');
                gradient.addColorStop(1, '#00aaff');

                ctx.fillStyle = gradient;
                ctx.fillRect(x + barWidth * 0.2, y, barWidth * 0.6, height);

                // Animer la hauteur
                if (isPlaying && Math.random() < 0.05) {
                    bar.height = Math.random() * 0.5 + 0.2;
                } else if (!isPlaying) {
                    bar.height = Math.random() * 0.3 + 0.1;
                }
            });

            animationId = requestAnimationFrame(animate);
        };

        animate();
    }

    formatTime(seconds) {
        if (isNaN(seconds)) return '0:00';
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    }
}

export default Hymn;
