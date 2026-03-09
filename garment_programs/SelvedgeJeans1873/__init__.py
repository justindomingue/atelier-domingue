# Shared pieces common to both 1873 and modern variants.
_SHARED_PIECES = [
    {'module': 'verify',              'name': 'Verify Draft'},
    # --- Main fabric (denim) ---
    {'module': 'jeans_front',         'name': 'Front',                'cut_count': 2, 'selvedge_edge': 'top'},
    {'module': 'jeans_waistband',     'name': 'Waistband',            'cut_count': 1, 'selvedge_edge': 'top', 'interfacing': True},
    {'module': 'jeans_front_facing',  'name': 'Facing',               'cut_count': 2, 'grain_axis': 'y'},
    # Watch pocket — same dimensions for both variants.
    # Historically the 1873 version is ~1" longer (top at waistband center,
    # bottom just below pocket opening); using identical geometry for now.
    {'module': 'jeans_watch_pocket',  'name': 'Watch Pocket',         'cut_count': 1, 'grain_axis': 'y'},
]

GARMENTS = [
    # ------------------------------------------------------------------ #
    # 1873 Historical                                                     #
    # ------------------------------------------------------------------ #
    {
        'name': '1873 Selvedge Denim Jeans',
        'fabric_width': 31,  # inches — narrow selvedge denim
        'fabric_widths': {
            'pocketing': 45,    # standard pocketing cotton
            'interfacing': 20,  # standard fusible interfacing
        },
        'pieces': _SHARED_PIECES + [
            {'module': 'jeans_back',          'name': 'Back',             'cut_count': 2, 'selvedge_edge': 'top',
             'kwargs': {'gathering_amount': 1.905}},      # 0.75" gathering for 1873
            {'module': 'jeans_yoke_1873',     'name': 'Yoke',             'cut_count': 2},
            {'module': 'jeans_fly_1873',      'name': 'Fly',              'cut_count': 2, 'grain_axis': 'y', 'interfacing': True},
            {'module': 'jeans_back_pocket',   'name': 'Back Pocket',      'cut_count': 2, 'grain_axis': 'y'},
            {'module': 'jeans_back_cinch',    'name': 'Cinch Belt',       'cut_count': 1, 'selvedge_edge': 'bottom'},
            # --- Pocketing fabric (last — cut from separate material) ---
            {'module': 'jeans_front_pocket_bag',  'name': 'Pocket Bag',           'cut_count': 1, 'fabric': 'pocketing'},
        ],
    },
    # ------------------------------------------------------------------ #
    # Modern                                                              #
    # ------------------------------------------------------------------ #
    {
        'name': 'Modern Selvedge Denim Jeans',
        'fabric_width': 31,  # inches — narrow selvedge denim
        'fabric_widths': {
            'pocketing': 45,    # standard pocketing cotton
            'interfacing': 20,  # standard fusible interfacing
        },
        'pieces': _SHARED_PIECES + [
            {'module': 'jeans_back',          'name': 'Back',             'cut_count': 2, 'selvedge_edge': 'top'},
            {'module': 'jeans_yoke_modern',   'name': 'Yoke',             'cut_count': 2},
            {'module': 'jeans_fly_one_piece', 'name': 'Fly',              'cut_count': 1, 'grain_axis': 'y'},
            {'module': 'jeans_back_pocket',   'name': 'Back Pocket',      'cut_count': 2, 'grain_axis': 'y'},
            # --- Pocketing fabric (last — cut from separate material) ---
            {'module': 'jeans_front_pocket_bag',  'name': 'Pocket Bag',           'cut_count': 1, 'fabric': 'pocketing'},
        ],
    },
]
