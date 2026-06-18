# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.http import request, Response
import json
import logging

_logger = logging.getLogger(__name__)


class EmployeeLanguageController(http.Controller):
  """
  API para cambiar el idioma del empleado vinculado al usuario autenticado.

  Endpoint: PATCH /api/v1/employee/lang
  Auth:     Sesión Odoo activa (cookie de sesión) o API key (header Api-Key)

  El usuario solo puede cambiar su PROPIO idioma.
  """

  @http.route(
      '/api/v1/employee/lang',
      type='json',
      auth='user',       # requiere usuario autenticado
      methods=['PATCH'],
      cors='*',
      csrf=False,
  )
  def update_employee_lang(self, **kwargs):
    """
    Cambia el idioma del empleado vinculado al usuario autenticado.

    Body JSON esperado:
        { "lang": "es_ES" }

    Respuestas:
        200  { "success": true, "lang": "es_ES", "employee_id": 42 }
        400  { "error": "...", "code": "..." }
    """
    body = request.get_json_data() or kwargs
    lang_code = body.get('lang', '').strip()

    # Validar que se ha enviado el idioma
    if not lang_code:
      return self._error(
          'El campo "lang" es obligatorio.',
          'MISSING_LANG',
          400,
      )

    # Validar que el idioma existe y está activo en Odoo 
    active_lang = request.env['res.lang'].sudo().search([
        ('code', '=', lang_code),
        ('active', '=', True),
    ], limit=1)

    if not active_lang:
      return self._error(
          f'El idioma "{lang_code}" no está activo en Odoo. '
          'Actívalo primero en Ajustes → Idiomas.',
          'LANG_NOT_ACTIVE',
          400,
      )

    # Buscar el empleado vinculado al usuario autenticado 
    current_user = request.env.user
    employee = request.env['maya_core.employee'].sudo().search([
        ('user_id', '=', current_user.id),
    ], limit=1)

    if not employee:
      return self._error(
          'No existe ningún empleado vinculado a tu usuario.',
          'EMPLOYEE_NOT_FOUND',
          404,
      )

    # Aplicar el cambio 
    try:
      employee.lang = lang_code   # dispara _inverse_lang → user_id.lang
      _logger.info(
          'Idioma actualizado: employee_id=%s user_id=%s lang=%s',
          employee.id, current_user.id, lang_code,
      )
    except Exception as e:
      _logger.exception('Error actualizando idioma del empleado %s', employee.id)
      return self._error(str(e), 'UPDATE_ERROR', 500)

    return {
        'success': True,
        'employee_id': employee.id,
        'lang': lang_code,
        'lang_name': active_lang.name,
    }

  @staticmethod
  def _error(message, code, http_status=400):
    """
    Devuelve un dict de error estándar.
    Para errores HTTP no-200, Odoo los enviará igualmente como 200
    en modo type='json'; para forzar el status code usa type='http'.
    """
    return {
        'success': False,
        'error': message,
        'code': code,
        'http_status': http_status,
    }
