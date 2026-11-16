# -*- coding: utf-8 -*-
"""Endpoints del quiosco de fichajes: solo con la clave del usuario técnico del quiosco.

Antes valía cualquier clave `rpc` o global de cualquier usuario activo (los endpoints trabajan con sudo) y
cambiar_hora_fichaje pedía además la cabecera `api-key: pass`.

  odoo -d <bd de pruebas> -i maya_attendance --test-tags /maya_attendance --stop-after-init
"""
import json

from odoo.tests import HttpCase, new_test_user, tagged

KIOSK_GROUP = 'maya_attendance.group_attendance_kiosk'
RFID = 'RFIDQUIOSCO1'


@tagged('post_install', '-at_install')
class TestKioskApi(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.location = cls.env['maya_core.location'].create({'name': 'Sede del quiosco', 'address': 'Calle 1'})
        cls.employee = cls.env['maya_core.employee'].create({
            'employee_type': 'profesor',
            'position_type': 'ESPJ',
            'team_ids': [(6, 0, [])],
            'id_card_rfid': RFID,
        })
        Users = cls.env['res.users']
        cls.kiosk_key = 'clave-de-prueba-del-quiosco-0123456789abcdef'
        cls.kiosk_user = Users._maya_attendance_register_clock_user(
            'svc-test-quiosco', cls.kiosk_key, key_name='quiosco', group=KIOSK_GROUP)
        cls.clock_key = 'clave-de-prueba-del-dashboard-0123456789abcdef'
        Users._maya_attendance_register_clock_user('svc-test-dashboard', cls.clock_key, key_name='dashboard')
        internal = new_test_user(cls.env, login='interno.quiosco', groups='base.group_user')
        Keys = cls.env['res.users.apikeys'].with_user(internal).sudo()
        cls.global_key = Keys._generate(None, 'global', None)
        cls.rpc_key = Keys._generate('rpc', 'rpc', None)

    def _get(self, url, key):
        headers = {'Authorization': f'Bearer {key}'} if key else {}
        return self.url_open(url, headers=headers)

    def test_kiosk_key_reads_the_employee(self):
        response = self._get(f'/api/v1/empleado_rfid/{RFID}', self.kiosk_key)

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['id_odoo'], self.employee.id)
        self.assertTrue(self.kiosk_user.has_group(KIOSK_GROUP))

    def test_without_key(self):
        self.assertEqual(self._get(f'/api/v1/empleado_rfid/{RFID}', None).status_code, 401)

    def test_rpc_key_of_any_user_is_not_valid(self):
        self.assertEqual(self._get(f'/api/v1/empleado_rfid/{RFID}', self.rpc_key).status_code, 401)

    def test_global_key_of_any_user_is_forbidden(self):
        response = self._get(f'/api/v1/empleado_rfid/{RFID}', self.global_key)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['code'], 'FORBIDDEN')

    def test_dashboard_key_is_not_the_kiosk(self):
        self.assertEqual(self._get(f'/api/v1/empleado_rfid/{RFID}', self.clock_key).status_code, 403)

    def test_double_signing_check_works(self):
        """buscar_fichaje usaba self.env en el controlador (error 500)."""
        response = self._get(f'/api/v1/buscar_fichaje/{self.employee.id}', self.kiosk_key)

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['fichaje_doble'], False)

    def test_change_time_needs_no_fixed_password(self):
        attendance = self.env['maya_attendance.attendance'].create({
            'employee_id': self.employee.id,
            'attendance_type': 'I',
            'terminal_id': 'quiosco',
            'location_id': self.location.id,
            'check_date': '2026-01-01',
            'check_time': '2026-01-01 08:00:30',
        })
        payload = {'jsonrpc': '2.0', 'method': 'call', 'params': {
            'employee_id': self.employee.id,
            'last_hour': '2026-01-01 08:00:30',
            'new_hour': '2026-01-01 07:55:00',
            'type': 'I',
        }}

        response = self.url_open('/api/v1/cambiar_hora_fichaje', data=json.dumps(payload), method='POST', headers={
            'Content-Type': 'application/json', 'Authorization': f'Bearer {self.kiosk_key}'})

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['result']['status'], 'success', response.text)
        attendance.invalidate_recordset()
        self.assertEqual(str(attendance.check_time), '2026-01-01 07:55:00')
