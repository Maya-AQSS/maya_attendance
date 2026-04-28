from odoo import models, fields, api

class MayaCoreEmployee(models.Model):
    _inherit = 'maya_core.employee' #Hereda de employee de maya_core


    id_tarjeta_rfid = fields.Char( #Campo Char para el codigo RFID
        string='ID Tarjeta RFID',
        help="Identificador físico de la tarjeta para poder fichar",
        index=True,     
        required = True,
    )

    id_rfid_decimal = fields.Char( #Campo que guarda el codigo rfid en formato decimal
        string="ID Tarjeta RFID Decimal",
        compute="_compute_rfid", #Calculamos el codigo a partir del rfid en hexadecimal
        store = True
    )

    @api.depends("id_tarjeta_rfid") #Funcion para calcular el codigo rfid en decimal
    def _compute_rfid(self):
        for record in self:
            if record.id_tarjeta_rfid and isinstance(record.id_tarjeta_rfid, str):
                # Si el codigo es string calculamos de hexadecimal a decimal el codigo
                record.id_rfid_decimal = int(record.id_tarjeta_rfid, 16)
               
            else:
                record.id_rfid_decimal = 0

    _sql_constraints = [ #Restricciones de la base de datos
        (
            'rfid_unique', 
            'unique(id_tarjeta_rfid)', 
            'Error: El ID de tarjeta RFID ya está asignado a otro empleado.'
        ),
         (
            'dni_unique',
            'unique(dni)',
            'El DNI ya está registrado.'
        )
    ]