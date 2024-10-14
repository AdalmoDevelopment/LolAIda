import json
import psycopg2
import pymysql
import time
import json
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

postgres_conn_params = {
        'dbname': dbname,
        'user': postgres_user,
        'password': postgres_password,
        'host': postgres_host,
        'port': postgres_port
}

mysql_conn_params = {
        'host': mysql_host,
        'user': mysql_user,
        'password': mysql_password,
        'database': mysql_database
}

def execute_query(query, params, conn_params):
    try:
        conn = psycopg2.connect(**conn_params)
        cursor = conn.cursor()
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return results
    except Exception as e:
        return str(e)
    
def get_pending_hilos(mysql_conn_params):
    try:
        conn = pymysql.connect(**mysql_conn_params)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, aida_generated_du, mail_track_id FROM hilos WHERE aida_generated_du is not null and aida_generated_du like '%Líneas del DU%' AND date_created > '2024-10-11' order by id desc ")
        hilos = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return hilos
    except pymysql.MySQLError as e:
        print(f"Error al conectar a MySQL: {e}")
        return []
    
def queries_du(json_du):
    holder_name = json_du["Titular"].replace("'", "''")
    num_contrato = json_du["Contrato"]
    lugar_recogida = json_du["Lugar de recogida"]
    categoria_vehiculo = (json_du["Categoria de vehiculo"].replace("/", " / ")).replace("Contenedor ", "Contenedores ")
    lineas_du = json_du["Lineas del DU"]
    
    print(f"Holder ID: {holder_name}")
    print(f"Contrato: {num_contrato}")
    
    # Consulta SQL
    query_holder_id = """
        select rp.id, paa.id
        from res_partner rp
        JOIN pnt_agreement_agreement paa ON rp.id  = paa.pnt_holder_id
        and rp.name != 'Adalmo'
        and paa.name = %s
    """
    query_pickup_id = """
        SELECT rprecog.id FROM public.pnt_agreement_agreement paa
        left join res_partner rp on paa.pnt_holder_id = rp.id
        left join pnt_agreement_partner_pickup_rel pappr on paa.id = pappr.pnt_agreement_id
        left join res_partner rprecog on pappr.partner_id = rprecog.id
        where (rprecog.name = %s OR rprecog.display_name = %s)
        and paa.name = %s
        limit 1
    """
    
    query_fleet_id = """
        select id from pnt_fleet_vehicle_category pfvc
        where pnt_complete_name = %s
    """
    
    query_product_ids = """
        select id
        from product_template
        where name = CASE 
            WHEN position(']' in %s) > 0 THEN split_part(%s, '] ', 2)
            ELSE %s
        END
        and company_id = 1
    """
    for linea in lineas_du:
        
        results4 = execute_query(query_product_ids, ( linea['Producto'], linea['Producto'], linea['Producto']), postgres_conn_params)
        results5 = execute_query(query_product_ids, ( linea['Envase'], linea['Envase'], linea['Envase']), postgres_conn_params)
        results6 = execute_query(query_product_ids, ( linea['Residuo'], linea['Residuo'], linea['Residuo']), postgres_conn_params)
        
        
        print("-------------------------------------------------------------------------------------------------------")
        print(linea['Producto'])
        print(f"product_id:{results4}")
        print(linea['Envase'])
        print(f"container_id:{results5}")
        print(linea['Residuo'])
        print(f"waste_id:{results6}")
        print("-------------------------------------------------------------------------------------------------------")
        linea["product_id"] = results4[0][0] if results4 else None
        linea["container_id"] = results5[0][0] if results5 else None
        linea["waste_id"] = results6[0][0] if results6 else None

    try:
        results = execute_query(query_holder_id, (num_contrato,), postgres_conn_params)
        results2 = execute_query(query_pickup_id, ( lugar_recogida, lugar_recogida, num_contrato), postgres_conn_params)
        results3 = execute_query(query_fleet_id, ( categoria_vehiculo,), postgres_conn_params)

        json_du["holder_id"] = results[0][0] if results else None
        json_du["agreement_id"] = results[0][1] if results else None
        json_du["pickup_id"] = results2[0][0] if results2 else None
        json_du["category_fleet_id"] = results3[0][0] if results3 else None            
        
        print(f"Id holder y contrato: {results}")
        print(f"{lugar_recogida} / {holder_name} / Id lugar de recogida: {results2}")
        print(f"Id categoria vehiculo: {results3}")
        print(f"Ids products: {results4}  \n")
        
    except Exception as e:
        print(f"Error al ejecutar la consulta: {e}")

def main():
    print('1')

    while True:
        pending_hilos = get_pending_hilos(mysql_conn_params)
        
        for hilo_id, aida_generated, mail_track_id in pending_hilos:
            print(hilo_id)
            try:
                # Intentamos cargar el JSON
                json_du = json.loads(aida_generated)
                print("JSON cargado con éxito")
            except json.JSONDecodeError as e:
                # Muestra el contenido que causó el error para facilitar la depuración
                print(f"Error al decodificar el JSON en el hilo {hilo_id}: {e}")
                print(f"Contenido de 'aida_generated': {aida_generated}")
                continue  # Salta a la siguiente iteración si el JSON es inválido

            queries_du(json_du)

            json_du["Track_Gmail_Uid"] = mail_track_id
            save_file = open(f"./dumps/savedata{hilo_id}.json", "x")  
            json.dump(json_du, save_file, indent = 6)  
            save_file.close()  
            print(json_du)
            
        break

if __name__ == "__main__":
    main()