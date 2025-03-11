from openai import OpenAI
import openai
import time
from dotenv import load_dotenv
import os
import pymysql
import json
import re
from colorama import Fore, Back, Style
from AidaDUMaker.HyperParams import model, aida_instructions, vector_store_id, aida_assistant_id

load_dotenv()

openai.api_key = os.getenv('OPENAI_API_KEY')

client = OpenAI()

mysql_host = os.getenv('MYSQL_HOST')
mysql_user = os.getenv('MYSQL_USER')
mysql_password = os.getenv('MYSQL_PASSWORD')
mysql_database = os.getenv('MYSQL_DATABASE')

# Parámetros de conexión MySQL
mysql_conn_params = {
	'host': mysql_host,
	'user': mysql_user,
	'password': mysql_password,
	'database': mysql_database
}

def get_pending_hilos(mysql_conn_params):
	
	try:
		conn = pymysql.connect(**mysql_conn_params)
		cursor = conn.cursor()
		print("Buscando hilos no aceptados")
		cursor.execute("""
			SELECT 
				id,
				CONCAT('¿Me haces este/estos DU? Mail:', aida_correo , ', "Info:": ', lola_response_json) AS user_message,
				aida_generated_du as system_message,
				aida_request
			FROM hilos
			WHERE aida_generated = 1
			AND approved = 0
			ORDER BY id desc
		""")
		hilos = cursor.fetchall()
		
		cursor.close()
		conn.close()
		
		return hilos
	except pymysql.MySQLError as e:
		print(f"Error al conectar a MySQL: {e}")
		return []

def mark_as_processed(mysql_conn_params, hilo_id, du, user_reponse, assistant_reponse):
	try:
		conn = pymysql.connect(**mysql_conn_params)
		cursor = conn.cursor()
		
		if du == None:
			cursor.execute("""
				UPDATE hilos
				SET user_for_wrong_examples = %s, model_for_wrong_examples = %s
				WHERE id = %s
			""", ( user_reponse, assistant_reponse, hilo_id))
			conn.commit()
			print('Línea ', hilo_id, ' actualizada')
		else:			
			cursor.execute("""
			INSERT INTO generated_dus_aida(id_hilo, du, message, time, finetuned)
			VALUES (%s, %s, %s, CURRENT_TIMESTAMP(), 1)
			""", (hilo_id, du, assistant_reponse))
			conn.commit()
		cursor.close()  
		conn.close()
	except:
		print('Error')

def ft_process_pending_hilos():
	
	hilos = get_pending_hilos(mysql_conn_params)
	
	for hilo in hilos:
		
		
		hilo_id, user_message, system_message, aida_request = hilo
		
		# print(user_message, system_message)
		thread = client.beta.threads.create(
			messages=[
				{
					"role": "user",
					"content": user_message
				},
				{
					"role": "assistant",
					"content": system_message
				}
			],
			tool_resources={
				"file_search": {
				"vector_store_ids": [vector_store_id]
				}
			}
   		)
		
		print(f'Respuesta para corregir el/los DU generados del hilo {hilo_id}, para {aida_request}:')
		# print()
		# print( Fore.BLUE + f'Link: http://localhost:3000/lolaida/#{hilo_id} \n', Style.RESET_ALL )
		message = input()
  
		if message != '':

			client.beta.threads.messages.create(
				thread_id=thread.id,
				role="user",
				content=message
			)

			run = client.beta.threads.runs.create(
				thread_id=thread.id,
				assistant_id=aida_assistant_id,
				temperature=0.1,
				model= model,
				instructions= aida_instructions,
				tools=[{"type": "file_search"}]
			)

			while True:
				run_status = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
				if run_status.status == "completed":
					break
				elif run_status.status == "failed":
					print("Error en la ejecución:", run_status.last_error)
					break
			
			thread_messages = client.beta.threads.messages.list(thread_id=thread.id)

			for message in thread_messages:
				if message.role == 'assistant': 
					last_message = message
					content_blocks = last_message.content
					assistant_reponse = ''
					for block in content_blocks:
						assistant_reponse += block.text.value
				if message.role == 'user':
					last_message = message
					content_blocks = last_message.content
					user_reponse = ''
					for block in content_blocks:
						user_reponse += block.text.value
					break

			if assistant_reponse:
				
				matches = re.findall(r'```json\s*(.*?)\s*```', assistant_reponse, re.DOTALL)
				mark_as_processed(mysql_conn_params, hilo_id, None, user_reponse, assistant_reponse)            
				if matches:
					for du in matches:
						
						try:
							# Validar si el contenido es JSON válido
							json_object = json.loads(du)
							print(f"Respuesta: {json.dumps(json_object, indent=4)}")
							# Marcar como procesado en la base de datos
							mark_as_processed(mysql_conn_params, hilo_id, du, assistant_reponse, None)
						except json.JSONDecodeError as e:
							print(f"Error al procesar JSON: {e}")
				else:
					print("No se encontró el JSON en el contenido.")
			else:
					print(" No se encontraron mensajes del asistente en la respuesta.")
		
	return(True)

if __name__ == "__main__":
	ft_process_pending_hilos()