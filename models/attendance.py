# -*- coding: utf-8 -*-
from odoo import models, fields, api

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

    # Campo para seleccionar el tipo de fichaje
    attendance_type = fields.Selection([
        ('I', 'Entrada'),
        ('O', 'Salida')
    ], string='Tipo', required=True)

    # Campo para guardar el id
    terminal_id = fields.Integer(string='ID Terminal', required=True)
    
    # Campo para guardar la localizacion
    location_id = fields.Many2one(
        'maya_core.location', 
        string='Ubicación', 
        required=True
    )