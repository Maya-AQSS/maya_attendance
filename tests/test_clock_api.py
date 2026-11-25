# -*- coding: utf-8 -*-
import json
from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessError, UserError
from odoo.tests import HttpCase, new_test_user, tagged

URL = '/api/v1/attendance/clock'


@tagged('post_install', '-at_install')
class TestAttendanceClockApi(HttpCase):
    """Endpoint de fichajes de los servicios (D21): POST /api/v1/attendance/clock."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Attendance = cls.env['maya_attendance.attendance']
        cls.location = cls.env['maya_core.location'].create({
            'name': 'Sede de prueba',
            'address': 'Calle de prueba 1',
        })
        cls.env['ir.config_parameter'].sudo().set_param('maya_attendance.api_location_id', str(cls.location.id))

        cls.employee_user = new_test_user(
            cls.env, login='empleado.fichajes', groups='base.group_user', oauth_uid='kc-sub-empleado')
        cls.employee = cls.env['maya_core.employee'].create({
            'employee_type': 'profesor',
            'position_type': 'ESPJ',
            'team_ids': [(6, 0, [])],
        })
        cls.employee_user.maya_employee_id = cls.employee

        cls.service_key = 'clave-de-prueba-del-servicio-0123456789abcdef'
        cls.service_user = cls.env['res.users']._maya_attendance_register_clock_user(
            'svc-test-fichajes', cls.service_key, key_name='test')

    def _post(self, body, key=None, raw=None):
        headers = {'Content-Type': 'application/json'}
        if key is not False:
            headers['Authorization'] = f'Bearer {key or self.service_key}'
        data = raw if raw is not None else json.dumps(body)
        return self.url_open(URL, data=data, headers=headers, method='POST')

    def _clock(self, clock_type, oauth_uid='kc-sub-empleado', **extra):
        return self._post({'oauth_uid': oauth_uid, 'type': clock_type, **extra})

    def _attendances(self):
        return self.Attendance.search([('employee_id', '=', self.employee.id)], order='id')

    # ------------------------------------------------------------------
    # Fichajes
    # ------------------------------------------------------------------

    def test_clock_in_creates_attendance(self):
        response = self._clock('I', terminal_id='dashboard')

        self.assertEqual(response.status_code, 201, response.text)
        body = response.json()
        self.assertTrue(body['success'])
        attendance = self._attendances()
        self.assertEqual(len(attendance), 1)
        self.assertEqual(body['attendance']['id'], attendance.id)
        self.assertEqual(body['attendance']['type'], 'I')
        self.assertEqual(body['attendance']['employee_id'], self.employee.id)
        self.assertTrue(body['attendance']['check_time'].endswith('Z'))
        self.assertNotIn('check_in', body)
        self.assertEqual(attendance.attendance_type, 'I')
        self.assertEqual(attendance.terminal_id, 'dashboard')
        self.assertEqual(attendance.location_id, self.location)
        self.assertEqual(attendance.create_uid, self.service_user, 'lo crea el usuario técnico, sin sudo')

    def test_terminal_defaults_to_api(self):
        self.assertEqual(self._clock('I').status_code, 201)
        self.assertEqual(self._attendances().terminal_id, 'api')

    def test_clock_out_closes_open_entry(self):
        entry = self._clock('I').json()['attendance']

        response = self._clock('O', terminal_id='dashboard')

        self.assertEqual(response.status_code, 201, response.text)
        body = response.json()
        self.assertEqual(body['attendance']['type'], 'O')
        self.assertEqual(body['check_in']['id'], entry['id'])
        self.assertEqual(body['check_in']['check_time'], entry['check_time'])
        self.assertEqual(self._attendances().mapped('attendance_type'), ['I', 'O'])

    def test_second_clock_in_is_rejected(self):
        entry = self._clock('I').json()['attendance']

        response = self._clock('I')

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()['code'], 'ALREADY_CHECKED_IN')
        self.assertEqual(response.json()['check_in']['id'], entry['id'])
        self.assertEqual(len(self._attendances()), 1)

    def test_clock_out_without_open_entry_is_rejected(self):
        response = self._clock('O')

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()['code'], 'NO_OPEN_CHECK_IN')
        self.assertFalse(self._attendances())

    def test_second_clock_out_is_rejected(self):
        self._clock('I')
        self._clock('O')

        response = self._clock('O')

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()['code'], 'NO_OPEN_CHECK_IN')
        self.assertEqual(len(self._attendances()), 2)

    def test_open_entry_of_a_previous_day_does_not_count(self):
        two_days_ago = fields.Datetime.now() - timedelta(days=2)
        self.Attendance.create({
            'employee_id': self.employee.id,
            'attendance_type': 'I',
            'check_time': two_days_ago,
            'check_date': two_days_ago.date(),
            'terminal_id': 'TERM01',
            'location_id': self.location.id,
        })

        self.assertEqual(self._clock('O').json()['code'], 'NO_OPEN_CHECK_IN')
        self.assertEqual(self._clock('I').status_code, 201)

    def test_pause_closes_the_entry(self):
        """Como el quiosco y la vista del dashboard: tras una pausa no hay entrada abierta."""
        self._clock('I')
        self.Attendance.create({
            'employee_id': self.employee.id,
            'attendance_type': 'P',
            'justification': 'Descanso',
            'terminal_id': 'TERM01',
            'location_id': self.location.id,
        })

        self.assertEqual(self._clock('O').json()['code'], 'NO_OPEN_CHECK_IN')
        self.assertEqual(self._clock('I').status_code, 201)

    def test_default_location_is_the_main_site(self):
        self.env['ir.config_parameter'].sudo().set_param('maya_attendance.api_location_id', False)

        self.assertEqual(self._clock('I').status_code, 201)
        self.assertEqual(self._attendances().location_id, self.env.ref('maya_core.location_CEED'))

    # ------------------------------------------------------------------
    # Validaciones
    # ------------------------------------------------------------------

    def test_unknown_oauth_uid(self):
        response = self._clock('I', oauth_uid='kc-sub-desconocido')

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['code'], 'EMPLOYEE_NOT_FOUND')

    def test_user_without_employee(self):
        new_test_user(self.env, login='sin.empleado', groups='base.group_user', oauth_uid='kc-sub-sin-empleado')

        response = self._clock('I', oauth_uid='kc-sub-sin-empleado')

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['code'], 'EMPLOYEE_NOT_FOUND')

    def test_archived_user_is_not_found(self):
        self.employee_user.active = False

        self.assertEqual(self._clock('I').json()['code'], 'EMPLOYEE_NOT_FOUND')

    def test_invalid_type(self):
        for clock_type in ('P', 'X', '', None):
            with self.subTest(clock_type=clock_type):
                response = self._clock(clock_type)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()['code'], 'INVALID_TYPE')
        self.assertFalse(self._attendances())

    def test_missing_oauth_uid(self):
        response = self._post({'type': 'I'})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['code'], 'INVALID_OAUTH_UID')

    def test_invalid_terminal_id(self):
        for terminal_id in ('', 'x' * 65, 42):
            with self.subTest(terminal_id=terminal_id):
                response = self._clock('I', terminal_id=terminal_id)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()['code'], 'INVALID_TERMINAL_ID')

    def test_invalid_json(self):
        for raw in ('no es json', '[1, 2]', ''):
            with self.subTest(raw=raw):
                response = self._post(None, raw=raw)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()['code'], 'INVALID_JSON')

    # ------------------------------------------------------------------
    # Autenticación y permisos
    # ------------------------------------------------------------------

    def test_missing_api_key(self):
        response = self._post({'oauth_uid': 'kc-sub-empleado', 'type': 'I'}, key=False)

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()['code'], 'MISSING_API_KEY')
        self.assertEqual(response.headers.get('WWW-Authenticate'), 'Bearer')

    def test_invalid_api_key(self):
        response = self._post({'oauth_uid': 'kc-sub-empleado', 'type': 'I'}, key='x' * 48)

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()['code'], 'INVALID_API_KEY')
        self.assertFalse(self._attendances())

    def test_key_of_a_user_without_the_group_is_forbidden(self):
        internal = new_test_user(self.env, login='interno.sin.grupo', groups='base.group_user')
        key = self.env['res.users.apikeys'].with_user(internal).sudo()._generate(None, 'global', None)

        response = self._post({'oauth_uid': 'kc-sub-empleado', 'type': 'I'}, key=key)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['code'], 'FORBIDDEN')
        self.assertFalse(self._attendances())

    def test_service_key_is_not_valid_for_rpc(self):
        apikeys = self.env['res.users.apikeys']

        self.assertFalse(apikeys._check_credentials(scope='rpc', key=self.service_key))
        self.assertEqual(apikeys._check_credentials(scope='maya_attendance', key=self.service_key),
                         self.service_user.id)

    def test_service_user_can_only_create_attendances(self):
        user = self.service_user

        self.assertEqual(user.group_ids, self.env.ref('maya_attendance.group_attendance_clock'))
        self.assertTrue(user.share, 'ni interno ni portal')
        self.assertFalse(user._is_internal())
        Attendance = self.Attendance.with_user(user)
        self.assertTrue(Attendance.has_access('create'))
        for operation in ('read', 'write', 'unlink'):
            self.assertFalse(Attendance.has_access(operation), operation)
        self.assertFalse(self.env['maya_core.employee'].with_user(user).has_access('read'))
        with self.assertRaises(AccessError):
            self.env['res.users'].with_user(user).search([('oauth_uid', '=', 'kc-sub-empleado')])

    # ------------------------------------------------------------------
    # Alta del usuario técnico (scripts/registrar_usuario_fichajes.py)
    # ------------------------------------------------------------------

    def test_register_again_rotates_the_key(self):
        new_key = 'otra-clave-de-prueba-del-servicio-9876543210'

        user = self.env['res.users']._maya_attendance_register_clock_user(
            'svc-test-fichajes', new_key, key_name='test')

        self.assertEqual(user, self.service_user)
        self.assertEqual(self._post({'oauth_uid': 'kc-sub-empleado', 'type': 'I'}).status_code, 401)
        self.assertEqual(self._post({'oauth_uid': 'kc-sub-empleado', 'type': 'I'}, key=new_key).status_code, 201)

    def test_register_refuses_short_keys_and_real_users(self):
        Users = self.env['res.users']
        with self.assertRaises(UserError):
            Users._maya_attendance_register_clock_user('svc-otro', 'corta')
        with self.assertRaises(UserError):
            Users._maya_attendance_register_clock_user('empleado.fichajes', self.service_key)
        with self.assertRaises(AccessError):
            Users.with_user(self.employee_user)._maya_attendance_register_clock_user('svc-otro', self.service_key)
