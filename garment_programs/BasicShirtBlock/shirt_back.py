# garment_programs/BasicShirtBlock/shirt_back.py
import numpy as np
import matplotlib.pyplot as plt

from garment_programs.measurements import load_measurements
from garment_programs.plot_utils import setup_figure, finalize_figure
from .shirt_draft import draft_shirt_block

def draft_shirt_back(m: dict[str, float], fit='slim') -> dict:
    draft = draft_shirt_block(m, fit=fit)

    pts = draft['points']
    lvl = draft['levels']
    ver = draft['verticals']
    mm = draft['measurements']

    from garment_programs.geometry import _bezier_cubic, _bezier_quad

    # ==========================================================
    # Step 2: Back neckline, shoulder, back armhole
    # ==========================================================
    # Yoke at CB is 7 cm wide; square out to the left.
    yoke_cb_y = -7.0
    pts['yoke_cb'] = np.array([0.0, yoke_cb_y])

    # Back pitch point: ¼ Sd up from the chest line on the back-width vertical,
    # shifted 2 cm to the left per the drafting text.
    sd_quarter = mm['Sd'] / 4
    pts['back_pitch'] = np.array([ver['back_width_x'] - 2.0, lvl['chest_y'] + sd_quarter])

    # Shoulder slope guide: 2 cm down from N's level on the back-width line.
    shoulder_slope_pt = np.array([ver['back_width_x'], -2.0])
    pts['shoulder_slope_guide'] = shoulder_slope_pt

    # Shoulder line runs from neck_w_pt through the slope guide, extended 2 cm
    # past the back-width line.
    shoulder_extension_x = 2.0
    dx = shoulder_slope_pt[0] - pts['neck_w_pt'][0]
    dy = shoulder_slope_pt[1] - pts['neck_w_pt'][1]
    slope = dy / dx if dx != 0 else 0

    back_shoulder_x = ver['back_width_x'] - shoulder_extension_x
    back_shoulder_y = shoulder_slope_pt[1] + slope * (-shoulder_extension_x)
    pts['back_shoulder_pt'] = np.array([back_shoulder_x, back_shoulder_y])

    # ==========================================================
    # Step 3: Shift shoulder seam forward
    # ==========================================================
    # The back shoulder seam moves 2 cm toward the front: draw a parallel line
    # 2 cm above (perpendicular to) the original neck_w_pt → back_shoulder_pt line.
    shoulder_dir = pts['back_shoulder_pt'] - pts['neck_w_pt']
    shoulder_unit = shoulder_dir / np.linalg.norm(shoulder_dir)
    shoulder_perp = np.array([-shoulder_unit[1], shoulder_unit[0]])  # up/right

    pts['shifted_neck_w_pt'] = pts['neck_w_pt'] + shoulder_perp * 2.0
    pts['shifted_back_shoulder_pt'] = pts['back_shoulder_pt'] + shoulder_perp * 2.0

    # Sideseam sits at the CB↔CF halfway point, squared down to the hem.
    halfway_x = ver['cf_x'] / 2.0
    ver['sideseam_x'] = halfway_x
    pts['sideseam_chest'] = np.array([halfway_x, lvl['chest_y']])
    pts['sideseam_waist'] = np.array([halfway_x, lvl['waist_y']])
    pts['sideseam_hem'] = np.array([halfway_x, lvl['hem_y']])

    # Back hem scoop: 5 cm up from hem on the sideseam, 2 cm toward CB.
    pts['sideseam_hem_scoop'] = np.array([halfway_x, lvl['hem_y'] + 5.0])
    pts['back_hem_scoop_start'] = np.array([halfway_x - 2.0, lvl['hem_y'] + 5.0])

    # 1.5 cm armhole intake on the back-width line at the yoke level.
    yoke_armhole_base = np.array([ver['back_width_x'], pts['yoke_cb'][1]])
    pts['yoke_armhole_intake'] = yoke_armhole_base + np.array([1.5, 0.0])
    pts['yoke_line'] = np.array([pts['yoke_cb'], pts['yoke_armhole_intake']])

    # 1.5 cm waist taper toward CB (positive x).
    waist_taper = 1.5
    pts['sideseam_waist_taper'] = pts['sideseam_waist'] + np.array([waist_taper, 0.0])

    # ==========================================================
    # Step 4: Curves
    # ==========================================================
    curves = {}

    # Back neck: N (0,0) → shifted_neck_w_pt (collar high point).
    curves['back_neck'] = _bezier_quad(
        pts['N'],
        pts['N'] + np.array([pts['shifted_neck_w_pt'][0] * 0.1,
                             pts['shifted_neck_w_pt'][1] * 0.5]),
        pts['shifted_neck_w_pt'],
    )

    # Back armhole in three segments: shoulder → yoke intake → back pitch → sideseam.
    curves['back_armhole_yoke'] = _bezier_quad(
        pts['shifted_back_shoulder_pt'],
        pts['shifted_back_shoulder_pt'] + np.array(
            [1.0, (pts['yoke_armhole_intake'][1] - pts['shifted_back_shoulder_pt'][1]) * 0.5]
        ),
        pts['yoke_armhole_intake'],
    )
    curves['back_armhole_main'] = _bezier_cubic(
        pts['yoke_armhole_intake'],
        pts['yoke_armhole_intake'] + np.array([0.0, -2.0]),
        pts['back_pitch'] + np.array([0.0, 2.0]),
        pts['back_pitch'],
    )
    curves['back_armhole_bottom'] = _bezier_cubic(
        pts['back_pitch'],
        pts['back_pitch'] + np.array([-0.5, -1.5]),
        pts['sideseam_chest'] + np.array([1.0, 1.0]),
        pts['sideseam_chest'],
    )

    # Sideseam: chest → waist taper → hem scoop.
    curves['sideseam_upper'] = _bezier_quad(
        pts['sideseam_chest'],
        pts['sideseam_chest'] + np.array([0.0, -3.0]),
        pts['sideseam_waist_taper'],
    )
    curves['sideseam_lower'] = _bezier_quad(
        pts['sideseam_waist_taper'],
        pts['sideseam_waist_taper'] + np.array([0.0, -5.0]),
        pts['sideseam_hem_scoop'],
    )

    # Hem scoop curve; the remainder of the hem is a straight line to cb_hem.
    curves['hem_scoop'] = _bezier_quad(
        pts['sideseam_hem_scoop'],
        np.array([pts['back_hem_scoop_start'][0], pts['sideseam_hem_scoop'][1]]),
        pts['back_hem_scoop_start'],
    )

    draft['curves'] = curves
    return draft

def plot_shirt_back(draft, output_path='Logs/shirt_back.svg', debug=False, units='cm', step=1):
    pts = draft['points']
    lvl = draft['levels']
    ver = draft['verticals']
    mm = draft['measurements']

    fig, ax, standalone = setup_figure(figsize=(12, 12))
    plt.rcParams['lines.solid_capstyle'] = 'butt'
    REF = dict(color='gray', linewidth=0.8, linestyle='--', alpha=0.4)

    if debug:
        # Step 1 geometry
        # Verticals
        ax.plot([ver['cb_x'], ver['cb_x']], [lvl['hem_y'], 10], 'k-', lw=1.2)
        ax.annotate('vertical baseline / C.B.', (ver['cb_x'], (lvl['chest_y']+lvl['waist_y'])/2),
                    rotation=90, ha='right', va='center', fontsize=8)

        ax.plot([ver['back_width_x'], ver['back_width_x']], [lvl['chest_y'], 10], 'k-', lw=0.8)
        ax.annotate('back width line', (ver['back_width_x'], (lvl['shoulder_y']+lvl['chest_y'])/2),
                    rotation=90, ha='right', va='center', fontsize=8)

        ax.plot([ver['front_pitch_x'], ver['front_pitch_x']], [lvl['waist_y'], lvl['armhole_depth_y']], 'k-', lw=0.8)
        ax.annotate('front pitch line', (ver['front_pitch_x'], (lvl['chest_y']+lvl['waist_y'])/2),
                    rotation=90, ha='right', va='center', fontsize=8)

        ax.plot([ver['cf_x'], ver['cf_x']], [lvl['hem_y'], lvl['armhole_depth_y']], 'k-', lw=1.2)
        ax.annotate('C.F.', (ver['cf_x'], (lvl['chest_y']+lvl['waist_y'])/2),
                    rotation=90, ha='right', va='center', fontsize=8)

        # Horizontals
        ax.plot([ver['cf_x'], ver['cb_x']], [lvl['chest_y'], lvl['chest_y']], 'k-', lw=1.2)
        ax.annotate('chest line', ((ver['cf_x']+ver['cb_x'])/2, lvl['chest_y']),
                    ha='center', va='top', fontsize=8)

        ax.plot([ver['cf_x'], ver['cb_x']], [lvl['waist_y'], lvl['waist_y']], 'k-', lw=1.2)
        ax.annotate('waistline', ((ver['cf_x']+ver['cb_x'])/2, lvl['waist_y']),
                    ha='center', va='bottom', fontsize=8)

        ax.plot([ver['cf_x'], ver['cb_x']], [lvl['hem_y'], lvl['hem_y']], 'k-', lw=1.2)
        ax.annotate('hemline', ((ver['cf_x']+ver['cb_x'])/2, lvl['hem_y']),
                    ha='center', va='bottom', fontsize=8)
        
        ax.plot([ver['cf_x'], ver['front_pitch_x']], [lvl['armhole_depth_y'], lvl['armhole_depth_y']], 'k-', lw=0.8)

        ax.plot([ver['back_width_x'], ver['cb_x']], [lvl['shoulder_y'], lvl['shoulder_y']], 'k-', lw=0.8)
        ax.annotate('shoulder line', ((ver['back_width_x']+ver['cb_x'])/2, lvl['shoulder_y']),
                    ha='center', va='bottom', fontsize=8)


        # Points & Measurements
        ax.plot(*pts['N'], 'ko', markersize=3)
        ax.annotate('N', pts['N'], textcoords='offset points', xytext=(2, 2), fontsize=8)

        # Draw Nw+1 line and point
        ax.plot([ver['cb_x'], pts['neck_w_pt'][0], pts['neck_w_pt'][0]],
                [pts['neck_w_pt'][1], pts['neck_w_pt'][1], lvl['shoulder_y']], **REF)
        ax.annotate('Nw+1', ((ver['cb_x']+pts['neck_w_pt'][0])/2, pts['neck_w_pt'][1]),
                    ha='center', va='top', fontsize=6)

        # Annotate depths on CB
        ax.annotate('', xy=(ver['cb_x']+2, lvl['shoulder_y']), xytext=(ver['cb_x']+2, lvl['chest_y']),
                    arrowprops=dict(arrowstyle='<->', lw=0.5))
        ax.text(ver['cb_x']+3, (lvl['shoulder_y']+lvl['chest_y'])/2, f"Sd {mm['Sd']:.1f}", va='center', fontsize=6)

        ax.annotate('', xy=(ver['cb_x']+4, lvl['shoulder_y']), xytext=(ver['cb_x']+4, lvl['waist_y']),
                    arrowprops=dict(arrowstyle='<->', lw=0.5))
        ax.text(ver['cb_x']+5, (lvl['shoulder_y']+lvl['waist_y'])/2, f"Bwl {mm['Bwl']:.1f}", va='center', fontsize=6)

        ax.annotate('', xy=(ver['cb_x']+6, lvl['shoulder_y']), xytext=(ver['cb_x']+6, lvl['hem_y']),
                    arrowprops=dict(arrowstyle='<->', lw=0.5))
        ax.text(ver['cb_x']+7, (lvl['shoulder_y']+lvl['hem_y'])/2, f"Lg {mm['Lg']:.1f}", va='center', fontsize=6)

        # Annotate widths on chest line
        ax.annotate('', xy=(ver['cb_x'], lvl['chest_y']+1), xytext=(ver['back_width_x'], lvl['chest_y']+1),
                    arrowprops=dict(arrowstyle='<->', lw=0.5, linestyle='--'))
        ax.text((ver['cb_x']+ver['back_width_x'])/2, lvl['chest_y']+1.5, f"Bw {mm['Bw']:.1f}", ha='center', fontsize=6)

        ax.annotate('', xy=(ver['back_width_x'], lvl['chest_y']+1), xytext=(ver['front_pitch_x'], lvl['chest_y']+1),
                    arrowprops=dict(arrowstyle='<->', lw=0.5, linestyle='--'))
        ax.text((ver['back_width_x']+ver['front_pitch_x'])/2, lvl['chest_y']+1.5, f"Sw {mm['Sw']:.1f}", ha='center', fontsize=6)

        ax.annotate('', xy=(ver['front_pitch_x'], lvl['chest_y']+1), xytext=(ver['cf_x'], lvl['chest_y']+1),
                    arrowprops=dict(arrowstyle='<->', lw=0.5, linestyle='--'))
        ax.text((ver['front_pitch_x']+ver['cf_x'])/2, lvl['chest_y']+1.5, f"Cw {mm['Cw']:.1f}", ha='center', fontsize=6)
        
        # Annotate Ad on front pitch line
        ax.annotate('', xy=(ver['front_pitch_x']+1, lvl['chest_y']), xytext=(ver['front_pitch_x']+1, lvl['armhole_depth_y']),
                    arrowprops=dict(arrowstyle='<->', lw=0.5, linestyle='--'))
        ax.text(ver['front_pitch_x']+2, (lvl['chest_y']+lvl['armhole_depth_y'])/2, f"Ad {mm['Ad']:.1f}", rotation=90, va='center', fontsize=6)

    if step >= 2 and debug:
        # Sideseam
        ax.plot([ver['sideseam_x'], ver['sideseam_x']], [lvl['hem_y'], lvl['chest_y']], 'k-', lw=1.2)
        ax.annotate('sideseam', (ver['sideseam_x'], (lvl['chest_y']+lvl['waist_y'])/2),
                    rotation=90, ha='right', va='center', fontsize=8)

        # Original Shoulder line (Step 2)
        ax.plot([pts['neck_w_pt'][0], pts['back_shoulder_pt'][0]], 
                [pts['neck_w_pt'][1], pts['back_shoulder_pt'][1]], 'k-', lw=0.8)
        
        # Back pitch point (1/4 Sd)
        ax.plot(*pts['back_pitch'], 'ko', markersize=3)
        ax.annotate('1/4 Sd', pts['back_pitch'], textcoords='offset points', xytext=(4, 0), fontsize=6)

        # Yoke line
        ax.plot([ver['cb_x'], ver['back_width_x']], [pts['yoke_cb'][1], pts['yoke_cb'][1]], 'k-', lw=0.8)

    if step >= 3 and debug:
        # Shifted shoulder
        ax.plot([pts['shifted_neck_w_pt'][0], pts['shifted_back_shoulder_pt'][0]], 
                [pts['shifted_neck_w_pt'][1], pts['shifted_back_shoulder_pt'][1]], 'k-', lw=1.2)
        ax.annotate('shift shoulder seam', 
                    ((pts['shifted_neck_w_pt'][0]+pts['shifted_back_shoulder_pt'][0])/2, 
                     (pts['shifted_neck_w_pt'][1]+pts['shifted_back_shoulder_pt'][1])/2), 
                    textcoords='offset points', xytext=(0, 4), fontsize=6, rotation=15)

        # Shift guide vectors
        ax.annotate('', xy=pts['shifted_neck_w_pt'], xytext=pts['neck_w_pt'], arrowprops=dict(arrowstyle='->', lw=0.5))
        ax.annotate('', xy=pts['shifted_back_shoulder_pt'], xytext=pts['back_shoulder_pt'], arrowprops=dict(arrowstyle='->', lw=0.5))

    if step >= 4:
        crv = draft['curves']
        # Draw curves
        OUTLINE = dict(color='black', linewidth=1.5, zorder=4)
        ax.plot(crv['back_neck'][:, 0], crv['back_neck'][:, 1], **OUTLINE)
        ax.plot(crv['back_armhole_yoke'][:, 0], crv['back_armhole_yoke'][:, 1], **OUTLINE)
        ax.plot(crv['back_armhole_main'][:, 0], crv['back_armhole_main'][:, 1], **OUTLINE)
        ax.plot(crv['back_armhole_bottom'][:, 0], crv['back_armhole_bottom'][:, 1], **OUTLINE)
        
        ax.plot(crv['sideseam_upper'][:, 0], crv['sideseam_upper'][:, 1], **OUTLINE)
        ax.plot(crv['sideseam_lower'][:, 0], crv['sideseam_lower'][:, 1], **OUTLINE)
        ax.plot(crv['hem_scoop'][:, 0], crv['hem_scoop'][:, 1], **OUTLINE)

        # Straight outlines
        ax.plot([pts['back_hem_scoop_start'][0], ver['cb_x']], 
                [pts['back_hem_scoop_start'][1], lvl['hem_y']], **OUTLINE)
        ax.plot([ver['cb_x'], ver['cb_x']], 
                [lvl['hem_y'], pts['N'][1]], **OUTLINE)
        ax.plot([pts['shifted_neck_w_pt'][0], pts['shifted_back_shoulder_pt'][0]], 
                [pts['shifted_neck_w_pt'][1], pts['shifted_back_shoulder_pt'][1]], **OUTLINE)
        ax.plot([pts['yoke_cb'][0], pts['yoke_armhole_intake'][0]], 
                [pts['yoke_cb'][1], pts['yoke_armhole_intake'][1]], **OUTLINE)

    finalize_figure(ax, fig, standalone, output_path, units=units, debug=debug)


def run(measurements_path, output_path, debug=False, units='cm', context=None, **kwargs):
    m = load_measurements(measurements_path)
    draft = draft_shirt_back(m, fit='slim')
    plot_shirt_back(draft, output_path, debug=debug, units=units, step=4)
