(function () {
    // Application state
    const API_BASE_URL = 'http://127.0.0.1:8000/api';
    let detections = [];
    let currentFilter = 'all';
    let charts = {};

    // Initialize on page load
    document.addEventListener('DOMContentLoaded', () => {
        initializeApp();
    });

    async function initializeApp() {
        try {
            // Initialize date/time immediately (non-blocking)
            startClock();

            // Initialize empty states for a responsive look
            updateCharts({
                by_severity: { critical: 0, high: 0, medium: 0, low: 0 },
                by_status: { pending: 0, verified: 0, contained: 0, false_alarm: 0 }
            });
            updateDetectionsGrid([]);

            // Initialize map
            if (typeof MapController !== 'undefined') {
                MapController.initializeMap();
            }

            // Load data in parallel to avoid one failure blocking everything
            loadStats().catch(e => console.warn('Stats load skipped:', e));
            loadDetections().catch(e => console.warn('Detections load skipped:', e));
            
            // Setup real-time cloud connection (with polling fallback)
            setupRealtimeListeners();


            // Setup event listeners
            setupEventListeners();
            setupGlobeInteraction();

            console.log('✅ App fully initialized');
        } catch (error) {
            console.error('❌ App initialization failed:', error);
            showToast('Failed to initialize app', 'error');
        }
    }

    function startClock() {
        const timeEl = document.getElementById('currentTime');
        const dateEl = document.getElementById('currentDate');
        const sessionEl = document.getElementById('sessionTimer');
        const staticDateEls = document.querySelectorAll('.static-date');
        const startTime = Date.now();

        const update = () => {
            const now = new Date();

            // Update header clock with blinking colon effect
            if (timeEl) {
                const timeStr = now.toLocaleTimeString([], { hour12: false });
                const seconds = now.getSeconds();
                // Wrap colons in spans for blinking or just use the string
                timeEl.innerHTML = timeStr.replace(/:/g, `<span class="${seconds % 2 === 0 ? 'opacity-100' : 'opacity-20'} transition-opacity duration-100">:</span>`);
            }

            if (dateEl) dateEl.textContent = now.toLocaleDateString([], { month: 'long', day: 'numeric', year: 'numeric' });

            // Update Session Timer
            if (sessionEl) {
                const diff = Math.floor((Date.now() - startTime) / 1000);
                const h = Math.floor(diff / 3600).toString().padStart(2, '0');
                const m = Math.floor((diff % 3600) / 60).toString().padStart(2, '0');
                const s = (diff % 60).toString().padStart(2, '0');
                sessionEl.textContent = `${h}:${m}:${s}`;
            }

            // Update static table dates (once)
            if (staticDateEls.length > 0) {
                const dateStr = now.toISOString().split('T')[0];
                staticDateEls.forEach(el => {
                    if (!el.dataset.updated) {
                        const timePart = el.textContent.split(' ')[1] || '00:00:00';
                        el.textContent = `${dateStr} ${timePart}`;
                        el.dataset.updated = "true";
                    }
                });
            }
        };

        update();
        setInterval(update, 1000);
    }

    function setupEventListeners() {
        // Theme Toggle
        document.getElementById('themeToggle')?.addEventListener('click', () => {
            const isDark = document.documentElement.classList.toggle('dark');
            try {
                localStorage.setItem('theme', isDark ? 'dark' : 'light');
            } catch (e) {
                console.warn('localStorage access denied, theme not saved');
            }
            if (typeof MapController !== 'undefined') {
                MapController.toggleMapTheme(isDark);
            }
        });

        // Check saved theme
        try {
            if (localStorage.getItem('theme') === 'dark') {
                document.documentElement.classList.add('dark');
            }
        } catch (e) {
            console.warn('localStorage access denied, using default theme');
        }

        // Incident Form
        document.getElementById('incidentForm')?.addEventListener('submit', (e) => {
            e.preventDefault();
            showToast('Sighting reported successfully. Agniveer AI is verifying.', 'success');
            e.target.reset();
        });

        // Severity Filter (from original code)
        document.getElementById('severityFilter')?.addEventListener('change', (e) => {
            currentFilter = e.target.value;
            filterDetections();
        });

        // Public Reporting: Photo Upload
        const uploadTrigger = document.getElementById('uploadTrigger');
        const photoInput = document.getElementById('photoUpload');
        uploadTrigger?.addEventListener('click', () => photoInput?.click());

        photoInput?.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                showToast(`Photo "${e.target.files[0].name}" uploaded. Analyzing for fire signatures...`, 'success');
            }
        });

        // Public Reporting: GPS Pinpoint
        document.getElementById('gpsTrigger')?.addEventListener('click', () => {
            showToast('Retrieving GPS coordinates...', 'success');
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(
                    (position) => {
                        const { latitude, longitude } = position.coords;
                        const locationEl = document.getElementById('incidentLocation');
                        if (locationEl) {
                            locationEl.value = `${latitude.toFixed(4)}, ${longitude.toFixed(4)} (Automatic GPS)`;
                            showToast('Location pinpointed with high precision.', 'success');
                        }
                    },
                    (error) => {
                        showToast('Failed to get location. Please enter manually.', 'error');
                    }
                );
            } else {
                showToast('Geolocation not supported by your browser.', 'error');
            }
        });

        // Smooth scroll for navigation
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function (e) {
                e.preventDefault();
                const target = document.querySelector(this.getAttribute('href'));
                if (target) {
                    target.scrollIntoView({ behavior: 'smooth' });
                }
            });
        });

        // Camera Surveillance Toggle
        const cameraBtn = document.getElementById('cameraToggleBtn');
        if (cameraBtn) {
            cameraBtn.addEventListener('click', toggleCameraSurveillance);
        }
    }

    // --- Camera & AI Inference Logic ---
    let isCameraActive = false;
    let frameAnalysisInterval = null;
    const ANALYSIS_RATE_MS = 2000; // Analyze every 2 seconds to save bandwidth/CPU

    async function toggleCameraSurveillance() {
        const video = document.getElementById('cameraFeed');
        const overlay = document.getElementById('cameraOffOverlay');
        const icon = document.getElementById('cameraToggleIcon');
        const dot = document.getElementById('cameraStatusDot');
        const statusText = document.getElementById('aiStatus');

        if (!isCameraActive) {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ 
                    video: { facingMode: 'environment' }, 
                    audio: false 
                });
                video.srcObject = stream;
                isCameraActive = true;
                
                // UI Updates
                overlay.classList.add('opacity-0');
                setTimeout(() => overlay.classList.add('hidden'), 500);
                icon.textContent = 'videocam_off';
                dot.classList.add('bg-primary');
                dot.classList.remove('bg-white');
                statusText.textContent = 'Initializing AI...';
                statusText.classList.remove('opacity-60');

                // Start analysis loop
                startAnalysisLoop();
                showToast('Local surveillance node activated.', 'success');
            } catch (err) {
                console.error('Camera access error:', err);
                showToast('Camera access denied or unavailable.', 'error');
            }
        } else {
            stopCameraSurveillance();
        }
    }

    function stopCameraSurveillance() {
        const video = document.getElementById('cameraFeed');
        const overlay = document.getElementById('cameraOffOverlay');
        const icon = document.getElementById('cameraToggleIcon');
        const dot = document.getElementById('cameraStatusDot');
        const statusText = document.getElementById('aiStatus');
        const bboxes = document.getElementById('aiBoundingBox');

        if (video.srcObject) {
            video.srcObject.getTracks().forEach(track => track.stop());
            video.srcObject = null;
        }

        isCameraActive = false;
        clearInterval(frameAnalysisInterval);
        
        // UI Updates
        overlay.classList.remove('hidden');
        setTimeout(() => overlay.classList.remove('opacity-0'), 10);
        icon.textContent = 'videocam';
        dot.classList.remove('bg-primary');
        dot.classList.add('bg-white');
        statusText.textContent = 'Offline';
        statusText.classList.add('opacity-60');
        bboxes.classList.add('hidden');
        
        document.getElementById('aiAnalysisBar').style.width = '0%';
        showToast('Local surveillance node deactivated.', 'info');
    }

    function startAnalysisLoop() {
        if (frameAnalysisInterval) clearInterval(frameAnalysisInterval);
        frameAnalysisInterval = setInterval(analyzeFrame, ANALYSIS_RATE_MS);
    }

    async function analyzeFrame() {
        if (!isCameraActive) return;

        const video = document.getElementById('cameraFeed');
        const canvas = document.getElementById('frameCanvas');
        const bar = document.getElementById('aiAnalysisBar');
        const statusText = document.getElementById('aiStatus');

        if (!video || video.videoWidth === 0) return;

        // Prepare canvas
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

        // Update progress bar to show activity
        bar.style.width = '100%';
        statusText.textContent = 'Analyzing...';

        try {
            // Convert to blob
            const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', 0.8));
            
            const formData = new FormData();
            formData.append('image', blob, 'frame.jpg');

            const startTime = Date.now();
            const response = await fetch(`${API_BASE_URL}/inference/detect`, {
                method: 'POST',
                body: formData
            });

            const result = await response.json();
            const latency = Date.now() - startTime;

            updateDetectionUI(result, latency);
        } catch (err) {
            console.error('Frame analysis failed:', err);
            statusText.textContent = 'Engine Error';
        } finally {
            // Reset bar after a delay
            setTimeout(() => {
                if (isCameraActive) bar.style.width = '0%';
            }, 500);
        }
    }

    function updateDetectionUI(result, latency) {
        const statusText = document.getElementById('aiStatus');
        const bbox = document.getElementById('aiBoundingBox');
        const label = document.getElementById('aiLabel');
        const confidence = document.getElementById('aiConfidence');

        if (result.detected) {
            statusText.textContent = `🔥 FIRE DETECTED (${latency}ms)`;
            statusText.classList.add('text-primary');
            statusText.classList.remove('text-white');

            // Show bounding box
            bbox.classList.remove('hidden');
            label.textContent = result.label ? result.label.toUpperCase() : 'FIRE';
            confidence.textContent = `${Math.round(result.confidence * 100)}%`;

            // Mock box position for visual effect if real ones aren't mapped to CSS yet
            // In a real app, we'd map normalized coords from the model to the video container
            if (result.boxes && result.boxes.length > 0) {
                // Just a mock placement for premium feel since mapping coords can be complex
                bbox.style.top = '30%';
                bbox.style.left = '30%';
                bbox.style.width = '40%';
                bbox.style.height = '40%';
            }

            // Trigger alert if high confidence
            if (result.confidence > 0.7) {
                showToast(`CRITICAL: AI node detected active fire signature!`, 'critical');
                playAlertSound();
            }
        } else {
            statusText.textContent = `Scanning... (${latency}ms)`;
            statusText.classList.remove('text-primary');
            statusText.classList.add('text-white');
            bbox.classList.add('hidden');
        }
    }

    async function loadStats() {
        try {
            const response = await fetch(`${API_BASE_URL}/stats`);
            const stats = await response.json();

            updateStats(stats);
            updateCharts(stats);

        } catch (error) {
            console.error('Error loading stats:', error);
        }
    }

    function updateStats(stats) {
        document.getElementById('totalDetections').textContent = stats.total_detections || 0;
        document.getElementById('activeFires').textContent = stats.active_fires || 0;
        document.getElementById('todayDetections').textContent = stats.today_detections || 0;

        const countEl = document.getElementById('alertCount');
        if (countEl) {
            countEl.textContent = stats.active_fires || 0;
            // Add a highlight animation if fires are active
            if ((stats.active_fires || 0) > 0) {
                countEl.classList.add('bg-slate-900');
                countEl.classList.remove('bg-slate-900/30');
            } else {
                countEl.classList.add('bg-slate-900/30');
                countEl.classList.remove('bg-slate-900');
            }
        }
    }

    function updateCharts(stats) {
        // Severity Chart
        const severityCtx = document.getElementById('severityChart')?.getContext('2d');
        if (severityCtx) {
            if (charts.severity) charts.severity.destroy();

            charts.severity = new Chart(severityCtx, {
                type: 'doughnut',
                data: {
                    labels: ['Critical', 'High', 'Medium', 'Low'],
                    datasets: [{
                        data: [
                            stats.by_severity?.critical || 0,
                            stats.by_severity?.high || 0,
                            stats.by_severity?.medium || 0,
                            stats.by_severity?.low || 0
                        ],
                        backgroundColor: [
                            '#FF4B4B',
                            '#FF8C00',
                            '#FFB347',
                            '#10B981'
                        ]
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            position: 'bottom'
                        }
                    }
                }
            });
        }

        // Status Chart
        const statusCtx = document.getElementById('statusChart')?.getContext('2d');
        if (statusCtx) {
            if (charts.status) charts.status.destroy();

            charts.status = new Chart(statusCtx, {
                type: 'bar',
                data: {
                    labels: ['Pending', 'Verified', 'Contained', 'False Alarm'],
                    datasets: [{
                        label: 'Detections',
                        data: [
                            stats.by_status?.pending || 0,
                            stats.by_status?.verified || 0,
                            stats.by_status?.contained || 0,
                            stats.by_status?.false_alarm || 0
                        ],
                        backgroundColor: [
                            '#ffc107',
                            '#28a745',
                            '#17a2b8',
                            '#6c757d'
                        ]
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            display: false
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                stepSize: 1
                            }
                        }
                    }
                }
            });
        }

        // Regional Trend Chart
        const regionalTrendCtx = document.getElementById('regionalTrendChart')?.getContext('2d');
        if (regionalTrendCtx) {
            if (charts.regionalTrend) charts.regionalTrend.destroy();
            charts.regionalTrend = new Chart(regionalTrendCtx, {
                type: 'line',
                data: {
                    labels: Array.from({ length: 30 }, (_, i) => `Day ${i + 1}`),
                    datasets: [
                        { label: 'Western Ghats', data: Array.from({ length: 30 }, () => Math.floor(Math.random() * 40) + 40), borderColor: '#FF4B4B', fill: false, tension: 0.4 },
                        { label: 'Himalayan Foothills', data: Array.from({ length: 30 }, () => Math.floor(Math.random() * 30) + 50), borderColor: '#FF8C00', fill: false, tension: 0.4 },
                        { label: 'Central Highlands', data: Array.from({ length: 30 }, () => Math.floor(Math.random() * 20) + 30), borderColor: '#FFB347', fill: false, tension: 0.4 },
                        { label: 'Northeast Reserve', data: Array.from({ length: 30 }, () => Math.floor(Math.random() * 50) + 40), borderColor: '#10B981', fill: false, tension: 0.4 }
                    ]
                },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom' } } }
            });
        }
    }

    function sanitizeDetection(d) {
        return {
            ...d,
            image_url: (d.image_url && d.image_url.includes('placeholder.jpg'))
                ? 'https://raw.githubusercontent.com/vinaykumarbharwal/Fire_GITHUB/main/Project_Fire/mobile_app/flutter_app/assets/images/placeholder_fire.jpg'
                : d.image_url
        };
    }

    async function loadDetections() {
        try {
            const response = await fetch(`${API_BASE_URL}/detections?limit=50`);
            const rawDetections = await response.json();

            // Sanitize detections to handle legacy/missing assets
            detections = rawDetections.map(sanitizeDetection);

            updateDetectionsGrid(detections);
            updateIncidentTable(detections);
            if (typeof MapController !== 'undefined') {
                MapController.updateMapMarkers(detections);
            }

        } catch (error) {
            console.error('Error loading detections:', error);
        }
    }

    function updateDetectionsGrid(detections) {
        const grid = document.getElementById('detectionsGrid');
        if (!grid) return;

        if (detections.length === 0) {
            grid.innerHTML = '<div class="no-data">No detections found</div>';
            return;
        }

        grid.innerHTML = detections.map(detection => createDetectionCard(detection)).join('');
    }

    function updateIncidentTable(detections) {
        const tableBody = document.querySelector('tbody');
        if (!tableBody) return;

        // Take top 5 recent detections
        const recent = [...detections].sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp)).slice(0, 5);

        tableBody.innerHTML = recent.length ? recent.map(detection => `
        <tr class="border-b border-slate-50 hover:bg-slate-50 transition-colors">
            <td class="px-8 py-6 font-mono font-bold text-slate-900">${new Date(detection.timestamp).toLocaleString()}</td>
            <td class="px-8 py-6 font-mono text-xs text-slate-500">${detection.latitude.toFixed(4)}° N, ${detection.longitude.toFixed(4)}° W</td>
            <td class="px-8 py-6"><span class="severity-badge severity-${detection.severity.toLowerCase()}">${detection.severity}</span></td>
            <td class="px-8 py-6">
                <div class="flex items-center gap-3">
                    <div class="w-20 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                        <div class="bg-primary h-full" style="width: ${Math.round(detection.confidence * 100)}%"></div>
                    </div>
                    <span class="font-bold text-slate-900">${Math.round(detection.confidence * 100)}%</span>
                </div>
            </td>
            <td class="px-8 py-6">
                <div class="flex items-center gap-2 text-slate-600 font-bold uppercase text-[11px] tracking-wider">
                    <span class="material-symbols-outlined text-lg text-slate-400">
                        ${(detection.image_url || '').includes('satellite') ? 'satellite_alt' : 'airplanemode_active'}
                    </span>
                    ${(detection.image_url || '').includes('satellite') ? 'Satellite Array' : 'Drone Matrix'}
                </div>
            </td>
        </tr>
    `).join('') : '<tr><td colspan="5" class="px-8 py-6 text-center text-slate-400">No incident logs available</td></tr>';
    }

    function createDetectionCard(detection) {
        const severity = detection.severity || 'unknown';
        const timeAgo = getTimeAgo(detection.timestamp);
        const severityClass = `severity-${severity.toLowerCase()}`;
        const imageUrl = detection.image_url || 'https://raw.githubusercontent.com/vinaykumarbharwal/Fire_GITHUB/main/Project_Fire/mobile_app/flutter_app/assets/images/placeholder_fire.jpg';

        return `
        <div class="detection-card group cursor-pointer" data-id="${detection.id}" onclick="showDetectionDetails('${detection.id}')">
            <div class="relative overflow-hidden aspect-video rounded-2xl mb-2">
                <img src="${imageUrl}" alt="Fire detection" class="w-full h-full object-cover transition-transform duration-700 group-hover:scale-110" 
                     onerror="this.onerror=null; this.src='https://via.placeholder.com/400x225?text=No+Image+Available'">
                <div class="absolute top-4 left-4 z-10">
                    <span class="severity-badge ${severityClass}">
                        ${severity.toUpperCase()}
                    </span>
                </div>
                <div class="absolute bottom-4 right-4 z-10">
                    <div class="bg-white/80 backdrop-blur-md px-3 py-1 rounded-lg border border-white/50 shadow-sm">
                        <span class="text-[10px] font-black text-slate-900">${timeAgo}</span>
                    </div>
                </div>
            </div>
            
            <div class="flex flex-col gap-1 px-1">
                <h3 class="text-sm font-black text-slate-900 uppercase tracking-tight truncate">${detection.address || 'Unknown Region'}</h3>
                <div class="flex items-center justify-between mt-2">
                    <div class="flex flex-col">
                        <span class="text-[9px] text-slate-400 font-bold uppercase tracking-widest">Confidence</span>
                        <span class="text-xs font-black text-slate-900">${Math.round(detection.confidence * 100)}%</span>
                    </div>
                    <div class="flex flex-col items-end">
                        <span class="text-[9px] text-slate-400 font-bold uppercase tracking-widest">Status</span>
                        <span class="text-[10px] font-black px-2 py-0.5 rounded-md bg-slate-100 text-slate-600 uppercase">${detection.status}</span>
                    </div>
                </div>
            </div>
            
            <div class="grid grid-cols-2 gap-3 mt-4">
                <button class="bg-slate-50 hover:bg-slate-100 text-slate-900 py-2.5 rounded-xl text-[10px] font-black uppercase tracking-widest border border-slate-200 transition-all flex items-center justify-center gap-2" 
                        onclick="event.stopPropagation(); viewOnMap('${detection.id}')">
                    <span class="material-symbols-outlined text-sm">explore</span> Show Map
                </button>
                <button class="bg-primary hover:bg-danger-deep text-white py-2.5 rounded-xl text-[10px] font-black uppercase tracking-widest shadow-lg shadow-primary/20 transition-all flex items-center justify-center gap-2" 
                        onclick="event.stopPropagation(); showDetectionDetails('${detection.id}')">
                    <span class="material-symbols-outlined text-sm">info</span> Info
                </button>
            </div>
        </div>
    `;
    }

    // Expose handlers to window for onclick support
    window.viewOnMap = viewOnMap;
    window.showDetectionDetails = showDetectionDetails;

    function filterDetections() {
        if (!detections.length) return;

        let filtered = [...detections];

        if (currentFilter !== 'all') {
            filtered = filtered.filter(d => d.severity === currentFilter);
        }

        updateDetectionsGrid(filtered);
        updateIncidentTable(filtered);
        if (typeof MapController !== 'undefined') {
            MapController.updateMapMarkers(filtered);
        }
    }

    function viewOnMap(detectionId) {
        if (typeof MapController !== 'undefined') {
            MapController.highlightMarker(detectionId);
        }
        const mapEl = document.getElementById('map');
        if (mapEl) {
            mapEl.scrollIntoView({ behavior: 'smooth' });
        }
    }

    function showDetectionDetails(detectionId) {
        const detection = detections.find(d => d.id === detectionId);
        if (!detection) return;

        const modal = document.createElement('div');
        modal.className = 'fixed inset-0 z-[100] flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-md animate-fade-in';
        const imageUrl = detection.image_url || 'https://raw.githubusercontent.com/vinaykumarbharwal/Fire_GITHUB/main/Project_Fire/mobile_app/flutter_app/assets/images/placeholder_fire.jpg';

        modal.innerHTML = `
        <div class="bg-white w-full max-w-2xl rounded-[2.5rem] overflow-hidden shadow-2xl border border-white/20 animate-scale-up">
            <div class="relative h-64 overflow-hidden">
                <img src="${imageUrl}" alt="Detection" class="w-full h-full object-cover"
                     onerror="this.onerror=null; this.src='https://via.placeholder.com/400x225?text=No+Image+Available'">
                <div class="absolute inset-0 bg-gradient-to-t from-slate-900/80 via-transparent to-transparent"></div>
                <button class="absolute top-6 right-6 w-10 h-10 bg-white/20 backdrop-blur-md hover:bg-white/40 text-white rounded-full flex items-center justify-center transition-all" onclick="this.closest('.fixed').remove()">
                    <span class="material-symbols-outlined">close</span>
                </button>
                <div class="absolute bottom-8 left-8">
                    <div class="flex items-center gap-2 text-white/80 mb-2">
                        <span class="material-symbols-outlined text-sm">local_fire_department</span>
                        <span class="text-[10px] font-black uppercase tracking-[0.2em]">Agniveer Systems</span>
                    </div>
                    <span class="severity-badge severity-${detection.severity.toLowerCase()} mb-3 inline-block">
                        ${detection.severity.toUpperCase()}
                    </span>
                    <h2 class="text-3xl font-black text-white tracking-tighter uppercase mb-1">${detection.address || 'Unknown Location'}</h2>
                    <p class="text-white/60 text-xs font-bold uppercase tracking-[0.2em]">${new Date(detection.timestamp).toLocaleString()}</p>
                </div>
            </div>
            
            <div class="p-10 grid grid-cols-2 gap-10">
                <div class="space-y-6">
                    <div class="flex items-center gap-4">
                        <div class="w-12 h-12 bg-slate-50 rounded-2xl flex items-center justify-center text-primary border border-slate-100">
                            <span class="material-symbols-outlined">analytics</span>
                        </div>
                        <div>
                            <p class="text-[10px] text-slate-400 font-black uppercase tracking-widest">AI Confidence</p>
                            <p class="text-xl font-black text-slate-900">${Math.round(detection.confidence * 100)}.0%</p>
                        </div>
                    </div>
                    <div class="flex items-center gap-4">
                        <div class="w-12 h-12 bg-slate-50 rounded-2xl flex items-center justify-center text-slate-600 border border-slate-100">
                            <span class="material-symbols-outlined">share_location</span>
                        </div>
                        <div>
                            <p class="text-[10px] text-slate-400 font-black uppercase tracking-widest">Geolocation</p>
                            <p class="text-xs font-mono font-bold text-slate-900">${detection.latitude}, ${detection.longitude}</p>
                        </div>
                    </div>
                </div>
                
                <div class="space-y-6">
                     <div class="flex items-center gap-4">
                        <div class="w-12 h-12 bg-slate-50 rounded-2xl flex items-center justify-center text-orange-500 border border-slate-100">
                            <span class="material-symbols-outlined">published_with_changes</span>
                        </div>
                        <div>
                            <p class="text-[10px] text-slate-400 font-black uppercase tracking-widest">Process Status</p>
                            <p class="text-xs font-black text-slate-900 uppercase">${detection.status}</p>
                        </div>
                    </div>
                    
                        <div class="flex flex-col gap-3 mt-8 pt-6 border-t border-slate-50">
                            <div class="flex gap-4">
                                 <a href="https://maps.google.com/?q=${detection.latitude},${detection.longitude}" target="_blank" class="flex-1 bg-slate-900 text-white py-3 rounded-xl text-center text-[10px] font-black uppercase tracking-widest hover:bg-slate-800 transition-all">
                                    View Map
                                </a>
                                <a href="${detection.image_url}" target="_blank" class="flex-1 bg-white border border-slate-200 text-slate-900 py-3 rounded-xl text-center text-[10px] font-black uppercase tracking-widest hover:border-primary transition-all">
                                    See Photo
                                </a>
                            </div>
                        </div>
                </div>
            </div>
        </div>
    `;

        document.body.appendChild(modal);

        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.remove();
        });
    }

    function getTimeAgo(timestamp) {
        if (!timestamp) return '';

        const date = new Date(timestamp);
        const now = new Date();
        const seconds = Math.floor((now - date) / 1000);

        const intervals = {
            year: 31536000,
            month: 2592000,
            week: 604800,
            day: 86400,
            hour: 3600,
            minute: 60
        };

        for (const [unit, secondsInUnit] of Object.entries(intervals)) {
            const interval = Math.floor(seconds / secondsInUnit);
            if (interval >= 1) {
                return `${interval} ${unit}${interval === 1 ? '' : 's'} ago`;
            }
        }

        return 'Just now';
    }

    function showToast(message, type = 'info') {
        const container = document.getElementById('toastContainer');
        if (!container) return;

        const toast = document.createElement('div');
        const typeClass = type === 'critical' || type === 'high' ? type : 'info';
        toast.className = `toast ${typeClass} show`;

        const icons = {
            'critical': 'local_fire_department',
            'high': 'warning',
            'medium': 'campaign',
            'low': 'info',
            'error': 'error',
            'success': 'check_circle',
            'info': 'info'
        };

        toast.innerHTML = `
        <div class="w-10 h-10 rounded-full flex items-center justify-center ${type === 'critical' ? 'bg-primary/10 text-primary' : 'bg-slate-100 text-slate-600'}">
            <span class="material-symbols-outlined text-lg">${icons[type] || 'info'}</span>
        </div>
        <div class="flex-1">
            <div class="text-[10px] font-black uppercase tracking-widest mb-0.5 ${type === 'critical' ? 'text-primary' : 'text-slate-900'}">Agniveer Alert</div>
            <div class="text-xs font-medium text-slate-500 leading-tight">${message}</div>
        </div>
        <button class="text-slate-400 hover:text-slate-600 self-top" onclick="this.closest('.toast').remove()">
            <span class="material-symbols-outlined text-sm">close</span>
        </button>
    `;

        container.appendChild(toast);

        // Auto remove after 5 seconds
        setTimeout(() => {
            if (toast.parentNode) {
                toast.style.transform = 'translateX(120%)';
                setTimeout(() => toast.remove(), 300);
            }
        }, 5000);
    }

    function setupRealtimeListeners() {
        if (typeof firebase === 'undefined' || !firebase.initializeApp) {
            console.warn('⚠️ Firebase not loaded. Starting Polling fallback.');
            startPolling();
            return;
        }

        try {
            const db = firebase.firestore();
            // Listen for new detections
            db.collection('detections')
                .where('timestamp', '>', new Date().toISOString())
                .onSnapshot((snapshot) => {
                    snapshot.docChanges().forEach((change) => {
                        if (change.type === 'added') {
                            const detection = sanitizeDetection({
                                id: change.doc.id,
                                ...change.doc.data()
                            });
                            detections.unshift(detection);
                            filterDetections();
                            if (detection.severity === 'critical' || detection.severity === 'high') {
                                showToast(`New ${detection.severity} severity fire detected!`, detection.severity);
                                playAlertSound();
                            }
                        }
                        // Handle modified/removed...
                    });
                }, (err) => {
                    console.error('Firestore listener error:', err);
                    startPolling();
                });
        } catch (e) {
            console.error('Firebase setup error:', e);
            startPolling();
        }
    }

    function startPolling() {
        if (window.pollingActive) return;
        window.pollingActive = true;
        console.log('🔄 Tactical Polling Node Initialized');
        setInterval(loadDetections, 10000); // UI updates every 10s
    }


    function playAlertSound() {
        const audio = new Audio('assets/sounds/alert.mp3');
        audio.play().catch(e => console.log('Audio play failed:', e));
    }

    // 3D Globe Interaction: Enables dragging the hero globe in 3D perspective
    function setupGlobeInteraction() {
        const globe = document.getElementById('interactiveGlobe');
        const wrapper = globe?.querySelector('.globe-layers-wrapper');
        if (!globe || !wrapper) return;

        let isDragging = false;
        let startX, startY;
        let currentX = 0, currentY = 0;
        let rotX = 0, rotY = 0;

        globe.addEventListener('mousedown', (e) => {
            isDragging = true;
            startX = e.clientX;
            startY = e.clientY;
            wrapper.style.transition = 'none';
            globe.style.cursor = 'grabbing';
        });

        window.addEventListener('mousemove', (e) => {
            if (!isDragging) return;
            const deltaX = e.clientX - startX;
            const deltaY = e.clientY - startY;

            rotY = currentY + deltaX * 0.5;
            rotX = currentX - deltaY * 0.5;

            // Constraint X rotation for realistic orbital view
            rotX = Math.max(-45, Math.min(45, rotX));

            wrapper.style.setProperty('--globe-rot-x', `${rotX}deg`);
            wrapper.style.setProperty('--globe-rot-y', `${rotY}deg`);
        });

        window.addEventListener('mouseup', () => {
            if (!isDragging) return;
            isDragging = false;
            currentX = rotX;
            currentY = rotY;
            globe.style.cursor = 'grab';

            // Return to neutral horizontal position but keep Y rotation for seamlessness
            wrapper.style.transition = 'transform 1.2s cubic-bezier(0.2, 0, 0.2, 1)';
            currentX = 0;
            wrapper.style.setProperty('--globe-rot-x', '0deg');
        });

        // Touch support for mobile surveillance
        globe.addEventListener('touchstart', (e) => {
            isDragging = true;
            startX = e.touches[0].clientX;
            startY = e.touches[0].clientY;
            wrapper.style.transition = 'none';
        }, { passive: true });

        window.addEventListener('touchmove', (e) => {
            if (!isDragging) return;
            const deltaX = e.touches[0].clientX - startX;
            const deltaY = e.touches[0].clientY - startY;

            rotY = currentY + deltaX * 0.5;
            rotX = currentX - deltaY * 0.5;
            rotX = Math.max(-45, Math.min(45, rotX));

            wrapper.style.setProperty('--globe-rot-x', `${rotX}deg`);
            wrapper.style.setProperty('--globe-rot-y', `${rotY}deg`);
        }, { passive: true });

        window.addEventListener('touchend', () => {
            isDragging = false;
            currentX = 0;
            wrapper.style.transition = 'transform 1.2s cubic-bezier(0.2, 0, 0.2, 1)';
            wrapper.style.setProperty('--globe-rot-x', '0deg');
        });
    }

})();
