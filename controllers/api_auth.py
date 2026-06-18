# -*- coding: utf-8 -*-
import json
import logging

from jose import jwt, JWTError        # pip install python-jose
from odoo import http
from odoo.http import request, Response

_logger = logging.getLogger(__name__)

# Configuración de Keycloak
# Mejor moverlos a ir.config_parameter para no hardcodearlos.
# En prod sera distinto que en debug
KEYCLOAK_REALM_URL = "http://keycloak:8080/auth/realms/CEED"
KEYCLOAK_ISSUER    = "http://localhost:8080/auth/realms/CEED"
KEYCLOAK_AUDIENCE  = "odoo19-sso"   # Client ID de Keycloak


def json_response(data, status=200):
  """
  Devuelve una respuesta JSON.
  """
  return Response(
    json.dumps(data, default=str),
    status=status,
    mimetype='application/json',
  )


def error_response(message, code, http_status=400):
  """
  Devuelve una respuesta JSON de error.
  """
  return json_response(
    {'success': False, 'error': message, 'code': code},
    status=http_status,
  )


class ApiBaseController(http.Controller):

  # Autenticar la aplicación
  def _authenticate_app(self):
    """
    Valida que la petición viene de una app autorizada mediante Bearer token.
    Usa _check_credentials() de Odoo que maneja el hash internamente.
    """
    auth_header = request.httprequest.headers.get('Authorization', '')

    if not auth_header.startswith('Bearer '):
        return None, error_response(
            'Header Authorization requerido. '
            'Formato: Authorization: Bearer <api_key>',
            'MISSING_AUTH', 401,
        )

    api_key = auth_header[len('Bearer '):]

    try:
        # _check_credentials recibe la key en CLARO,
        # la hashea internamente y la compara con la BD.
        # Devuelve el user_id si es válida, None si no.
        uid = request.env['res.users.apikeys'].sudo()._check_credentials(
            scope='rpc',
            key=api_key,
        )

        if not uid:
            return None, error_response(
                'API key inválida o expirada.',
                'INVALID_API_KEY', 401,
            )

        app_user = request.env['res.users'].sudo().browse(uid)
        if not app_user.exists() or not app_user.active:
            return None, error_response(
                'Usuario de servicio inactivo.',
                'SERVICE_USER_INACTIVE', 401,
            )

        return app_user, None

    except Exception as e:
        _logger.warning('Error validando API key: %s', e)
        return None, error_response(
            'API key inválida o expirada.',
            'INVALID_API_KEY', 401,
        )

  # Identificar el usuario humano (via Keycloak JWT)
  def _identify_human_user(self, keycloak_token: str):
    """
    Valida el JWT de Keycloak del usuario activo en la sesión de keycloak.
    Extrae el preferred_username y busca el usuario en Odoo.
    Devuelve (odoo_user, None) o (None, error_response).
    """
    if not keycloak_token:
      return None, error_response(
            'Se requiere el token Keycloak del usuario activo '
            '(campo "keycloak_token" en el body).',
            'MISSING_USER_TOKEN', 400,
      )

    # Obtener la clave pública de Keycloak para verificar la firma del JWT
    # En producción cachear esta clave para no pedirla en cada request
    try:
        import requests as http_requests
        jwks_url = f"{KEYCLOAK_REALM_URL}/protocol/openid-connect/certs"
        jwks = http_requests.get(jwks_url, timeout=5).json()
    except Exception as e:
        _logger.error('No se pudo obtener JWKS de Keycloak: %s', e)
        return None, error_response(
            'No se pudo verificar el token: error contactando Keycloak.',
            'KEYCLOAK_UNAVAILABLE', 503,
        )

    try:
        # Verificar firma, expiración e issuer del JWT
        payload = jwt.decode(
            keycloak_token,
            jwks,
            algorithms=['RS256'],
            audience=KEYCLOAK_AUDIENCE,
            issuer=KEYCLOAK_ISSUER,
        )
    except JWTError as e:
        _logger.warning('JWT inválido: %s', e)
        return None, error_response(
            'Token de usuario inválido o expirado. '
            'El usuario debe volver a autenticarse.',
            'INVALID_USER_TOKEN', 401,
        )

    # Extraer el login (preferred_username de Keycloak = login en Odoo)
    username = payload.get('preferred_username')
    if not username:
        return None, error_response(
            'El token no contiene preferred_username.',
            'TOKEN_MISSING_USERNAME', 400,
        )

    # Buscar el usuario en Odoo por login
    odoo_user = request.env['res.users'].sudo().search([
        ('login', '=', username.upper()),
        ('active', '=', True),
    ], limit=1)

    if not odoo_user:
        return None, error_response(
            f'El usuario "{username}" no existe en Odoo.',
            'USER_NOT_FOUND', 404,
        )

    return odoo_user, None
  
  def _authenticate(self, body: dict = None):
    """
    Autenticación completa en dos niveles:
        1. Valida que la app es legítima via API key
        2. Identifica al usuario humano via JWT de Keycloak

    Devuelve (odoo_user_humano, None) o (None, error_response).
    """
    # Nivel 1: De qué aplicación viene
    _, err = self._authenticate_app()
    if err:
        return None, err

    # Nivel 2: ¿qué usuario humano está detrás?
    keycloak_token = (body or {}).get('keycloak_token', '')
    return self._identify_human_user(keycloak_token)

  def _get_employee(self, user):
    """
    Obtiene el empleado asociado a un usuario.
    """
    employee = request.env['maya_core.employee'].sudo().search([
        ('user_id', '=', user.id),
    ], limit=1)

    if not employee:
        return None, error_response(
            'No existe ningún empleado vinculado a este usuario.',
            'EMPLOYEE_NOT_FOUND', 404,
        )
    return employee, None