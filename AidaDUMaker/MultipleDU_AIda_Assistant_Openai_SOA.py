import openai
import time
import os
import json
from openai import OpenAI
import re
from AidaDUMaker.HyperParams import model, aida_instructions, vector_store_id, aida_assistant_id
from AidaDUMaker.funcs.funcs import get_pending_hilos, mark_as_processed, mysql_conn_params
from AidaDUMaker.MultipleDU_Corrector import correct_dus

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
			assistant_id=aida_assistant_id,
			temperature=0.1,
			model= model,
			instructions= aida_instructions,
			
			tools=[{"type": "file_search"}]
		)
		
		while True:
			run_status = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id	=run.id)
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
			
			# Se llama a la función correct_dus para reforzar los DU's generados
			print(f"Mensaje Du inicial: {json_content}")
			json_content = correct_dus(json_content)
			matches = re.findall(r'```json\s*(.*?)\s*```',json_content, re.DOTALL)
			mark_as_processed(mysql_conn_params, hilo_id, None, None)            
			if matches:
				for du in matches:
					
					try:
						# Validar si el contenido es JSON válido
						json_object = json.loads(du)
						print(f"Dus format: {json.dumps(json_object, indent=4)}")
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
	return(True)

# def email_listener():
# 	while True:
# 		process_pending_hilos()
# 		time.sleep(6)  # Espera 60 segundos antes de volver a verificar

# if __name__ == "__main__":
# 	email_listener()


