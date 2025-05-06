import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST"),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DATABASE"),
    )

def fetch_table_data(cursor, table_name):
    cursor.execute(f"SELECT * FROM {table_name}")
    return cursor.fetchall(), [desc[0] for desc in cursor.description]

def get_all_configs_and_params():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        data = {}
        
        for table in ["params", "configs"]:
            rows, columns = fetch_table_data(cursor, table)
            data[table] = [dict(zip(columns, row)) for row in rows]
            
        cursor.close()
        conn.close()
        return data
    except mysql.connector.Error as err:
        print(f"Error al conectar con la base de datos: {err}")
        return None
    
def get_config_by_name(name):
    all_data = get_all_configs_and_params()
    if not all_data:
        return None

    # Buscar en params
    for param in all_data["params"]:
        if param.get("name") == name:
            return param

    # Buscar en configs
    for config in all_data["configs"]:
        if config.get("name") == name:
            return config

    return None  # No encontrado


if __name__ == "__main__":
    all_configs = get_config_by_name("Prompt Email Interpreter")["value"]
    from_ = 'skibidi@toilet.sigma'
    print (get_config_by_name("Prompt Email Interpreter")["value"].format(from_=from_))
    if all_configs:
        import json
        print(json.dumps(all_configs, indent=2, ensure_ascii=False))
