{
    'name': 'Extensión RFID - Empleados',
    'version': '1.0',
    'summary': 'Añade ID de tarjeta RFID a la ficha del empleado',
    'category': 'Human Resources',
    'author': 'Tu Nombre / DAM',
    'depends': [
        'hr',
        'maya_core', # CRÍTICO para evitar el error 500
    ],
    'data': [
        'views/views.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}