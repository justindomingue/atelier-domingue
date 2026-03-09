# Shared pieces common to both 1873 and modern variants.
_SHARED_PIECES = [
    {'module': 'verify',             'name': 'Verify Draft'},
    {'module': 'jeans_front',        'name': 'Front Panel',      'cut': 2, 'mirror': True},
    {'module': 'jeans_back',         'name': 'Back Panel',       'cut': 2, 'mirror': True},
    {'module': 'jeans_waistband',    'name': 'Waistband',        'cut': 1},
    {'module': 'jeans_front_pocket', 'name': 'Front Pocket',     'cut': 2, 'mirror': True},
]

GARMENTS = [
    {
        'name': '1873 Selvedge Denim Jeans',
        'pieces': _SHARED_PIECES + [
            {'module': 'jeans_yoke_1873',    'name': 'Yoke (1873)',      'cut': 2, 'mirror': True},
            {'module': 'jeans_fly_1873',     'name': 'Fly (1873)',       'cut': 1},
            {'module': 'jeans_back_pocket',  'name': 'Back Pocket',      'cut': 2},
            {'module': 'jeans_back_cinch',   'name': 'Back Cinch Belt',  'cut': 1},
        ],
    },
    {
        'name': 'Modern Selvedge Denim Jeans',
        'pieces': _SHARED_PIECES + [
            {'module': 'jeans_yoke_modern',   'name': 'Yoke (Modern)',    'cut': 2, 'mirror': True},
            {'module': 'jeans_fly_one_piece', 'name': 'Fly (One-Piece)', 'cut': 1},
            {'module': 'jeans_back_pocket',   'name': 'Back Pocket',      'cut': 2},
        ],
    },
]
