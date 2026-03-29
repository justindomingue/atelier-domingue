GARMENT = {
    'name': 'Kinto-Style Bread Bag',
    'fabric_width': 45,  # inches — typical linen bolt
    'fabric_widths': {
        'lining': 45,  # cotton canvas
    },
    'pieces': [
        {'module': 'bag_body',   'name': 'Outer Body',  'cut_count': 2, 'fabric': 'main'},
        {'module': 'bag_lining', 'name': 'Lining Body', 'cut_count': 2, 'fabric': 'lining'},
        {'module': 'bag_strap',  'name': 'Side Strap',  'cut_count': 2, 'fabric': 'main'},
    ],
}
