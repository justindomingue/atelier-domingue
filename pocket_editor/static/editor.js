const canvas = document.getElementById('editor-canvas');
const ctx = canvas.getContext('2d');

let controlPoints = [];
let defaultControlPoints = [];
let frontPanel = null;
let watchOutline = null;
let panelBounds = null;
let draggingIndex = -1;
let scale = 1;
let offsetRX = 0;
let offsetRY = 0;

function resize() {
    const area = canvas.parentElement;
    const dpr = window.devicePixelRatio || 1;
    canvas.width = area.clientWidth * dpr;
    canvas.height = area.clientHeight * dpr;
    canvas.style.width = area.clientWidth + 'px';
    canvas.style.height = area.clientHeight + 'px';
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    computeTransform();
    draw();
}

window.addEventListener('resize', resize);

function worldToRotated(wx, wy) {
    return [wy, -wx];
}

function rotatedToWorld(rx, ry) {
    return [-ry, rx];
}

function toCanvas(wx, wy) {
    const [rx, ry] = worldToRotated(wx, wy);
    const dpr = window.devicePixelRatio || 1;
    return [
        (rx - offsetRX) * scale,
        (canvas.height / dpr) - (ry - offsetRY) * scale
    ];
}

function toWorld(cx, cy) {
    const dpr = window.devicePixelRatio || 1;
    const rx = cx / scale + offsetRX;
    const ry = ((canvas.height / dpr) - cy) / scale + offsetRY;
    return rotatedToWorld(rx, ry);
}

function buildPanelBounds() {
    if (!frontPanel) return;
    const fp = frontPanel;
    const poly = [];
    poly.push(fp.pt1);
    for (let i = 0; i < fp.hip.length; i++) poly.push(fp.hip[i]);
    for (let i = 0; i < fp.crotch.length; i++) poly.push(fp.crotch[i]);
    for (let i = 0; i < fp.inseam.length; i++) poly.push(fp.inseam[i]);
    poly.push(fp.pt0);
    poly.push(fp.pt9);
    for (let i = fp.rise.length - 1; i >= 0; i--) poly.push(fp.rise[i]);
    poly.push(fp.pt7);
    panelBounds = poly;
}

function pointInPolygon(x, y, poly) {
    let inside = false;
    for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
        const xi = poly[i][0], yi = poly[i][1];
        const xj = poly[j][0], yj = poly[j][1];
        if (((yi > y) !== (yj > y)) && (x < (xj - xi) * (y - yi) / (yj - yi) + xi)) {
            inside = !inside;
        }
    }
    return inside;
}

function clampToPanel(wx, wy) {
    if (!panelBounds || pointInPolygon(wx, wy, panelBounds)) return [wx, wy];

    let bestX = wx, bestY = wy, bestDist = Infinity;
    for (let i = 0, j = panelBounds.length - 1; i < panelBounds.length; j = i++) {
        const ax = panelBounds[j][0], ay = panelBounds[j][1];
        const bx = panelBounds[i][0], by = panelBounds[i][1];
        const dx = bx - ax, dy = by - ay;
        const len2 = dx * dx + dy * dy;
        if (len2 === 0) continue;
        let t = ((wx - ax) * dx + (wy - ay) * dy) / len2;
        t = Math.max(0, Math.min(1, t));
        const px = ax + t * dx, py = ay + t * dy;
        const d = (wx - px) ** 2 + (wy - py) ** 2;
        if (d < bestDist) { bestDist = d; bestX = px; bestY = py; }
    }
    return [bestX, bestY];
}

function computeTransform() {
    if (!frontPanel) return;
    const dpr = window.devicePixelRatio || 1;
    const w = canvas.width / dpr;
    const h = canvas.height / dpr;

    let allRX = [], allRY = [];
    const addPt = (p) => {
        const [rx, ry] = worldToRotated(p[0], p[1]);
        allRX.push(rx); allRY.push(ry);
    };
    const addCurve = (c) => c.forEach(addPt);

    addPt(frontPanel.pt1);
    addPt(frontPanel.pt7);
    addPt(frontPanel.pt0);
    addPt(frontPanel.pt9);
    addPt(frontPanel.pt10);
    addCurve(frontPanel.hip);
    addCurve(frontPanel.rise);
    addCurve(frontPanel.crotch);
    addCurve(frontPanel.inseam);

    const pad = 3;
    const minRX = Math.min(...allRX) - pad;
    const maxRX = Math.max(...allRX) + pad;
    const minRY = Math.min(...allRY) - pad;
    const maxRY = Math.max(...allRY) + pad;

    const rangeX = maxRX - minRX;
    const rangeY = maxRY - minRY;

    scale = Math.min(w / rangeX, h / rangeY);
    offsetRX = minRX - (w / scale - rangeX) / 2;
    offsetRY = minRY - (h / scale - rangeY) / 2;
}

function drawCurve(points, color, width, dash) {
    if (!points || points.length < 2) return;
    ctx.save();
    ctx.strokeStyle = color;
    ctx.lineWidth = width;
    if (dash) ctx.setLineDash(dash);
    ctx.beginPath();
    const [sx, sy] = toCanvas(points[0][0], points[0][1]);
    ctx.moveTo(sx, sy);
    for (let i = 1; i < points.length; i++) {
        const [px, py] = toCanvas(points[i][0], points[i][1]);
        ctx.lineTo(px, py);
    }
    ctx.stroke();
    ctx.restore();
}

function drawClosedShape(points, fill, stroke, width) {
    if (!points || points.length < 3) return;
    ctx.save();
    ctx.beginPath();
    const [sx, sy] = toCanvas(points[0][0], points[0][1]);
    ctx.moveTo(sx, sy);
    for (let i = 1; i < points.length; i++) {
        const [px, py] = toCanvas(points[i][0], points[i][1]);
        ctx.lineTo(px, py);
    }
    ctx.closePath();
    if (fill) { ctx.fillStyle = fill; ctx.fill(); }
    if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = width || 1; ctx.stroke(); }
    ctx.restore();
}

function evaluateBezier(p0, p1, p2, p3, steps) {
    const pts = [];
    for (let i = 0; i <= steps; i++) {
        const t = i / steps;
        const mt = 1 - t;
        pts.push([
            mt*mt*mt*p0[0] + 3*mt*mt*t*p1[0] + 3*mt*t*t*p2[0] + t*t*t*p3[0],
            mt*mt*mt*p0[1] + 3*mt*mt*t*p1[1] + 3*mt*t*t*p2[1] + t*t*t*p3[1],
        ]);
    }
    return pts;
}

function offsetCurve(points, dist) {
    const result = [];
    for (let i = 0; i < points.length; i++) {
        let nx, ny;
        if (i === 0) {
            nx = -(points[1][1] - points[0][1]);
            ny = points[1][0] - points[0][0];
        } else if (i === points.length - 1) {
            nx = -(points[i][1] - points[i-1][1]);
            ny = points[i][0] - points[i-1][0];
        } else {
            nx = -(points[i+1][1] - points[i-1][1]);
            ny = points[i+1][0] - points[i-1][0];
        }
        const len = Math.sqrt(nx * nx + ny * ny);
        if (len === 0) { result.push([...points[i]]); continue; }
        result.push([points[i][0] + (nx / len) * dist, points[i][1] + (ny / len) * dist]);
    }
    return result;
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

function drawFrontPanel() {
    if (!frontPanel) return;
    const fp = frontPanel;

    drawCurve([fp.pt1, fp.pt7], '#ccc', 1.5);
    drawCurve(fp.hip, '#aaa', 1.5);
    drawCurve(fp.rise, '#aaa', 1.5);
    drawCurve(fp.crotch, '#aaa', 1.5);
    drawCurve(fp.inseam, '#aaa', 1.5);
    drawCurve([fp.pt0, fp.pt9], '#ccc', 1.5);
    drawCurve([fp.pt10, fp.pt0], '#ddd', 1, [4, 4]);

    ctx.save();
    ctx.fillStyle = '#bbb';
    ctx.font = '10px sans-serif';
    const [wx, wy] = toCanvas(fp.pt7[0], fp.pt7[1]);
    ctx.fillText('waist', wx + 4, wy - 4);
    const [hx, hy] = toCanvas(fp.hip[fp.hip.length-1][0], fp.hip[fp.hip.length-1][1]);
    ctx.fillText('hip', hx + 4, hy - 4);
    ctx.restore();
}

function drawWatchPocket() {
    if (!watchOutline || watchOutline.length < 3) return;
    drawClosedShape(watchOutline, 'rgba(201,169,110,0.06)', 'rgba(201,169,110,0.5)', 1);
}

function drawTopstitching(curve) {
    const INCH = 2.54;
    const row1 = offsetCurve(curve, 0.15 * INCH);
    const row2 = offsetCurve(curve, 0.40 * INCH);

    [row1, row2].forEach(row => {
        ctx.save();
        ctx.strokeStyle = '#222';
        ctx.lineWidth = 0.8;
        ctx.setLineDash([3 * scale / 4, 2.5 * scale / 4]);
        ctx.beginPath();
        const [sx, sy] = toCanvas(row[0][0], row[0][1]);
        ctx.moveTo(sx, sy);
        for (let i = 1; i < row.length; i++) {
            const [px, py] = toCanvas(row[i][0], row[i][1]);
            ctx.lineTo(px, py);
        }
        ctx.stroke();
        ctx.restore();
    });
}

function draw() {
    const dpr = window.devicePixelRatio || 1;
    ctx.clearRect(0, 0, canvas.width / dpr, canvas.height / dpr);

    if (!frontPanel || controlPoints.length < 4) return;

    computeTransform();
    drawFrontPanel();
    drawWatchPocket();

    const [p0, p1, p2, p3] = controlPoints;
    const curve = evaluateBezier(p0, p1, p2, p3, 100);

    ctx.save();
    ctx.strokeStyle = '#1a1a2e';
    ctx.lineWidth = 2.5;
    ctx.beginPath();
    const [sx, sy] = toCanvas(curve[0][0], curve[0][1]);
    ctx.moveTo(sx, sy);
    for (let i = 1; i < curve.length; i++) {
        const [px, py] = toCanvas(curve[i][0], curve[i][1]);
        ctx.lineTo(px, py);
    }
    ctx.stroke();
    ctx.restore();

    drawTopstitching(curve);

    const cp0 = toCanvas(p0[0], p0[1]);
    const cp1 = toCanvas(p1[0], p1[1]);
    const cp2 = toCanvas(p2[0], p2[1]);
    const cp3 = toCanvas(p3[0], p3[1]);

    ctx.save();
    ctx.strokeStyle = '#c9a96e';
    ctx.lineWidth = 1;
    ctx.setLineDash([3, 3]);
    ctx.beginPath(); ctx.moveTo(cp0[0], cp0[1]); ctx.lineTo(cp1[0], cp1[1]); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(cp3[0], cp3[1]); ctx.lineTo(cp2[0], cp2[1]); ctx.stroke();
    ctx.setLineDash([]);
    ctx.restore();

    controlPoints.forEach((pt, i) => {
        const [cx, cy] = toCanvas(pt[0], pt[1]);
        const isEnd = (i === 0 || i === 3);
        ctx.save();
        if (isEnd) {
            ctx.fillStyle = '#1a1a2e';
            ctx.fillRect(cx - 6, cy - 6, 12, 12);
            ctx.strokeStyle = '#fff';
            ctx.lineWidth = 1.5;
            ctx.strokeRect(cx - 6, cy - 6, 12, 12);
        } else {
            ctx.beginPath();
            ctx.arc(cx, cy, 5, 0, Math.PI * 2);
            ctx.fillStyle = '#c9a96e';
            ctx.fill();
            ctx.strokeStyle = '#1a1a2e';
            ctx.lineWidth = 1.5;
            ctx.stroke();
        }
        ctx.restore();
    });

    updateInfo(curve);
}

function updateInfo(curve) {
    const INCH = 2.54;
    const units = document.getElementById('units-select').value;
    const f = units === 'inch' ? 1 / INCH : 1;
    const u = units === 'inch' ? '"' : ' cm';

    const len = curveLength(curve);
    document.getElementById('curve-length').textContent = (len * f).toFixed(1) + u;

    const xs = curve.map(p => p[0]);
    const ys = curve.map(p => p[1]);
    document.getElementById('curve-width').textContent =
        ((Math.max(...xs) - Math.min(...xs)) * f).toFixed(1) + u;
    document.getElementById('curve-height').textContent =
        ((Math.max(...ys) - Math.min(...ys)) * f).toFixed(1) + u;
}

function getMousePos(e) {
    const rect = canvas.getBoundingClientRect();
    return [e.clientX - rect.left, e.clientY - rect.top];
}

function findClosest(mx, my) {
    let best = -1, bestDist = 25;
    controlPoints.forEach((pt, i) => {
        const [cx, cy] = toCanvas(pt[0], pt[1]);
        const d = Math.sqrt((mx - cx) ** 2 + (my - cy) ** 2);
        if (d < bestDist) { bestDist = d; best = i; }
    });
    return best;
}

canvas.addEventListener('mousedown', (e) => {
    const [mx, my] = getMousePos(e);
    draggingIndex = findClosest(mx, my);
    if (draggingIndex >= 0) canvas.style.cursor = 'grabbing';
});

canvas.addEventListener('mousemove', (e) => {
    const [mx, my] = getMousePos(e);
    if (draggingIndex >= 0) {
        const [wx, wy] = toWorld(mx, my);
        controlPoints[draggingIndex] = clampToPanel(wx, wy);
        draw();
    } else {
        canvas.style.cursor = findClosest(mx, my) >= 0 ? 'grab' : 'default';
    }
});

canvas.addEventListener('mouseup', () => { draggingIndex = -1; canvas.style.cursor = 'default'; });
canvas.addEventListener('mouseleave', () => { draggingIndex = -1; });

canvas.addEventListener('touchstart', (e) => {
    e.preventDefault();
    const [mx, my] = getMousePos(e.touches[0]);
    draggingIndex = findClosest(mx, my);
});

canvas.addEventListener('touchmove', (e) => {
    e.preventDefault();
    if (draggingIndex >= 0) {
        const [mx, my] = getMousePos(e.touches[0]);
        const [wx, wy] = toWorld(mx, my);
        controlPoints[draggingIndex] = clampToPanel(wx, wy);
        draw();
    }
});

canvas.addEventListener('touchend', (e) => { e.preventDefault(); draggingIndex = -1; });

async function loadDefaultShape() {
    const mfile = document.getElementById('measurements-select').value;
    try {
        const resp = await fetch(`/api/default-shape?measurements=${encodeURIComponent(mfile)}`);
        const data = await resp.json();
        if (data.error) return;
        controlPoints = data.control_points.map(p => [...p]);
        defaultControlPoints = data.control_points.map(p => [...p]);
        frontPanel = data.front_panel;
        watchOutline = data.watch_pocket_outline;
        buildPanelBounds();
        resize();
    } catch (err) {
        console.error('Failed to load:', err);
    }
}

document.getElementById('reset-btn').addEventListener('click', () => {
    controlPoints = defaultControlPoints.map(p => [...p]);
    draw();
});

document.getElementById('measurements-select').addEventListener('change', loadDefaultShape);
document.getElementById('units-select').addEventListener('change', draw);

document.getElementById('generate-btn').addEventListener('click', async () => {
    const container = document.getElementById('pieces-container');
    const loading = document.getElementById('loading-indicator');
    loading.classList.remove('hidden');
    container.innerHTML = '';

    try {
        const resp = await fetch('/api/generate', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                control_points: controlPoints,
                measurements: document.getElementById('measurements-select').value,
                units: document.getElementById('units-select').value,
            }),
        });
        const data = await resp.json();
        loading.classList.add('hidden');

        if (data.error) {
            container.innerHTML = `<div class="error-msg">${data.error}</div>`;
            return;
        }

        [
            ['pocket_bag', 'Pocket Bag'],
            ['facing', 'Facing'],
            ['watch_pocket', 'Watch Pocket'],
        ].forEach(([key, title]) => {
            if (data[key]) {
                const card = document.createElement('div');
                card.className = 'piece-card';
                card.innerHTML = `<h3>${title}</h3><div class="piece-svg">${data[key]}</div>`;
                container.appendChild(card);
            } else if (data[key + '_error']) {
                container.innerHTML += `<div class="error-msg">${title}: ${data[key + '_error']}</div>`;
            }
        });
    } catch (err) {
        loading.classList.add('hidden');
        container.innerHTML = `<div class="error-msg">${err.message}</div>`;
    }
});

loadDefaultShape();
