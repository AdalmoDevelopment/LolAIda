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
            AND lola_response != '{ "Contratos": [], "Lugares de recogida": [] }'
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
    pending_hilos = get_pending_hilos(mysql_conn_params)

    for hilo_id, prompt in pending_hilos:
        print(f"Procesando hilo ID: {hilo_id}")

        try:
            # Crear un nuevo thread
            thread = client.beta.threads.create()

            # Enviar el mensaje del usuario al thread
            client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=prompt
            )

            # Iniciar el run en el thread
            run = client.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id='asst_kvPVylsdw6ys08dN8RXVnAEB',
                instructions="""
                Cuando se te pida y te veas capaz de generar el DU, solo responderás con:
                {
                    "Titular": "",
                    "Contrato": "",
                    "Lugar de recogida": "",
                    "Categoría de vehículo": "",
                    "Líneas del DU": [
                        {
                            "Producto": "",
                            "Cantidad": si no se especifica en el mail, es 1,
                            "Envase": "",
                            "Categoria_producto": "",
                            "Residuo":""
                        }
                    ]
                }, nada más.
                SIEMPRE se reponen los envases utilizados en las líneas Envase.
                SIEMPRE VA UNA LINEA DE TRANSPORTE/SERVICIO. Nunca completarás información por tu cuenta, solo colocarás la que se te da en los Contratos con la estructura: {"Titular", "Contrato", "Producto", "Envase", "Categoria_producto”, “Residuo”}.
                """
            )

            # Esperar a que se complete la ejecución
            while True:
                run_status = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
                if run_status.status == "completed":
                    break
                elif run_status.status == "failed":
                    print("Error en la ejecución:", run_status.last_error)
                    break
                time.sleep(2)  # Espera 2 segundos antes de verificar nuevamente

            # Obtener los mensajes de la respuesta
            messages = client.beta.threads.messages.list(thread_id=thread.id)
            
            print(messages)

            # Acceder al último mensaje recibido
            last_message = None
            for message in messages:
                if message.role == 'assistant':  # Asegúrate de obtener el mensaje del asistente
                    last_message = message
                    break

            
            if last_message:
                # Obtener el contenido del mensaje
                content_blocks = last_message.content
                
                # Extraer el JSON directamente de los bloques de contenido
                json_content = ''
                for block in content_blocks:
                    json_content += block.text.value
                
                # Imprimir contenido combinado antes de limpiar
                print(f"Contenido combinado antes de limpiar: {json_content}")

                # Extraer el JSON que está entre ```json\n y \n```
                match = re.search(r'```json\s*(.*?)\s*```', json_content, re.DOTALL)
                if match:
                    clean_content = match.group(1).strip()
                    # Imprimir contenido después de limpiar
                    print(f"Contenido después de limpiar: {clean_content}")

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
            else:
                print("No se encontraron mensajes del asistente en la respuesta.")

        except openai.OpenAIError as e:
            print(f"Error en la ejecución de OpenAI: {e}")

        except Exception as e:
            print(f"Error inesperado: {e}")

def email_listener():
    while True:
        process_pending_hilos()
        time.sleep(6)  # Espera 60 segundos antes de volver a verificar

if __name__ == "__main__":
    email_listener()
