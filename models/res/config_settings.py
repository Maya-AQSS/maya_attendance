# -*- coding: utf-8 -*-
from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    double_signing_time = fields.Integer(
        string = 'Tiempo de fichaje doble en segudos',
        config_parameter='maya_attendance.double_signing_time',
        help = 'Tiempo en que se considera que el fichaje es doble'
    )

    attendance_api_location_id = fields.Many2one(
        'maya_core.location',
        string='Ubicación de los fichajes por API',
        config_parameter='maya_attendance.api_location_id',
        help='Ubicación que se guarda en los fichajes que registran otros servicios (p. ej. el dashboard) '
             'por /api/v1/attendance/clock. Si no se indica, la sede CEED.'
    )

