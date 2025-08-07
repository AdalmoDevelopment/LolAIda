import os
import requests
from msal import ConfidentialClientApplication
from dotenv import load_dotenv
import openai
from bs4 import BeautifulSoup
# from msgraph import GraphServiceClient
from load_params import fetch_table_data_prop
from load_params import get_config_by_name
from colorama import Fore, Style
import pymysql
from AidaMailInterpreter.auth_outlook import get_access_token 
from openai import OpenAI

load_dotenv()

CLIENT_ID = os.getenv("OUTLOOK_CLIENT_ID")
CLIENT_SECRET = os.getenv("OUTLOOK_CLIENT_SECRET")
TENANT_ID = os.getenv("OUTLOOK_TENANT_ID")
USER_ID = os.getenv("OUTLOOK_USER_ID")

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

client = OpenAI()

# URL base para Microsoft Graph
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPE = ["https://graph.microsoft.com/.default"]

mydb = pymysql.connect(
	host = os.getenv("MYSQL_HOST"),
	user = os.getenv("MYSQL_USER"),
	password = os.getenv("MYSQL_PASSWORD"),
	database = os.getenv("MYSQL_DATABASE"),
	port=3306
)

def generate_response(from_, body):
	# Para sacar la cantidad de contratos del cliente en cuestión
	# result = execute_query( from_, postgres_conn_params)

	try:
		openai.api_key = OPENAI_API_KEY
		
		response = client.responses.create(
			model="gpt-4o",
   			input=[				{
					"role": "assistant",
					"content": [
						{
							"type": "output_text",
							"text": get_config_by_name("Prompt Email Interpreter")["value"].format(from_=from_)
						}
					]
				},
				{"role": "user", "content":  f"{from_}\n {body}\n "}],
		)
		
		return response.output[0].content[0].text
	except Exception as e:
		print(f"Error al generar la respuesta: {e}")
		return "Error al generar la respuesta."

# def generate_response(from_, body):
# 	# Para sacar la cantidad de contratos del cliente en cuestión
# 	# result = execute_query( from_, postgres_conn_params)

# 	try:
# 		openai.api_key = OPENAI_API_KEY
		
# 		response = openai.chat.completions.create(
# 			model="gpt-4o",
# 			messages=[
	   
# 				{"role": "system", "content":
# 	 				get_config_by_name("Prompt Email Interpreter")["value"].format(from_=from_)},
# 				{"role": "user", "content": f"{from_}\n {body}\n "}
# 		 	],
# 			max_tokens=2048,
# 			temperature= 1
# 		)
		
# 		return response.choices[0].message.content
# 	except Exception as e:
# 		print(f"Error al generar la respuesta: {e}")
# 		return "Error al generar la respuesta."

def parse_email_graph(body):
	try:
		soup = BeautifulSoup(body, "html.parser")
		return soup.get_text()
	except Exception as e:
		print(f"Error al analizar el cuerpo del correo: {e}")
		return body or ""

def email_listener():
	access_token = get_access_token()
	headers = {
		"Authorization": f"Bearer {access_token}",
		"Prefer": 'outlook.body-content-type="text"'
	}

	# Obtener el correo más reciente
	url = f"https://graph.microsoft.com/v1.0/users/{USER_ID}/mailFolders/inbox/messages?$top=50&$orderby=receivedDateTime desc"
	response = requests.get(url, headers=headers)

	if response.status_code != 200:
		print(f"Error al obtener correos: {response.status_code}")
		print(response.json())
		return

	emails = response.json().get("value", [])
	if not emails:
		print("No se encontraron correos.")
		return
	
	existing_ids = [row[0] for row in fetch_table_data_prop('microsoft_mail_conversation_id','hilos')]

	for email in emails:
		
		graph_id = email.get("id")
		web_link = email.get("webLink")
		conversation_id = email.get("conversationId")
		
		print("A ver los id:", email.get("conversationId"))
		

		if conversation_id in existing_ids :
			print("Ya se ha procesado este mail.")
			continue
		print('email de:', email.get("from", {}).get("emailAddress", {}).get("address", "Desconocido"))
		if 'adalmo' in email.get("from", {}).get("emailAddress", {}).get("address", "Desconocido"):
			print("Es de Adalmo, no se procesa.")
			continue
		attachment_text = ""
		if email.get("hasAttachments", False):
			print("Tiene adjuntos, no se procesa ...")
			continue
			
			print("El correo tiene adjuntos, procesando...")
			attachments_url = f"https://graph.microsoft.com/v1.0/users/{USER_ID}/messages/{email['id']}/attachments"
			attach_resp = requests.get(attachments_url, headers=headers)
			if attach_resp.status_code == 200:
				attachments = attach_resp.json().get("value", [])
				for attachment in attachments:
					if attachment.get("@odata.type") == "#microsoft.graph.fileAttachment":
						name = attachment.get("name", "").lower()
						if name.endswithmira(('.xlsx', '.xls', '.csv')):
							from base64 import b64decode
							import pandas as pd
							import io

							try:
								content_bytes = b64decode(attachment.get("contentBytes", ""))
								if name.endswith('.csv'):
									df = pd.read_csv(io.BytesIO(content_bytes))
								else:
									df = pd.read_excel(io.BytesIO(content_bytes))

								attachment_text += f"\nContenido del archivo `{name}`:\n"
								attachment_text += df.head(5).to_string(index=False)  # Only include first 5 rows
							except Exception as e:
								print(f"Error procesando el archivo {name}: {e}")
			else:
				print	(f"Error obteniendo adjuntos ({attach_resp.status_code}):", attach_resp.json())

			
		# Obtener los mensajes del hilo
		thread_url = f"https://graph.microsoft.com/v1.0/users/{USER_ID}/mailFolders/inbox/messages?$filter=conversationId eq '{conversation_id}'"
		thread_resp = requests.get(thread_url, headers=headers)

		if thread_resp.status_code != 200:
			print(f"Error obteniendo hilo ({thread_resp.status_code}):", thread_resp.json())
			continue

		thread_messages = thread_resp.json().get("value", [])
		if not thread_messages:
			print("No se encontraron mensajes en el hilo.")
			continue

		merged_body = ""

		for msg in thread_messages[:2]:  # Primeros 2 mensajes
			subject = msg.get("subject", "(sin asunto)")
			sender = msg.get("from", {}).get("emailAddress", {}).get("address", "(desconocido)")
			date = msg.get("sentDateTime", "(sin fecha)")
			content = parse_email_graph(msg.get("body", {}).get("content", ""))
			parsed_body = sender
			# print("Fecha:", date)
			# print("Cuerpo (preview):", parsed_body[:300], "\n---")

			merged_body += f"{content}\n"
		mycursor = mydb.cursor()
		try:
			# Normalizar remitente
			from_ = sender  # Use the sender as from_
			if any(domain in from_ for domain in ["@gmail", "@hotmail", "@telefonica", "@outlook"]):
				from_ = from_.split('@')[0]
			else:
				from_ = from_.split('@')[1].split('.')[0]

			if 'adalmo'  in from_ or 'ecoembes' in from_ or 'ecolec' in from_ or 'leroy' in from_ or 'ecotic' in from_:
				print("Es de {from_}, no se procesa.")
				continue
   
			if from_ == 'inpronet':
				from_ = 'leroymerlin'

			for receiver in email.get("toRecipients", []):
				receiver_email = receiver.get("emailAddress", {}).get("address", "")
				print(Fore.CYAN + receiver_email + Style.RESET_ALL)

				if 'aena' in from_ and 'emaya' in receiver_email:
					print("Se ha identificado que es un pedido de Emaya para el lugar de recogida de Aena")
					from_ = 'emaya'

			print("Mail para Aida:", Fore.CYAN + from_ + Style.RESET_ALL)
			print(merged_body[:2000])
			# Generar respuesta IA
			full_prompt_body = merged_body[:2000] + "\n\n" + attachment_text
			response = generate_response(subject, full_prompt_body)

			print("Respuesta generada:", response)

			# Guardar en base de datos
			microsoft_mail_conversation_id = conversation_id  # Assign a value to mail_track_id
			query = """
				INSERT INTO hilos(date, date_created, aida_correo, aida_response, aida_request, microsoft_mail_graph_id, microsoft_mail_url, microsoft_mail_conversation_id, attachment) 
				VALUES (%s, curdate(), CONCAT('Asunto:', '\n', %s,'\n', %s), %s, %s, %s, %s, %s, %s)
			"""
			
			mycursor.execute(query, (
				date,
				subject,
				response,
				response,
				from_,
    			graph_id,
				web_link,
				microsoft_mail_conversation_id,
                email.get("hasAttachments", False)
			))
			mydb.commit()
			print("Correo guardado en la base de datos")

		except Exception as e:
			print(f"Error al procesar el correo: {e}")
			continue
		finally:
			mycursor.close()
	return True

if __name__ == "__main__":
	email_listener()
