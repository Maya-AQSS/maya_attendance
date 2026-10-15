# -*- coding: utf-8 -*-
import re

from odoo import Command, api, models
from odoo.addons.base.models.res_users import INDEX_SIZE, KEY_CRYPT_CONTEXT
from odoo.exceptions import AccessError, UserError
from odoo.tools import SQL

# Fichajes por API de otros servicios (D21): ver controllers/v1/clock.py
CLOCK_GROUP = 'maya_attendance.group_attendance_clock'
# Ámbito de las claves de API de los usuarios técnicos. Una clave con ámbito solo vale donde se pide ese
# ámbito (este módulo); /json/2 y XML-RPC piden «rpc» o una clave global, así que no la aceptan.
API_KEY_SCOPE = 'maya_attendance'
MIN_API_KEY_LENGTH = 32
_API_KEY_RE = re.compile(r'^[A-Za-z0-9_-]+$')


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def _maya_attendance_register_clock_user(self, login, api_key, key_name='maya-dashboard', name=None):
        """Crea o actualiza un usuario técnico de fichajes y le registra una clave de API (D21).

        Lo usa ``scripts/registrar_usuario_fichajes.py`` desde el shell de Odoo; no es una acción de la
        interfaz. El usuario queda activo, sin contraseña (no puede entrar en la interfaz) y con
        ``group_attendance_clock`` como único grupo: ni interno ni portal, así que solo puede crear
        fichajes. La clave la genera el despliegue (está en Vault) y Odoo guarda solo su hash, con ámbito
        ``maya_attendance`` y sin caducidad; las claves anteriores del usuario con el mismo nombre se
        borran, de modo que volver a ejecutarlo con otra clave es rotarla.

        :param str login: login del usuario técnico (p. ej. ``svc-maya-dashboard``)
        :param str api_key: la clave en claro (al menos 32 caracteres: letras, números, «-» o «_»)
        :param str key_name: nombre de la clave (el servicio que la usa)
        :param str name: nombre visible del usuario (por defecto, el login)
        :returns: el usuario técnico
        """
        if not self.env.is_superuser():
            raise AccessError('Solo el superusuario (shell de Odoo) registra usuarios técnicos de fichajes.')
        if not isinstance(api_key, str) or len(api_key) < MIN_API_KEY_LENGTH or not _API_KEY_RE.match(api_key):
            raise UserError(
                f'La clave de API debe tener al menos {MIN_API_KEY_LENGTH} caracteres: letras, números, «-» o «_».')
        if not login or not key_name:
            raise UserError('Faltan el login del usuario técnico o el nombre de la clave.')

        group = self.env.ref(CLOCK_GROUP)
        # no_reset_password: sin invitación por correo de auth_signup (además, no tiene correo)
        Users = self.sudo().with_context(active_test=False, no_reset_password=True)
        user = Users.search([('login', '=', login)], limit=1)
        if user and (not user.share or user.maya_employee_id or user.oauth_uid):
            raise UserError(
                f'Ya existe el usuario «{login}» y no es técnico (es interno, tiene empleado o entra con '
                'Keycloak): usa otro login.')

        values = {'name': name or login, 'active': True, 'group_ids': [Command.set(group.ids)]}
        if user:
            user.write(values)
        else:
            user = Users.create(dict(values, login=login))

        cr = self.env.cr
        cr.execute(SQL('DELETE FROM res_users_apikeys WHERE user_id = %s AND name = %s', user.id, key_name))
        cr.execute(SQL(
            'INSERT INTO res_users_apikeys (name, user_id, scope, expiration_date, key, index)'
            ' VALUES (%s, %s, %s, NULL, %s, %s)',
            key_name, user.id, API_KEY_SCOPE, KEY_CRYPT_CONTEXT.hash(api_key), api_key[:INDEX_SIZE],
        ))
        self.env.registry.clear_cache()
        return user
