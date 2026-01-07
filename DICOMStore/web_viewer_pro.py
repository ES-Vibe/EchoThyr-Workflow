"""
Viewer Web DICOM Pro - Avec outils de mesure
Interface professionnelle sans dépendances CDN complexes
"""

from flask import Flask, render_template_string, send_file, jsonify, request, Response
from pathlib import Path
from pydicom import dcmread
from datetime import datetime
import io
import os
import logging
import numpy as np
from PIL import Image

log = logging.getLogger('werkzeug')
log.setLevel(logging.WARNING)

app = Flask(__name__)

ARCHIVE_PATH = Path("C:/Users/Emeric/Desktop/Claude/DICOMStore/DICOM_Archive")

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DICOM Viewer Pro</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0a0a14;
            color: #eee;
            height: 100vh;
            overflow: hidden;
            user-select: none;
        }

        .app-container {
            display: flex;
            height: 100vh;
        }

        /* Sidebar */
        .sidebar {
            width: 260px;
            background: #12121e;
            border-right: 1px solid #2a2a3e;
            display: flex;
            flex-direction: column;
        }

        .sidebar-header {
            padding: 15px;
            background: #1a1a2e;
            border-bottom: 1px solid #2a2a3e;
        }

        .sidebar-header h1 {
            font-size: 1.1em;
            color: #00d9ff;
            margin-bottom: 10px;
        }

        .search-box input {
            width: 100%;
            padding: 8px 12px;
            border: 1px solid #2a2a3e;
            border-radius: 6px;
            background: #0a0a14;
            color: #fff;
            font-size: 0.9em;
        }

        .patients-list {
            flex: 1;
            overflow-y: auto;
            padding: 10px;
        }

        .patient-item {
            padding: 12px;
            margin-bottom: 8px;
            background: #1a1a2e;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s;
        }

        .patient-item:hover { background: #252538; }
        .patient-item.active {
            background: #0f3460;
            border-left: 3px solid #00d9ff;
        }

        .patient-name {
            font-weight: 600;
            color: #00d9ff;
            margin-bottom: 4px;
        }

        .patient-meta {
            font-size: 0.8em;
            color: #888;
        }

        .study-item {
            padding: 8px 12px;
            margin: 4px 0 4px 12px;
            font-size: 0.85em;
            color: #aaa;
            background: #0a0a14;
            border-radius: 4px;
            cursor: pointer;
        }

        .study-item:hover { color: #00d9ff; background: #1a1a2e; }

        /* Main viewer area */
        .main-area {
            flex: 1;
            display: flex;
            flex-direction: column;
            background: #000;
        }

        /* Toolbar */
        .toolbar {
            display: flex;
            align-items: center;
            padding: 8px 15px;
            background: #12121e;
            border-bottom: 1px solid #2a2a3e;
            gap: 5px;
            flex-wrap: wrap;
        }

        .tool-group {
            display: flex;
            gap: 3px;
            padding: 0 10px;
            border-right: 1px solid #2a2a3e;
        }

        .tool-group:last-child { border-right: none; }

        .tool-btn {
            padding: 8px 12px;
            border: none;
            border-radius: 6px;
            background: #1a1a2e;
            color: #ccc;
            cursor: pointer;
            font-size: 0.85em;
            transition: all 0.2s;
        }

        .tool-btn:hover { background: #252538; color: #fff; }
        .tool-btn.active { background: #0f3460; color: #00d9ff; }

        /* Viewer container */
        .viewer-container {
            flex: 1;
            display: flex;
            position: relative;
            overflow: hidden;
        }

        .thumbnails-strip {
            width: 100px;
            background: #0a0a14;
            border-right: 1px solid #2a2a3e;
            overflow-y: auto;
            padding: 10px 5px;
        }

        .thumbnail {
            width: 80px;
            height: 80px;
            margin: 5px auto;
            border: 2px solid #2a2a3e;
            border-radius: 4px;
            overflow: hidden;
            cursor: pointer;
            transition: all 0.2s;
        }

        .thumbnail:hover { border-color: #00d9ff; }
        .thumbnail.active { border-color: #00d9ff; box-shadow: 0 0 10px rgba(0,217,255,0.3); }
        .thumbnail img { width: 100%; height: 100%; object-fit: cover; }

        .dicom-viewport {
            flex: 1;
            position: relative;
            display: flex;
            align-items: center;
            justify-content: center;
            background: #000;
        }

        #viewer-canvas {
            max-width: 100%;
            max-height: 100%;
        }

        #measurement-canvas {
            position: absolute;
            top: 0;
            left: 0;
            pointer-events: none;
        }

        .viewport-overlay {
            position: absolute;
            font-size: 12px;
            color: #0f0;
            text-shadow: 1px 1px 2px #000;
            padding: 10px;
            font-family: monospace;
        }

        .overlay-top-left { top: 0; left: 110px; }
        .overlay-top-right { top: 0; right: 10px; text-align: right; }
        .overlay-bottom-left { bottom: 0; left: 110px; }
        .overlay-bottom-right { bottom: 0; right: 10px; text-align: right; }

        .wl-display {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: rgba(0,0,0,0.7);
            padding: 10px 20px;
            border-radius: 8px;
            color: #00d9ff;
            font-family: monospace;
            font-size: 14px;
        }

        .empty-state {
            color: #666;
            text-align: center;
            padding: 40px;
        }

        .info-panel {
            position: absolute;
            bottom: 10px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(0,0,0,0.8);
            padding: 5px 15px;
            border-radius: 20px;
            color: #888;
            font-size: 11px;
        }

        .measurement-result {
            position: absolute;
            background: rgba(0,100,200,0.8);
            color: #fff;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 11px;
            font-family: monospace;
            pointer-events: none;
        }
    </style>
</head>
<body>
    <div class="app-container">
        <!-- Sidebar -->
        <div class="sidebar">
            <div class="sidebar-header">
                <h1>DICOM Viewer Pro</h1>
                <div class="search-box">
                    <input type="text" id="search" placeholder="Rechercher..." oninput="filterPatients()">
                </div>
            </div>
            <div class="patients-list" id="patients-list"></div>
        </div>

        <!-- Main Area -->
        <div class="main-area">
            <!-- Toolbar -->
            <div class="toolbar">
                <div class="tool-group">
                    <button class="tool-btn active" id="tool-wl" onclick="setTool('wl')" title="Fenetrage (Window/Level)">
                        W/L
                    </button>
                    <button class="tool-btn" id="tool-pan" onclick="setTool('pan')" title="Deplacer">
                        Pan
                    </button>
                    <button class="tool-btn" id="tool-zoom" onclick="setTool('zoom')" title="Zoom">
                        Zoom
                    </button>
                </div>
                <div class="tool-group">
                    <button class="tool-btn" id="tool-length" onclick="setTool('length')" title="Mesurer distance">
                        Distance
                    </button>
                    <button class="tool-btn" id="tool-angle" onclick="setTool('angle')" title="Mesurer angle">
                        Angle
                    </button>
                </div>
                <div class="tool-group">
                    <button class="tool-btn" onclick="resetView()" title="Reinitialiser">
                        Reset
                    </button>
                    <button class="tool-btn" onclick="invertColors()" title="Inverser">
                        Inverser
                    </button>
                    <button class="tool-btn" onclick="clearMeasurements()" title="Effacer mesures">
                        Effacer
                    </button>
                </div>
                <div class="tool-group">
                    <button class="tool-btn" onclick="prevImage()" title="Image precedente">Prec</button>
                    <span id="image-counter" style="color:#888; padding: 0 10px;">-/-</span>
                    <button class="tool-btn" onclick="nextImage()" title="Image suivante">Suiv</button>
                </div>
            </div>

            <!-- Viewer -->
            <div class="viewer-container" id="viewer-container">
                <div class="thumbnails-strip" id="thumbnails"></div>
                <div class="dicom-viewport" id="viewport">
                    <canvas id="viewer-canvas"></canvas>
                    <canvas id="measurement-canvas"></canvas>
                    <div class="viewport-overlay overlay-top-left" id="overlay-tl"></div>
                    <div class="viewport-overlay overlay-top-right" id="overlay-tr"></div>
                    <div class="viewport-overlay overlay-bottom-left" id="overlay-bl"></div>
                    <div class="viewport-overlay overlay-bottom-right" id="overlay-br"></div>
                    <div class="wl-display" id="wl-display" style="display:none;"></div>
                    <div class="info-panel" id="info-panel">Selectionnez un patient pour commencer</div>
                    <div id="measurements-container"></div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // State
        let patients = [];
        let currentImages = [];
        let currentIndex = 0;
        let currentTool = 'wl';
        let isInverted = false;

        // Image state
        let originalImageData = null;
        let windowCenter = 128;
        let windowWidth = 256;
        let panX = 0, panY = 0;
        let zoomLevel = 1;

        // Measurement state
        let measurements = [];
        let currentMeasurement = null;
        let measurementPoints = [];

        // Canvas elements
        const viewerCanvas = document.getElementById('viewer-canvas');
        const measureCanvas = document.getElementById('measurement-canvas');
        const viewerCtx = viewerCanvas.getContext('2d');
        const measureCtx = measureCanvas.getContext('2d');
        const viewport = document.getElementById('viewport');

        // Mouse tracking
        let isDragging = false;
        let lastX = 0, lastY = 0;
        let startX = 0, startY = 0;

        // Pixel spacing (mm per pixel, default assumption)
        let pixelSpacing = 0.3; // Will be updated from DICOM metadata

        // Load patients
        async function loadPatients() {
            const resp = await fetch('/api/patients');
            patients = await resp.json();
            renderPatients();
        }

        function renderPatients() {
            const search = document.getElementById('search').value.toLowerCase();
            const filtered = patients.filter(p =>
                p.name.toLowerCase().includes(search) ||
                p.id.toLowerCase().includes(search)
            );

            document.getElementById('patients-list').innerHTML = filtered.map(p => {
                const pPath = p.path.replace(/\\\\/g, '/');
                return `
                    <div class="patient-item" onclick="selectPatient('${pPath}')">
                        <div class="patient-name">${p.name}</div>
                        <div class="patient-meta">${p.studies.length} examen(s)</div>
                        ${p.studies.map(s => {
                            const sPath = s.path.replace(/\\\\/g, '/');
                            return `<div class="study-item" onclick="event.stopPropagation(); loadStudy('${sPath}')">${s.date} (${s.count})</div>`;
                        }).join('')}
                    </div>
                `;
            }).join('') || '<div class="empty-state">Aucun patient</div>';
        }

        function filterPatients() { renderPatients(); }

        function selectPatient(path) {
            const patient = patients.find(p => p.path.replace(/\\\\/g, '/') === path);
            if (patient && patient.studies.length > 0) {
                loadStudy(patient.studies[0].path.replace(/\\\\/g, '/'));
            }
        }

        async function loadStudy(studyPath) {
            const resp = await fetch(`/api/images?path=${encodeURIComponent(studyPath)}`);
            currentImages = await resp.json();
            currentIndex = 0;

            // Render thumbnails
            document.getElementById('thumbnails').innerHTML = currentImages.map((img, i) => `
                <div class="thumbnail ${i === 0 ? 'active' : ''}" onclick="loadImage(${i})">
                    <img src="/api/thumbnail?path=${encodeURIComponent(img.path)}" loading="lazy">
                </div>
            `).join('');

            if (currentImages.length > 0) {
                loadImage(0);
            }
        }

        async function loadImage(index) {
            currentIndex = index;
            const img = currentImages[index];

            // Update thumbnails
            document.querySelectorAll('.thumbnail').forEach((t, i) => {
                t.classList.toggle('active', i === index);
            });

            // Update counter
            document.getElementById('image-counter').textContent = `${index + 1}/${currentImages.length}`;

            // Update overlays
            document.getElementById('overlay-tl').innerHTML = `
                <div>${img.patient_name || ''}</div>
                <div>${img.patient_id || ''}</div>
            `;
            document.getElementById('overlay-tr').innerHTML = `
                <div>${img.study_date || ''}</div>
                <div>${img.modality || ''}</div>
            `;
            document.getElementById('overlay-bl').innerHTML = `
                <div>${img.description || ''}</div>
            `;

            // Update pixel spacing if available
            if (img.pixel_spacing) {
                pixelSpacing = img.pixel_spacing;
            }

            // Load image
            const imageUrl = `/api/image?path=${encodeURIComponent(img.path)}`;
            const image = new Image();
            image.onload = () => {
                // Resize canvas to match image
                viewerCanvas.width = image.width;
                viewerCanvas.height = image.height;
                measureCanvas.width = viewport.clientWidth;
                measureCanvas.height = viewport.clientHeight;

                // Draw image
                viewerCtx.drawImage(image, 0, 0);

                // Store original image data
                originalImageData = viewerCtx.getImageData(0, 0, image.width, image.height);

                // Reset view
                windowCenter = 128;
                windowWidth = 256;
                panX = 0;
                panY = 0;
                zoomLevel = 1;
                isInverted = false;

                // Clear measurements for new image
                measurements = [];
                renderMeasurements();

                // Update info
                document.getElementById('info-panel').textContent =
                    `${image.width} x ${image.height} | Molette: zoom | Outils: W/L, Pan, Zoom, Distance, Angle`;

                applyWindowLevel();
            };
            image.src = imageUrl;
        }

        function applyWindowLevel() {
            if (!originalImageData) return;

            const imageData = new ImageData(
                new Uint8ClampedArray(originalImageData.data),
                originalImageData.width,
                originalImageData.height
            );

            const data = imageData.data;
            const low = windowCenter - windowWidth / 2;
            const high = windowCenter + windowWidth / 2;

            for (let i = 0; i < data.length; i += 4) {
                let val = data[i];

                // Apply window/level
                if (val <= low) val = 0;
                else if (val >= high) val = 255;
                else val = ((val - low) / windowWidth) * 255;

                // Apply invert
                if (isInverted) val = 255 - val;

                data[i] = data[i + 1] = data[i + 2] = val;
            }

            viewerCtx.putImageData(imageData, 0, 0);
            updateWLDisplay();
        }

        function updateWLDisplay() {
            const wlDisplay = document.getElementById('wl-display');
            wlDisplay.textContent = `W: ${Math.round(windowWidth)} L: ${Math.round(windowCenter)}`;
        }

        function setTool(tool) {
            currentTool = tool;
            document.querySelectorAll('.tool-btn').forEach(btn => btn.classList.remove('active'));
            document.getElementById('tool-' + tool)?.classList.add('active');

            measurementPoints = [];
            document.getElementById('info-panel').textContent = getToolInfo(tool);
        }

        function getToolInfo(tool) {
            switch(tool) {
                case 'wl': return 'W/L: Glissez pour ajuster contraste';
                case 'pan': return 'Pan: Glissez pour deplacer l\'image';
                case 'zoom': return 'Zoom: Glissez haut/bas pour zoomer';
                case 'length': return 'Distance: Cliquez 2 points pour mesurer';
                case 'angle': return 'Angle: Cliquez 3 points pour mesurer';
                default: return '';
            }
        }

        function resetView() {
            windowCenter = 128;
            windowWidth = 256;
            panX = 0;
            panY = 0;
            zoomLevel = 1;
            isInverted = false;
            applyWindowLevel();
            updateCanvasTransform();
        }

        function invertColors() {
            isInverted = !isInverted;
            applyWindowLevel();
        }

        function clearMeasurements() {
            measurements = [];
            measurementPoints = [];
            renderMeasurements();
        }

        function updateCanvasTransform() {
            viewerCanvas.style.transform = `translate(${panX}px, ${panY}px) scale(${zoomLevel})`;
        }

        // Mouse events
        viewport.addEventListener('mousedown', (e) => {
            if (e.target !== viewerCanvas && e.target !== measureCanvas) return;

            isDragging = true;
            lastX = e.clientX;
            lastY = e.clientY;
            startX = e.clientX;
            startY = e.clientY;

            if (currentTool === 'length' || currentTool === 'angle') {
                const rect = viewerCanvas.getBoundingClientRect();
                const x = (e.clientX - rect.left) / zoomLevel;
                const y = (e.clientY - rect.top) / zoomLevel;
                measurementPoints.push({ x, y, screenX: e.clientX, screenY: e.clientY });

                if (currentTool === 'length' && measurementPoints.length === 2) {
                    addLengthMeasurement();
                } else if (currentTool === 'angle' && measurementPoints.length === 3) {
                    addAngleMeasurement();
                }
                renderMeasurements();
            }

            if (currentTool === 'wl') {
                document.getElementById('wl-display').style.display = 'block';
            }
        });

        viewport.addEventListener('mousemove', (e) => {
            if (!isDragging) return;

            const dx = e.clientX - lastX;
            const dy = e.clientY - lastY;

            switch (currentTool) {
                case 'wl':
                    windowWidth = Math.max(1, windowWidth + dx * 2);
                    windowCenter = Math.max(0, Math.min(255, windowCenter + dy));
                    applyWindowLevel();
                    break;
                case 'pan':
                    panX += dx;
                    panY += dy;
                    updateCanvasTransform();
                    break;
                case 'zoom':
                    zoomLevel = Math.max(0.1, Math.min(10, zoomLevel + dy * 0.01));
                    updateCanvasTransform();
                    break;
            }

            lastX = e.clientX;
            lastY = e.clientY;
        });

        viewport.addEventListener('mouseup', () => {
            isDragging = false;
            if (currentTool === 'wl') {
                setTimeout(() => {
                    document.getElementById('wl-display').style.display = 'none';
                }, 1000);
            }
        });

        viewport.addEventListener('mouseleave', () => {
            isDragging = false;
        });

        // Mouse wheel for zoom
        viewport.addEventListener('wheel', (e) => {
            e.preventDefault();
            zoomLevel = Math.max(0.1, Math.min(10, zoomLevel - e.deltaY * 0.001));
            updateCanvasTransform();
        });

        // Measurement functions
        function addLengthMeasurement() {
            const p1 = measurementPoints[0];
            const p2 = measurementPoints[1];
            const dx = (p2.x - p1.x) * pixelSpacing;
            const dy = (p2.y - p1.y) * pixelSpacing;
            const distance = Math.sqrt(dx * dx + dy * dy);

            measurements.push({
                type: 'length',
                points: [...measurementPoints],
                value: distance.toFixed(1) + ' mm'
            });

            measurementPoints = [];
        }

        function addAngleMeasurement() {
            const p1 = measurementPoints[0];
            const p2 = measurementPoints[1]; // vertex
            const p3 = measurementPoints[2];

            const angle1 = Math.atan2(p1.y - p2.y, p1.x - p2.x);
            const angle2 = Math.atan2(p3.y - p2.y, p3.x - p2.x);
            let angle = Math.abs(angle1 - angle2) * (180 / Math.PI);
            if (angle > 180) angle = 360 - angle;

            measurements.push({
                type: 'angle',
                points: [...measurementPoints],
                value: angle.toFixed(1) + ' deg'
            });

            measurementPoints = [];
        }

        function renderMeasurements() {
            // Clear measurement canvas
            measureCanvas.width = viewport.clientWidth;
            measureCanvas.height = viewport.clientHeight;
            measureCtx.clearRect(0, 0, measureCanvas.width, measureCanvas.height);

            // Clear measurement labels
            document.getElementById('measurements-container').innerHTML = '';

            const rect = viewerCanvas.getBoundingClientRect();

            // Draw completed measurements
            measurements.forEach(m => {
                measureCtx.strokeStyle = '#00ff00';
                measureCtx.lineWidth = 2;
                measureCtx.setLineDash([]);

                if (m.type === 'length') {
                    const x1 = rect.left + m.points[0].x * zoomLevel + panX - viewport.getBoundingClientRect().left;
                    const y1 = rect.top + m.points[0].y * zoomLevel + panY - viewport.getBoundingClientRect().top;
                    const x2 = rect.left + m.points[1].x * zoomLevel + panX - viewport.getBoundingClientRect().left;
                    const y2 = rect.top + m.points[1].y * zoomLevel + panY - viewport.getBoundingClientRect().top;

                    measureCtx.beginPath();
                    measureCtx.moveTo(x1, y1);
                    measureCtx.lineTo(x2, y2);
                    measureCtx.stroke();

                    // Draw endpoints
                    drawPoint(x1, y1);
                    drawPoint(x2, y2);

                    // Add label
                    addMeasurementLabel((x1 + x2) / 2, (y1 + y2) / 2, m.value);
                }

                if (m.type === 'angle') {
                    const points = m.points.map(p => ({
                        x: rect.left + p.x * zoomLevel + panX - viewport.getBoundingClientRect().left,
                        y: rect.top + p.y * zoomLevel + panY - viewport.getBoundingClientRect().top
                    }));

                    measureCtx.beginPath();
                    measureCtx.moveTo(points[0].x, points[0].y);
                    measureCtx.lineTo(points[1].x, points[1].y);
                    measureCtx.lineTo(points[2].x, points[2].y);
                    measureCtx.stroke();

                    points.forEach(p => drawPoint(p.x, p.y));
                    addMeasurementLabel(points[1].x, points[1].y - 20, m.value);
                }
            });

            // Draw current measurement in progress
            if (measurementPoints.length > 0) {
                measureCtx.strokeStyle = '#ffff00';
                measureCtx.setLineDash([5, 5]);

                measurementPoints.forEach((p, i) => {
                    const x = rect.left + p.x * zoomLevel + panX - viewport.getBoundingClientRect().left;
                    const y = rect.top + p.y * zoomLevel + panY - viewport.getBoundingClientRect().top;
                    drawPoint(x, y, '#ffff00');

                    if (i > 0) {
                        const prevP = measurementPoints[i - 1];
                        const prevX = rect.left + prevP.x * zoomLevel + panX - viewport.getBoundingClientRect().left;
                        const prevY = rect.top + prevP.y * zoomLevel + panY - viewport.getBoundingClientRect().top;
                        measureCtx.beginPath();
                        measureCtx.moveTo(prevX, prevY);
                        measureCtx.lineTo(x, y);
                        measureCtx.stroke();
                    }
                });
            }
        }

        function drawPoint(x, y, color = '#00ff00') {
            measureCtx.fillStyle = color;
            measureCtx.beginPath();
            measureCtx.arc(x, y, 4, 0, Math.PI * 2);
            measureCtx.fill();
        }

        function addMeasurementLabel(x, y, text) {
            const label = document.createElement('div');
            label.className = 'measurement-result';
            label.textContent = text;
            label.style.left = (x + 10) + 'px';
            label.style.top = (y - 10) + 'px';
            document.getElementById('measurements-container').appendChild(label);
        }

        // Navigation
        function prevImage() {
            if (currentImages.length > 0) {
                loadImage((currentIndex - 1 + currentImages.length) % currentImages.length);
            }
        }

        function nextImage() {
            if (currentImages.length > 0) {
                loadImage((currentIndex + 1) % currentImages.length);
            }
        }

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.key === 'ArrowLeft') prevImage();
            if (e.key === 'ArrowRight') nextImage();
            if (e.key === 'r' || e.key === 'R') resetView();
            if (e.key === 'i' || e.key === 'I') invertColors();
            if (e.key === 'Escape') clearMeasurements();
        });

        // Init
        loadPatients();
    </script>
</body>
</html>
"""


def get_dicom_info(filepath):
    """Extrait les metadonnees d'un fichier DICOM"""
    try:
        ds = dcmread(filepath, stop_before_pixels=True, force=True)

        # Get pixel spacing if available
        pixel_spacing = 0.3  # Default
        if hasattr(ds, 'PixelSpacing') and ds.PixelSpacing:
            pixel_spacing = float(ds.PixelSpacing[0])
        elif hasattr(ds, 'ImagerPixelSpacing') and ds.ImagerPixelSpacing:
            pixel_spacing = float(ds.ImagerPixelSpacing[0])

        return {
            'patient_name': str(getattr(ds, 'PatientName', '')).replace('^', ' '),
            'patient_id': str(getattr(ds, 'PatientID', '')),
            'study_date': str(getattr(ds, 'StudyDate', '')),
            'modality': str(getattr(ds, 'Modality', '')),
            'description': str(getattr(ds, 'SeriesDescription', getattr(ds, 'StudyDescription', ''))),
            'pixel_spacing': pixel_spacing,
        }
    except:
        return {}


def dicom_to_png(filepath, size=None):
    """Convertit un fichier DICOM en PNG"""
    try:
        ds = dcmread(filepath, force=True)
        pixel_array = ds.pixel_array

        if pixel_array.dtype != np.uint8:
            pixel_min = pixel_array.min()
            pixel_max = pixel_array.max()
            if pixel_max > pixel_min:
                pixel_array = ((pixel_array - pixel_min) / (pixel_max - pixel_min) * 255).astype(np.uint8)
            else:
                pixel_array = np.zeros_like(pixel_array, dtype=np.uint8)

        if len(pixel_array.shape) == 2:
            img = Image.fromarray(pixel_array, mode='L')
        else:
            img = Image.fromarray(pixel_array)

        if size:
            img.thumbnail((size, size), Image.Resampling.LANCZOS)

        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        return buffer
    except Exception as e:
        print(f"Erreur conversion DICOM: {e}")
        return None


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/api/patients')
def api_patients():
    """Liste des patients avec leurs examens"""
    patients = []

    if not ARCHIVE_PATH.exists():
        return jsonify([])

    for patient_dir in ARCHIVE_PATH.iterdir():
        if patient_dir.is_dir():
            # Get patient info from first DICOM file
            dcm_files = list(patient_dir.glob('**/*.dcm'))
            if not dcm_files:
                continue

            info = get_dicom_info(dcm_files[0])

            # Get studies (subdirectories)
            studies = []
            for study_dir in patient_dir.iterdir():
                if study_dir.is_dir():
                    study_dcm = list(study_dir.glob('**/*.dcm'))
                    if study_dcm:
                        study_info = get_dicom_info(study_dcm[0])
                        studies.append({
                            'path': str(study_dir),
                            'date': study_info.get('study_date', 'Unknown'),
                            'count': len(study_dcm)
                        })

            if not studies:
                # No subdirectories, treat patient dir as single study
                studies.append({
                    'path': str(patient_dir),
                    'date': info.get('study_date', 'Unknown'),
                    'count': len(dcm_files)
                })

            patients.append({
                'name': info.get('patient_name', patient_dir.name),
                'id': info.get('patient_id', ''),
                'path': str(patient_dir),
                'studies': studies
            })

    return jsonify(patients)


@app.route('/api/images')
def api_images():
    """Liste des images d'un examen"""
    study_path = request.args.get('path', '')
    if not study_path:
        return jsonify([])

    study_dir = Path(study_path)
    if not study_dir.exists():
        return jsonify([])

    images = []
    dcm_files = sorted(study_dir.glob('**/*.dcm'))

    for dcm_file in dcm_files:
        info = get_dicom_info(dcm_file)
        info['path'] = str(dcm_file)
        images.append(info)

    return jsonify(images)


@app.route('/api/image')
def api_image():
    """Retourne une image DICOM en PNG"""
    filepath = request.args.get('path', '')
    if not filepath or not Path(filepath).exists():
        return "Not found", 404

    png_buffer = dicom_to_png(filepath)
    if png_buffer:
        return send_file(png_buffer, mimetype='image/png')
    return "Error", 500


@app.route('/api/thumbnail')
def api_thumbnail():
    """Retourne une miniature"""
    filepath = request.args.get('path', '')
    if not filepath or not Path(filepath).exists():
        return "Not found", 404

    png_buffer = dicom_to_png(filepath, size=80)
    if png_buffer:
        return send_file(png_buffer, mimetype='image/png')
    return "Error", 500


def run_viewer(host='0.0.0.0', port=8080):
    print(f"\n{'='*50}")
    print(f"  DICOM VIEWER PRO")
    print(f"{'='*50}")
    print(f"\n  URL: http://localhost:{port}")
    print(f"  Archive: {ARCHIVE_PATH}")
    print(f"\n  Outils disponibles:")
    print(f"    - W/L : Fenetrage (Window/Level)")
    print(f"    - Pan : Deplacer l'image")
    print(f"    - Zoom : Zoomer/Dezoomer")
    print(f"    - Distance : Mesurer une distance")
    print(f"    - Angle : Mesurer un angle")
    print(f"\n  Raccourcis clavier:")
    print(f"    Fleches : Image precedente/suivante")
    print(f"    R : Reinitialiser")
    print(f"    I : Inverser les couleurs")
    print(f"    Echap : Effacer les mesures")
    print(f"{'='*50}\n")

    app.run(host=host, port=port, debug=False, threaded=True)


if __name__ == '__main__':
    run_viewer()
