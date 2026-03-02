const canvas = document.getElementById('editor-canvas');
const ctx = canvas.getContext('2d');

let controlPoints = [];
let defaultControlPoints = [];
let frontPanel = null;
let watchOutline = null;
let draggingIndex = -1;
let scale = 1;
let offsetX = 0;
let offsetY = 0;

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

function toCanvas(wx, wy) {
    const dpr = window.devicePixelRatio || 1;
    return [
        (wx - offsetX) * scale,
        (canvas.height / dpr) - (wy - offsetY) * scale
    ];
}

function toWorld(cx, cy) {
    const dpr = window.devicePixelRatio || 1;
    return [
        cx / scale + offsetX,
        ((canvas.height / dpr) - cy) / scale + offsetY
    ];
}

function computeTransform() {
    if (!frontPanel) return;
    const dpr = window.devicePixelRatio || 1;
    const w = canvas.width / dpr;
    const h = canvas.height / dpr;

    let allX = [], allY = [];
    const addPt = (p) => { allX.push(p[0]); allY.push(p[1]); };
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
    const minX = Math.min(...allX) - pad;
    const maxX = Math.max(...allX) + pad;
    const minY = Math.min(...allY) - pad;
    const maxY = Math.max(...allY) + pad;

    const rangeX = maxX - minX;
    const rangeY = maxY - minY;

    scale = Math.min(w / rangeX, h / rangeY);
    offsetX = minX - (w / scale - rangeX) / 2;
    offsetY = minY - (h / scale - rangeY) / 2;
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

    const waistLine = [fp.pt1, fp.pt7];
    drawCurve(waistLine, '#bbb', 1.5);
    drawCurve(fp.hip, '#999', 1.5);
    drawCurve(fp.rise, '#999', 1.5);
    drawCurve(fp.crotch, '#999', 1.5);
    drawCurve(fp.inseam, '#999', 1.5);

    const hemLine = [fp.pt0, fp.pt9];
    drawCurve(hemLine, '#bbb', 1.5);

    const cf = [fp.pt10, fp.pt0];
    drawCurve(cf, '#ddd', 1, [4, 4]);

    ctx.save();
    ctx.fillStyle = '#bbb';
    ctx.font = '10px sans-serif';
    const [wx, wy] = toCanvas(fp.pt7[0], fp.pt7[1]);
    ctx.fillText('waist', wx + 4, wy - 4);
    const [hx, hy] = toCanvas(fp.hip[fp.hip.length-1][0], fp.hip[fp.hip.length-1][1]);
    ctx.fillText('hip', hx + 4, hy);
    const [rx, ry] = toCanvas(fp.rise[fp.rise.length-1][0], fp.rise[fp.rise.length-1][1]);
    ctx.fillText('rise', rx + 4, ry - 4);
    ctx.restore();
}

function drawWatchPocket() {
    if (!watchOutline || watchOutline.length < 3) return;
    drawClosedShape(watchOutline, 'rgba(201,169,110,0.08)', '#c9a96e', 1);
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
    ctx.lineWidth = 3;
    ctx.beginPath();
    const [sx, sy] = toCanvas(curve[0][0], curve[0][1]);
    ctx.moveTo(sx, sy);
    for (let i = 1; i < curve.length; i++) {
        const [px, py] = toCanvas(curve[i][0], curve[i][1]);
        ctx.lineTo(px, py);
    }
    ctx.stroke();
    ctx.restore();

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
    return [
        e.clientX - rect.left,
        e.clientY - rect.top
    ];
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
        controlPoints[draggingIndex] = toWorld(mx, my);
        draw();
    } else {
        canvas.style.cursor = findClosest(mx, my) >= 0 ? 'grab' : 'crosshair';
    }
});

canvas.addEventListener('mouseup', () => { draggingIndex = -1; canvas.style.cursor = 'crosshair'; });
canvas.addEventListener('mouseleave', () => { draggingIndex = -1; canvas.style.cursor = 'crosshair'; });

canvas.addEventListener('touchstart', (e) => {
    e.preventDefault();
    const t = e.touches[0];
    const [mx, my] = getMousePos(t);
    draggingIndex = findClosest(mx, my);
});

canvas.addEventListener('touchmove', (e) => {
    e.preventDefault();
    if (draggingIndex >= 0) {
        const t = e.touches[0];
        const [mx, my] = getMousePos(t);
        controlPoints[draggingIndex] = toWorld(mx, my);
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
