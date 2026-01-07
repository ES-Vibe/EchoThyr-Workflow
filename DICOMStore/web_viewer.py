"""
Viewer Web DICOM - Interface de consultation des images archivées
"""

from flask import Flask, render_template_string, send_file, jsonify, request
from pathlib import Path
from pydicom import dcmread
from datetime import datetime
import io
import os
import logging

# Désactiver les logs Flask en production
log = logging.getLogger('werkzeug')
log.setLevel(logging.WARNING)

app = Flask(__name__)

# Configuration
ARCHIVE_PATH = Path("C:/Users/Emeric/Desktop/Claude/DICOMStore/DICOM_Archive")

# Template HTML principal
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DICOM Viewer - PACS Local</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1a1a2e;
            color: #eee;
            min-height: 100vh;
        }
        .header {
            background: #16213e;
            padding: 15px 20px;
            border-bottom: 2px solid #0f3460;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .header h1 {
            font-size: 1.5em;
            color: #00d9ff;
        }
        .header .stats {
            color: #888;
            font-size: 0.9em;
        }
        .container {
            display: flex;
            height: calc(100vh - 60px);
        }
        .sidebar {
            width: 300px;
            background: #16213e;
            border-right: 1px solid #0f3460;
            overflow-y: auto;
        }
        .main {
            flex: 1;
            padding: 20px;
            overflow-y: auto;
        }
        .patient-card {
            padding: 15px;
            border-bottom: 1px solid #0f3460;
            cursor: pointer;
            transition: background 0.2s;
        }
        .patient-card:hover {
            background: #0f3460;
        }
        .patient-card.active {
            background: #0f3460;
            border-left: 3px solid #00d9ff;
        }
        .patient-name {
            font-weight: bold;
            color: #00d9ff;
            margin-bottom: 5px;
        }
        .patient-info {
            font-size: 0.85em;
            color: #888;
        }
        .study-list {
            margin-top: 10px;
        }
        .study-item {
            padding: 8px 15px;
            margin-left: 10px;
            font-size: 0.9em;
            color: #aaa;
            cursor: pointer;
            border-left: 2px solid #333;
        }
        .study-item:hover {
            color: #fff;
            border-left-color: #00d9ff;
        }
        .study-item.active {
            color: #00d9ff;
            border-left-color: #00d9ff;
        }
        .images-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 15px;
        }
        .image-card {
            background: #16213e;
            border-radius: 8px;
            overflow: hidden;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .image-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 5px 20px rgba(0,217,255,0.2);
        }
        .image-card img {
            width: 100%;
            height: 200px;
            object-fit: cover;
            background: #000;
        }
        .image-card .info {
            padding: 10px;
            font-size: 0.85em;
            color: #888;
        }
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.98);
            z-index: 1000;
            flex-direction: column;
        }
        .modal.active {
            display: flex;
        }
        .modal-toolbar {
            display: flex;
            gap: 5px;
            padding: 10px;
            background: #1a1a2e;
            border-bottom: 1px solid #333;
        }
        .tool-btn {
            padding: 8px 14px;
            border: none;
            border-radius: 5px;
            background: #0f3460;
            color: #ccc;
            cursor: pointer;
            font-size: 0.85em;
        }
        .tool-btn:hover { background: #1a4a7a; color: #fff; }
        .tool-btn.active { background: #00d9ff; color: #000; }
        .tool-separator { width: 1px; background: #333; margin: 0 10px; }
        .modal-viewer {
            flex: 1;
            display: flex;
            justify-content: center;
            align-items: center;
            position: relative;
            overflow: hidden;
        }
        .modal-viewer canvas {
            max-width: 95%;
            max-height: 95%;
        }
        #measure-canvas {
            position: absolute;
            top: 0;
            left: 0;
            width: 100% !important;
            height: 100% !important;
            max-width: none !important;
            max-height: none !important;
            pointer-events: none;
        }
        .modal .close {
            position: absolute;
            top: 10px;
            right: 20px;
            font-size: 1.5em;
            color: #fff;
            cursor: pointer;
            z-index: 10;
        }
        .modal .nav {
            position: absolute;
            top: 50%;
            transform: translateY(-50%);
            font-size: 3em;
            color: #fff;
            cursor: pointer;
            padding: 20px;
            user-select: none;
            z-index: 10;
        }
        .modal .nav.prev { left: 10px; }
        .modal .nav.next { right: 10px; }
        .modal .nav:hover { color: #00d9ff; }
        .wl-indicator {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: rgba(0,0,0,0.8);
            padding: 10px 20px;
            border-radius: 8px;
            color: #00d9ff;
            font-family: monospace;
            display: none;
        }
        .measure-label {
            position: absolute;
            background: rgba(0,150,0,0.8);
            color: #fff;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 12px;
            font-family: monospace;
            pointer-events: none;
        }
        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: #666;
        }
        .empty-state h2 {
            margin-bottom: 10px;
            color: #888;
        }
        .dicom-info {
            position: absolute;
            bottom: 20px;
            left: 20px;
            background: rgba(0,0,0,0.8);
            padding: 15px;
            border-radius: 8px;
            font-size: 0.9em;
            max-width: 400px;
        }
        .dicom-info div {
            margin: 5px 0;
        }
        .dicom-info .label {
            color: #888;
            display: inline-block;
            width: 120px;
        }
        .search-box {
            padding: 10px;
            border-bottom: 1px solid #0f3460;
        }
        .search-box input {
            width: 100%;
            padding: 10px;
            border: none;
            border-radius: 5px;
            background: #0f3460;
            color: #fff;
            font-size: 0.95em;
        }
        .search-box input::placeholder {
            color: #666;
        }
        .refresh-btn {
            background: #0f3460;
            border: none;
            color: #00d9ff;
            padding: 8px 15px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 0.9em;
        }
        .refresh-btn:hover {
            background: #1a4a7a;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>DICOM Viewer</h1>
        <div>
            <span class="stats" id="stats">Chargement...</span>
            <button class="refresh-btn" onclick="loadPatients()">Actualiser</button>
        </div>
    </div>

    <div class="container">
        <div class="sidebar">
            <div class="search-box">
                <input type="text" id="search" placeholder="Rechercher un patient..." oninput="filterPatients()">
            </div>
            <div id="patients-list"></div>
        </div>

        <div class="main">
            <div id="content">
                <div class="empty-state">
                    <h2>PACS Local - Viewer DICOM</h2>
                    <p>Selectionnez un patient dans la liste</p>
                </div>
            </div>
        </div>
    </div>

    <div class="modal" id="modal">
        <div class="modal-toolbar">
            <button class="tool-btn active" id="btn-wl" onclick="setTool('wl')">W/L</button>
            <button class="tool-btn" id="btn-zoom" onclick="setTool('zoom')">Zoom</button>
            <button class="tool-btn" id="btn-pan" onclick="setTool('pan')">Pan</button>
            <div class="tool-separator"></div>
            <button class="tool-btn" id="btn-length" onclick="setTool('length')">Distance</button>
            <button class="tool-btn" id="btn-angle" onclick="setTool('angle')">Angle</button>
            <div class="tool-separator"></div>
            <button class="tool-btn" onclick="resetView()">Reset</button>
            <button class="tool-btn" onclick="invertImage()">Inverser</button>
            <button class="tool-btn" onclick="clearMeasures()">Effacer</button>
            <div class="tool-separator"></div>
            <label style="color:#888;font-size:0.8em;">Calibration:</label>
            <input type="number" id="pixel-spacing-input" value="0.07" min="0.01" max="2" step="0.01"
                   style="width:60px;padding:4px;border-radius:4px;border:1px solid #333;background:#0f3460;color:#fff;"
                   onchange="updatePixelSpacing()" title="mm/pixel">
            <span style="color:#666;font-size:0.8em;">mm/px</span>
            <div class="tool-separator"></div>
            <button class="tool-btn" onclick="prevImage(event)">Prec</button>
            <span style="color:#888;padding:0 10px;" id="img-counter">1/1</span>
            <button class="tool-btn" onclick="nextImage(event)">Suiv</button>
            <div style="flex:1"></div>
            <button class="tool-btn" onclick="closeModal()" style="background:#600;">Fermer</button>
        </div>
        <div class="modal-viewer" id="modal-viewer">
            <canvas id="dicom-canvas"></canvas>
            <canvas id="measure-canvas"></canvas>
            <div class="wl-indicator" id="wl-indicator">W: 256 L: 128</div>
            <span class="nav prev" onclick="prevImage(event)">&lt;</span>
            <span class="nav next" onclick="nextImage(event)">&gt;</span>
            <div class="dicom-info" id="dicom-info"></div>
            <div id="measure-labels"></div>
        </div>
    </div>

    <script>
        let patients = [];
        let currentImages = [];
        let currentIndex = 0;
        let currentPatient = null;
        let currentStudy = null;

        // Image manipulation state
        let currentTool = 'wl';
        let windowWidth = 256, windowCenter = 128;
        let zoomLevel = 1, panX = 0, panY = 0;
        let isInverted = false;
        let originalImageData = null;
        let loadedImage = null;

        // Measurement state
        let measurements = [];
        let measurePoints = [];
        let pixelSpacing = 0.07; // mm per pixel - calibré pour GE Logiq P9

        // Mouse state
        let isDragging = false;
        let lastX = 0, lastY = 0;

        // Canvas refs
        const canvas = document.getElementById('dicom-canvas');
        const ctx = canvas.getContext('2d');
        const measureCanvas = document.getElementById('measure-canvas');
        const measureCtx = measureCanvas.getContext('2d');

        async function loadPatients() {
            const resp = await fetch('/api/patients');
            patients = await resp.json();
            renderPatients();
            document.getElementById('stats').textContent = patients.length + ' patient(s)';
        }

        function renderPatients() {
            const search = document.getElementById('search').value.toLowerCase();
            const filtered = patients.filter(p =>
                p.name.toLowerCase().includes(search) ||
                p.id.toLowerCase().includes(search)
            );

            const html = filtered.map(p => {
            const pPath = p.path.replace(/\\\\/g, '/');
            return `
                <div class="patient-card ${currentPatient === p.path ? 'active' : ''}" onclick="selectPatient('${pPath}')">
                    <div class="patient-name">${p.name}</div>
                    <div class="patient-info">${p.studies.length} examen(s)</div>
                    <div class="study-list">
                        ${p.studies.map(s => {
                            const sPath = s.path.replace(/\\\\/g, '/');
                            return `
                            <div class="study-item ${currentStudy === s.path ? 'active' : ''}"
                                 onclick="event.stopPropagation(); selectStudy('${pPath}', '${sPath}')">
                                ${s.date} (${s.count} images)
                            </div>
                        `}).join('')}
                    </div>
                </div>
            `}).join('');

            document.getElementById('patients-list').innerHTML = html || '<div class="empty-state">Aucun patient</div>';
        }

        function filterPatients() { renderPatients(); }

        async function selectPatient(path) {
            currentPatient = path;
            const patient = patients.find(p => p.path === path);
            if (patient && patient.studies.length > 0) {
                selectStudy(path, patient.studies[0].path);
            }
            renderPatients();
        }

        async function selectStudy(patientPath, studyPath) {
            currentPatient = patientPath;
            currentStudy = studyPath;
            renderPatients();

            const resp = await fetch(`/api/images?path=${encodeURIComponent(studyPath)}`);
            currentImages = await resp.json();

            const html = currentImages.map((img, i) => `
                <div class="image-card" onclick="openModal(${i})">
                    <img src="/api/thumbnail?path=${encodeURIComponent(img.path)}" loading="lazy">
                    <div class="info">${img.filename}</div>
                </div>
            `).join('');

            document.getElementById('content').innerHTML =
                currentImages.length > 0
                    ? `<div class="images-grid">${html}</div>`
                    : '<div class="empty-state"><h2>Aucune image</h2></div>';
        }

        function openModal(index) {
            currentIndex = index;
            document.getElementById('modal').classList.add('active');
            loadImageToCanvas();
        }

        function closeModal(event) {
            if (!event || event.target.id === 'modal' || event.target.classList.contains('close')) {
                document.getElementById('modal').classList.remove('active');
            }
        }

        function loadImageToCanvas() {
            const img = currentImages[currentIndex];
            const image = new Image();
            image.onload = () => {
                loadedImage = image;
                canvas.width = image.width;
                canvas.height = image.height;
                ctx.drawImage(image, 0, 0);
                originalImageData = ctx.getImageData(0, 0, image.width, image.height);

                // Reset view for new image
                windowWidth = 256; windowCenter = 128;
                zoomLevel = 1; panX = 0; panY = 0;
                isInverted = false;
                measurements = [];
                measurePoints = [];

                // Use pixel spacing from DICOM if available
                if (img.pixel_spacing) {
                    pixelSpacing = img.pixel_spacing;
                    document.getElementById('pixel-spacing-input').value = pixelSpacing.toFixed(2);
                } else {
                    pixelSpacing = 0.07; // Calibré pour GE Logiq P9
                    document.getElementById('pixel-spacing-input').value = '0.07';
                }

                applyWindowLevel();
                updateMeasureCanvas();
                updateInfo(img);
            };
            image.src = `/api/image?path=${encodeURIComponent(img.path)}`;
        }

        function updateInfo(img) {
            document.getElementById('img-counter').textContent = `${currentIndex + 1}/${currentImages.length}`;
            document.getElementById('dicom-info').innerHTML = `
                <div><span class="label">Patient:</span> ${img.patient_name || 'N/A'}</div>
                <div><span class="label">Date:</span> ${img.study_date || 'N/A'}</div>
                <div><span class="label">Modalite:</span> ${img.modality || 'N/A'}</div>
                <div><span class="label">Image:</span> ${currentIndex + 1} / ${currentImages.length}</div>
            `;
        }

        function applyWindowLevel() {
            if (!originalImageData) return;
            const data = new Uint8ClampedArray(originalImageData.data);
            const low = windowCenter - windowWidth / 2;
            const high = windowCenter + windowWidth / 2;

            for (let i = 0; i < data.length; i += 4) {
                let val = data[i];
                if (val <= low) val = 0;
                else if (val >= high) val = 255;
                else val = ((val - low) / windowWidth) * 255;
                if (isInverted) val = 255 - val;
                data[i] = data[i+1] = data[i+2] = val;
            }

            const newImageData = new ImageData(data, originalImageData.width, originalImageData.height);
            ctx.putImageData(newImageData, 0, 0);
            updateCanvasTransform();
        }

        function updateCanvasTransform() {
            canvas.style.transform = `translate(${panX}px, ${panY}px) scale(${zoomLevel})`;
        }

        function setTool(tool) {
            currentTool = tool;
            measurePoints = [];
            document.querySelectorAll('.tool-btn').forEach(b => b.classList.remove('active'));
            document.getElementById('btn-' + tool)?.classList.add('active');
        }

        function resetView() {
            windowWidth = 256; windowCenter = 128;
            zoomLevel = 1; panX = 0; panY = 0;
            isInverted = false;
            applyWindowLevel();
        }

        function invertImage() {
            isInverted = !isInverted;
            applyWindowLevel();
        }

        function clearMeasures() {
            measurements = [];
            measurePoints = [];
            updateMeasureCanvas();
        }

        function updatePixelSpacing() {
            const val = parseFloat(document.getElementById('pixel-spacing-input').value);
            if (val > 0) {
                pixelSpacing = val;
                // Recalculate existing measurements
                measurements.forEach(m => {
                    if (m.type === 'length') {
                        const dx = (m.points[1].x - m.points[0].x) * pixelSpacing;
                        const dy = (m.points[1].y - m.points[0].y) * pixelSpacing;
                        m.value = Math.sqrt(dx*dx + dy*dy).toFixed(1) + ' mm';
                    }
                });
                updateMeasureCanvas();
            }
        }

        function prevImage(event) {
            if (event) event.stopPropagation();
            currentIndex = (currentIndex - 1 + currentImages.length) % currentImages.length;
            loadImageToCanvas();
        }

        function nextImage(event) {
            if (event) event.stopPropagation();
            currentIndex = (currentIndex + 1) % currentImages.length;
            loadImageToCanvas();
        }

        // Mouse events for modal viewer
        const viewer = document.getElementById('modal-viewer');

        viewer.addEventListener('mousedown', (e) => {
            if (e.target.tagName === 'BUTTON' || e.target.classList.contains('nav')) return;
            isDragging = true;
            lastX = e.clientX;
            lastY = e.clientY;

            if (currentTool === 'length' || currentTool === 'angle') {
                // Coordonnées écran relatives au viewer (pour affichage)
                const viewerRect = viewer.getBoundingClientRect();
                const screenX = e.clientX - viewerRect.left;
                const screenY = e.clientY - viewerRect.top;

                // Coordonnées image (pour calcul distance)
                const canvasRect = canvas.getBoundingClientRect();
                const scaleX = canvas.width / canvasRect.width;
                const scaleY = canvas.height / canvasRect.height;
                const imgX = (e.clientX - canvasRect.left) * scaleX;
                const imgY = (e.clientY - canvasRect.top) * scaleY;

                measurePoints.push({screenX, screenY, imgX, imgY});

                if (currentTool === 'length' && measurePoints.length === 2) {
                    const dx = (measurePoints[1].imgX - measurePoints[0].imgX) * pixelSpacing;
                    const dy = (measurePoints[1].imgY - measurePoints[0].imgY) * pixelSpacing;
                    const dist = Math.sqrt(dx*dx + dy*dy);
                    measurements.push({type: 'length', points: [...measurePoints], value: dist.toFixed(1) + ' mm'});
                    measurePoints = [];
                }
                else if (currentTool === 'angle' && measurePoints.length === 3) {
                    const p1 = measurePoints[0], p2 = measurePoints[1], p3 = measurePoints[2];
                    const a1 = Math.atan2(p1.imgY - p2.imgY, p1.imgX - p2.imgX);
                    const a2 = Math.atan2(p3.imgY - p2.imgY, p3.imgX - p2.imgX);
                    let angle = Math.abs(a1 - a2) * 180 / Math.PI;
                    if (angle > 180) angle = 360 - angle;
                    measurements.push({type: 'angle', points: [...measurePoints], value: angle.toFixed(1) + ' deg'});
                    measurePoints = [];
                }
                updateMeasureCanvas();
            }

            if (currentTool === 'wl') {
                document.getElementById('wl-indicator').style.display = 'block';
            }
        });

        viewer.addEventListener('mousemove', (e) => {
            if (!isDragging) return;
            const dx = e.clientX - lastX;
            const dy = e.clientY - lastY;

            if (currentTool === 'wl') {
                windowWidth = Math.max(1, windowWidth + dx * 2);
                windowCenter = Math.max(0, Math.min(255, windowCenter + dy));
                document.getElementById('wl-indicator').textContent = `W: ${Math.round(windowWidth)} L: ${Math.round(windowCenter)}`;
                applyWindowLevel();
            } else if (currentTool === 'pan') {
                panX += dx;
                panY += dy;
                updateCanvasTransform();
            } else if (currentTool === 'zoom') {
                zoomLevel = Math.max(0.1, Math.min(10, zoomLevel - dy * 0.01));
                updateCanvasTransform();
            }

            lastX = e.clientX;
            lastY = e.clientY;
        });

        viewer.addEventListener('mouseup', () => {
            isDragging = false;
            setTimeout(() => document.getElementById('wl-indicator').style.display = 'none', 800);
        });

        viewer.addEventListener('wheel', (e) => {
            e.preventDefault();
            zoomLevel = Math.max(0.1, Math.min(10, zoomLevel - e.deltaY * 0.001));
            updateCanvasTransform();
        });

        function updateMeasureCanvas() {
            measureCanvas.width = viewer.clientWidth;
            measureCanvas.height = viewer.clientHeight;
            measureCtx.clearRect(0, 0, measureCanvas.width, measureCanvas.height);
            document.getElementById('measure-labels').innerHTML = '';

            // Draw completed measurements - utiliser directement les coordonnées écran
            measurements.forEach(m => {
                measureCtx.strokeStyle = '#0f0';
                measureCtx.lineWidth = 2;

                if (m.type === 'length') {
                    const x1 = m.points[0].screenX;
                    const y1 = m.points[0].screenY;
                    const x2 = m.points[1].screenX;
                    const y2 = m.points[1].screenY;
                    measureCtx.beginPath();
                    measureCtx.moveTo(x1, y1);
                    measureCtx.lineTo(x2, y2);
                    measureCtx.stroke();
                    drawPoint(x1, y1); drawPoint(x2, y2);
                    addLabel((x1+x2)/2, (y1+y2)/2, m.value);
                }
                else if (m.type === 'angle') {
                    measureCtx.beginPath();
                    measureCtx.moveTo(m.points[0].screenX, m.points[0].screenY);
                    measureCtx.lineTo(m.points[1].screenX, m.points[1].screenY);
                    measureCtx.lineTo(m.points[2].screenX, m.points[2].screenY);
                    measureCtx.stroke();
                    m.points.forEach(p => drawPoint(p.screenX, p.screenY));
                    addLabel(m.points[1].screenX, m.points[1].screenY - 20, m.value);
                }
            });

            // Draw points in progress
            measureCtx.strokeStyle = '#ff0';
            measureCtx.setLineDash([5, 5]);
            measurePoints.forEach((p, i) => {
                drawPoint(p.screenX, p.screenY, '#ff0');
                if (i > 0) {
                    const prev = measurePoints[i-1];
                    measureCtx.beginPath();
                    measureCtx.moveTo(prev.screenX, prev.screenY);
                    measureCtx.lineTo(p.screenX, p.screenY);
                    measureCtx.stroke();
                }
            });
            measureCtx.setLineDash([]);
        }

        function drawPoint(x, y, color = '#0f0') {
            measureCtx.fillStyle = color;
            measureCtx.beginPath();
            measureCtx.arc(x, y, 4, 0, Math.PI * 2);
            measureCtx.fill();
        }

        function addLabel(x, y, text) {
            const label = document.createElement('div');
            label.className = 'measure-label';
            label.textContent = text;
            label.style.left = (x + 10) + 'px';
            label.style.top = (y - 10) + 'px';
            document.getElementById('measure-labels').appendChild(label);
        }

        document.addEventListener('keydown', (e) => {
            if (document.getElementById('modal').classList.contains('active')) {
                if (e.key === 'Escape') closeModal();
                if (e.key === 'ArrowLeft') prevImage(e);
                if (e.key === 'ArrowRight') nextImage(e);
                if (e.key === 'r') resetView();
                if (e.key === 'i') invertImage();
            }
        });

        loadPatients();
    </script>
</body>
</html>
"""


def get_dicom_info(filepath):
    """Extrait les métadonnées d'un fichier DICOM"""
    try:
        ds = dcmread(filepath, stop_before_pixels=True, force=True)

        # Récupérer le PixelSpacing (mm par pixel)
        pixel_spacing = None
        if hasattr(ds, 'PixelSpacing') and ds.PixelSpacing:
            pixel_spacing = float(ds.PixelSpacing[0])
        elif hasattr(ds, 'ImagerPixelSpacing') and ds.ImagerPixelSpacing:
            pixel_spacing = float(ds.ImagerPixelSpacing[0])
        elif hasattr(ds, 'SequenceOfUltrasoundRegions'):
            # Pour les images d'échographie
            for region in ds.SequenceOfUltrasoundRegions:
                if hasattr(region, 'PhysicalDeltaX'):
                    pixel_spacing = float(region.PhysicalDeltaX) * 10  # cm to mm
                    break

        return {
            'patient_name': str(getattr(ds, 'PatientName', 'N/A')),
            'patient_id': str(getattr(ds, 'PatientID', 'N/A')),
            'study_date': str(getattr(ds, 'StudyDate', 'N/A')),
            'modality': str(getattr(ds, 'Modality', 'N/A')),
            'description': str(getattr(ds, 'SeriesDescription', getattr(ds, 'StudyDescription', 'N/A'))),
            'pixel_spacing': pixel_spacing,
        }
    except:
        return {}


def dicom_to_png(filepath):
    """Convertit un fichier DICOM en PNG"""
    try:
        import numpy as np
        from PIL import Image

        ds = dcmread(filepath, force=True)
        pixel_array = ds.pixel_array

        # Normaliser en 8-bit
        if pixel_array.dtype != np.uint8:
            pixel_min = pixel_array.min()
            pixel_max = pixel_array.max()
            if pixel_max > pixel_min:
                pixel_array = ((pixel_array - pixel_min) / (pixel_max - pixel_min) * 255).astype(np.uint8)
            else:
                pixel_array = np.zeros_like(pixel_array, dtype=np.uint8)

        # Créer l'image
        if len(pixel_array.shape) == 2:
            img = Image.fromarray(pixel_array, mode='L')
        else:
            img = Image.fromarray(pixel_array)

        # Sauvegarder en mémoire
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        return buffer
    except Exception as e:
        print(f"Error converting {filepath}: {e}")
        return None


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/api/patients')
def api_patients():
    """Liste tous les patients et leurs examens"""
    patients = []

    if not ARCHIVE_PATH.exists():
        return jsonify([])

    for patient_dir in sorted(ARCHIVE_PATH.iterdir()):
        if not patient_dir.is_dir():
            continue

        # Parser le nom du dossier patient
        name = patient_dir.name.replace('_', ' ').replace('^', ' ')

        studies = []
        for study_dir in sorted(patient_dir.iterdir(), reverse=True):
            if not study_dir.is_dir():
                continue

            # Compter les fichiers DICOM (recherche récursive dans sous-dossiers)
            dcm_files = list(study_dir.glob('**/*.dcm'))
            png_files = list(study_dir.glob('**/*.png'))
            count = len(dcm_files) + len(png_files)

            if count > 0:
                studies.append({
                    'date': study_dir.name,
                    'path': str(study_dir),
                    'count': count
                })

        if studies:
            patients.append({
                'name': name,
                'id': patient_dir.name,
                'path': str(patient_dir),
                'studies': studies
            })

    return jsonify(patients)


@app.route('/api/images')
def api_images():
    """Liste les images d'un examen"""
    path = request.args.get('path', '')
    study_dir = Path(path)

    if not study_dir.exists():
        return jsonify([])

    images = []
    # Recherche récursive dans les sous-dossiers
    for f in sorted(study_dir.glob('**/*')):
        if f.is_file() and f.suffix.lower() in ['.dcm', '.png', '.jpg', '.jpeg']:
            info = get_dicom_info(f) if f.suffix.lower() == '.dcm' else {}
            images.append({
                'filename': f.name,
                'path': str(f),
                **info
            })

    return jsonify(images)


@app.route('/api/thumbnail')
def api_thumbnail():
    """Génère une miniature d'une image"""
    path = request.args.get('path', '')
    filepath = Path(path)

    if not filepath.exists():
        return '', 404

    if filepath.suffix.lower() == '.dcm':
        buffer = dicom_to_png(filepath)
        if buffer:
            return send_file(buffer, mimetype='image/png')
        return '', 404
    else:
        return send_file(filepath)


@app.route('/api/image')
def api_image():
    """Retourne une image en taille réelle"""
    path = request.args.get('path', '')
    filepath = Path(path)

    if not filepath.exists():
        return '', 404

    if filepath.suffix.lower() == '.dcm':
        buffer = dicom_to_png(filepath)
        if buffer:
            return send_file(buffer, mimetype='image/png')
        return '', 404
    else:
        return send_file(filepath)


def run_viewer(host='0.0.0.0', port=8080, archive_path=None):
    """Lance le serveur web du viewer"""
    global ARCHIVE_PATH
    if archive_path:
        ARCHIVE_PATH = Path(archive_path)

    print(f"\n{'='*50}")
    print("  DICOM VIEWER - Interface Web")
    print(f"{'='*50}")
    print(f"\n  URL: http://localhost:{port}")
    print(f"  Archive: {ARCHIVE_PATH}")
    print(f"\n  Ouvrez votre navigateur sur http://localhost:{port}")
    print(f"{'='*50}\n")

    app.run(host=host, port=port, debug=False, threaded=True)


if __name__ == '__main__':
    run_viewer()
