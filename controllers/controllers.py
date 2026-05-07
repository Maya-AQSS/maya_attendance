from odoo import http
from odoo.http import request
import json
from odoo.fields import Datetime
from datetime import datetime
import time
from datetime import datetime
import json
from odoo import http
from odoo import fields
import json
from odoo import http

#Api para la conexion entre la base de datos y maya-time-gate
class MayaAttendance(http.Controller):

    #Funcion para buscar emplados a partir del codigo RFID
    @http.route('/api/empleado_rfid/<string:codigo_rfid>', type='http', auth='none', website=True)
    def buscar_empleado(self, codigo_rfid, **kwargs):

        #Buscamos el empleado a partir del modelo heredado
        empleado = request.env['maya_core.employee'].sudo().search([
            ('id_tarjeta_rfid', '=', codigo_rfid)
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

    # Funcion para calcular si el fichaje es doble
    def calcular_fichaje_doble(self, ultimo_fichaje): 
        hora_actual = Datetime.now()
        duracion = hora_actual - ultimo_fichaje

        return duracion.total_seconds() < 300
        

    # Funcion para comprobar si el fichaje es doble
    @http.route('/api/buscar_fichaje/<int:employee_id>', type='http', auth='none', website=True)
    def buscar_ultimo_fichaje_empleado(self, employee_id, **kwargs):
        
        # Buscamos al empleado a partir de su id
        employee = request.env['maya_core.employee'].sudo().browse(employee_id) 

        if not employee.exists(): # Si el empleado no existe devolvemos error
            res = {
                "status": "error",
                "message": f"No existe empleado con el id {employee_id}"
            }
        else: # Si existe buscamos el ultimo fichaje del empleado
            attendance = request.env['maya_attendance.attendance'].sudo().search([
                ('employee_id', '=', employee.id)
            ], order='check_time desc', limit=1)

            if attendance: # Si el fichaje existe
                # Usamos la funcion para calcular si el fichaje es doble 
                es_doble = self.calcular_fichaje_doble(attendance.check_time) 
            else: # Si no se encuentra fichaje devolvemos falso
                es_doble = False

            res = { # Creamos la respuesta en formato json 
                "status": "success",
                "id_odoo": employee.id,
                "fichaje_doble": es_doble
            }

        return request.make_response( #Y devolvemos un json con la informacion 
            json.dumps(res),
            headers=[('Content-Type', 'application/json')]
        )
   
    # Funcion para calcular el dia de la semana
    def calcular_dia_semana(self):
        fecha_actual = datetime.today()
        dias = ["L", "M", "X", "J", "V"]
        return dias[fecha_actual.weekday()]
    
    def calcular_hora_float(self):
        tz = pytz.timezone("Europe/Madrid")
        now = datetime.now(pytz.utc).astimezone(tz)

        return now.hour + (now.minute / 60)

    def calcular_hora_minutos(self):
        now = self.get_now_madrid()
        return now.hour * 60 + now.minute


    def calcular_fichaje_tarde(self, session):
        hora_actual = self.calcular_hora_float()
        hora_sesion = session.start_time  # ya es float

        return hora_actual > hora_sesion, hora_actual

    # Funcion para comprobar si se ha fichado despues del comienzo de la ultima sesion
    @http.route('/api/comprobar_sesion', type = 'http', auth='none', website=True)
    def comprobar_sesion(self, **kargs):
        
        dia_semana = self.calcular_dia_semana() # Dia de la semana con formato de caracter
        
        session = request.env['maya_core.session_schedule'].sudo().search(
            [('week_day', 'ilike', dia_semana)],
            order='create_date desc',
            limit=1
        )   # Consulta para calcular la ultima sesion del dia actual
        
        if session.exists(): # Si la sesion existe
            
            fichaje_tarde, hora = self.calcular_fichaje_tarde(session) # Variable que guarda si llega tarde

            res = { # Json de respuesta
                "status": "success",
                "fichaje_tarde": fichaje_tarde,
                "hora": hora
            }
        else: # Si la sesion no existe mandamos error
            res = {
                "status": "error", 
                "message": "Error, no hay sesiones"
            }
           

        return request.make_response( # Devolvemos el json
            json.dumps(res),
            headers=[('Content-Type', 'application/json')]
        )
    