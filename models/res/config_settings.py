# -*- coding: utf-8 -*-
from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    double_signing_time = fields.Integer(
        string = 'Tiempo de fichaje doble en segudos',
        config_parameter='maya_attendance.double_signing_time',
        help = 'Tiempo en que se considera que el fichaje es doble'
    )
    