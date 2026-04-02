from odoo import http


class MayaAttendance(http.Controller):
    @http.route('/maya_attendance/maya_attendance', auth='public')
    def index(self, **kw):
        return "Hello, world"
