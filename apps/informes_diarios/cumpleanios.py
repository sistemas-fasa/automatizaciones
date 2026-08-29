import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import mysql.connector
from datetime import datetime

# Configuración de la base de datos
db = mysql.connector.connect(
    host="192.168.0.150",
    user="root",
    password="fasca",
    database="fasa"
)

cursor = db.cursor()

# Obtener clientes que cumplen años hoy
hoy = datetime.now().strftime('%m-%d')
query = f"SELECT concat(zona,cliente) codigo, nombre, correo, fecha_nacimiento FROM clientes WHERE DATE_FORMAT(fecha_nacimiento, '%m-%d') = '{hoy}'"
cursor.execute(query)
clientes = cursor.fetchall()

# Si no hay cumpleaños, salir
if not clientes:
    print("No hay clientes que cumplan años hoy.")
    exit()

# Preparar cuerpo de la tabla HTML
tabla_clientes = """
<table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse; width: 100%; font-family: Arial, sans-serif;">
  <thead>
    <tr style="background-color: #f2f2f2;">
      <th style="text-align:left;">Nombre</th>
      <th style="text-align:left;">Email</th>
      <th style="text-align:left;">Fecha de Nacimiento</th>
      <th style="text-align:left;">Edad</th>
    </tr>
  </thead>
  <tbody>
"""

for cliente in clientes:
    codigo, nombre, email, fecha_nac = cliente
    edad = datetime.now().year - fecha_nac.year
    tabla_clientes += f"""
    <tr>
      <td>{codigo} - {nombre}</td>
      <td>{email}</td>
      <td>{fecha_nac.strftime('%d/%m/%Y')}</td>
      <td>{edad}</td>
    </tr>
    """

tabla_clientes += """
  </tbody>
</table>
"""

# Cuerpo completo del email
cuerpo_html = f"""
<html>
  <body style="font-family: Arial, sans-serif; background-color: #f9f9f9; padding: 20px;">
    <div style="max-width: 800px; margin: auto; background-color: #fff; border-radius: 8px; padding: 20px; box-shadow: 0 0 8px rgba(0,0,0,0.1);">
      <h2 style="color: #e67e22;">Clientes que cumplen años hoy</h2>
      <p>Estos son los clientes que celebran su cumpleaños el día de hoy:</p>
      {tabla_clientes}
      <br>
      <p><strong>Por favor, contactarlos vía WhatsApp o por otros medios con salutaciones personalizadas.</strong></p>
      <p>Saludos cordiales,<br><strong>Ferretería Avenida Sa</strong></p>
    </div>
  </body>
</html>
"""


SMTP_SERVER='c2740921.ferozo.com'
SMTP_PORT=465
SMTP_USER='facturas@fasa.ar'
SMTP_PASSWORD='45*HJJG2sH'
TO_EMAILS='ventas@ferreteriaavenida.com.ar, ventas_rolando@ferreteriaavenida.com.ar'
# TO_EMAILS=oscar@ferreteriaavenida.com.ar
FROM_EMAIL='facturas@fasa.ar'

mensaje = MIMEMultipart()
mensaje['From'] = SMTP_USER
mensaje['To'] = TO_EMAILS
mensaje['Subject'] = "🎂 Clientes que cumplen años hoy - Ferretería Avenida Sa"
mensaje['Bcc'] = 'oscar@ferreteriaavenida.com.ar'

mensaje.attach(MIMEText(cuerpo_html, 'html'))

# Enviar el correo
with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=30) as server:
    # server.starttls()
    server.login(SMTP_USER, SMTP_PASSWORD)
    # Incluir BCC en la lista de destinatarios
    all_recipients = [TO_EMAILS] + ['oscar@ferreteriaavenida.com.ar']
    server.sendmail(SMTP_USER, all_recipients, mensaje.as_string())
    print("Correo enviado a ventas@ferreteriaavenida.com.ar con la lista de cumpleaños.")

cursor.close()
db.close()