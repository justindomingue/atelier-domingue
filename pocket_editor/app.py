"""Flask app for the interactive pocket shape editor."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template, jsonify, request
from pocket_editor.generate import get_default_control_points, generate_pieces

app = Flask(__name__)

MEASUREMENTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'measurements',
)

DEFAULT_MEASUREMENTS = os.path.join(MEASUREMENTS_DIR, 'justin_1873_jeans.yaml')


@app.route('/')
def index():
    measurements = []
    for f in sorted(os.listdir(MEASUREMENTS_DIR)):
        if f.endswith('.yaml'):
            measurements.append(f)
    return render_template('index.html', measurements=measurements)


def _safe_measurements_path(filename):
    """Validate and return a safe measurements file path."""
    basename = os.path.basename(filename)
    if basename != filename or '..' in filename:
        return None
    if not basename.endswith('.yaml'):
        return None
    path = os.path.join(MEASUREMENTS_DIR, basename)
    real = os.path.realpath(path)
    if not real.startswith(os.path.realpath(MEASUREMENTS_DIR) + os.sep):
        return None
    if not os.path.exists(real):
        return None
    return real


@app.route('/api/default-shape')
def default_shape():
    mfile = request.args.get('measurements', 'justin_1873_jeans.yaml')
    measurements_path = _safe_measurements_path(mfile)
    if not measurements_path:
        return jsonify({'error': f'Measurements file not found: {mfile}'}), 404

    try:
        data = get_default_control_points(measurements_path)
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/generate', methods=['POST'])
def generate():
    body = request.get_json()
    if not body or 'control_points' not in body:
        return jsonify({'error': 'Missing control_points'}), 400

    control_points = body['control_points']
    if len(control_points) != 4:
        return jsonify({'error': 'Need exactly 4 control points [P0, P1, P2, P3]'}), 400

    mfile = body.get('measurements', 'justin_1873_jeans.yaml')
    measurements_path = _safe_measurements_path(mfile)
    if not measurements_path:
        return jsonify({'error': f'Measurements file not found: {mfile}'}), 404

    units = body.get('units', 'cm')

    try:
        results = generate_pieces(control_points, measurements_path, units)
        return jsonify(results)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/measurements')
def list_measurements():
    measurements = []
    for f in sorted(os.listdir(MEASUREMENTS_DIR)):
        if f.endswith('.yaml'):
            measurements.append(f)
    return jsonify({'measurements': measurements})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
