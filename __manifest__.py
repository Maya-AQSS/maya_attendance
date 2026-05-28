{
    'name': 'Maya | Attendance',
    'version': '1.0',
    'summary': 'Modulo Maya | Attendance para la gestion del fichaje',
    'depends': [
        'maya_core',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',  
        'views/config_settings_view.xml',
    ],
    'application': True,
    'installable': True,
    'license': 'LGPL-3',
}