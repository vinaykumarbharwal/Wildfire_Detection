const MapController = {
    map: null,
    lightTiles: null,
    darkTiles: null,
    markers: {},

    initializeMap: function () {
        if (this.map) return;

        const defaultCenter = [28.6139, 77.2090];
        this.map = L.map('fireMap').setView(defaultCenter, 10);

        this.lightTiles = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors'
        });

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
            this.darkTiles.addTo(this.map);
        } else {
            if (this.map.hasLayer(this.darkTiles)) this.map.removeLayer(this.darkTiles);
            this.lightTiles.addTo(this.map);
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

        marker.bindPopup(`
            <div style="min-width: 200px;">
                <h3 style="margin: 0 0 10px 0; color: ${this.getSeverityColor(detection.severity)};">
                    🔥 ${detection.severity.toUpperCase()} FIRE
                </h3>
                <p><strong>Location:</strong> ${detection.address || 'Unknown'}</p>
                <p><strong>Confidence:</strong> ${Math.round(detection.confidence * 100)}%</p>
                <p><strong>Time:</strong> ${new Date(detection.timestamp).toLocaleString()}</p>
                <p><strong>Status:</strong> ${detection.status}</p>
                <img src="${detection.image_url || 'https://via.placeholder.com/400x225?text=No+Image+Available'}" 
                     style="width: 100%; max-height: 150px; object-fit: cover; border-radius: 5px; margin-top: 10px;"
                     onerror="this.onerror=null; this.src='https://via.placeholder.com/400x225?text=No+Image+Available'">
                <div style="display: flex; gap: 5px; margin-top: 10px;">
                    <a href="https://maps.google.com/?q=${detection.latitude},${detection.longitude}" target="_blank" style="flex: 1; text-align: center; padding: 5px; background: #007bff; color: white; text-decoration: none; border-radius: 3px;">📍 Map</a>
                    <a href="${detection.image_url || '#'}" target="_blank" style="flex: 1; text-align: center; padding: 5px; background: #28a745; color: white; text-decoration: none; border-radius: 3px;">🖼️ Image</a>
                </div>
            </div>
        `);

        return marker;
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
