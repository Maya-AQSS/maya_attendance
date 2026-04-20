from odoo import http
from odoo.http import request
import json

#Api para la conexion entre la base de datos y maya-time-gate
class MayaAttendance(http.Controller):

    #Funcion para buscar emplados a partir del codigo RFID
    @http.route('/api/empleado_rfid/<string:codigo_rfid>', type='http', auth='none', website=True)
    def buscar_empleado(self, codigo_rfid, **kwargs):
        
        if not codigo_rfid.isdigit(): #Validacion numerica
            return request.make_response(
                json.dumps({"status": "error", "message": "El codigo debe ser un numero"}),
                headers=[('Content-Type', 'application/json')]
            )

        #Buscamos el empleado a partir del modelo heredado
        empleado = request.env['maya_core.employee'].sudo().search([
            ('id_tarjeta_rfid', '=', int(codigo_rfid))
        ], limit=1)

        if empleado: #Si existe un empleado creamos un diccionario con su informacion
            res = {
                "status": "success",
                "id_odoo": empleado.id,
                "nombre": empleado.name,
                "apellidos": empleado.surname,
                "dni": empleado.dni
            }
        else: #Si no existe, mandamos un error
            res = {
                "status": "error",
                "message": f"No existe empleado con tarjeta RFID {codigo_rfid}"
            }

        return request.make_response( #Y devolvemos un json con la informacion 
            json.dumps(res),
            headers=[('Content-Type', 'application/json')]
        )

    #Funcion para buscar emplados a partir de su dni
    #TODO Implementar que se busque con din y constraseña
    @http.route('/api/empleado_dni/<string:dni>', type='http', auth='none', website=True)
    def buscar_empleado_por_dni(self, dni, **kwargs):
        
        if dni.isdigit(): #Validacion numerica
            return request.make_response(
                json.dumps({"status": "error", "message": "Error, introduce la letra"}),
                headers=[('Content-Type', 'application/json')]
            )

        #Buscamos el empleado a partir del modelo heredado
        empleado = request.env['maya_core.employee'].sudo().search([
            ('dni', '=', dni)
        ], limit=1)

        if empleado: #Si existe un empleado creamos un diccionario con su informacion
            res = {
                "status": "success",
                "id_odoo": empleado.id,
                "nombre": empleado.name,
                "apellidos": empleado.surname,
                "dni": empleado.dni
            }
        else: #Si no existe, mandamos un error
            res = {
                "status": "error",
                "message": f"No existe empleado con el dni {dni}"
            }

        return request.make_response( #Y devolvemos un json con la informacion 
            json.dumps(res),
            headers=[('Content-Type', 'application/json')]
        )

    @http.route('/api/v1/attendance/log', type='json', auth='none', methods=['POST'], csrf=False)
    def log_attendance(self, **post):
        # En Odoo 19, los datos ya vienen en el diccionario 'post'
        # No hace falta usar request.jsonrequest
        # Artibutos sacados del json
        employee_id = post.get('employee_id')
        attendance_type = post.get('type')
        terminal_id = post.get('terminal_id')
        location_id = post.get('location_id')

        # Condicion para comprobar si estan todos los valores necesarios
        if not employee_id or not attendance_type or not terminal_id or not location_id:
            return {'status': 'error', 'message': 'Faltan parámetros obligatorios'}

        #   Creacion de una instancia empleado a partir de una busqueda en odoo
        employee = request.env['maya_core.employee'].sudo().search([
            ('employee_id', '=', employee_id)
        ], limit=1)
         
        # Si despues de la busqueda no se ha encontrado el empleado devolvemos error
        if not employee:
            return {'status': 'error', 'message': 'Empleado no encontrado'}

        # Metemos los datos en el modelo de maya_attendance
        try:
            new_attendance = request.env['maya_attendance.attendance'].sudo().create({
                'employee_id': employee_id,
                'attendance_type': attendance_type,
                'terminal_id': terminal_id,
                'location_id': location_id,
            })
            return {
                'status': 'success',
                'employee_name': employee.name,
                'message': 'Fichaje registrado'
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}