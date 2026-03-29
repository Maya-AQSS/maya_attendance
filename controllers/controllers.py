# from odoo import http


# class MayaAttendance(http.Controller):
#     @http.route('/maya_attendance/maya_attendance', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/maya_attendance/maya_attendance/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('maya_attendance.listing', {
#             'root': '/maya_attendance/maya_attendance',
#             'objects': http.request.env['maya_attendance.maya_attendance'].search([]),
#         })

#     @http.route('/maya_attendance/maya_attendance/objects/<model("maya_attendance.maya_attendance"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('maya_attendance.object', {
#             'object': obj
#         })

