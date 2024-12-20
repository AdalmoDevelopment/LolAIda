from openai import OpenAI
import openai
import time
from dotenv import load_dotenv
import os

load_dotenv()

openai.api_key = os.getenv('OPENAI_API_KEY')

client = OpenAI()

thread = client.beta.threads.create(
    tool_resources={
        "file_search": { "vector_store_ids": ["vs_jHWxYjUYCPWM1TfyWU4Dq6Ox"] }
    }        
)

client.beta.threads.messages.create(
    thread_id=thread.id,
    role="user",
    content="Dime que categoría vehículo le corresponderia a un du con servicio [TT] TRANSPORTE"
)

run = client.beta.threads.runs.create(
    thread_id=thread.id,
    assistant_id="asst_5ZarbjA6POT814f7nIJvbEWu",
    temperature=0.1,
    model= 'gpt-4o',
    instructions='Te llamas AIda',    
    tools=[{"type": "file_search"}]
    # Lo siguiente no se pone porque en teoria el asistente ya tiene el vector, en todo caso se le pone al crearlo o actualizarlo
    # tool_resources={
    #     "file_search": {
    #     "vector_store_ids": ["vs_2"]
    #     }
    # }
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