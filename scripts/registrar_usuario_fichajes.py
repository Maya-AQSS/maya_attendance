# -*- coding: utf-8 -*-
# pylint: skip-file
"""Registra el usuario técnico de fichajes y su clave de API (D21). Se ejecuta con el shell de Odoo.

Qué hace (``res.users._maya_attendance_register_clock_user``):
  - crea o actualiza el usuario técnico (por defecto ``svc-maya-dashboard``): activo, sin contraseña y con
    el grupo «Maya | Asistencia: registrar fichajes por API» como único grupo, así que solo puede crear
    fichajes y únicamente por ``POST /api/v1/attendance/clock``;
  - le registra la clave de API que le pasa el despliegue (Odoo guarda solo su hash; ámbito
    ``maya_attendance``, sin caducidad). Si ya tenía una clave con el mismo nombre, la sustituye: para
    rotarla basta con volver a ejecutarlo con la clave nueva.

La clave la genera el despliegue y vive en Vault (``ODOO_ATTENDANCE_API_KEY`` de ``secret/maya-dashboard``,
la que usa el dashboard); por ejemplo ``openssl rand -hex 32``. Debe tener al menos 32 caracteres (letras,
números, «-» o «_»). Este script no la muestra nunca.

Variables de entorno:
  MAYA_ATTENDANCE_API_KEY       la clave (o MAYA_ATTENDANCE_API_KEY_FILE con la ruta de un fichero que la
                                contenga); obligatoria
  MAYA_ATTENDANCE_LOGIN         login del usuario técnico (por defecto svc-maya-dashboard)
  MAYA_ATTENDANCE_KEY_NAME      nombre de la clave (por defecto maya-dashboard)

El script se lee por la entrada estándar, así que la clave llega por una variable de entorno. Ejemplo en el
clúster, sin que la clave pase por la línea de órdenes ni por la salida (la primera línea de la entrada es
la clave y el resto, el script; el módulo ya actualizado en la base de datos):

    { vault kv get -field=ODOO_ATTENDANCE_API_KEY secret/maya-dashboard
      cat scripts/registrar_usuario_fichajes.py
    } | kubectl -n maya-erp exec -i deploy/odoo-maya-app -- bash -c '
        IFS= read -r MAYA_ATTENDANCE_API_KEY; export MAYA_ATTENDANCE_API_KEY
        odoo shell -c /etc/odoo/odoo.conf -d maya_erp --no-http'

(con las opciones de conexión a la base de datos que use el servidor, si no están en odoo.conf).
Termina con «RESULTADO: OK …»; si algo falla, no guarda nada.
"""
import os
import sys

key_file = os.environ.get('MAYA_ATTENDANCE_API_KEY_FILE')
if key_file:
    with open(key_file, encoding='utf-8') as handle:
        api_key = handle.read().strip()
else:
    api_key = os.environ.get('MAYA_ATTENDANCE_API_KEY', '').strip()
login = os.environ.get('MAYA_ATTENDANCE_LOGIN', 'svc-maya-dashboard').strip()
key_name = os.environ.get('MAYA_ATTENDANCE_KEY_NAME', 'maya-dashboard').strip()

if not api_key:
    print('RESULTADO: ERROR — falta la clave (MAYA_ATTENDANCE_API_KEY o MAYA_ATTENDANCE_API_KEY_FILE)')
    sys.exit(1)

try:
    user = env['res.users']._maya_attendance_register_clock_user(login, api_key, key_name=key_name)  # noqa: F821
    env.cr.commit()  # noqa: F821
except Exception as exc:  # noqa: BLE001
    env.cr.rollback()  # noqa: F821
    print(f'RESULTADO: ERROR — {exc}')
    sys.exit(1)

print(f'RESULTADO: OK — usuario técnico «{user.login}» (id {user.id}) con la clave «{key_name}» registrada')
