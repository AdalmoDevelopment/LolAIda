from colorama import Fore, Back, Style
import json
import psycopg2
import pymysql
import json
from decimal import Decimal
from conn_params import postgres_conn_params, mysql_conn_params

def execute_query(query, params):
    try:
        conn = psycopg2.connect(**postgres_conn_params)
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
        
        cursor.execute("SELECT gda.id, id_hilo, du , h.mail_track_id FROM generated_dus_aida gda, hilos h WHERE id_hilo = h.id AND date_created > '2024-10-12' ")
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
        select pp.id
        from product_template pt
        left join product_product pp on pt.id = pp.product_tmpl_id 
        where
            case WHEN position(']' in %s) = 0 then pt.name = %s
            else concat('[',pp.default_code,'] ', pt.name) = %s
        END
        and pp.active          
        and company_id = 1 
    """
    
    try:
        results = execute_query(query_holder_id, (num_contrato,))
        results2 = execute_query(query_pickup_id, ( lugar_recogida, lugar_recogida, num_contrato))
        results3 = execute_query(query_fleet_id, ( categoria_vehiculo,))

        json_du["holder_id"] = results[0][0] if results else None
        json_du["agreement_id"] = results[0][1] if results else None
        json_du["pickup_id"] = results2[0][0] if results2 else None
        json_du["category_fleet_id"] = results3[0][0] if results3 else None            
        
        print("\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\")
        print(f"Id holder y contrato: {results}")
        print(f"{lugar_recogida} / {holder_name} / Id lugar de recogida: {results2}")
        print(f"Id categoria vehiculo: {results3}")
        print("-------------------------------------------------------------------------------------------------------")

        du_cambio = False
        for linea in lineas_du:
            if linea['Producto'] == '[TC] CAMBIO':
                du_cambio = True
                print("Es un du de cambio")
        
        residuo_cache = ''
        
        for linea in reversed(lineas_du):
            print('residuo cache actual:',residuo_cache)
            results4 = execute_query(query_product_ids, ( linea['Producto'], linea['Producto'], linea['Producto'],))
            results5 = execute_query(query_product_ids, ( linea['Envase'], linea['Envase'], linea['Envase'],))
            results6 = execute_query(query_product_ids, ( linea['Residuo'], linea['Residuo'], linea['Residuo'],))
           
            if du_cambio and linea['Producto'] != '[TC] CAMBIO':
                residuo_cache = results4[0][0]
                print('se ha guardado el id', results4, 'en cache')
            print("\n", linea['Producto'])
            print(f"\____product_id:{results4} \n")
            linea["product_id"] = results4[0][0] if results4 else None
            
            print(linea['Envase'])
            print(f"\____pcontainer_id:{results5} \n")
            linea["container_id"] = results5[0][0] if results5 else None
            
            if linea['Producto'] == '[TC] CAMBIO':
                print(linea['Residuo'])
                print(f"\____waste_id:{residuo_cache} \n")
                linea["waste_id"] = residuo_cache
                print("Se ha colocado el residuo en caché")
            else:
                print(linea['Residuo'])
                print(f"\____waste_id:{results6} \n")
                linea["waste_id"] = results6[0][0] if results6 else None
            
            print("-------------------------------------------------------------------------------------------------------")

    except Exception as e:
        print(f"Error al ejecutar la consulta: {e}")

def main():
    print('1')
    print(mysql_conn_params)
    while True:
        pending_hilos = get_pending_hilos(mysql_conn_params)
        
        for du_id, hilo_id, aida_generated, mail_track_id in pending_hilos:
            print(hilo_id)
            try:
                json_du = json.loads(aida_generated)
                print("JSON cargado con éxito")
            except json.JSONDecodeError as e:
                print(f"Error al decodificar el JSON en el hilo {hilo_id}: {e}")
                print(f"Contenido de 'aida_generated': {aida_generated}")
                continue  

            queries_du(json_du)

            json_du["Track_Gmail_Uid"] = mail_track_id
            save_file = open(f"./dumps/savedata{hilo_id}_{du_id}.json", "x", encoding="utf-8")  
            json.dump(json_du, save_file, ensure_ascii= False, indent = 6)  
            save_file.close()  
            print(json_du)
            
        break

if __name__ == "__main__":
    main()