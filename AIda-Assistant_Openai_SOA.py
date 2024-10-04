import openai
import time
from dotenv import load_dotenv
import os
import pymysql
import json
from decimal import Decimal
from openai import OpenAI
import re

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
            SELECT id, CONCAT('¿Me haces este DU? Mail:', aida_correo , ', "Info:": ', lola_response,' }')
            FROM hilos
            WHERE lola_generated = 1 AND aida_generated = 0
            AND lola_response != '{ "Contratos": [], "Lugares de recogida": [] }' AND CONCAT('¿Me haces este DU? Mail:', aida_correo , ', "Info:": ', lola_response,' }') IS NOT NULL

        """)
        hilos = cursor.fetchall()
        
        
        cursor.close()
        conn.close()
        
        return hilos
    except pymysql.MySQLError as e:
        print(f"Error al conectar a MySQL: {e}")
        return []

def mark_as_processed(mysql_conn_params, hilo_id, aida_generated_du):
    try:
        conn = pymysql.connect(**mysql_conn_params)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE hilos
            SET aida_generated_du = %s, aida_generated = 1
            WHERE id = %s
        """, (aida_generated_du, hilo_id))
        
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
            "vector_store_ids": ["vs_jHWxYjUYCPWM1TfyWU4Dq6Ox"]
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
            assistant_id="asst_5ZarbjA6POT814f7nIJvbEWu",
            temperature=0.1,
            model="ft:gpt-4o-2024-08-06:personal:primerfinetuning:AAc44BUA",
            instructions="""
                Instruction:

                Only use the information provided. You must not invent, assume, or infer any information that is not clearly present in the contracts or emails. Use only what is explicitly given.

                Strict DU Format:
                When generating the DU or DUs, follow this strict JSON format:

                {
                "Titular": "",
                "Contrato": "",
                "Lugar de recogida": "",
                "Categoría de vehículo": (ALWAYS RPs, Contenedores/Cadenas, Contenedores/Ganchos, Recolectores, Sanitarios, Pulpos, Cisternas look at the Tabla Equivalencias in the provided document),
                "Líneas del DU": [
                    {
                    "Producto": (could be a service, envase or waste),
                    "Unidades": (if not specified in the email, set it to 1),
                    "Envase": (same as set in the line you chose),
                    "Residuo": (if not a waste line, depends on the waste selected),
                    }
                ]
                }
                IMPORTANT:
                Only use the information exactly as it appears in the contracts.
                If any category, product, or other data is not in the contracts, leave it blank or use the default value (e.g., Unidades: 1).
                Logic for Container Replenishments:
                Whenever a container (Envase) is specified in a line, automatically add an additional line for the replenishment of that container, ALWAYS. The quantity should match the original (e.g., if you use 8 containers for contaminated plastic waste, replenish 8 containers).
                Information about this replenishment must be present in the provided contracts.
                Do not assume replenishment information if it is not clearly specified in the contract.

                Service Line:
                Service lines can only be: [TT] TRANSPORTE,[THORA] SERVICIO CAMIÓN HORA (PULPO/GRÚA) and [THORAR] SERVICIO CAMIÓN HORA (RECOLECTOR), [TC] CAMBIO.

                You will just put [TC] CAMBIO  in case you find an [TA] ALQUILER with the same "Envase" in contratos provided. Example: to put a "[TC] CAMBIO" "Envase":"BIDÓN 60L" you must be provided with a "[TA] ALQUILER", "BIDÓN 60L", if not the case, put a Waste line and an Envase one to replenish it)

                Fixed Structure:
                Do not change or add categories or values unless they are explicitly provided.
                If you need to put a waste line, add a envase line to replenish that picked up envase, just in case envase is not GRANEL.

                You always put at least TWO Líneas del DU, one for a service and 1 for a Product(Waste or Containers)

                Additional Note:
                If the requested waste or containers would require different types of service, do say "He detectado que la petición supone más de un DU, no lo puedo generar"

                Only Product with Categoria_producto:"ENVASE" products will have the "Residuo" field filled.

                The info I'm providing you follows the next structure:
                *You won't take info from categoria_producto, just to classify and make decisions*
                {"Titular", "Contrato", "Producto", "Envase", "Categoria_producto”,“Residuo” }, and you must fill the DU with the equivalent fields. 
            """,
            
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
                
                # # Imprimir contenido combinado antes de limpiar
                # print(f"Contenido combinado antes de limpiar: {json_content}")

                # Extraer el JSON que está entre ```json\n y \n```
                match = re.search(r'```json\s*(.*?)\s*```', json_content, re.DOTALL)
                if match:
                    clean_content = match.group(1).strip()
                    # # Imprimir contenido después de limpiar
                    # print(f"Contenido después de limpiar: {clean_content}")

                    try:
                        # Validar si el contenido es JSON válido
                        json_object = json.loads(clean_content)
                        print(f"Respuesta: {json.dumps(json_object, indent=4)}")

                        # Marcar como procesado en la base de datos
                        mark_as_processed(mysql_conn_params, hilo_id, clean_content)
                    except json.JSONDecodeError as e:
                        print(f"Error al procesar JSON: {e}")
                else:
                    print("No se encontró el JSON en el contenido.")
                    message = ''
                    for block in content_blocks:
                        message += block.text.value
                    mark_as_processed(mysql_conn_params, hilo_id, message)
        else:
                print("No se encontraron mensajes del asistente en la respuesta.")

 
                

def email_listener():
    while True:
        process_pending_hilos()
        time.sleep(6)  # Espera 60 segundos antes de volver a verificar

if __name__ == "__main__":
    email_listener()
