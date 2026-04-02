from odoo import models, fields

class MayaCoreEmployee(models.Model):
    _inherit = 'maya_core.employee' #Hereda de employee de maya_core

    id_tarjeta_rfid = fields.Integer( #Campo integer para el codigo RFID
        string='ID Tarjeta RFID',
        help="Identificador físico de la tarjeta para poder fichar",
        index=True,     
        required = True
    )

    _sql_constraints = [ #Restricciones de la base de datos
        (
            'rfid_unique', 
            'unique(id_tarjeta_rfid)', 
            'Error: El ID de tarjeta RFID ya está asignado a otro empleado.'
        )
    ]