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
        # Extraemos los datos del diccionario
        employee_id = post.get('employee_id')
        attendance_type = post.get('type')
        terminal_id = post.get('terminal_id')
        location_id = post.get('location_id')

        # Comprobamos si están todos los valores
        if not all([employee_id, attendance_type, terminal_id, location_id]):
            return {'status': 'error', 'message': 'Faltan parámetros obligatorios'}

        try:
            # Buscamos al empleado y guardamos el objeto en la variable
            employee = request.env['maya_core.employee'].sudo().browse(int(employee_id))
            
            # Comprobamos si el objeto existe de verdad en la base de datos
            if not employee.exists():
                return {'status': 'error', 'message': 'Empleado no encontrado'}
            
            
        except (ValueError, TypeError):
            return {'status': 'error', 'message': 'ID de empleado no válido'}

    
        try:
            # Finalmente devolvemos todos los valores
            request.env['maya_attendance.attendance'].sudo().create({
                'employee_id': employee.id,  # Usamos el ID del objeto que hemos validado
                'attendance_type': attendance_type,
                'terminal_id': terminal_id,
                'location_id': location_id,
            })
            
            return {
                'status': 'success',
                'message': 'Fichaje registrado correctamente'
            }
        except Exception as e:
            # Si falla algo en la DB (constraints, etc.), capturamos el error
            return {'status': 'error', 'message': str(e)}