import openai
import time
from dotenv import load_dotenv
import os
from openai import OpenAI
from AidaDUMaker.HyperParams import model, aida2_instructions, vector_store_id, aida2_assistant_id

# Inicializar la clave API de OpenAI
openai.api_key = os.getenv('OPENAI_API_KEY')

client = OpenAI()

def correct_dus(du_request):
	
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
		content=du_request
	)
	
	run = client.beta.threads.runs.create(
		thread_id=thread.id,
		assistant_id=aida2_assistant_id,
		temperature=0.1,
		model= model,
		instructions= aida2_instructions,
		
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
				
	last_message = None
	
	for message in messages:
		if message.role == 'assistant':  # Asegúrate de obtener el mensaje del asistente
			last_message = message
			print(last_message)
			break
				
	if last_message:
		content_blocks = last_message.content

		json_content = ''
		for block in content_blocks:
			json_content += block.text.value

		return json_content

	else:
			print(" No se encontraron mensajes del asistente en la respuesta.")

# def email_listener():
# 	while True:
# 		correct_dus()
# 		time.sleep(6)  # Espera 60 segundos antes de volver a verificar

# if __name__ == "__main__":
# 	email_listener()


