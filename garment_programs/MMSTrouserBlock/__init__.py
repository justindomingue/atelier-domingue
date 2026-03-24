GARMENTS = [
    {
        # MM&S pp. 30–33: the 0-pleat block carries a 2 cm front dart on the
        # creaseline — it is "Trousers with Dart", not a true flat front.
        'name': 'Trouser with Dart (MM&S)',
        'fabric_width': 60,
        'pieces': [
            {'module': 'trouser_front', 'name': 'Front Panel', 'cut_count': 2, 'grain_axis': 'y', 'kwargs': {'num_pleats': 0}},
            {'module': 'trouser_back',  'name': 'Back Panel',  'cut_count': 2, 'grain_axis': 'y', 'kwargs': {'num_pleats': 0}},
        ],
    },
    {
        'name': '1-Pleat Trouser (MM&S)',
        'fabric_width': 60,
        'pieces': [
            {'module': 'trouser_front', 'name': 'Front Panel', 'cut_count': 2, 'grain_axis': 'y', 'kwargs': {'num_pleats': 1}},
            {'module': 'trouser_back',  'name': 'Back Panel',  'cut_count': 2, 'grain_axis': 'y', 'kwargs': {'num_pleats': 1}},
        ],
    },
    {
        'name': '2-Pleat Trouser (MM&S)',
        'fabric_width': 60,
        'pieces': [
            {'module': 'trouser_front', 'name': 'Front Panel', 'cut_count': 2, 'grain_axis': 'y', 'kwargs': {'num_pleats': 2}},
            {'module': 'trouser_back',  'name': 'Back Panel',  'cut_count': 2, 'grain_axis': 'y', 'kwargs': {'num_pleats': 2}},
        ],
    },
]
