from odoo import http
from odoo.http import request
import json
from odoo.fields import Datetime
import pytz
from datetime import datetime, timedelta

class MayaAttendance(http.Controller):

    #Funcion para buscar emplados a partir del codigo RFID
    @http.route('/api/empleado_rfid/<string:codigo_rfid>', type='http', auth='none', website=True)
    def buscar_empleado(self, codigo_rfid, **kwargs):

        #Buscamos el empleado a partir del modelo heredado
        empleado = request.env['maya_core.employee'].sudo().search([
            ('id_card_rfid', '=', codigo_rfid)
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
    def calcular_fichaje_doble(self, ultimo_fichaje, tiempo): 
        hora_actual = Datetime.now()
        duracion = hora_actual - ultimo_fichaje
        tiempo = int(tiempo)
        return duracion.total_seconds() < tiempo
        

    # Funcion para comprobar si el fichaje es doble
    @http.route('/api/buscar_fichaje/<int:employee_id>', type='http', auth='none', website=True)
    def buscar_ultimo_fichaje_empleado(self, employee_id, **kwargs):
        
        # Buscamos al empleado a partir de su id
        employee = request.env['maya_core.employee'].sudo().browse(employee_id) 
        segundos = self.env['ir.config_parameter'].sudo().get_param(
            'maya_attendance.double_signing_time',
            default='300'
        )
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
                es_doble = self.calcular_fichaje_doble(attendance.check_time, segundos) 
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

        return hora_actual > hora_sesion, hora_actual, hora_sesion

    # Funcion para comprobar si se ha fichado despues del comienzo de la ultima sesion
    @http.route('/api/comprobar_sesion', type = 'http', auth='none', website=True)
    def comprobar_sesion(self, **kargs):
        
        dia_semana = self.calcular_dia_semana() # Dia de la semana con formato de caracter
        
        session = request.env['maya_core.session_schedule'].sudo().search(
            [('week_day', 'ilike', dia_semana)],
            order='start_time desc',
            limit=1
        )   # Consulta para calcular la ultima sesion del dia actual
        
        if session.exists(): # Si la sesion existe
            
            fichaje_tarde, hora_actual, hora_inicio_sesion = self.calcular_fichaje_tarde(session) # Variable que guarda si llega tarde

            res = { # Json de respuesta
                "status": "success",
                "fichaje_tarde": fichaje_tarde,
                "hora": hora_actual,
                "hora ultima sesion":hora_inicio_sesion
            }
        else: #Si no hay sesiones
            res = {
                "status": "success", 
                "fichaje_tarde": False,
                "hora": 0
            }
           

        return request.make_response( # Devolvemos el json
            json.dumps(res),
            headers=[('Content-Type', 'application/json')]
        )
        

    @http.route('/api/buscar_estado_fichaje/<int:employee_id>', type='http', auth='none', website=True)
    def buscar_ultimo_estado_fichaje(self, employee_id, **kwargs):
        
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
                estado = attendance.attendance_type == "I"
            else: # Si no se encuentra fichaje devolvemos falso
                estado = False

            res = { # Creamos la respuesta en formato json 
                "status": "success",
                "tipo_fichaje": estado
            }

        return request.make_response( #Y devolvemos un json con la informacion 
            json.dumps(res),
            headers=[('Content-Type', 'application/json')]
        )


    # @http.route('/api/v1/attendance/pause', type='json', auth='none', methods=['POST'], csrf=False)
    # def attendance_pause(self, **post):
    #     employee_id = post.get("employee_id")
    #     reason = post.get("reason", "break") # Por defecto 'break', puede ser 'lunch', 'pharmacy', etc.
    #     current_time = post.get("current_time") # La hora actual enviada por el dispositivo/app

    #     if not all([employee_id, current_time]):
    #         return {"status": "error", "message": "Faltan parametros obligatorios (employee_id, current_time)"}

    #     try:
    #         # Buscamos el último fichaje activo de este empleado (que no tenga hora de salida real)
    #         attendance = request.env["maya_attendance.attendance"].sudo().search([
    #             ('employee_id', '=', int(employee_id)),
    #             # ('check_out', '=', False) 
    #         ], limit=1, order='id desc')

    #         if not attendance.exists():
    #             return {"status": "error", "message": "No se encontro un fichaje activo para este empleado"}

    #         # MODIFICAMOS EL REGISTRO: Marcamos que salió temporalmente
    #         attendance.write({
    #             'is_on_break': True,        # Campo hipotético para saber si está en pausa
    #             'break_reason': reason,    # Guardamos el motivo: 'almuerzo', 'medico', etc.
    #             'break_start': current_time # Guardamos la hora a la que se fue
    #         })

    #         return {
    #             'status': 'success',
    #             'message': f'Salida temporal registrada con éxito por motivo: {reason}'
    #         }

    #     except Exception as e:
    #         return {"status": "error", "message": f"Error interno: {str(e)}"}


    # # 2. ENDPOINT PARA VOLVER DE LA PAUSA (Anular el estado de ausencia)
    # @http.route('/api/v1/attendance/resume', type='json', auth='none', methods=['POST'], csrf=False)
    # def attendance_resume(self, **post):
    #     employee_id = post.get("employee_id")
    #     current_time = post.get("current_time")

    #     if not all([employee_id, current_time]):
    #         return {"status": "error", "message": "Faltan parametros obligatorios"}

    #     try:
    #         # Buscamos el último registro para quitarle el estado de pausa
    #         attendance = request.env["maya_attendance.attendance"].sudo().search([
    #             ('employee_id', '=', int(employee_id)),
    #             ('is_on_break', '=', True) # Buscamos específicamente el que estaba pausado
    #         ], limit=1, order='id desc')

    #         if not attendance.exists():
    #             return {"status": "error", "message": "El empleado no figuraba como 'Fuera del centro'"}

    #         # MODIFICAMOS EL REGISTRO: Volvemos al estado normal
    #         attendance.write({
    #             'is_on_break': False,
    #             'break_end': current_time # Opcional: si quieres trackear cuánto tiempo tardó en volver
    #         })

    #         return {
    #             'status': 'success',
    #             'message': 'Regreso registrado. El empleado vuelve a estar activo.'
    #         }

    #     except Exception as e:
    #         return {"status": "error", "message": f"Error interno: {str(e)}"}


    @http.route(
        '/api/cambiar_hora_fichaje',
        type='json',
        auth='none',
        methods=['POST'],
        csrf=False
    )
    def cambiar_hora_fichaje(self, **post):
        #Crear una api que devuelva la fecha exacta
        # 🔑 leer API key desde headers
        if request.httprequest.headers.get('api-key') != "pass":
            return {
                "status": "error",
                "message": "No autorizado"
            }

        employee_id = post.get("employee_id")
        last_hour = post.get("last_hour")
        new_hour = post.get("new_hour")
        type = post.get("type")

        if not all([employee_id, last_hour, new_hour]):
            return {
                "status": "error",
                "message": "Faltan parámetros"
            }

        try:
            base_time = datetime.strptime(last_hour, "%Y-%m-%d %H:%M:%S")

            start = base_time.replace(second=0)
            end = start + timedelta(minutes=1)
            attendance = request.env["maya_attendance.attendance"].sudo().search([
                ('employee_id', '=', int(employee_id)),
                ('check_time', '>=', start),
                ('check_time', '<', end),
                ('attendance_type','=',type)
            ], limit=1)

            if not attendance:
                return {
                    "status": "error",
                    "message": "Fichaje no encontrado"
                }

            attendance.write({
                'check_time': new_hour
            })

            return {
                "status": "success",
                "message": "Hora cambiada correctamente"
            }

        except (ValueError, TypeError):
            return {
                "status": "error",
                "message": "Datos inválidos"
            }
