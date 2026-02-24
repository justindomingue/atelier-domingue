GARMENT = {
    'name': '1873 Selvedge Denim Jeans',
    'fabric_width': 31,  # inches — narrow selvedge denim
    # grain_axis: which SVG axis carries the grainline ('x' default, 'y' for
    # pieces drafted with grain running vertically in their local coords).
    'pieces': [
        {'module': 'verify',              'name': 'Verify Draft'},
        # --- Main fabric (denim) ---
        {'module': 'jeans_front',         'name': 'Front Panel',          'cut_count': 2, 'selvedge_edge': 'top'},
        {'module': 'jeans_back',          'name': 'Back Panel',           'cut_count': 2, 'selvedge_edge': 'top'},
        {'module': 'jeans_yoke_1873',     'name': 'Yoke (1873)',          'cut_count': 2},
        {'module': 'jeans_yoke_modern',   'name': 'Yoke (Modern)',        'cut_count': 2},
        {'module': 'jeans_waistband',     'name': 'Waistband',            'cut_count': 1, 'interfacing': True},
        {'module': 'jeans_fly_1873',      'name': 'Fly (1873)',           'cut_count': 2, 'grain_axis': 'y', 'interfacing': True},
        {'module': 'jeans_fly_one_piece', 'name': 'Fly (One-Piece)',      'cut_count': 1, 'grain_axis': 'y'},
        {'module': 'jeans_back_pocket',   'name': 'Back Pocket',          'cut_count': 1, 'grain_axis': 'y'},
        {'module': 'jeans_watch_pocket',  'name': 'Watch Pocket (1873)',  'cut_count': 1, 'grain_axis': 'y'},
        {'module': 'jeans_front_facing',  'name': 'Front Pocket Facing',  'cut_count': 2, 'grain_axis': 'y'},
        {'module': 'jeans_back_cinch',    'name': 'Back Cinch Belt',      'cut_count': 1},
        # --- Pocketing fabric ---
        {'module': 'jeans_front_pocket',  'name': 'Front Pocket Bag',     'cut_count': 2, 'fabric': 'pocketing'},
    ],
}
