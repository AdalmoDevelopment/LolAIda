import os
import base64
import imaplib
import email
from email.header import decode_header
import openai
import time
import pymysql
import smtplib
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from datetime import datetime
import psycopg2
import pickle
import google.auth
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from extract_msg_id import get_message_by_id
from diccionario import palabras
from colorama import Fore, Back, Style

CREDENTIALS_FILE = './credentials.json'
TOKEN_PICKLE = 'token.pickle'
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

SCOPES = ['https://mail.google.com/']

# def lambda_handler(event, context):
def obtener_credenciales():
	"""
		Autenticar y obtener credenciales OAuth2 para Gmail.
		Si ya existen credenciales almacenadas, se usan; de lo contrario, se solicitan.
	"""
	creds = None
	if os.path.exists(TOKEN_PICKLE):
		with open(TOKEN_PICKLE, 'rb') as token:
			creds = pickle.load(token)
	
	if not creds or not creds.valid:
		if creds and creds.expired and creds.refresh_token:
			creds.refresh(Request())
		else:
			flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
			creds = flow.run_local_server(port=0)
		with open(TOKEN_PICKLE, 'wb') as token:
			pickle.dump(creds, token)
	
	return creds


load_dotenv()

# Configuración IMAP
mail_imap_server = "imap.gmail.com"
mail_user = os.getenv('MAIL_USER')
mail_password = os.getenv('MAIL_PASSWORD')

dbname = os.getenv('DB_NAME')
postgres_user = os.getenv('DB_USER')
postgres_password = os.getenv('DB_PASSWORD')
postgres_host = os.getenv('DB_HOST')
postgres_port = os.getenv('DB_PORT')
postgres_conn_params = {
	'dbname': dbname,
	'user': postgres_user,
	'password': postgres_password,
	'host': postgres_host,
	'port': postgres_port
}

mysql_host = os.getenv('MYSQL_HOST')
mysql_user = os.getenv('MYSQL_USER')
mysql_password = os.getenv('MYSQL_PASSWORD')
mysql_database = os.getenv('MYSQL_DATABASE')

mydb = pymysql.connect(
host = mysql_host,
user = mysql_user,
password = mysql_password,
database = mysql_database,
port=3306
)

# Establecer la clave de API desde una variable de entorno
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

def connect_imap_oauth2(token):
	"""Conectar al servidor IMAP usando OAuth 2.0."""
	mail = imaplib.IMAP4_SSL("imap.gmail.com")
	
	# Crear la cadena de autenticación XOAUTH2
	auth_string = f'user={mail_user}\1auth=Bearer {token.token}\1\1'
	try:
		# Autenticar usando XOAUTH2
		mail.authenticate('XOAUTH2', lambda x: auth_string)
		print("Autenticado exitosamente con IMAP usando OAuth.")
		return mail
	except imaplib.IMAP4.error as e:
		print(f"Error al autenticar con OAuth: {e}")
		return None

def check_inbox(mail):
	"""Revisar la bandeja de entrada en busca de correos no leídos."""
	try:
		mail.select("inbox")
		status, messages = mail.search(None, '(SEEN)')
		if status != "OK":
			print("No hay mensajes nuevos.")
			return []
		email_ids = messages[0].split()
		email_ids.reverse()
		return email_ids
	except Exception as e:
		print(f"Error al revisar la bandeja de entrada: {e}")
		return []

def fetch_email(mail, email_id):
	"""Recuperar un correo específico."""
	try:
		status, msg_data = mail.fetch(email_id, "(RFC822)")
		if status != "OK":
			print("No se pudo recuperar el correo.")
			return None
		msg = email.message_from_bytes(msg_data[0][1])
		
		msg_id = msg.get("Message-ID")
		
		# mail.uid('STORE', msg_id, '-FLAGS', '\\UNSEEN')
		
		return msg, msg_id
	except Exception as e:
		print(f"Error al recuperar el correo: {e}")
		return None

def parse_email(msg, email_id):
	"""Analizar el correo y extraer el remitente, el cuerpo sin etiquetas HTML, y el Message-ID."""
	try:
		subject = decode_header(msg["Subject"])[0][0]
		if isinstance(subject, bytes):
			subject = subject.decode()
		
		from_ = msg.get("From")
		if "<" in from_ and ">" in from_:
			from_ = from_.split("<")[1].split(">")[0]
		
		to_ = msg.get_all("To")
		
		print("Destinatarios:",to_)
		
		date_str = msg.get("Date")
		date = None

		# Probar diferentes formatos de fecha
		date_formats = [
			'%a, %d %b %Y %H:%M:%S %z',  # Formato con día de la semana
			'%d %b %Y %H:%M:%S %z'       # Formato sin día de la semana
		]

		for fmt in date_formats:
			try:
				date = datetime.strptime(date_str, fmt)
				break
			except ValueError:
				continue

		# Obtener el Message-ID
		message_id = msg.get("Message-ID", email_id)  # Si no hay Message-ID, usar el ID de IMAP

		print(f"Message-ID: {message_id}")  # Imprimir el Message-ID

		body = ""
		if msg.is_multipart():
			for part in msg.walk():
				content_type = part.get_content_type()
				content_disposition = str(part.get("Content-Disposition"))

				if "attachment" not in content_disposition:
					if content_type == "text/plain":
						body += part.get_payload(decode=True).decode(errors='replace')
					elif content_type == "text/html":
						html = part.get_payload(decode=True).decode(errors='replace')
						soup = BeautifulSoup(html, "html.parser")
						body += soup.get_text()
		else:
			if msg.get_content_type() == "text/plain":
				body = msg.get_payload(decode=True).decode(errors='replace')
			elif msg.get_content_type() == "text/html":
				html = msg.get_payload(decode=True).decode(errors='replace')
				soup = BeautifulSoup(html, "html.parser")
				body = soup.get_text()

		MAX_LENGTH = 5000  # para que no dé error por exceso de tokens
		if len(body) > MAX_LENGTH:
			body = body[:MAX_LENGTH] + '...'
		
		return message_id, from_, subject, body, date, to_  # Devolver el Message-ID junto con el resto de información
	except Exception as e:
		print(f"Error al analizar el correo: {e}")
		return email_id, None, None, None, None, None

def get_pending_hilos(mysql_conn_params):
	try:
		conn = pymysql.connect(**mysql_conn_params)
		cursor = conn.cursor()
		
		cursor.execute("SELECT id, aida_request FROM hilos WHERE lola_generated = 0 AND aida_response LIKE 'Lola%'")
		hilos = cursor.fetchall()
		
		cursor.close()
		conn.close()
		
		return hilos
	except pymysql.MySQLError as e:
		print(f"Error al conectar a MySQL: {e}")
		return []

def execute_query(from_, conn_params):
	try:
		# Establecer la conexión con la base de datos
		conn = psycopg2.connect(**conn_params)
		cursor = conn.cursor()
		print(from_)
		# Modificar el valor de 'from_' para que funcione con LIKE
		
		if "@gmail" in from_:
			from_ = f"{from_.split('@')[0]}"
			from_ = f"%{from_}%"
		else:
			from_ = f"{from_.split('@')[1]}"
			from_ = f"{from_.split('.')[0]}"    
			from_ = f"%{from_}%"                                                    
				
		print(from_)

		query = """
			SELECT count(*)
			FROM public.pnt_agreement_agreement paa
			INNER JOIN res_partner rp ON paa.pnt_holder_id = rp.id
			INNER JOIN pnt_agreement_partner_pickup_rel pappr ON paa.id = pappr.pnt_agreement_id
			INNER JOIN res_partner rprecog ON pappr.partner_id = rprecog.id
			WHERE paa.state = 'done'
			AND paa.pnt_holder_id IN (
				SELECT id FROM res_partner WHERE email ILIKE %s AND is_company = true
			)
			AND rprecog.type = 'delivery'
		"""
		# Ejecutar la consulta con el parámetro correctamente (como tupla)
		cursor.execute(query, (from_,) )  # El parámetro from_ debe estar dentro de una tupla
		
		result = cursor.fetchone()  # Solo obtendremos un resultad
		# Cerrar la conexión
		cursor.close()
		conn.close()
		
		return result
	except Exception as e:
		return str(e)

def generate_response(from_, body):
	"""Generar una respuesta utilizando gpt-4."""
	result = execute_query( from_, postgres_conn_params)
	try:
		openai.api_key = OPENAI_API_KEY

		if result[0] > 1:  
			multiple_lugar_recogida = "y el lugar de recogida"
		else:
			multiple_lugar_recogida = ""
			
		messages = [
			{"role": "system", "content": f"Me llamo AIda, no haré nunca referencia a que soy un asistente AI. Reviso los datos de cada mail que me llega, si no interpreto que me están solicitando una entrega, cambio, o recogida de algun tipo de residuo/recipiente/contenedor o vaciado de alguno de estos, respondo 'No se ha detectado ninguna petición'. Una vez interprete algo de esto responderé 'Lola. Dame la información de {from_}' (siempre el mail del remitente). A su vez, me devolverás también el correo pero limpio con solo lo importante, borrando mensajes evidentemente predeterminados, plantillas, etc. y puntualizando la petición hecha.''"},
			{"role": "user", "content": f"{from_}\n {body}\n "}
		]
		
		response = openai.chat.completions.create(
			model="gpt-4o",
			messages=messages,
			max_tokens=200,
			temperature= 1
		)
		return response.choices[0].message.content
	except Exception as e:
		print(f"Error al generar la respuesta: {e}")
		return "Error al generar la respuesta."

def email_listener():
	try:
		token = obtener_credenciales()
		mail = connect_imap_oauth2(token)
		if mail:
			email_ids = check_inbox(mail)
			if email_ids:
				email_count = 0
				for email_id in email_ids:
					email_count += 1
					msg, msg_id = fetch_email(mail, email_id)
					print('Mail Numero', email_count)
					if msg:
						message_id, from_, subject, body, date, to_ = parse_email(msg, email_id)
						if date is not None:
							print("Fecha correo: ", date.strftime("%d/%m/%Y"), " Fecha python: ", datetime.now().strftime("%d/%m/%Y") )
							if date.strftime("%d/%m/%Y") != datetime.now().strftime("%d/%m/%Y"):
								print( Fore.CYAN + "Todos los correos de hoy leidos jeje xd" + Style.RESET_ALL )
								break
						# print(body)
						
						if body:
							if from_ and subject and body and "adalmo" not in from_:
								mail_track_id = get_message_by_id(message_id)
								# print(f"Nuevo correo id({mail_track_id}) de {from_}: {subject}\n\n")
								
								# response = generate_response(from_, body)
								
								# if response:
								# 	print(response)
								# try:
								# #Extraer nombre de usuario o dominio del correo
								# 	print(from_)
								# 	if "adalmo" not in from_:
								# 		if any(domain in from_ for domain in ["@gmail", "@hotmail"]):
								# 			from_ = f"{from_.split('@')[0]}"
								# 			print(from_)
								# 		else:
								# 			from_ = f"{from_.split('@')[1].split('.')[0]}"
								# 			print(from_)
									
								# 	if from_ == 'inpronet':
								# 		from_ = 'leroymerlin'										
								# 	if to_:
								# 		for receiver in to_:
								# 			print( "Ecubidubi", Fore.CYAN + receiver + Style.RESET_ALL )

								# 			if 'aena' in from_ and 'emaya' in receiver:
								# 				print("Se ha identificado que es es un pedido de Emaya para el lugar de recogida de Aena")
								# 				from_  = 'emaya'
								# 	print( "Mail para Aida:", Fore.CYAN + from_ + Style.RESET_ALL )
								# 	# Guardar en la base de datos
								# 	query = """
								# 	INSERT INTO hilos(date, date_created, aida_correo, aida_response, aida_request, mail_track_id) 
								# 	VALUES (%s, curdate(), CONCAT('Asunto:', '\n', %s,'\n', %s), %s, %s, %s)
								# 	"""
								# 	mycursor = mydb.cursor()
								# 	mycursor.execute(query, (date, subject, response, response, from_, mail_track_id))
								# 	mydb.commit()  # Confirmar los cambios
								# 	print("Correo guardado en la base de datos")
									
								# except pymysql.MySQLError as e:
								# 	print(f"Error al ejecutar la consulta SQL: {e}")
								# finally:
								# 	mycursor.close()
						else:
							print('Ninguna palabra del diccionario en el cuerpo del mensaje')    

		# Cerrar la conexión IMAP después de procesar
		mail.logout()
		print( Fore.CYAN + "Exitoooo" + Style.RESET_ALL )
		time.sleep(60)  # Esperar 1 minuto antes de revisar nuevamente

	except Exception as e:
		print(f"Error general: {e}")
		time.sleep(60)  # Esperar y reintentar en caso de error

if __name__ == "__main__":
	email_listener()