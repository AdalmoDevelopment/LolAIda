import openai
import time
from dotenv import load_dotenv
import os
import pymysql
import json
from decimal import Decimal
from openai import OpenAI
import re
from AidaDUMaker.HyperParams import model, instructions, vector_store_id, assistant_id

# Cargar variables de entorno
load_dotenv()

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
		
		cursor.execute("""
			SELECT id, CONCAT('¿Me haces este/estos DU? Mail:', aida_correo , ', "Info:": ', lola_response_json)
			FROM hilos
			WHERE lola_generated = 1 AND aida_generated = 0
			AND lola_response != '{ "Contratos": [], "Lugares de recogida": [] }' AND CONCAT('¿Me haces este DU? Mail:', aida_correo , ', "Info:": ', lola_response,' }') IS NOT NULL and date_created = CURDATE()
		""")
		hilos = cursor.fetchall()
		
		cursor.close()
		conn.close()
		
		return hilos
	except pymysql.MySQLError as e:
		print(f"Error al conectar a MySQL: {e}")
		return []

def mark_as_processed(mysql_conn_params, hilo_id, aida_generated_du, aida_response):
	try:
		conn = pymysql.connect(**mysql_conn_params)
		cursor = conn.cursor()
		
		if aida_generated_du == None and aida_response == None:
			print('Se borra lo anterior del hilo:', hilo_id)
			cursor.execute("""
				DELETE FROM generated_dus_aida WHERE id_hilo = %s
			""", ( hilo_id ))
			conn.commit()
		else:
			cursor.execute("""
				UPDATE hilos
				SET aida_generated = 1, aida_generated_du = %s
				WHERE id = %s
			""", ( aida_response, hilo_id))
			conn.commit()
			
			if aida_generated_du != None :
				cursor.execute("""
				INSERT INTO generated_dus_aida(id_hilo, message, du, time)
				VALUES (%s, %s, %s, CURRENT_TIMESTAMP())
				""", (hilo_id, aida_response, aida_generated_du))
				conn.commit()
				
		cursor.close()  
		conn.close()

	except pymysql.MySQLError as e:
		print(f"Error al actualizar MySQL: {e}")

# Inicializar la clave API de OpenAI
openai.api_key = os.getenv('OPENAI_API_KEY')

client = OpenAI()


def process_pending_hilos():
	
	hilos = get_pending_hilos(mysql_conn_params)
	
	for hilo in hilos: 
		
		hilo_id, mensaje = hilo
		
		thread = client.beta.threads.create(
		tool_resources={
			"file_search": {
			"vector_store_ids": [vector_store_id]
			}
		}        
		)
		
		client.beta.threads.messages.create(
			thread_id=thread.id,
			role="user",	
			content=mensaje
		)
		
		run = client.beta.threads.runs.create(
			thread_id=thread.id,
			assistant_id=assistant_id,
			temperature=0.1,
			model= model,
			instructions= instructions,
			
			tools=[{"type": "file_search"}]
		)
		
		while True:
			run_status = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
			if run_status.status == "completed":
				break
			elif run_status.status == "failed":
				print("Error en la ejecución:", run_status.last_error)
				break
			time.sleep(2)  # Espera 2 segundos antes de verificar nuevamente

		messages = client.beta.threads.messages.list(thread_id=thread.id)
		# print(messages)
					
		last_message = None
		
		for message in messages:
			if message.role == 'assistant':  # Asegúrate de obtener el mensaje del asistente
				last_message = message
				print(last_message)
				break
					
		if last_message:
			# Obtener el contenido del mensaje
			content_blocks = last_message.content
			
			# Extraer el JSON directamente de los bloques de contenido
			json_content = ''
			for block in content_blocks:
				json_content += block.text.value
			
			# # Imprimir contenido combinado antes de limpiar
			# print(f"Contenido combinado antes de limpiar: {json_content}")

			# Extraer el JSON que está entre ```json\n y \n```
			# La única diferencia con el AIda-Assistant_Openai_SOA es que este va a sacar todos los json que haya, en bucle, por si hubiesen más de uno 
			
			matches = re.findall(r'```json\s*(.*?)\s*```',json_content, re.DOTALL)
			mark_as_processed(mysql_conn_params, hilo_id, None, None)            
			if matches:
				for du in matches:
					
					try:
						# Validar si el contenido es JSON válido
						json_object = json.loads(du)
						print(f"Respuesta: {json.dumps(json_object, indent=4)}")
						# Marcar como procesado en la base de datos
						mark_as_processed(mysql_conn_params, hilo_id, du, json_content)
					except json.JSONDecodeError as e:
						print(f"Error al procesar JSON: {e}")
			else:
				print("No se encontró el JSON en el contenido.")
				message = ''
				for block in content_blocks:
					message += block.text.value
					
				mark_as_processed(mysql_conn_params, hilo_id, None, json_content)
		else:
				print(" No se encontraron mensajes del asistente en la respuesta.")

# def email_listener():
# 	while True:
# 		process_pending_hilos()
# 		time.sleep(6)  # Espera 60 segundos antes de volver a verificar

# if __name__ == "__main__":
# 	email_listener()


