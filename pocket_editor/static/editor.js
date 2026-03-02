const canvas = document.getElementById('editor-canvas');
const ctx = canvas.getContext('2d');

let controlPoints = [];
let defaultControlPoints = [];
let frontBounds = null;
let draggingIndex = -1;
let canvasScale = 1;
let canvasOffsetX = 0;
let canvasOffsetY = 0;

const POINT_RADIUS = 7;
const HANDLE_RADIUS = 5;

function toCanvas(worldX, worldY) {
    return [
        (worldX - canvasOffsetX) * canvasScale,
        canvas.height - (worldY - canvasOffsetY) * canvasScale
    ];
}

function toWorld(canvasX, canvasY) {
    return [
        canvasX / canvasScale + canvasOffsetX,
        (canvas.height - canvasY) / canvasScale + canvasOffsetY
    ];
}

function computeTransform() {
    if (controlPoints.length < 4) return;

    let allX = controlPoints.map(p => p[0]);
    let allY = controlPoints.map(p => p[1]);

    if (frontBounds) {
        allX.push(frontBounds.pt1[0], frontBounds.pt7[0]);
        allY.push(frontBounds.pt1[1], frontBounds.pt7[1]);
    }

    const minX = Math.min(...allX);
    const maxX = Math.max(...allX);
    const minY = Math.min(...allY);
    const maxY = Math.max(...allY);

    const padding = 2;
    const rangeX = (maxX - minX) + padding * 2;
    const rangeY = (maxY - minY) + padding * 2;

    canvasScale = Math.min(canvas.width / rangeX, canvas.height / rangeY);
    canvasOffsetX = minX - padding - (canvas.width / canvasScale - rangeX) / 2;
    canvasOffsetY = minY - padding - (canvas.height / canvasScale - rangeY) / 2;
}

function evaluateBezier(p0, p1, p2, p3, steps) {
    const points = [];
    for (let i = 0; i <= steps; i++) {
        const t = i / steps;
        const mt = 1 - t;
        const x = mt*mt*mt*p0[0] + 3*mt*mt*t*p1[0] + 3*mt*t*t*p2[0] + t*t*t*p3[0];
        const y = mt*mt*mt*p0[1] + 3*mt*mt*t*p1[1] + 3*mt*t*t*p2[1] + t*t*t*p3[1];
        points.push([x, y]);
    }
    return points;
}

function curveLength(points) {
    let len = 0;
    for (let i = 1; i < points.length; i++) {
        const dx = points[i][0] - points[i-1][0];
        const dy = points[i][1] - points[i-1][1];
        len += Math.sqrt(dx*dx + dy*dy);
    }
    return len;
}

function drawGrid() {
    ctx.save();
    ctx.strokeStyle = '#e8e8e8';
    ctx.lineWidth = 0.5;

    const INCH = 2.54;
    const step = INCH;

    const topLeft = toWorld(0, 0);
    const bottomRight = toWorld(canvas.width, canvas.height);
    const startX = Math.floor(Math.min(topLeft[0], bottomRight[0]) / step) * step;
    const endX = Math.ceil(Math.max(topLeft[0], bottomRight[0]) / step) * step;
    const startY = Math.floor(Math.min(topLeft[1], bottomRight[1]) / step) * step;
    const endY = Math.ceil(Math.max(topLeft[1], bottomRight[1]) / step) * step;

    for (let x = startX; x <= endX; x += step) {
        const [cx] = toCanvas(x, 0);
        ctx.beginPath();
        ctx.moveTo(cx, 0);
        ctx.lineTo(cx, canvas.height);
        ctx.stroke();
    }
    for (let y = startY; y <= endY; y += step) {
        const [, cy] = toCanvas(0, y);
        ctx.beginPath();
        ctx.moveTo(0, cy);
        ctx.lineTo(canvas.width, cy);
        ctx.stroke();
    }

    ctx.strokeStyle = '#d0d0d0';
    ctx.lineWidth = 1;
    const majorStep = step * 5;
    for (let x = Math.floor(startX / majorStep) * majorStep; x <= endX; x += majorStep) {
        const [cx] = toCanvas(x, 0);
        ctx.beginPath();
        ctx.moveTo(cx, 0);
        ctx.lineTo(cx, canvas.height);
        ctx.stroke();
    }
    for (let y = Math.floor(startY / majorStep) * majorStep; y <= endY; y += majorStep) {
        const [, cy] = toCanvas(0, y);
        ctx.beginPath();
        ctx.moveTo(0, cy);
        ctx.lineTo(canvas.width, cy);
        ctx.stroke();
    }

    ctx.restore();
}

function drawReferenceGeometry() {
    if (!frontBounds) return;

    ctx.save();
    ctx.strokeStyle = '#ccc';
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 4]);

    const pt1 = toCanvas(frontBounds.pt1[0], frontBounds.pt1[1]);
    const pt7 = toCanvas(frontBounds.pt7[0], frontBounds.pt7[1]);
    ctx.beginPath();
    ctx.moveTo(pt1[0], pt1[1]);
    ctx.lineTo(pt7[0], pt7[1]);
    ctx.stroke();

    ctx.setLineDash([]);
    ctx.fillStyle = '#999';
    ctx.font = '10px sans-serif';
    ctx.fillText('waist', pt7[0] + 4, pt7[1] - 4);
    ctx.fillText('outseam corner', pt1[0] - 10, pt1[1] + 14);

    ctx.restore();
}

function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (controlPoints.length < 4) return;

    computeTransform();
    drawGrid();
    drawReferenceGeometry();

    const [p0, p1, p2, p3] = controlPoints;
    const curvePoints = evaluateBezier(p0, p1, p2, p3, 100);

    ctx.save();
    ctx.strokeStyle = '#1a1a2e';
    ctx.lineWidth = 2.5;
    ctx.beginPath();
    const start = toCanvas(curvePoints[0][0], curvePoints[0][1]);
    ctx.moveTo(start[0], start[1]);
    for (let i = 1; i < curvePoints.length; i++) {
        const pt = toCanvas(curvePoints[i][0], curvePoints[i][1]);
        ctx.lineTo(pt[0], pt[1]);
    }
    ctx.stroke();
    ctx.restore();

    ctx.save();
    ctx.strokeStyle = '#c9a96e';
    ctx.lineWidth = 1;
    ctx.setLineDash([3, 3]);

    const cp0 = toCanvas(p0[0], p0[1]);
    const cp1 = toCanvas(p1[0], p1[1]);
    ctx.beginPath();
    ctx.moveTo(cp0[0], cp0[1]);
    ctx.lineTo(cp1[0], cp1[1]);
    ctx.stroke();

    const cp2 = toCanvas(p2[0], p2[1]);
    const cp3 = toCanvas(p3[0], p3[1]);
    ctx.beginPath();
    ctx.moveTo(cp3[0], cp3[1]);
    ctx.lineTo(cp2[0], cp2[1]);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.restore();

    const labels = ['P0 (upper)', 'P1 (handle)', 'P2 (handle)', 'P3 (lower)'];
    controlPoints.forEach((pt, i) => {
        const [cx, cy] = toCanvas(pt[0], pt[1]);
        const isEndpoint = (i === 0 || i === 3);

        ctx.save();
        if (isEndpoint) {
            ctx.fillStyle = '#1a1a2e';
            ctx.fillRect(cx - POINT_RADIUS, cy - POINT_RADIUS, POINT_RADIUS * 2, POINT_RADIUS * 2);
        } else {
            ctx.fillStyle = '#c9a96e';
            ctx.beginPath();
            ctx.arc(cx, cy, HANDLE_RADIUS, 0, Math.PI * 2);
            ctx.fill();
            ctx.strokeStyle = '#8a7a4e';
            ctx.lineWidth = 1.5;
            ctx.stroke();
        }

        ctx.fillStyle = '#666';
        ctx.font = '10px sans-serif';
        ctx.fillText(labels[i], cx + 10, cy - 6);
        ctx.restore();
    });

    updateInfo(curvePoints);
}

function updateInfo(curvePoints) {
    const INCH = 2.54;
    const len = curveLength(curvePoints);
    const units = document.getElementById('units-select').value;
    const factor = units === 'inch' ? 1 / INCH : 1;
    const label = units === 'inch' ? '"' : ' cm';

    document.getElementById('curve-length').textContent = (len * factor).toFixed(2) + label;

    const xs = curvePoints.map(p => p[0]);
    const ys = curvePoints.map(p => p[1]);
    const w = (Math.max(...xs) - Math.min(...xs)) * factor;
    const h = (Math.max(...ys) - Math.min(...ys)) * factor;
    document.getElementById('curve-width').textContent = w.toFixed(2) + label;
    document.getElementById('curve-height').textContent = h.toFixed(2) + label;
}

function getMousePos(e) {
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    return [
        (e.clientX - rect.left) * scaleX,
        (e.clientY - rect.top) * scaleY
    ];
}

function findClosestPoint(mx, my) {
    let minDist = Infinity;
    let idx = -1;
    controlPoints.forEach((pt, i) => {
        const [cx, cy] = toCanvas(pt[0], pt[1]);
        const dist = Math.sqrt((mx - cx) ** 2 + (my - cy) ** 2);
        if (dist < minDist) {
            minDist = dist;
            idx = i;
        }
    });
    return minDist < 20 ? idx : -1;
}

canvas.addEventListener('mousedown', (e) => {
    const [mx, my] = getMousePos(e);
    draggingIndex = findClosestPoint(mx, my);
    if (draggingIndex >= 0) {
        canvas.style.cursor = 'grabbing';
    }
});

canvas.addEventListener('mousemove', (e) => {
    const [mx, my] = getMousePos(e);
    if (draggingIndex >= 0) {
        const [wx, wy] = toWorld(mx, my);
        controlPoints[draggingIndex] = [wx, wy];
        draw();
    } else {
        const idx = findClosestPoint(mx, my);
        canvas.style.cursor = idx >= 0 ? 'grab' : 'crosshair';
    }
});

canvas.addEventListener('mouseup', () => {
    draggingIndex = -1;
    canvas.style.cursor = 'crosshair';
});

canvas.addEventListener('mouseleave', () => {
    draggingIndex = -1;
    canvas.style.cursor = 'crosshair';
});

canvas.addEventListener('touchstart', (e) => {
    e.preventDefault();
    const touch = e.touches[0];
    const [mx, my] = getMousePos(touch);
    draggingIndex = findClosestPoint(mx, my);
});

canvas.addEventListener('touchmove', (e) => {
    e.preventDefault();
    if (draggingIndex >= 0) {
        const touch = e.touches[0];
        const [mx, my] = getMousePos(touch);
        const [wx, wy] = toWorld(mx, my);
        controlPoints[draggingIndex] = [wx, wy];
        draw();
    }
});

canvas.addEventListener('touchend', (e) => {
    e.preventDefault();
    draggingIndex = -1;
});

async function loadDefaultShape() {
    const mfile = document.getElementById('measurements-select').value;
    try {
        const resp = await fetch(`/api/default-shape?measurements=${encodeURIComponent(mfile)}`);
        const data = await resp.json();
        if (data.error) {
            console.error('Error loading shape:', data.error);
            return;
        }
        controlPoints = data.control_points.map(p => [...p]);
        defaultControlPoints = data.control_points.map(p => [...p]);
        frontBounds = data.front_bounds;
        draw();
    } catch (err) {
        console.error('Failed to load default shape:', err);
    }
}

document.getElementById('reset-btn').addEventListener('click', () => {
    controlPoints = defaultControlPoints.map(p => [...p]);
    draw();
});

document.getElementById('measurements-select').addEventListener('change', () => {
    loadDefaultShape();
});

document.getElementById('units-select').addEventListener('change', () => {
    draw();
});

document.getElementById('generate-btn').addEventListener('click', async () => {
    const container = document.getElementById('pieces-container');
    const loading = document.getElementById('loading-indicator');

    loading.classList.remove('hidden');
    container.innerHTML = '';

    const mfile = document.getElementById('measurements-select').value;
    const units = document.getElementById('units-select').value;

    try {
        const resp = await fetch('/api/generate', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                control_points: controlPoints,
                measurements: mfile,
                units: units,
            }),
        });
        const data = await resp.json();
        loading.classList.add('hidden');

        if (data.error) {
            container.innerHTML = `<div class="error-msg">${data.error}</div>`;
            return;
        }

        const pieces = [
            { key: 'pocket_bag', title: 'Pocket Bag (Cut-on-fold)' },
            { key: 'facing', title: 'Front Facing' },
            { key: 'watch_pocket', title: 'Watch Pocket' },
        ];

        pieces.forEach(({ key, title }) => {
            if (data[key]) {
                const card = document.createElement('div');
                card.className = 'piece-card';
                card.innerHTML = `
                    <h3>${title}</h3>
                    <div class="piece-svg">${data[key]}</div>
                `;
                container.appendChild(card);
            } else if (data[key + '_error']) {
                const card = document.createElement('div');
                card.className = 'error-msg';
                card.textContent = `${title}: ${data[key + '_error']}`;
                container.appendChild(card);
            }
        });

        if (container.children.length === 0) {
            container.innerHTML = '<div class="piece-placeholder">No pieces generated.</div>';
        }
    } catch (err) {
        loading.classList.add('hidden');
        container.innerHTML = `<div class="error-msg">Request failed: ${err.message}</div>`;
    }
});

loadDefaultShape();
