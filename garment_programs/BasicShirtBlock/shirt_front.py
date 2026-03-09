# garment_programs/BasicShirtBlock/shirt_front.py
import numpy as np
import matplotlib.pyplot as plt

from garment_programs.measurements import load_measurements
from garment_programs.plot_utils import setup_figure, finalize_figure
from .shirt_draft import draft_shirt_block

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
    
    # The intersection is N_front = (ver['cf_x'], 0.0) -> actually lvl['shoulder_y']
    cf_intersection = np.array([ver['cf_x'], lvl['shoulder_y']])
    pts['front_neck_w_pt'] = cf_intersection + np.array([mm['Nw'], 0.0])
    pts['front_neck_depth_pt'] = cf_intersection + np.array([0.0, -(mm['Nw'] + 2.0)])

    # "Measure 4 cm for the front shoulder slope and connect the neckline corner and the 
    # shoulder slope with a guideline."
    # The line is squared left from the armhole depth to the CF.
    # Shoulder slope: measured down from the shoulder line on the front pitch line?
    # Diagram 2 shows shoulder slope drops 4cm on the front pitch line.
    pts['front_shoulder_slope_guide'] = np.array([ver['front_pitch_x'], -4.0])

    # Shoulder line: from front_neck_w_pt through front_shoulder_slope_guide.
    # We must make it the same length as the back shoulder (from Nw to shifted shoulder pt).
    # Back shoulder is shifted_back_shoulder_pt - shifted_neck_w_pt
    # But step 4 says: "Measure the back shoulder seam and transfer this measurement 
    # to the new front shoulder seam."
    # So we need to calculate the back shoulder length first (from step 3 of back).
    
    # Re-calculate back shoulder points to get the length
    # This happens via: back_shoulder_x = ver['back_width_x'] - 2.0
    shoulder_slope_pt_back = np.array([ver['back_width_x'], -2.0])
    back_neck_w_x = -(mm['Nw'] + 1.0)
    neck_w_pt_back = np.array([back_neck_w_x, 2.0])
    dx = shoulder_slope_pt_back[0] - neck_w_pt_back[0]
    dy = shoulder_slope_pt_back[1] - neck_w_pt_back[1]
    slope_back = dy / dx if dx != 0 else 0
    back_shoulder_x = ver['back_width_x'] - 2.0
    back_shoulder_y = shoulder_slope_pt_back[1] + slope_back * (-2.0)
    back_shoulder_pt_orig = np.array([back_shoulder_x, back_shoulder_y])
    
    # Back shoulder length
    back_shoulder_len = np.linalg.norm(back_shoulder_pt_orig - neck_w_pt_back)
    
    # Now extend front shoulder line to match this length.
    front_shoulder_dir = pts['front_shoulder_slope_guide'] - pts['front_neck_w_pt']
    front_shoulder_unit = front_shoulder_dir / np.linalg.norm(front_shoulder_dir)
    pts['front_shoulder_pt_orig'] = pts['front_neck_w_pt'] + front_shoulder_unit * back_shoulder_len

    # "Relocate the front shoulder seam 2 cm to the front. Draw a parallel line 2 cm below..."
    # The back shoulder shifted UP and FORWARD by 2cm, so front shoulder shifts DOWN and BACK by 2cm.
    # Actually diagram says "Draw a parallel line 2 cm below the front shoulder seam".
    # Downward is negative Y. So shift -2cm Y. Or perpendicular? "parallel line 2cm below".
    front_shoulder_perp_down = np.array([front_shoulder_unit[1], -front_shoulder_unit[0]]) # Down and left
    # Actually just visually it moves down, maybe perpendicular.
    shift_vec = front_shoulder_perp_down * 2.0
    if shift_vec[1] > 0: shift_vec = -shift_vec # Ensure it shifts down
    
    pts['shifted_front_neck_w_pt'] = pts['front_neck_w_pt'] + shift_vec
    pts['shifted_front_shoulder_pt'] = pts['front_shoulder_pt_orig'] + shift_vec

    # Front neckline curve (Step 3)
    # "Mark halfway point on guideline for front neckline and square down 1.8cm."
    # "Draw the front neckline from the shoulder point over this point to the CF"
    neckline_guide = pts['front_neck_depth_pt'] - pts['front_neck_w_pt']
    neckline_mid = pts['front_neck_w_pt'] + neckline_guide * 0.5
    # Square down 1.8cm from the guideline. Perpendicular direction towards origin (down/right)
    neckline_unit = neckline_guide / np.linalg.norm(neckline_guide)
    neckline_perp = np.array([-neckline_unit[1], neckline_unit[0]]) # Pointing roughly into the curve
    pts['front_neck_curve_pt'] = neckline_mid + neckline_perp * 1.8

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
    
    # Calculate proper sideseam
    halfway_x = ver['back_width_x'] - (mm['Sw'] / 2.0)
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
    
    # "Mark halfway point on front and back hemline and measure 2cm toward CF..."
    front_hem_mid_x = (halfway_x + ver['cf_x']) / 2.0
    pts['front_hem_scoop_start'] = np.array([front_hem_mid_x + 2.0, lvl['hem_y'] + 5.0])
    
    # Taper sideseam at waist
    waist_taper = 1.5
    pts['sideseam_waist_taper'] = pts['sideseam_waist'] + np.array([-waist_taper, 0.0]) # Taper INwards (right)

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

    # Front hem curve
    pts['front_hem_curve'] = _bezier_quad(
        pts['sideseam_hem_scoop'],
        np.array([pts['front_hem_scoop_start'][0], pts['sideseam_hem_scoop'][1]]),
        pts['front_hem_scoop_start']
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
    ax.plot([pts['front_hem_scoop_start'][0], ver['cf_x']], 
            [pts['front_hem_scoop_start'][1], lvl['hem_y']], **OUTLINE)

    if debug:
        REF = dict(color='gray', linewidth=0.8, linestyle='--', alpha=0.4)
        ax.plot([ver['cf_x'], ver['cf_x']], [lvl['hem_y'], lvl['shoulder_y']], **REF)
        ax.plot([ver['sideseam_x'], ver['sideseam_x']], [lvl['hem_y'], lvl['chest_y']], **REF)
        ax.plot([ver['front_pitch_x'], ver['front_pitch_x']], [lvl['waist_y'], lvl['shoulder_y']], **REF)
        
        ax.plot([ver['cf_x'], ver['sideseam_x']], [lvl['chest_y'], lvl['chest_y']], **REF)
        ax.plot([ver['cf_x'], ver['sideseam_x']], [lvl['waist_y'], lvl['waist_y']], **REF)
        ax.plot([ver['cf_x'], ver['sideseam_x']], [lvl['hem_y'], lvl['hem_y']], **REF)

    finalize_figure(ax, fig, standalone, output_path, units=units, debug=debug)

def run(measurements_path, output_path, debug=False, units='cm'):
    m = load_measurements(measurements_path)
    draft = draft_shirt_front(m, fit='slim', step=4)
    plot_shirt_front(draft, output_path, debug=debug, units=units, step=4)
