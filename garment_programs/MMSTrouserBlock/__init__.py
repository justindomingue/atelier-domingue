GARMENTS = [
    {
        'name': 'Flat-Front Trouser (MM&S)',
        'pieces': [
            {'module': 'trouser_front', 'name': 'Front Panel', 'cut_count': 2, 'kwargs': {'num_pleats': 0}},
            {'module': 'trouser_back',  'name': 'Back Panel',  'cut_count': 2, 'kwargs': {'num_pleats': 0}},
        ],
    },
    {
        'name': '1-Pleat Trouser (MM&S)',
        'fabric_width': 60,
        'pieces': [
            {'module': 'trouser_front', 'name': 'Front Panel', 'cut_count': 2, 'kwargs': {'num_pleats': 1}},
            {'module': 'trouser_back',  'name': 'Back Panel',  'cut_count': 2, 'kwargs': {'num_pleats': 1}},
        ],
    },
    {
        'name': '2-Pleat Trouser (MM&S)',
        'pieces': [
            {'module': 'trouser_front', 'name': 'Front Panel', 'cut_count': 2, 'kwargs': {'num_pleats': 2}},
            {'module': 'trouser_back',  'name': 'Back Panel',  'cut_count': 2, 'kwargs': {'num_pleats': 2}},
        ],
    },
]
