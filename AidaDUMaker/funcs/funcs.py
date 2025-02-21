from dotenv import load_dotenv
import os
import pymysql

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
			SELECT id, CONCAT('¿Me haces este/estos DU? Mail:', aida_correo , ', "Info:": ', lola_response_json)
			FROM hilos
			WHERE lola_generated = 1 AND aida_generated = 0
			AND lola_response != '{ "Contratos": [], "Lugares de recogida": [] }' AND CONCAT('¿Me haces este DU? Mail:', aida_correo , ', "Info:": ', lola_response,' }') IS NOT NULL and DATE(date_created) = CURDATE()
		""")
		hilos = cursor.fetchall()
		
		cursor.close()
		conn.close()
		
		return hilos
	except pymysql.MySQLError as e:
		print(f"Error al conectar a MySQL: {e}")
		return []

def mark_as_processed(mysql_conn_params, hilo_id, aida_generated_du, aida_response):
	try:
		conn = pymysql.connect(**mysql_conn_params)
		cursor = conn.cursor()
		
		if aida_generated_du == None and aida_response == None:
			print('Se borra lo anterior del hilo:', hilo_id)
			cursor.execute("""
				DELETE FROM generated_dus_aida WHERE id_hilo = %s
			""", ( hilo_id ))
			conn.commit()
		else:
			cursor.execute("""
				UPDATE hilos
				SET aida_generated = 1, aida_generated_du = %s
				WHERE id = %s
			""", ( aida_response, hilo_id))
			conn.commit()
			
			if aida_generated_du != None :
				cursor.execute("""
				INSERT INTO generated_dus_aida(id_hilo, message, du, time)
				VALUES (%s, %s, %s, CURRENT_TIMESTAMP())
				""", (hilo_id, aida_response, aida_generated_du))
				conn.commit()
				
		cursor.close()  
		conn.close()

	except pymysql.MySQLError as e:
		print(f"Error al actualizar MySQL: {e}")