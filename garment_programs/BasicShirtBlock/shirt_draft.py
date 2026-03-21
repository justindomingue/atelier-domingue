# garment_programs/BasicShirtBlock/shirt_draft.py
import numpy as np

# -- Fits -------------------------------------------------------------------
EASE_CONFIGS = {
    'slim':    {'Sd': 2.0, 'Bwl': 1.0, 'Bw': 1.25, 'Sw': 3.5, 'Cw': 0.75},
    'regular': {'Sd': 3.0, 'Bwl': 2.0, 'Bw': 2.0,  'Sw': 4.5, 'Cw': 1.0},
    'loose':   {'Sd': 3.0, 'Bwl': 2.0, 'Bw': 3.0,  'Sw': 5.5, 'Cw': 2.0},
}

def draft_shirt_block(m: dict[str, float], fit='slim', **_) -> dict:
    """
    Compute shared geometry for the basic shirt block.
    """
    config = EASE_CONFIGS[fit]

    # -- Extract core measurements --
    Bh = m['body_height']
    Cg = m['chest_girth']
    Wg = m['waist_girth']
    Ng = m['neck_girth']
    Sl = m['sleeve_length']

    # -- Auxiliary measurements (calculated) --
    # Neck width (Nw)
    Nw = Ng / 6
    # Scye depth (Sd)  = 1/10 Cg + 12 cm + ease
    Sd = (Cg / 10) + 12.0 + config['Sd']
    # Back waist length (Bwl) = 1/4 Bh + ease
    Bwl = (Bh / 4) + config['Bwl']
    # Length (Lg) = 1/2 Bh minus 13 to 15 (using 14.5 as average or fixed 74 for size 50)
    # The chart specifies 74.0 for size 50. Formula is 1/2 Bh - 13..15
    Lg = (Bh / 2) - 14.5 # 88.5 - 14.5 = 74.0

    # Armhole depth (Ad) = finished Sd minus 0 to 1 cm
    Ad = Sd - 1.0 # The chart uses 24 Sd -> 23 Ad, so it's Sd - 1.0

    # Back width (Bw)
    if Cg <= 112:
        Bw_calc = (Cg * 0.2) - 1.0
    else:
        Bw_calc = (Cg * 0.1) + 10.5
    Bw = Bw_calc + config['Bw']

    # Scye width (Sw)
    Sw_calc = (Cg * 0.1) + 2.0
    Sw = Sw_calc + config['Sw']

    # Chest width (Cw)
    if Cg <= 112:
        Cw_calc = (Cg * 0.2) - 1.0
    else:
        Cw_calc = (Cg * 0.5) - Bw_calc - Sw_calc
    Cw = Cw_calc + config['Cw']

    # Total width (Bw + Sw + Cw) should equal ½ Cg + total ease.
    total_width = Bw + Sw + Cw
    expected_total = (Cg / 2) + config['Bw'] + config['Sw'] + config['Cw']
    assert abs(total_width - expected_total) < 1e-6, (
        f"total_width={total_width:.2f} != expected={expected_total:.2f}"
    )

    # Coordinate system: Origin at Neck point N (top-right on CB line).
    # Left is negative X, down is negative Y.

    N = np.array([0.0, 0.0]) # Neck point

    # Scye depth (Sd) down from N on vertical line -> chest line
    chest_y = -Sd

    # Back waist length (Bwl) down from N -> waistline
    waist_y = -Bwl

    # Length (Lg) down from N -> hemline
    hem_y = -Lg

    # Square out left for shoulder, chest, waist, and hem lines.
    # We will build x-coordinates from right to left (0 to negative).

    # Measure neck width (Nw) to the left -> W
    # Square up 2 cm from W
    # The diagram shows "Nw + 1" for the back neck width point
    back_neck_w_x = -(Nw + 1.0)
    neck_w_pt = np.array([back_neck_w_x, 2.0])

    # Measure back width (Bw) from CB to left on chest line
    back_width_x = -Bw
    back_width_pt = np.array([back_width_x, chest_y])
    # Square up from back width point (this is the back width line)
    
    # Measure scye width (Sw) from back width point to left on chest line
    front_pitch_x = back_width_x - Sw
    front_pitch_pt = np.array([front_pitch_x, chest_y])
    # Square up and down to waistline (this is the front pitch line)

    # Measure chest width (Cw) from front pitch point to left on chest line
    cf_x = front_pitch_x - Cw
    cf_pt = np.array([cf_x, chest_y])
    # Square up and down -> Centre Front (CF)

    # Armhole depth: upward from chest line on front pitch line
    armhole_depth_y = chest_y + Ad
    armhole_depth_pt = np.array([front_pitch_x, armhole_depth_y])
    # Square out to centre front from this point

    points = {
        'N': N,
        'neck_w_pt': neck_w_pt,
        'back_width_cf': np.array([back_width_x, 0.0]),
        'back_width_pt': back_width_pt,
        'front_pitch_pt': front_pitch_pt,
        'front_pitch_waist': np.array([front_pitch_x, waist_y]),
        'cf_pt': cf_pt,
        'cf_waist': np.array([cf_x, waist_y]),
        'cf_hem': np.array([cf_x, hem_y]),
        'cf_top': np.array([cf_x, armhole_depth_y]),
        'armhole_depth_pt': armhole_depth_pt,
        'cb_waist': np.array([0.0, waist_y]),
        'cb_hem': np.array([0.0, hem_y]),
        'cb_chest': np.array([0.0, chest_y]),
    }

    levels = {
        'shoulder_y': 0.0,
        'chest_y': chest_y,
        'waist_y': waist_y,
        'hem_y': hem_y,
        'armhole_depth_y': armhole_depth_y,
    }

    verticals = {
        'cb_x': 0.0,
        'back_width_x': back_width_x,
        'front_pitch_x': front_pitch_x,
        'cf_x': cf_x,
    }

    measurements = {
        'Bh': Bh, 'Cg': Cg, 'Wg': Wg, 'Ng': Ng, 'Sl': Sl,
        'Nw': Nw, 'Sd': Sd, 'Bwl': Bwl, 'Lg': Lg, 'Ad': Ad,
        'Bw': Bw, 'Sw': Sw, 'Cw': Cw,
        'total_width': total_width,
    }

    return {
        'points': points,
        'levels': levels,
        'verticals': verticals,
        'measurements': measurements,
    }
