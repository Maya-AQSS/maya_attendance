# -*- coding: utf-8 -*-
"""Fichajes registrados por otros servicios de Maya (D21).

A Odoo solo se escribe por sus endpoints, nunca por FDW. El dashboard registra la entrada y la salida de
un empleado con este endpoint, como un usuario técnico de Odoo que solo tiene el grupo
``maya_attendance.group_attendance_clock`` (crear fichajes y nada más) y una clave de API de Odoo de
ámbito ``maya_attendance``: vale para este endpoint y no para /json/2 ni XML-RPC, que piden claves de
ámbito ``rpc`` o globales. El usuario y su clave los crea el despliegue con
``scripts/registrar_usuario_fichajes.py``.

``POST /api/v1/attendance/clock``

Cabeceras
    ``Authorization: Bearer <clave de API del usuario técnico>`` y ``Content-Type: application/json``.

Cuerpo (JSON)
    ``oauth_uid``   obligatorio: ``res_users.oauth_uid`` del empleado, el ``sub`` de su token de Keycloak
                    (D26, R4).
    ``type``        obligatorio: ``"I"`` (entrada) u ``"O"`` (salida).
    ``terminal_id`` opcional: origen del fichaje (texto de 1 a 64 caracteres); por defecto ``"api"``.

La hora es la del servidor de Odoo en el momento de la petición; el cliente no la elige.

Respuestas (JSON, siempre con ``success``; los errores, con ``code`` y ``error``)
    201 ``{"success": true, "attendance": {...}}`` y, en las salidas, ``"check_in"``: la entrada que cierra.
    400 ``INVALID_JSON``, ``INVALID_OAUTH_UID``, ``INVALID_TYPE``, ``INVALID_TERMINAL_ID``.
    401 ``MISSING_API_KEY``, ``INVALID_API_KEY`` (con ``WWW-Authenticate: Bearer``).
    403 ``FORBIDDEN``: la clave es de un usuario sin el grupo; ``ACCESS_DENIED``: el grupo no da permiso.
    404 ``EMPLOYEE_NOT_FOUND``: ningún usuario activo con ese ``oauth_uid``, o no tiene empleado.
    409 ``AMBIGUOUS_OAUTH_UID``; ``ALREADY_CHECKED_IN``: ya hay una entrada abierta hoy (con
        ``check_in``); ``NO_OPEN_CHECK_IN``: hoy no hay ninguna entrada abierta que cerrar.
    422 ``VALIDATION_ERROR``: el modelo rechaza el fichaje.
    503 ``LOCATION_NOT_CONFIGURED``: no hay ubicación para los fichajes de la API.

«Hoy» es el día en Europe/Madrid. Hay una entrada abierta si el último fichaje del empleado de hoy es
una entrada; una salida o una pausa la cierran, como en el quiosco (``buscar_estado_fichaje``) y en la
vista de lectura del dashboard (``v_app_attendances``). Dos fichajes a la vez del mismo empleado no se
duplican: el segundo espera al primero y Odoo lo reintenta (ver ``_lock_employee``).
"""
import logging
import re
from datetime import datetime, time, timedelta

import pytz

from odoo import fields, http
from odoo.exceptions import AccessError, UserError
from odoo.http import request
from odoo.tools import SQL

from ...models.res.res_users import API_KEY_SCOPE, CLOCK_GROUP

_logger = logging.getLogger(__name__)

CLOCK_TYPES = ('I', 'O')
TIMEZONE = 'Europe/Madrid'
DEFAULT_TERMINAL_ID = 'api'
TERMINAL_ID_MAX_LENGTH = 64
OAUTH_UID_MAX_LENGTH = 255
LOCATION_PARAM = 'maya_attendance.api_location_id'
DEFAULT_LOCATION_XMLID = 'maya_core.location_CEED'

_BEARER_RE = re.compile(r'^bearer\s+(\S+)\s*$', re.IGNORECASE)


def _json(status, payload, headers=None):
    return request.make_json_response(payload, headers=headers, status=status)


def _error(status, code, message, headers=None, **extra):
    return _json(status, {'success': False, 'code': code, 'error': message, **extra}, headers=headers)


def _iso_utc(value):
    """Datetime de Odoo (UTC sin zona) en ISO 8601 con «Z»."""
    return value.strftime('%Y-%m-%dT%H:%M:%SZ')


def _local_day(now_utc):
    """Día local (Europe/Madrid) de ``now_utc`` y sus límites en UTC sin zona, como guarda Odoo."""
    tz = pytz.timezone(TIMEZONE)
    day = pytz.utc.localize(now_utc).astimezone(tz).date()
    start = tz.localize(datetime.combine(day, time.min)).astimezone(pytz.utc).replace(tzinfo=None)
    end = tz.localize(datetime.combine(day + timedelta(days=1), time.min)).astimezone(pytz.utc).replace(tzinfo=None)
    return day, start, end


def _attendance_summary(attendance):
    return {
        'id': attendance.id,
        'type': attendance.attendance_type,
        'check_time': _iso_utc(attendance.check_time),
        'terminal_id': attendance.terminal_id,
    }


class AttendanceClockController(http.Controller):

    @http.route(
        '/api/v1/attendance/clock',
        type='http',
        auth='none',
        methods=['POST'],
        csrf=False,
        save_session=False,
    )
    def clock(self, **kwargs):
        service_user, error = self._authenticate_service()
        if error:
            return error

        data, error = self._parse_body()
        if error:
            return error
        oauth_uid, clock_type, terminal_id = data

        employee, error = self._find_employee(oauth_uid)
        if error:
            return error

        location = self._clock_location()
        if not location:
            _logger.warning('Fichajes por API: falta la ubicación (%s o %s)', LOCATION_PARAM, DEFAULT_LOCATION_XMLID)
            return _error(503, 'LOCATION_NOT_CONFIGURED',
                          'No hay ubicación configurada para los fichajes de la API.')

        self._lock_employee(employee)

        now = fields.Datetime.now()
        day, day_start, day_end = _local_day(now)
        last = request.env['maya_attendance.attendance'].sudo().search([
            ('employee_id', '=', employee.id),
            ('check_time', '>=', day_start),
            ('check_time', '<', day_end),
        ], order='check_time desc, id desc', limit=1)
        open_check_in = last if last.attendance_type == 'I' else last.browse()

        if clock_type == 'I' and open_check_in:
            return _error(409, 'ALREADY_CHECKED_IN', 'El empleado ya tiene una entrada abierta hoy.',
                          check_in=_attendance_summary(open_check_in))
        if clock_type == 'O' and not open_check_in:
            return _error(409, 'NO_OPEN_CHECK_IN', 'El empleado no tiene hoy ninguna entrada abierta que cerrar.')

        values = {
            'employee_id': employee.id,
            'attendance_type': clock_type,
            'check_time': now,
            'check_date': day,
            'terminal_id': terminal_id,
            'location_id': location.id,
        }
        # Sin sudo: lo crea el usuario técnico y valen sus permisos (solo crear fichajes). El punto de
        # guardado deshace la fila si el modelo la rechaza, porque la petición termina con commit.
        try:
            with request.env.cr.savepoint():
                attendance = request.env['maya_attendance.attendance'].create(values)
        except AccessError:
            _logger.warning('Fichajes por API: el usuario técnico %s no puede crear fichajes', service_user.login)
            return _error(403, 'ACCESS_DENIED', 'El usuario técnico no tiene permiso para crear fichajes.')
        except UserError as exc:
            return _error(422, 'VALIDATION_ERROR', exc.args[0] if exc.args else str(exc))

        _logger.info('Fichaje %s (%s) del empleado %s registrado por API: usuario técnico %s, terminal %s',
                     attendance.id, clock_type, employee.id, service_user.login, terminal_id)

        payload = {
            'success': True,
            'attendance': {
                'id': attendance.id,
                'employee_id': employee.id,
                'type': clock_type,
                'check_time': _iso_utc(now),
                'check_date': fields.Date.to_string(day),
                'terminal_id': terminal_id,
                'location_id': location.id,
            },
        }
        if clock_type == 'O':
            payload['check_in'] = _attendance_summary(open_check_in)
        return _json(201, payload)

    # ------------------------------------------------------------------
    # Pasos
    # ------------------------------------------------------------------

    def _authenticate_service(self):
        """Usuario técnico de la clave de API (``Authorization: Bearer``), que debe tener el grupo."""
        match = _BEARER_RE.match(request.httprequest.headers.get('Authorization', ''))
        unauthorized = [('WWW-Authenticate', 'Bearer')]
        if not match:
            return None, _error(401, 'MISSING_API_KEY',
                                'Falta la cabecera «Authorization: Bearer <clave de API>».',
                                headers=unauthorized)

        uid = request.env['res.users.apikeys']._check_credentials(scope=API_KEY_SCOPE, key=match.group(1))
        if not uid:
            return None, _error(401, 'INVALID_API_KEY', 'Clave de API no válida o caducada.',
                                headers=unauthorized)

        request.update_env(user=uid)
        user = request.env.user
        if not user.has_group(CLOCK_GROUP):
            _logger.warning('Fichajes por API: el usuario %s no tiene el grupo %s', user.login, CLOCK_GROUP)
            return None, _error(403, 'FORBIDDEN', 'El usuario de la clave no puede registrar fichajes.')
        return user, None

    def _parse_body(self):
        try:
            body = request.get_json_data()
        except ValueError:
            return None, _error(400, 'INVALID_JSON', 'El cuerpo debe ser un objeto JSON.')
        if not isinstance(body, dict):
            return None, _error(400, 'INVALID_JSON', 'El cuerpo debe ser un objeto JSON.')

        oauth_uid = body.get('oauth_uid')
        if not isinstance(oauth_uid, str) or not oauth_uid.strip() or len(oauth_uid) > OAUTH_UID_MAX_LENGTH:
            return None, _error(400, 'INVALID_OAUTH_UID',
                                '«oauth_uid» es obligatorio: el sub de Keycloak del empleado.')

        clock_type = body.get('type')
        if clock_type not in CLOCK_TYPES:
            return None, _error(400, 'INVALID_TYPE', '«type» debe ser "I" (entrada) u "O" (salida).')

        terminal_id = body.get('terminal_id', DEFAULT_TERMINAL_ID)
        if (not isinstance(terminal_id, str) or not terminal_id.strip()
                or len(terminal_id) > TERMINAL_ID_MAX_LENGTH):
            return None, _error(400, 'INVALID_TERMINAL_ID',
                                f'«terminal_id» debe ser un texto de 1 a {TERMINAL_ID_MAX_LENGTH} caracteres.')

        return (oauth_uid.strip(), clock_type, terminal_id.strip()), None

    def _find_employee(self, oauth_uid):
        """Empleado del usuario activo con ese ``oauth_uid`` (lectura con sudo: el usuario técnico no lee nada)."""
        users = request.env['res.users'].sudo().search([('oauth_uid', '=', oauth_uid)], limit=2)
        if len(users) > 1:
            _logger.warning('Fichajes por API: %s usuarios activos con el mismo oauth_uid', len(users))
            return None, _error(409, 'AMBIGUOUS_OAUTH_UID', 'Hay más de un usuario con ese oauth_uid.')
        employee = None
        if users:
            employee = users.maya_employee_id or request.env['maya_core.employee'].sudo().search(
                [('user_id', '=', users.id)], limit=1)
        if not employee:
            return None, _error(404, 'EMPLOYEE_NOT_FOUND', 'No hay ningún empleado con ese oauth_uid.')
        return employee, None

    def _clock_location(self):
        """Ubicación de los fichajes de la API: la de Ajustes o, si no hay, la sede (maya_core.location_CEED)."""
        location_id = request.env['ir.config_parameter'].sudo().get_param(LOCATION_PARAM)
        Location = request.env['maya_core.location'].sudo()
        location = Location.browse(int(location_id)).exists() if location_id and location_id.isdigit() else Location
        if not location:
            location = request.env.ref(DEFAULT_LOCATION_XMLID, raise_if_not_found=False) or Location
            location = location.sudo().exists()
        return location

    def _lock_employee(self, employee):
        """Serializa los fichajes del mismo empleado.

        Odoo trabaja en REPEATABLE READ: un ``SELECT … FOR UPDATE`` haría esperar a la segunda petición,
        pero con la foto de datos de antes de que la primera guardara su fichaje, y lo duplicaría. Un
        ``UPDATE`` de la fila del empleado sí la hace fallar por concurrencia cuando la primera termina, y
        Odoo reintenta la petición entera (``service.model.retrying``), que ya ve el fichaje nuevo.
        """
        request.env.cr.execute(SQL(
            'UPDATE %s SET write_date = write_date WHERE id = %s',
            SQL.identifier(employee._table), employee.id,
        ))
