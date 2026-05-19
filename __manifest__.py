{
    'name': 'Maya | Attendance',
    'version': '1.0',
    'summary': 'Modulo Maya | Attendance para la gestion del fichaje',
    'depends': [
        'hr',
        'maya_core',
        #'website',
        'project',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',  
        'views/config_settings_view.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}