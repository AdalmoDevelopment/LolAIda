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
			SELECT id, CONCAT('Tarea: Generar un Documento Único (DU) en formato JSON. \n Correo recibido:', aida_correo, '\n Información contextual: ', lola_response_json, 'Instrucciones:
		- Extrae solo lo necesario desde el bloque "Información contextual".
		- Selecciona el titular correcto, el contrato correcto y el lugar de recogida exacto.
		- Añade la línea del producto/residuo correspondiente y la del envase si aplica.
		- Devuelve el resultado exclusivamente llamando a la función generate_du.')
  
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
	print('🟢 Llega a mark_as_processed con:', hilo_id, '\n DU: \n', aida_generated_du, '\n Respuesta: \n', aida_response)
	try:
		print('🔄 Conectando a MySQL...')
		conn = pymysql.connect(**mysql_conn_params)
		cursor = conn.cursor()  
		if aida_generated_du is None and aida_response is None:
			print('🧹 Borrando datos anteriores para hilo:', hilo_id)
			cursor.execute("""DELETE FROM generated_dus_aida WHERE id_hilo = %s""", (hilo_id,))
			conn.commit()
		else:
			print('📝 Actualizando tabla `hilos`...')
			cursor.execute("""
				UPDATE hilos
				SET aida_generated = 1, aida_generated_du = %s
				WHERE id = %s
			""", (aida_response, hilo_id))
			conn.commit()

		try:
			if aida_generated_du is not None:
				print("📥 Intentando insertar en `generated_dus_aida`...")
				cursor.execute("""
					INSERT INTO generated_dus_aida(id_hilo, message, du, time)
					VALUES (%s, %s, %s, CURRENT_TIMESTAMP())
				""", (hilo_id, aida_response, aida_generated_du))
				conn.commit()
				print("✅ Insert OK")
		except Exception as insert_err:
			print(f"❌ Error durante INSERT: {insert_err}")


		print('✅ Cambios guardados correctamente.')
		cursor.close()
		conn.close()

	except Exception as e:
		print(f"❌ ERROR en mark_as_processed: {e}")
