# garment_programs/BasicShirtBlock/shirt_front.py
import numpy as np

from garment_programs.measurements import load_measurements
from garment_programs.plot_utils import setup_figure, finalize_figure
from .shirt_draft import _back_shoulder_line, draft_shirt_block

def draft_shirt_front(m: dict[str, float], fit='slim', step=4) -> dict:
    draft = draft_shirt_block(m, fit=fit, step=step)
    
    pts = draft['points']
    lvl = draft['levels']
    ver = draft['verticals']
    mm = draft['measurements']

    from garment_programs.geometry import _bezier_cubic, _bezier_quad

    # ==========================================================
    # Front Neckline and Shoulder (Steps 2-3)
    # ==========================================================
    # "From the intersection with the centre front measure the neck width (Nw) to the right
    # and the neck width (Nw) plus 2 cm downward. Connect both points with a guideline."
    cf_intersection = np.array([ver['cf_x'], lvl['shoulder_y']])
    pts['front_neck_w_pt'] = cf_intersection + np.array([mm['Nw'], 0.0])
    pts['front_neck_depth_pt'] = cf_intersection + np.array([0.0, -(mm['Nw'] + 2.0)])

    # "Measure 4 cm for the front shoulder slope and connect the neckline corner and the
    # shoulder slope with a guideline."
    # Diagram 2: shoulder slope drops 4 cm on the front pitch line.
    pts['front_shoulder_slope_guide'] = np.array([ver['front_pitch_x'], -4.0])

    # Shoulder line: from front_neck_w_pt through front_shoulder_slope_guide, with length
    # matched to the back shoulder seam ("Measure the back shoulder seam and transfer this
    # measurement to the new front shoulder seam").
    _, _, back_shoulder_len = _back_shoulder_line(ver, pts['neck_w_pt'])

    # Extend front shoulder line to match the back shoulder length.
    front_shoulder_dir = pts['front_shoulder_slope_guide'] - pts['front_neck_w_pt']
    front_shoulder_unit = front_shoulder_dir / np.linalg.norm(front_shoulder_dir)
    pts['front_shoulder_pt_orig'] = pts['front_neck_w_pt'] + front_shoulder_unit * back_shoulder_len

    # "Relocate the front shoulder seam 2 cm to the front. Draw a parallel line 2 cm below
    # the front shoulder seam." Shift perpendicular to the shoulder line, ensuring downward.
    front_shoulder_perp_down = np.array([front_shoulder_unit[1], -front_shoulder_unit[0]])
    shift_vec = front_shoulder_perp_down * 2.0
    if shift_vec[1] > 0:
        shift_vec = -shift_vec
    
    pts['shifted_front_neck_w_pt'] = pts['front_neck_w_pt'] + shift_vec
    pts['shifted_front_shoulder_pt'] = pts['front_shoulder_pt_orig'] + shift_vec

    # Front neckline curve (Step 3)
    # "Draw the front neckline from the shoulder point over this point to the CF"
    pts['front_neck_curve'] = _bezier_quad(
        pts['shifted_front_neck_w_pt'],
        np.array([pts['shifted_front_neck_w_pt'][0] - 2.0, pts['front_neck_depth_pt'][1]]),
        pts['front_neck_depth_pt']
    )

    # ==========================================================
    # Front Armhole and Hemline (Steps 3-4)
    # ==========================================================
    # "Plot the front armhole from the shoulder seam to the 1/4 scye depth point and further to the side seam."
    front_pitch_1_4_sd = np.array([ver['front_pitch_x'], lvl['chest_y'] + (mm['Sd'] / 4.0)])
    
    # Sideseam at halfway point between CB (x=0) and CF — must match back sideseam
    # (shirt_back.py uses ver['cf_x'] / 2.0) so the seams join cleanly.
    halfway_x = ver['cf_x'] / 2.0
    ver['sideseam_x'] = halfway_x
    pts['sideseam_chest'] = np.array([halfway_x, lvl['chest_y']])
    pts['sideseam_waist'] = np.array([halfway_x, lvl['waist_y']])
    pts['sideseam_hem_scoop'] = np.array([halfway_x, lvl['hem_y'] + 5.0])

    # To make it smooth: control points should push deep towards front pitch and chest line
    # Enforce vertical tangents at front_pitch_1_4_sd
    pts['front_armhole_upper'] = _bezier_cubic(
        pts['shifted_front_shoulder_pt'],
        pts['shifted_front_shoulder_pt'] + np.array([0.0, -3.0]),  # down from shoulder
        front_pitch_1_4_sd + np.array([0.0, 3.0]),                 # vertically above pitch point
        front_pitch_1_4_sd
    )
    
    pts['front_armhole_lower'] = _bezier_cubic(
        front_pitch_1_4_sd,
        front_pitch_1_4_sd + np.array([0.0, -2.0]),                # vertically below pitch point
        pts['sideseam_chest'] + np.array([-2.0, 0.0]),             # horizontally left of sideseam
        pts['sideseam_chest']
    )
    
    # Taper sideseam at waist. CF is to the LEFT (more negative x) of the sideseam,
    # so subtracting moves the sideseam toward CF — narrowing the front panel.
    # This mirrors the back's +waist_taper (toward CB) so both panels slim symmetrically.
    waist_taper = 1.5
    pts['sideseam_waist_taper'] = pts['sideseam_waist'] + np.array([-waist_taper, 0.0])

    # Sideseam curves
    pts['front_sideseam_upper'] = _bezier_quad(
        pts['sideseam_chest'],
        pts['sideseam_chest'] + np.array([0.0, -3.0]),
        pts['sideseam_waist_taper']
    )
    pts['front_sideseam_lower'] = _bezier_quad(
        pts['sideseam_waist_taper'],
        pts['sideseam_waist_taper'] + np.array([0.0, -5.0]),
        pts['sideseam_hem_scoop']
    )

    # Front hem: a single smooth shirt-tail curve from the sideseam scoop down to
    # the CF hem. Horizontal tangents at both ends — flat near the sideseam so the
    # scoop stays level before dipping, and flat into CF so the hem meets the fold
    # at a right angle (no kink when the front is mirrored across CF).
    pts['cf_hem'] = np.array([ver['cf_x'], lvl['hem_y']])
    hem_span = pts['sideseam_hem_scoop'][0] - ver['cf_x']
    pts['front_hem_curve'] = _bezier_cubic(
        pts['sideseam_hem_scoop'],
        pts['sideseam_hem_scoop'] + np.array([-hem_span * 0.4, 0.0]),
        pts['cf_hem'] + np.array([hem_span * 0.4, 0.0]),
        pts['cf_hem'],
    )

    draft['curves'] = {
        'front_neck': pts['front_neck_curve'],
        'front_armhole_upper': pts['front_armhole_upper'],
        'front_armhole_lower': pts['front_armhole_lower'],
        'sideseam_upper': pts['front_sideseam_upper'],
        'sideseam_lower': pts['front_sideseam_lower'],
        'hem_scoop': pts['front_hem_curve']
    }

    return draft

def plot_shirt_front(draft, output_path='Logs/shirt_front.svg', debug=False, units='cm', step=4):
    pts = draft['points']
    lvl = draft['levels']
    ver = draft['verticals']
    crv = draft['curves']

    fig, ax, standalone = setup_figure(figsize=(10, 12))
    
    OUTLINE = dict(color='black', linewidth=1.5, zorder=4)
    
    # Draw curves
    ax.plot(crv['front_neck'][:, 0], crv['front_neck'][:, 1], **OUTLINE)
    ax.plot(crv['front_armhole_upper'][:, 0], crv['front_armhole_upper'][:, 1], **OUTLINE)
    ax.plot(crv['front_armhole_lower'][:, 0], crv['front_armhole_lower'][:, 1], **OUTLINE)
    ax.plot(crv['sideseam_upper'][:, 0], crv['sideseam_upper'][:, 1], **OUTLINE)
    ax.plot(crv['sideseam_lower'][:, 0], crv['sideseam_lower'][:, 1], **OUTLINE)
    ax.plot(crv['hem_scoop'][:, 0], crv['hem_scoop'][:, 1], **OUTLINE)

    # Draw straight lines
    ax.plot([ver['cf_x'], ver['cf_x']], [lvl['hem_y'], pts['front_neck_depth_pt'][1]], **OUTLINE)
    ax.plot([pts['shifted_front_neck_w_pt'][0], pts['shifted_front_shoulder_pt'][0]],
            [pts['shifted_front_neck_w_pt'][1], pts['shifted_front_shoulder_pt'][1]], **OUTLINE)

    if debug:
        REF = dict(color='gray', linewidth=0.8, linestyle='--', alpha=0.4)
        ax.plot([ver['cf_x'], ver['cf_x']], [lvl['hem_y'], lvl['shoulder_y']], **REF)
        ax.plot([ver['sideseam_x'], ver['sideseam_x']], [lvl['hem_y'], lvl['chest_y']], **REF)
        ax.plot([ver['front_pitch_x'], ver['front_pitch_x']], [lvl['waist_y'], lvl['shoulder_y']], **REF)
        
        ax.plot([ver['cf_x'], ver['sideseam_x']], [lvl['chest_y'], lvl['chest_y']], **REF)
        ax.plot([ver['cf_x'], ver['sideseam_x']], [lvl['waist_y'], lvl['waist_y']], **REF)
        ax.plot([ver['cf_x'], ver['sideseam_x']], [lvl['hem_y'], lvl['hem_y']], **REF)

    finalize_figure(ax, fig, standalone, output_path, units=units, debug=debug)

def run(measurements_path, output_path, debug=False, units='cm', context=None, **kwargs):
    m = load_measurements(measurements_path)
    draft = draft_shirt_front(m, fit='slim', step=4)
    plot_shirt_front(draft, output_path, debug=debug, units=units, step=4)
