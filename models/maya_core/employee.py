from odoo import models, fields, api

class MayaCoreEmployee(models.Model):
    _inherit = 'maya_core.employee' #Hereda de employee de maya_core


    id_card_rfid = fields.Char( #Campo Char para el codigo RFID
        string='ID Tarjeta RFID',
        help="Identificador físico de la tarjeta para poder fichar",
        index=True,     
    )

    id_rfid_decimal = fields.Char( #Campo que guarda el codigo rfid en formato decimal
        string="ID Tarjeta RFID Decimal",
        compute="_compute_rfid", #Calculamos el codigo a partir del rfid en hexadecimal
    )

    
    is_editing = fields.Boolean(default=False) # El "interruptor"

    attendance_ids = fields.One2many(
        'maya_attendance.attendance', 
        'employee_id', 
        string ='Historial de fichajes'
    )

    def action_toggle_edit(self): #Funcion para cambiar el estado de edicion
        for record in self:
            record.is_editing = not record.is_editing

    @api.depends("id_card_rfid") #Funcion para calcular el codigo rfid en decimal
    def _compute_rfid(self):
        for record in self:
            if record.id_card_rfid and isinstance(record.id_card_rfid, str):
                # Si el codigo es string calculamos de hexadecimal a decimal el codigo
                try:
                    record.id_rfid_decimal = int(record.id_card_rfid, 16)
                except:
                    record.id_rfid_decimal = "0"
            else:
                record.id_rfid_decimal = 0

    #Restricciones de la base de datos
    _unique_rfid = models.Constraint('unique(id_card_rfid)', 'El ID de tarjeta RFID ya está asignado a otro empleado.')
    _unique_dni = models.Constraint('unique(dni)', 'El DNI ya está registrado.')
    