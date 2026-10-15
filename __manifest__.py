{
    'name': 'Maya | Attendance',
    'version': '1.1',
    'summary': 'Modulo Maya | Attendance para la gestion del fichaje',
    'depends': [
        'maya_core',
        # res.users.oauth_uid (el `sub` de Keycloak): con él identifica al empleado el endpoint de
        # fichajes de los servicios (/api/v1/attendance/clock). Ya lo instala maya_core (auth_oidc).
        'auth_oauth',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
        'views/config_settings_view.xml',
    ],
    'application': True,
    'installable': True,
    'license': 'LGPL-3',
}
