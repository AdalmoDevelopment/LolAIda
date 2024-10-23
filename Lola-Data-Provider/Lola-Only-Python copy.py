
import psycopg2
import pymysql
import time
import json
from decimal import Decimal
from dotenv import load_dotenv
import os
from Json_Formatter import json_formatter

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

def execute_query(query, params, conn_params):
    try:
        # Establecer la conexión con la base de datos
        conn = psycopg2.connect(**conn_params)
        cursor = conn.cursor()
        
        # Ejecutar la consulta con parámetros
        cursor.execute(query)
        results = cursor.fetchall()
        
        # Cerrar la conexión
        cursor.close()
        conn.close()
        
        return results
    except Exception as e:
        return str(e)
    
def nose():
    postgres_conn_params = {
        'dbname': dbname,
        'user': postgres_user,
        'password': postgres_password,
        'host': postgres_host,
        'port': postgres_port
    }
    
    query_contratos = """
        SELECT rp.display_name, paa.name as Contrato,
        case when pp.default_code is not null then concat('[',pp.default_code,'] ', pt.name) end as Producto,

        case when ptContainer.default_code is not null then concat('[',ptContainer.default_code,'] ', ptContainer.name) end as ENVASE,

        case when pc.name = 'TRANSPORTE' then null when ppWaste.default_code is not null then concat('[',ppWaste.default_code,'] ', ptWaste.name) end as categoria_producto,

        pc.name as categoria_producto

        FROM public.pnt_agreement_agreement paa

        left join res_partner rp on paa.pnt_holder_id = rp.id
        LEFT JOIN pnt_agreement_line pal ON paa.id  = pal.pnt_agreement_id

        left join uom_uom uu on pal.pnt_product_Economic_uom = uu.id

        LEFT JOIN product_product pp ON pal.pnt_product_id  = pp.id
        LEFT JOIN product_template pt ON pp.product_tmpl_id  = pt.id

        LEFT JOIN product_product ppContainer ON pal.pnt_container_id  = ppContainer.id
        LEFT JOIN product_template ptContainer ON ppContainer.product_tmpl_id  = ptContainer.id

        LEFT JOIN product_product ppWaste ON pal.pnt_product_waste_id  = ppWaste.id
        LEFT JOIN product_template ptWaste ON ppWaste.product_tmpl_id  = ptWaste.id

        left join product_category pc  on pt.categ_id = pc.id

        where pnt_holder_id IN (select id from res_partner where email ilike '%havenmarine%' and is_company = true)
        and paa.state = 'done'and pt.company_id = 1
        order by rp.display_name, paa.name
    """
    results = execute_query(query_contratos, ("nose",), postgres_conn_params)
    
    titulares = {}
    for row in results:
        cliente, contrato, producto, envase, residuo, categoria_producto = row
        
        # Si el cliente no existe, añadirlo
        if cliente not in titulares:
            titulares[cliente] = {
                "Contratos": {}
            }
        
        if contrato not in titulares[cliente]["Contratos"]:
            titulares[cliente]["Contratos"][contrato] = {
                "Productos": []
            }
        
        producto_obj = {
            "Producto": producto,
            "Envase": envase,
            "Residuo": residuo,
            "Categoria Producto": categoria_producto
        }
        titulares[cliente]["Contratos"][contrato]["Productos"].append(producto_obj)

    query_lugares_recogida = """
        SELECT paa.name, rprecog.display_name as Lugar_de_recogida
        FROM public.pnt_agreement_agreement paa
        LEFT JOIN res_partner rp ON paa.pnt_holder_id = rp.id
        LEFT JOIN pnt_agreement_partner_pickup_rel pappr ON paa.id = pappr.pnt_agreement_id
        LEFT JOIN res_partner rprecog ON pappr.partner_id = rprecog.id
        WHERE paa.pnt_holder_id IN (SELECT id FROM res_partner WHERE email ILIKE '%havenmarine%' AND is_company = true)
        AND paa.state = 'done'
        and rp.company_id = 1
        order by paa.name
    """
    results2 = execute_query(query_lugares_recogida, ("ns",), postgres_conn_params)
    
    contratos = {"Contratos": []}
    for row in results2:
        contrato, lugar_de_recogida = row
        contrato_existente = next((c for c in contratos["Contratos"] if c["Contrato"] == contrato), None)

        if contrato_existente is None:
            # Si no existe, crear una nueva entrada para el contrato
            contratos["Contratos"].append({
                "Contrato": contrato,
                "Lugares_de_recogida": [lugar_de_recogida]
            })
        else:
            if lugar_de_recogida not in contrato_existente["Lugares_de_recogida"]:
                contrato_existente["Lugares_de_recogida"].append(lugar_de_recogida)

    json_contratos = json.dumps(titulares, ensure_ascii= False, indent=4 )
    json_lugares = json.dumps(contratos, ensure_ascii= False, indent=4)

    # print("Contratos:", json_contratos, "\n")
    # print("Lugares de recogida:", json_lugares, "\n")
    
    
    result = json_formatter(results, results2)
    
    print(result)
    
    if isinstance(results, str):
        print(f"Error ejecutando la consulta: {results}\n")
    else:
        print(f" Resultado exitoso")

if __name__ == "__main__":
    nose()