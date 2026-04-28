from odoo import models, fields, api

class MayaCoreEmployee(models.Model):
    _inherit = 'maya_core.employee' #Hereda de employee de maya_core


    id_tarjeta_rfid = fields.Char( #Campo Char para el codigo RFID
        string='ID Tarjeta RFID',
        help="Identificador físico de la tarjeta para poder fichar",
        index=True,     
    )

    id_rfid_decimal = fields.Char( #Campo que guarda el codigo rfid en formato decimal
        string="ID Tarjeta RFID Decimal",
        compute="_compute_rfid", #Calculamos el codigo a partir del rfid en hexadecimal
        store = True,
    )

    
    esta_editando = fields.Boolean(default=False) # El "interruptor"

    attendance_ids = fields.One2many(
        'maya_attendance.attendance', 
        'employee_id', 
        string='Historial de Asistencias'
    )

    def action_toggle_edit(self): #Funcion para cambiar el estado de edicion
        for record in self:
            record.esta_editando = not record.esta_editando

    @api.depends("id_tarjeta_rfid") #Funcion para calcular el codigo rfid en decimal
    def _compute_rfid(self):
        for record in self:
            if record.id_tarjeta_rfid and isinstance(record.id_tarjeta_rfid, str):
                # Si el codigo es string calculamos de hexadecimal a decimal el codigo
                try:
                    record.id_rfid_decimal = int(record.id_tarjeta_rfid, 16)
                except:
                    record.id_rfid_decimal = "0"
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