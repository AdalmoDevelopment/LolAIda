import openai
import time
from dotenv import load_dotenv
import os
import pymysql
import json
from decimal import Decimal
from openai import OpenAI


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

# Inicializar el cliente OpenAI
openai.api_key = os.getenv('OPENAI_API_KEY')
private = openai.api_key

client = OpenAI(
    api_key=private,
)

def process_pending_hilos():
    

    
    pending_hilos = get_pending_hilos(mysql_conn_params)

    for hilo_id, prompt in pending_hilos:
        print(f"Procesando hilo ID: {hilo_id}")

        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": """
                     Cuando se te pida y te veas capaz de generar el DU, solo responderas con:
                        {Titular": "",
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
                        }, rellenado y nada más.  SIEMPRE VA UNA LINEA DE TRANSPORTE/SERVICIO. Nunca completarás información por tu cuenta, solo colocarás la que se te da en los Contratos con al estructura: {"Titular", "Contrato", "Producto", "Envase", "Categoria_producto”, “Residuo”}
                    """},
                    {"role": "user", "content": prompt}
                ]
<<<<<<< HEAD
                
=======
>>>>>>> 45140bb9dbed86a97fb868f7b85bb080828fa816
            )
            aida_generated_du = response.choices[0].message.content
            print(f"Respuesta: {aida_generated_du}")

            mark_as_processed(mysql_conn_params, hilo_id, aida_generated_du)

        except openai.OpenAIError as e:  # Manejar errores específicos de OpenAI
            print(f"Error en la ejecución de OpenAI: {e}")

        except Exception as e:  # Manejar cualquier otro tipo de error
            print(f"Error inesperado: {e}")

def email_listener():
    while True:
        process_pending_hilos()
        time.sleep(3)  # Espera 60 segundos antes de volver a verificar

if __name__ == "__main__":
    email_listener()
