# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import datetime
from odoo.fields import Datetime
from odoo.exceptions import ValidationError

class MayaAttendance(models.Model):
    # Nombre y descripcion del modelo
    _name = 'maya_attendance.attendance'
    _description = 'Registro de Fichajes'

    # Campo id de empleado
    employee_id = fields.Many2one(
        'maya_core.employee', 
        string='Empleado', 
        required=True, 
        index=True, 
    )
    
    # Campo apellido del empleado
    employee_surname = fields.Char(
        related='employee_id.surname', 
        string='Apellido Empleado', 
        store=True, 
        index=True
    )

    # Campo fecha
    check_date = fields.Date(
        string='Fecha', 
        required=True, 
        index=True, 
        default=fields.Date.context_today
    )
    
    # Campo hora
    check_time = fields.Datetime(
        string='Hora del Fichaje', 
        required=True, 
        default=fields.Datetime.now
    )

    #Campo hora que muestra solo la hora
    check_time_only = fields.Char(
        string='Hora del Fichaje',
        compute="_compute_time"
    )

    # Campo para seleccionar el tipo de fichaje
    attendance_type = fields.Selection([
        ('I', 'Entrada'),
        ('O', 'Salida'),
        ('P', 'Pausa')
    ], string='Tipo', required=True)

    # Campo para guardar el id
    terminal_id = fields.Char(string='ID Terminal', required=True)
    
    # Campo para guardar la localizacion
    location_id = fields.Many2one(
        'maya_core.location', 
        string='Ubicación', 
        required=True
    )

    justification = fields.Text(string="Justificación")
    total_time = fields.Char(string="Entrada")
    
    # Calcula la hora actual
    def _compute_time(self):
        for rec in self:
            if rec.check_time:
                # Convertimos la hora de UTC a la zona horaria del contexto del usuario
                local_time = Datetime.context_timestamp(self, rec.check_time)
                rec.check_time_only = local_time.strftime("%H:%M")
            else:
                rec.check_time_only = ""
    
    @api.constrains('attendance_type', 'justification')
    def _check_justification(self):
        for rec in self:
            if rec.attendance_type == 'P' and not rec.justification:
                raise ValidationError("La pausa requiere justificación")