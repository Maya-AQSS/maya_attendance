from odoo import http
from odoo.http import request
import json

#Api para la conexion entre la base de datos y maya-time-gate
class MayaAttendance(http.Controller):

    #Funcion para buscar emplados a partir del codigo RFID
    @http.route('/api/empleado/<string:codigo_rfid>', type='http', auth='none', website=True)
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

    