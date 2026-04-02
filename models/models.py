from odoo import models, fields

class MayaCoreEmployee(models.Model):
    _inherit = 'maya_core.employee'

    id_tarjeta_rfid = fields.Integer(
        string='ID Tarjeta RFID',
        help="Identificador físico de la tarjeta para poder fichar",
        index=True,     
        required = True
    )

    _sql_constraints = [
        (
            'rfid_unique', 
            'unique(id_tarjeta_rfid)', 
            'Error: El ID de tarjeta RFID ya está asignado a otro empleado.'
        )
    ]