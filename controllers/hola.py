from datetime import datetime

now = datetime.now()
hora_string = f"{now.hour}.{now.minute}" 
hora_float = float(hora_string)

print(hora_float)