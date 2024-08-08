import psycopg2
import pymysql
import time
import json
from decimal import Decimal
from dotenv import load_dotenv
import os

load_dotenv()

# Configuración de conexión a PostgreSQL
dbname = os.getenv('DB_NAME')
postgres_user = os.getenv('DB_USER')
postgres_password = os.getenv('DB_PASSWORD')
postgres_host = os.getenv('DB_HOST')
postgres_port = os.getenv('DB_PORT')

# Configuración de conexión a MySQL
mysql_host = os.getenv('MYSQL_HOST')
mysql_user = os.getenv('MYSQL_USER')
mysql_password = os.getenv('MYSQL_PASSWORD')
mysql_database = os.getenv('MYSQL_DATABASE')

print(mysql_host)
print(postgres_host)

# Función para ejecutar una consulta SQL en PostgreSQL
def execute_query(query, params, conn_params):
    try:
        # Establecer la conexión con la base de datos
        conn = psycopg2.connect(**conn_params)
        cursor = conn.cursor()
        
        # Ejecutar la consulta con parámetros
        cursor.execute(query, params)
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
        
        cursor.execute("SELECT id, aida_request FROM hilos WHERE lola_generated = 0 AND aida_response LIKE 'Lola%'")
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

# Función principal
def main():
    print("Listening for new queries...\n")

    # Parámetros de conexión a la base de datos PostgreSQL
    postgres_conn_params = {
        'dbname': dbname,
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
        
        for hilo_id, aida_request in pending_hilos:
            # Usamos el valor de `aida_request` para formar las consultas
            email_pattern = f"%{aida_request}%"

            print(f"Obteniendo contratos para: {aida_request}")
            query_contratos = """
                SELECT rp.name, paa.name, pt.name as producto, uu.name as UNIDAD_ECONOMICA,
                       pal.pnt_price_unit as precio_unitario, ptContainer.name as ENVASE,
                       case when ppWaste.default_code is not null then 
                            concat('[', ppWaste.default_code, '] ', ptWaste.name) 
                       end as Residuo 
                FROM public.pnt_agreement_agreement paa
                LEFT JOIN res_partner rp ON paa.pnt_holder_id = rp.id
                LEFT JOIN pnt_agreement_line pal ON paa.id = pal.pnt_agreement_id
                LEFT JOIN uom_uom uu ON pal.pnt_product_Economic_uom = uu.id
                LEFT JOIN product_product pp ON pal.pnt_product_id = pp.id
                LEFT JOIN product_template pt ON pp.product_tmpl_id = pt.id
                LEFT JOIN product_product ppContainer ON pal.pnt_container_id = ppContainer.id
                LEFT JOIN product_template ptContainer ON ppContainer.product_tmpl_id = ptContainer.id
                LEFT JOIN product_product ppWaste ON pal.pnt_product_waste_id = ppWaste.id
                LEFT JOIN product_template ptWaste ON ppWaste.product_tmpl_id = ptWaste.id
                WHERE pnt_holder_id IN (SELECT id FROM res_partner WHERE email ILIKE %s AND is_company = true)
            """
            results = execute_query(query_contratos, (email_pattern,), postgres_conn_params)

            print(f"Obteniendo lugares de recogida para: {aida_request}")
            query_lugares_recogida = """
                SELECT paa.pnt_complete_name, rprecog.display_name as Lugares_de_recogida
                FROM public.pnt_agreement_agreement paa
                LEFT JOIN res_partner rp ON paa.pnt_holder_id = rp.id
                LEFT JOIN pnt_agreement_partner_pickup_rel pappr ON paa.id = pappr.pnt_agreement_id
                LEFT JOIN res_partner rprecog ON pappr.partner_id = rprecog.id
                WHERE paa.pnt_holder_id IN (SELECT id FROM res_partner WHERE email ILIKE %s AND is_company = true)
                AND paa.state = 'done'
            """
            results2 = execute_query(query_lugares_recogida, (email_pattern,), postgres_conn_params)
            
            if isinstance(results, str):
                print(f"Error ejecutando la consulta: {results}\n")
            else:
                print(f"Resultados obtenidos: {results}")
            
            mark_as_processed(mysql_conn_params, hilo_id, results, results2)
        
        # Esperar un tiempo antes de volver a revisar la tabla
        time.sleep(10)  # Espera de 10 segundos antes de la siguiente verificación

if __name__ == "__main__":
    main()
