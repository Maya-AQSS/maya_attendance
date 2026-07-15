from odoo.tests import TransactionCase
from odoo.exceptions import ValidationError
from psycopg2 import IntegrityError


class TestMayaAttendance(TransactionCase):

    def setUp(self):
        super().setUp()

        self.employee = self.env['maya_core.employee'].create({
            'employee_type': 'profesor',
            'position_type': 'ESPJ',
            'team_ids': [(6, 0, [])],
        })

        self.location = self.env['maya_core.location'].create({
            'name': 'Centro Test',
            'address': 'Direccion Test',
            'phone_number': 'Numero Test'
        })

    def test_create_attendance_ok(self):
        attendance = self.env['maya_attendance.attendance'].create({
            'employee_id': self.employee.id,
            'check_date': '2026-01-01',
            'check_time': '2026-01-01 08:00:00',
            'attendance_type': 'I',
            'terminal_id': 'TERM01',
            'location_id': self.location.id,
        })

        self.assertTrue(attendance.id)
        self.assertEqual(attendance.attendance_type, 'I')

    def test_pause_requires_justification(self):
        with self.assertRaises(ValidationError):
            self.env['maya_attendance.attendance'].create({
                'employee_id': self.employee.id,
                'check_date': '2026-01-01',
                'check_time': '2026-01-01 10:00:00',
                'attendance_type': 'P',
                'terminal_id': 'TERM01',
                'location_id': self.location.id,
                'justification': False
            })

    def test_pause_requires_justification(self):
        with self.assertRaises(ValidationError):
            self.env['maya_attendance.attendance'].create({
                'employee_id': self.employee.id,
                'check_date': '2026-01-01',
                'check_time': '2026-01-01 10:00:00',
                'attendance_type': 'P',
                'terminal_id': 'TERM01',
                'location_id': self.location.id,
                'justification': False
            })

    def test_employee_required(self):
        with self.assertRaises(Exception):
            self.env['maya_attendance.attendance'].create({
                'check_date': '2026-01-01',
                'check_time': '2026-01-01 08:00:00',
                'attendance_type': 'I',
                'terminal_id': 'TERM01',
                'location_id': self.location.id,
            })