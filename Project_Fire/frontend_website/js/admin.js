/**
 * Agniveer — Admin Tactical Command Hub Logic
 * Optimized for v8 Firebase SDK + Tactical API Polling
 */

(function () {
    let detections = [];
    let isRealtime = false;
    const API_BASE_URL = 'http://127.0.0.1:8000/api';

    // ─────────────────────────────────────────────────────────────────────────
    // GLOBAL EXPOSURE (Ensure these are available immediately for button clicks)
    // ─────────────────────────────────────────────────────────────────────────
    
    window.deleteIncident = async function(id) {
        if (!confirm('Permanently delete this incident?')) return;
        
        try {
            console.log(`📡 Sending Deletion Signal for: ${id}`);
            showToast('Initiating deletion protocol...', 'info');
            
            // Priority 1: Backend API (Central Truth)
            const response = await fetch(`${API_BASE_URL}/detections/${id}`, {
                method: 'DELETE'
            });

            // Even if API returns 404, we proceed to clear it from the cloud
            if (response.ok || response.status === 404) {
                if (response.status === 404) console.warn('⚠️ Incident record missing from Backend. Finalizing Cloud Purge...');
                
                // Priority 2: Firebase (Real-time Broadcast)
                if (typeof firebase !== 'undefined' && firebase.apps.length > 0) {
                    try {
                        const db = firebase.firestore();
                        await db.collection('detections').doc(id).delete();
                    } catch (fsErr) {
                        console.error('Firestore Delete Error (Check Rules):', fsErr);
                    }
                }
                
                showToast('Incident deletion complete.', 'success');
                // Force a local update to UI
                detections = detections.filter(d => d.id !== id);
                renderTable();
                updateStats();
                
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

    window.resolveIncident = async function(id) {
        if (!confirm('Mark this incident as safely resolved?')) return;
        
        try {
            console.log(`📡 Sending Resolve Signal for: ${id}`);
            showToast('Initiating resolution protocol...', 'info');
            
            const response = await fetch(`${API_BASE_URL}/detections/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status: 'resolved' })
            });

            if (response.ok) {
                if (typeof firebase !== 'undefined' && firebase.apps.length > 0) {
                    try {
                        const db = firebase.firestore();
                        await db.collection('detections').doc(id).update({ status: 'resolved' });
                    } catch (fsErr) {
                        console.error('Firestore Update Error:', fsErr);
                    }
                }
                
                showToast('Incident marked as resolved.', 'success');
                const target = detections.find(d => d.id === id);
                if (target) target.status = 'resolved';
                
                renderTable();
                updateStats();
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
        showToast('Purge protocol requires Root Authentication.', 'error');
    };

    // ─────────────────────────────────────────────────────────────────────────
    // INITIALIZATION logic
    // ─────────────────────────────────────────────────────────────────────────

    document.addEventListener('DOMContentLoaded', async () => {
        startClock();
        
        // Initial data pull (Guaranteed start)
        await fetchData();
        
        try {
            const success = await initializeFirebase();
            if (success && typeof firebase !== 'undefined' && firebase.apps.length > 0) {
                console.log('📡 Real-time Cloud Intelligence Active');
                isRealtime = true;
                setupAdminListeners();
            } else {
                console.warn('⚠️ Firebase skipped. Staying in Tactical Polling mode.');
                startPolling();
            }
        } catch (e) {
            console.warn('⚠️ Cloud Sync Initialization Error. Falling back to Polling.');
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
        // Already did once on load, so just set interval
        setInterval(fetchData, 5000); 
    }

    async function fetchData() {
        try {
            const response = await fetch(`${API_BASE_URL}/detections/?limit=100`);
            if (!response.ok) throw new Error(`API error ${response.status}`);
            const data = await response.json();
            detections = data;
            renderTable();
            updateStats();
        } catch (error) {
            console.error('Polling error:', error);
        }
    }

    function setupAdminListeners() {
        if (typeof firebase === 'undefined') return;
        const db = firebase.firestore();
        
        db.collection('detections')
            .orderBy('timestamp', 'desc')
            .onSnapshot((snapshot) => {
                snapshot.docChanges().forEach((change) => {
                    const docId = change.doc.id;
                    if (change.type === 'added') {
                        const newDoc = { id: docId, ...change.doc.data() };
                        if (!detections.find(d => d.id === docId)) {
                            detections.unshift(newDoc);
                        }
                    } else if (change.type === 'modified') {
                        const idx = detections.findIndex(d => d.id === docId);
                        if (idx !== -1) {
                            detections[idx] = { id: docId, ...change.doc.data() };
                        }
                    } else if (change.type === 'removed') {
                        detections = detections.filter(d => d.id !== docId);
                    }
                });
                
                renderTable();
                updateStats();
            }, (error) => {
                console.error('Snapshot error (Permissions/Indexes?):', error);
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
            const confidence = Math.round((parseFloat(d.confidence) || 0) * 100);

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
                         <span class="px-3 py-1 rounded-lg bg-white/5 border border-white/10 text-[9px] font-black uppercase text-slate-400 tracking-widest">${d.status || 'Pending'}</span>
                    </td>
                    <td class="px-10 py-6">
                        <div class="flex gap-2">
                             <button onclick="resolveIncident('${d.id}')" class="bg-emerald-500/10 hover:bg-emerald-500 text-emerald-500 hover:text-white px-3 py-2 rounded-lg text-[9px] font-black uppercase tracking-widest border border-emerald-500/20 transition-all flex items-center gap-1">
                                 <span class="material-symbols-outlined text-[10px]">check</span> Resolve
                             </button>
                             <button onclick="deleteIncident('${d.id}')" class="bg-rose-500/10 hover:bg-rose-500 text-rose-500 hover:text-white px-3 py-2 rounded-lg text-[9px] font-black uppercase tracking-widest border border-rose-500/20 transition-all flex items-center gap-1">
                                 <span class="material-symbols-outlined text-[10px]">delete</span> Delete
                             </button>
                        </div>
                    </td>
                </tr>
            `;
        }).join('');
    }

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
