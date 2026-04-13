const MapController = {
    map: null,
    lightTiles: null,
    darkTiles: null,
    labelTiles: null,   // City/village name labels overlay
    markers: {},

    initializeMap: function () {
        if (this.map) return;

        const defaultCenter = [28.6139, 77.2090];
        this.map = L.map('fireMap').setView(defaultCenter, 10);

        // Premium Free Satellite Map (Esri) - Perfect for Wildfire tracking, NO API key needed
        this.lightTiles = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
            attribution: 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community'
        });

        // FREE Esri Label Overlay — shows city, village & road names on top of satellite
        this.labelTiles = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}', {
            attribution: '',
            pane: 'overlayPane',
            opacity: 1
        });

        // Sleek Dark Map (Carto) - Already implemented, NO API key needed
        this.darkTiles = L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
            attribution: '© OpenStreetMap contributors, © CARTO',
            subdomains: 'abcd',
            maxZoom: 20
        });

        const isDark = document.documentElement.classList.contains('dark');
        this.toggleMapTheme(isDark);
        L.control.scale().addTo(this.map);
    },

    toggleMapTheme: function (isDark) {
        if (!this.map) return;

        if (isDark) {
            if (this.map.hasLayer(this.lightTiles)) this.map.removeLayer(this.lightTiles);
            if (this.map.hasLayer(this.labelTiles)) this.map.removeLayer(this.labelTiles);
            this.darkTiles.addTo(this.map);
        } else {
            if (this.map.hasLayer(this.darkTiles)) this.map.removeLayer(this.darkTiles);
            this.lightTiles.addTo(this.map);
            this.labelTiles.addTo(this.map);  // Labels on top of satellite
        }
    },

    updateMapMarkers: function (detections) {
        Object.values(this.markers).forEach(marker => marker.remove());
        this.markers = {};

        detections.forEach(detection => {
            const marker = this.createMarker(detection);
            marker.addTo(this.map);
            this.markers[detection.id] = marker;
        });
    },

    createMarker: function (detection) {
        const icon = L.divIcon({
            className: `custom-marker ${detection.severity}`,
            html: `<div style="
                background-color: ${this.getSeverityColor(detection.severity)};
                width: 30px;
                height: 30px;
                border-radius: 50%;
                border: 3px solid white;
                box-shadow: 0 2px 5px rgba(0,0,0,0.3);
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                font-size: 16px;
            ">🔥</div>`,
            iconSize: [30, 30],
            iconAnchor: [15, 15],
            popupAnchor: [0, -15]
        });

        const marker = L.marker([detection.latitude, detection.longitude], { icon });

        let weatherHTML = '';
        if (detection.weather_snapshot && typeof detection.weather_snapshot.temperature_celsius !== 'undefined') {
            const w = detection.weather_snapshot;
            weatherHTML = `
                <div style="background: rgba(0,0,0,0.05); border: 1px solid rgba(0,0,0,0.1); padding: 8px; border-radius: 5px; margin-top: 8px; font-size: 12px; color: #333;">
                    <strong style="display: block; margin-bottom: 4px; color: #d97706;">☁️ Live Weather Data:</strong>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 4px;">
                        <div>🌡️ Temp: <b>${w.temperature_celsius}°C</b></div>
                        <div>💨 Wind: <b>${w.wind_speed_kmh} km/h</b></div>
                        <div>🧭 Dir: <b>${w.wind_direction_degrees}°</b></div>
                        <div>💧 Hum: <b>${w.humidity_percent || '--'}%</b></div>
                    </div>
                </div>
            `;
        }

        // Pre-render cached AI report if available
        const existingReport = detection.ai_tactical_report
          ? `<div id="ai-report-${detection.id}" style="background:#fffbeb;border:1px solid #fcd34d;border-radius:5px;padding:8px;margin-top:8px;font-size:12px;color:#333;">
               <strong style="color:#92400e;">🤖 AI Tactical Assessment:</strong>
               <div style="margin-top:4px;white-space:pre-wrap;">${detection.ai_tactical_report}</div>
             </div>`
          : `<div id="ai-report-${detection.id}"></div>`;

        marker.bindPopup(`
            <div style="min-width: 240px; font-family: sans-serif;">
                <h3 style="margin: 0 0 10px 0; color: ${this.getSeverityColor(detection.severity)}; font-size: 16px;">
                    🔥 ${(detection.severity || 'Unknown').toUpperCase()} FIRE
                </h3>
                <p style="margin: 4px 0;"><strong>Location:</strong> ${detection.address || 'Unknown'}</p>
                <p style="margin: 4px 0;"><strong>Confidence:</strong> ${Math.round(detection.confidence * 100)}%</p>
                <p style="margin: 4px 0;"><strong>Status:</strong> ${detection.status}</p>
                <p style="margin: 4px 0; font-size: 11px; color: #666;"><strong>Time:</strong> ${new Date(detection.timestamp).toLocaleString()}</p>
                
                ${weatherHTML}

                ${existingReport}

                <button onclick="MapController.generateAIReport('${detection.id}', this)"
                        style="width:100%;margin-top:8px;padding:7px;background:linear-gradient(135deg,#7c3aed,#4f46e5);color:white;border:none;border-radius:5px;cursor:pointer;font-size:13px;font-weight:bold;">
                    ✨ ${detection.ai_tactical_report ? 'Regenerate' : 'Generate'} AI Report
                </button>

                <img src="${detection.image_url || 'https://via.placeholder.com/400x225?text=No+Image+Available'}" 
                     style="width: 100%; max-height: 150px; object-fit: cover; border-radius: 5px; margin-top: 10px;"
                     onerror="this.onerror=null; this.src='https://via.placeholder.com/400x225?text=No+Image+Available'">
                <div style="display: flex; gap: 5px; margin-top: 10px;">
                    <a href="https://maps.google.com/?q=${detection.latitude},${detection.longitude}" target="_blank" style="flex: 1; text-align: center; padding: 5px; background: #007bff; color: white; text-decoration: none; border-radius: 3px; font-size: 13px;">📍 Open Map</a>
                    <a href="${detection.image_url || '#'}" target="_blank" style="flex: 1; text-align: center; padding: 5px; background: #28a745; color: white; text-decoration: none; border-radius: 3px; font-size: 13px;">🖼️ HD Image</a>
                </div>
            </div>
        `);

        return marker;
    },

    generateAIReport: async function(detectionId, btn) {
        const reportDiv = document.getElementById(`ai-report-${detectionId}`);
        if (!reportDiv) return;

        btn.disabled = true;
        btn.textContent = '⏳ Generating Report...';
        reportDiv.innerHTML = `<div style="color:#6b7280;font-size:12px;padding:6px;">🔄 Contacting Gemini AI, please wait...</div>`;

        try {
            const API_BASE = window.API_BASE_URL || 'http://localhost:8000';
            const res = await fetch(`${API_BASE}/api/detections/${detectionId}/generate-ai-report`, { method: 'POST' });
            const data = await res.json();

            if (data.ai_tactical_report) {
                reportDiv.innerHTML = `
                    <div style="background:#fffbeb;border:1px solid #fcd34d;border-radius:5px;padding:8px;font-size:12px;color:#333;">
                        <strong style="color:#92400e;">🤖 AI Tactical Assessment:</strong>
                        <div style="margin-top:4px;white-space:pre-wrap;">${data.ai_tactical_report}</div>
                    </div>`;
                btn.textContent = '✨ Regenerate AI Report';
            } else {
                reportDiv.innerHTML = `<div style="color:red;font-size:12px;">⚠️ Could not generate report.</div>`;
                btn.textContent = '✨ Generate AI Report';
            }
        } catch (err) {
            reportDiv.innerHTML = `<div style="color:red;font-size:12px;">⚠️ Error: ${err.message}</div>`;
            btn.textContent = '✨ Generate AI Report';
        }
        btn.disabled = false;
    },

    getSeverityColor: function (severity) {
        const colors = {
            'critical': '#FF4B4B',
            'high': '#FF8C00',
            'medium': '#FFB347',
            'low': '#10B981'
        };
        return colors[severity?.toLowerCase()] || '#64748B';
    },

    highlightMarker: function (detectionId) {
        if (this.markers[detectionId]) {
            this.markers[detectionId].openPopup();
        }
    }
};
