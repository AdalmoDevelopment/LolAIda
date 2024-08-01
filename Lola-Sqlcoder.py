import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
import psycopg2
import pymysql
import time
import json  # Para serializar los resultados a JSON
from decimal import Decimal
from dotenv import load_dotenv
import os

load_dotenv()

dbname = os.getenv('DB_NAME')
postgres_user = os.getenv('DB_USER')
postgres_password = os.getenv('DB_PASSWORD')
postgres_host = os.getenv('DB_HOST')
postgres_port = os.getenv('DB_PORT')

mysql_host = os.getenv('MYSQL_HOST')
mysql_user = os.getenv('MYSQL_USER')
mysql_password = os.getenv('MYSQL_PASSWORD')
mysql_database = os.getenv('MYSQL_DATABASE')

print(mysql_host)
print(postgres_host)

# Función para generar el prompt
def generate_prompt(question, prompt_file="prompt.md", metadata_file="metadata.sql"):
    with open(prompt_file, "r") as f:
        prompt = f.read()
    
    with open(metadata_file, "r") as f:
        table_metadata_string = f.read()

    prompt = prompt.format(
        user_question=question, table_metadata_string=table_metadata_string
    )
    return prompt

# Función para cargar el tokenizador y el modelo
def get_tokenizer_model(model_name):
    model_path = "./saved_model"
    if not os.path.exists(model_path):
        # Descargar y guardar el modelo y el tokenizador si no existen en disco
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            trust_remote_code=True,
            torch_dtype=torch.float32,
            device_map="auto",
            use_cache=True,
            load_in_8bit=True 
        )
        tokenizer.save_pretrained(model_path)
        model.save_pretrained(model_path)
    else:
        # Cargar desde disco
        tokenizer = AutoTokenizer.from_pretrained(model_path)
        model = AutoModelForCausalLM.from_pretrained(model_path)

    return tokenizer, model

# Función para ejecutar la inferencia
def run_inference(question, tokenizer, model):
    prompt = generate_prompt(question)
    
    pipe = pipeline(
        "text-generation",
        model=model,
        tokenizer=tokenizer,
        max_new_tokens=380,
        do_sample=False,
        return_full_text=False,
        num_beams=5,
    )
    
    eos_token_id = tokenizer.eos_token_id
    generated_query = (
        pipe(
            prompt,
            num_return_sequences=1,
            eos_token_id=eos_token_id,
            pad_token_id=eos_token_id,
        )[0]["generated_text"]
        .split(";")[0]
        .split("```")[0]
        .strip()
        + ";"
    )
    return generated_query

# Función para ejecutar una consulta SQL en la base de datos PostgreSQL
def execute_query(query, conn_params):
    try:
        # Establecer la conexión con la base de datos
        conn = psycopg2.connect(**conn_params)
        cursor = conn.cursor()
        
        # Ejecutar la consulta
        cursor.execute(query)
        results = cursor.fetchall()
        
        # Cerrar la conexión
        cursor.close()
        conn.close()
        
        return results
    except Exception as e:
        return str(e)

# Función para obtener las queries de la tabla hilos en MySQL donde lola_generated = 0
def get_pending_hilos(mysql_conn_params):
    try:
        conn = pymysql.connect(**mysql_conn_params)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, aida_request FROM hilos WHERE lola_generated = 0")
        hilos = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return hilos
    except pymysql.MySQLError as e:
        print(f"Error al conectar a MySQL: {e}")
        return []

# Función para actualizar el campo lola_generated en la tabla hilos
def mark_as_processed(mysql_conn_params, hilo_id, results, results2):
    def default_converter(obj):
        if isinstance(obj, Decimal):
            return float(obj)
        raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

    try:
        conn = pymysql.connect(**mysql_conn_params)
        cursor = conn.cursor()
        
        # Convertir los resultados a JSON utilizando el convertidor personalizado
        results_str = json.dumps(results, default=default_converter, ensure_ascii=False)
        results_str2 = json.dumps(results2, default=default_converter, ensure_ascii=False)
         
        cursor.execute(
            """
            UPDATE hilos
            SET lola_response = (CONCAT('{ "Contratos": ', %s, ', "Lugares de recogida": ', %s, ' }')), lola_generated = 1
            WHERE id = %s
            """,
            (results_str, results_str2, hilo_id)
        )
        
        conn.commit()
        
        cursor.close()
        conn.close()
    except pymysql.MySQLError as e:
        print(f"Error al actualizar MySQL: {e}")


def main():
    print("Loading model...")
    tokenizer, model = get_tokenizer_model("defog/sqlcoder-7b-2")
    print("Model loaded. Listening for new queries...\n")

    # Parámetros de conexión a la base de datos PostgreSQL
    postgres_conn_params = {
        'dbname': 'STA',
        'user': postgres_user,
        'password': postgres_password,
        'host': postgres_host,
        'port': postgres_port
    }
    
    # Parámetros de conexión a la base de datos MySQL
    mysql_conn_params = {
        'host': mysql_host,
        'user': mysql_user,
        'password': mysql_password,
        'database': mysql_database
    }

    while True:
        # Obtener las queries pendientes desde la base de datos MySQL
        pending_hilos = get_pending_hilos(mysql_conn_params)
        
        for hilo_id, question in pending_hilos:
           
            print(f"Obteniendo contratos de {question}")
            question = f"Dame la información de {question}"
            sql_query = run_inference(question, tokenizer, model)
            print("Executing SQL query...")
            results = execute_query(sql_query, postgres_conn_params)
            
            print(f"Obteniendo lugares de recogida")
            question2 = f"Dame los lugares de recogida de {question}"
            sql_query = run_inference(question2, tokenizer, model)
            results2 = execute_query(sql_query, postgres_conn_params)
    
            print("Executing SQL query...")
            results2 = execute_query(sql_query, postgres_conn_params)
            
            if isinstance(results, str):
                print(f"Error executing query: {results}\n")
                mark_as_processed(mysql_conn_params, hilo_id, results, results2)
            else:
                print(f'Resultados :', results)
                print(f"Generated SQL query:\n{sql_query}\n")
                mark_as_processed(mysql_conn_params, hilo_id, results, results2)
        
        # Esperar un tiempo antes de volver a revisar la tabla
        time.sleep(10)  # Espera de 10 segundos antes de la siguiente verificación

if __name__ == "__main__":
    main()
