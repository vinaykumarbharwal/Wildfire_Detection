(function () {
    let detections = [];
    let isRealtime = false;
    const API_BASE_URL = 'http://127.0.0.1:8000/api';

    // Initialize on page load
    document.addEventListener('DOMContentLoaded', async () => {
        startClock();
        try {
            const success = await initializeFirebase();
            if (success && typeof firebase !== 'undefined' && firebase.apps.length > 0) {
                console.log('📡 Real-time Cloud Intelligence Active');
                isRealtime = true;
                setupAdminListeners();
            } else {
                throw new Error('Firebase skipped');
            }
        } catch (e) {
            console.warn('⚠️ Cloud Sync unavailable. Reverting to Tactical API Polling.');
            showToast('Cloud sync unavailable. Using direct API polling.', 'info');
            startPolling();
        }
    });

    function startClock() {
        const timeEl = document.getElementById('currentTime');
        if (!timeEl) return;
        setInterval(() => {
            timeEl.textContent = new Date().toLocaleTimeString([], { hour12: false });
        }, 1000);
    }

    function startPolling() {
        fetchData();
        setInterval(fetchData, 5000); // Poll every 5 seconds
    }

    async function fetchData() {
        try {
            const response = await fetch(`${API_BASE_URL}/detections/?limit=100`);
            const data = await response.json();
            detections = data;
            renderTable();
            updateStats();
        } catch (error) {
            console.error('Polling error:', error);
        }
    }

    function setupAdminListeners() {
        const db = firebase.firestore();
        
        // Listen for ALL detections
        db.collection('detections')
            .orderBy('timestamp', 'desc')
            .onSnapshot((snapshot) => {
                detections = snapshot.docs.map(doc => ({
                    id: doc.id,
                    ...doc.data()
                }));
                
                renderTable();
                updateStats();
            }, (error) => {
                console.error('Snapshot error (permissions/indexes?):', error);
                showToast('Cloud sync error. Falling back to Polling.', 'error');
                isRealtime = false;
                startPolling();
            });
    }

    function updateStats() {
        const activeCount = detections.filter(d => d.status === 'pending').length;
        const totalCount = detections.length;
        
        const activeEl = document.getElementById('stats-active');
        const totalEl = document.getElementById('stats-total');
        
        if (activeEl) activeEl.textContent = activeCount;
        if (totalEl) totalEl.textContent = totalCount;
    }

    function renderTable() {
        const tableBody = document.getElementById('adminIncidentTable');
        if (!tableBody) return;

        if (detections.length === 0) {
            tableBody.innerHTML = `<tr><td colspan="5" class="px-10 py-20 text-center text-slate-500 font-bold uppercase tracking-widest">No Active Incidents Found in Grid</td></tr>`;
            return;
        }

        tableBody.innerHTML = detections.map(d => {
            const date = d.timestamp ? new Date(d.timestamp).toLocaleString() : 'N/A';
            const confidence = Math.round((d.confidence || 0) * 100);

            return `
                <tr class="data-table-row border-b border-white/5 hover:bg-white/5 transition-colors">
                    <td class="px-10 py-6">
                        <div class="flex flex-col">
                            <span class="text-xs font-black text-white uppercase tracking-tighter">${d.address || 'Mobile Surveillance Node'}</span>
                            <span class="text-[9px] font-mono font-bold text-slate-500 uppercase mt-1">${d.id}</span>
                        </div>
                    </td>
                    <td class="px-10 py-6">
                        <div class="flex items-center gap-3">
                            <div class="w-16 h-1.5 bg-white/5 rounded-full overflow-hidden">
                                <div class="h-full bg-primary" style="width: ${confidence}%"></div>
                            </div>
                            <span class="text-xs font-mono font-black text-white">${confidence}%</span>
                        </div>
                    </td>
                    <td class="px-10 py-6 text-[10px] font-bold text-slate-400 font-mono">${date}</td>
                    <td class="px-10 py-6">
                         <span class="px-3 py-1 rounded-lg bg-white/5 border border-white/10 text-[9px] font-black uppercase text-slate-400 tracking-widest">${d.status}</span>
                    </td>
                    <td class="px-10 py-6">
                        <button onclick="resolveIncident('${d.id}')" class="bg-primary/10 hover:bg-primary text-primary hover:text-white px-4 py-2 rounded-lg text-[9px] font-black uppercase tracking-widest border border-primary/20 transition-all flex items-center gap-2">
                             <span class="material-symbols-outlined text-xs">check_circle</span> Resolve
                        </button>
                    </td>
                </tr>
            `;
        }).join('');
    }

    window.resolveIncident = async function(id) {
        if (!confirm('Permanently resolve and archive this incident?')) return;
        
        try {
            console.log(`📡 Sending Resolution Signal for: ${id}`);
            // Priority 1: Backend API (Central Truth)
            const response = await fetch(`${API_BASE_URL}/detections/${id}`, {
                method: 'DELETE'
            });

            if (response.ok || response.status === 404) {
                if (response.status === 404) console.warn('⚠️ Incident record missing from Backend. Finalizing Cloud Purge...');
                
                // Priority 2: Firebase (Real-time Broadcast)
                if (isRealtime) {
                    const db = firebase.firestore();
                    await db.collection('detections').doc(id).delete();
                }
                
                showToast('Resolution protocol complete.', 'success');
                if (!isRealtime) fetchData();
            } else {
                const errorData = await response.json().catch(() => ({}));
                console.error('API Protocol Rejection:', response.status, errorData);
                throw new Error(errorData.detail || 'API protocol rejection');
            }
        } catch (error) {
            console.error('Command Execution Error:', error);
            showToast(`Protocol Error: ${error.message}`, 'error');
        }
    };

    window.purgeAllDetections = async function() {
        if (!confirm('CRITICAL ACTION: Reset global map and purge all incident history?')) return;
        
        showToast('Initiating Global Purge...', 'critical');
        try {
            // This is a mock: In real scenario, backend would have a /purge endpoint
            // For now, we resolve visible ones or require manual DB wipe
            showToast('Global Purge requires Root Authentication.', 'error');
        } catch (error) {
            showToast('Purge protocol failed.', 'error');
        }
    };

    function showToast(message, type = 'info') {
        const container = document.getElementById('toastContainer');
        if (!container) return;

        const toast = document.createElement('div');
        toast.className = `p-4 rounded-xl bg-white/10 backdrop-blur-md border border-white/10 shadow-2xl flex items-center gap-4 animate-slide-in pointer-events-auto`;
        
        const colors = {
            'success': 'text-emerald-400 bg-emerald-400/10',
            'error': 'text-rose-400 bg-rose-400/10',
            'critical': 'text-primary bg-primary/10',
            'info': 'text-blue-400 bg-blue-400/10'
        };
        const colorClass = colors[type] || colors.info;

        toast.innerHTML = `
            <div class="w-8 h-8 rounded-full flex items-center justify-center ${colorClass}">
                <span class="material-symbols-outlined text-sm">
                    ${type === 'success' ? 'check' : type === 'error' ? 'close' : 'info'}
                </span>
            </div>
            <span class="text-xs font-bold text-white">${message}</span>
        `;

        container.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(20px)';
            setTimeout(() => toast.remove(), 500);
        }, 5000);
    }
})();
