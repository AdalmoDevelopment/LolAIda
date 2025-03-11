from colorama import Fore, Back, Style
import json, time
import psycopg2
import pymysql
import json
from decimal import Decimal
from OdooConnector.conn_params import postgres_conn_params, mysql_conn_params
from OdooConnector.send_du_odoo import send_du_odoo
from AidaMailInterpreter.set_label_mail import set_label_gmail
from OdooConnector.product_groups import envases_tc_cambio, tipos_thora, tipos_servicio

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

def mysql_execute_query(query, params):
	try:
		conn = pymysql.connect(**mysql_conn_params)
		cursor = conn.cursor()
		if params:
			json_du, response, success, du_id  = params
			cursor.execute(query, [json_du, response, success, du_id])
		else:
			cursor.execute(query)
		hilos = cursor.fetchall()

		conn.commit()
		cursor.close()
		conn.close()
		
		return hilos
	except pymysql.MySQLError as e:
		print(f"Error al conectar a MySQL: {e}")
		return []

def query_format_du(json_du):
	holder_name = json_du["Titular"].replace("'", "''")
	num_contrato = json_du["Contrato"]
	lugar_recogida = json_du["Lugar de recogida"]
	json_du["Categoria de vehiculo"] = ""
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
		select pp.id, pc.name
		from product_template pt
		left join product_product pp on pt.id = pp.product_tmpl_id
		left join product_category pc  on pt.categ_id = pc.id
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
		
		print(Fore.BLUE + '─' * 200 + Style.RESET_ALL)
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
		envase_cache = ''
		
		for linea in reversed(lineas_du):
			checkpoint = 1
			print('residuo y envase cache actual:',residuo_cache, envase_cache)
			results4 = execute_query(query_product_ids, (linea['Producto'], linea['Producto'], linea['Producto'],))
			results5 = execute_query(query_product_ids, (linea['Envase'], linea['Envase'], linea['Envase'],)) or [('', '')]
			results6 = execute_query(query_product_ids, (linea['Residuo'], linea['Residuo'], linea['Residuo'],)) or [('', '')]
   
			print(f"estado de la linea: {linea}, resultado 1: {results4}, resultado 2: {results5}, resultado 3: {results6}")
			# Para poner el residuo en las lineas de TC CAMBIO que vengan sin Residuo
			if du_cambio and linea['Producto'] != '[TC] CAMBIO':
				residuo_cache = results4[0][0]
				envase_cache = results5[0][0]
				print(Fore.YELLOW + 'se ha guardado el id', results4, 'en cache' + Style.RESET_ALL)
    
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
				if linea["container_id"] == None:
					linea["container_id"] = envase_cache
				print("Se ha colocado el residuo en caché")
			else:
				print(linea['Residuo'])
				print(f"\____waste_id:{results6} \n")
				linea["waste_id"] = results6[0][0] if results6 else None
				
			cat_vehiculo_aida = json_du["Categoria de vehiculo"]
			
			try:
				linea["Tipo_Producto"] = results4[0][1]
				print(f"Tipo producto es {linea['Tipo_Producto']}")
			except:
				print("No se ha podido extraer Tipo_Producto")	

			# Si la línea actual es de transporte, la usamos para condicionar la Categoría de Vehículo
			if results4[0][1] == 'TRANSPORTE':
				if linea['Producto'] == '[THORAC] SERVICIO CAMIÓN HORA (CISTERNA)':
					json_du["Categoria de vehiculo"] = "Cisternas"
					json_du["category_fleet_id"] = 13
					
				elif linea['Producto'] == '[THORA] SERVICIO CAMIÓN HORA (PULPO/GRÚA)':
					hay_big_bag = any('BIG BAG' in linea['Producto'] and linea['Tipo_Producto'] == 'ENVASE' for linea in json_du["Lineas del DU"])
					solo_big_bag = all(('BIG BAG' in linea['Producto']) for linea in json_du["Lineas del DU"] if linea['Tipo_Producto'] == 'ENVASE')

					if hay_big_bag and solo_big_bag:
						json_du["Categoria de vehiculo"] = "Gruas"
						json_du["category_fleet_id"] = 16
					else:
						json_du["Categoria de vehiculo"] = "Pulpos" 	
						json_du["category_fleet_id"] = 8
					
				elif linea['Producto'] == '[THORAR] SERVICIO CAMIÓN HORA (RECOLECTOR)':
					json_du["Categoria de vehiculo"] = "Recolectores"
					json_du["category_fleet_id"] = 15 
					
				elif linea['Producto'] == '[TC] CAMBIO':
					if linea["container_id"] in [2672, 2668, 2926]:
						json_du["Categoria de vehiculo"] = "Contenedores/Cadenas"
						json_du["category_fleet_id"] = 7
					else:
						json_du["Categoria de vehiculo"] = "Contenedores/Ganchos"
						json_du["category_fleet_id"] = 6
					
				elif linea['Producto'] == '[TT] TRANSPORTE':
					es_sanitario = any('[ES' in linea['Producto'] or 'SANITARIO' in linea['Producto'] or linea['Producto'] == "[EUHF] UNIDAD HIGIENE FEMENINA" for linea in json_du["Lineas del DU"])

					if es_sanitario:
						json_du["Categoria de vehiculo"] = "Sanitarios"
						json_du["category_fleet_id"] = 4
					else:
						json_du["Categoria de vehiculo"] = "RPs"
						json_du["category_fleet_id"] = 14
				
				if linea['Producto'] != '[TC] CAMBIO':
					linea["container_id"] = None
					linea["Envase"] = None

				if cat_vehiculo_aida != json_du["Categoria de vehiculo"]:
					print(Fore.MAGENTA + "Se ha modificado la categoría vehículo a " + json_du["Categoria de vehiculo"] + Style.RESET_ALL)
			print("-------------------------------------------------------------------------------------------------------")
	
	except Exception as e:
		print(f"Error al ejecutar la consulta: {e} {checkpoint}")
  
def change_du_type(json_du, lineas_du):
    
	for linea in lineas_du:
		# Se cambian los [TC] CAMBIO que deberían ser [TT] TRANSPORTE
		#Se ha extraido esta línea para que cualquier CAMBIO de un envase que no esté en la lista no se haga
		# and linea['Envase'] in [
		# 		'[EGRGA] GRG 1000L ABIERTO', '[EGRG1000L] GRG 1000L',
		# 		'[ECUB] CUBETO', '[EJ] JAULA'
		# 	]
		if linea['Producto'] == '[TC] CAMBIO' and linea["Envase"] not in [
				'[EC] CONTENEDOR C (28 m3)', '[EK] CONTENEDOR K (5 m3)', '[EKT] CONTENEDOR TAPADO K (5 m3)', '[EP] CONTENEDOR P (11 m3)',
				'CONTENEDOR K PEQUEÑO (1.5 m3)',
				'[EAZ1000] CONTENEDOR AZUL 1000L', '[EV1000] CONTENEDOR VERDE 1000L', '[EAM1000] CONTENEDOR AMARILLO 1000L',
				'[EAUTO] AUTOCOMPACTADOR',
				'[EAE] COMPACTADOR ESTÁTICO (30 m3)'
			]:
			print(f"Es un cambio de un Envase({linea['Envase']}) que debería ser TT")
			
			if any(l["Producto"] == linea["Envase"] for l in lineas_du):
				# Eliminar la línea con el Producto "[TC] CAMBIO"
				lineas_du = [l for l in lineas_du if l['Producto'] != "[TC] CAMBIO"]
				json_du["Lineas del DU"] = lineas_du
				print("Se ha eliminado la línea de TC CAMBIO porque debería ser TT")
			else:
				linea["Producto"] = linea["Envase"]
				linea["Envase"] = None
				linea["Residuo"] = None
				linea["Tipo_Producto"] = 'TRANSPORTE'
				linea["Unidades"] = 1

	
			print(f'Lineas hasta aqui: {json.dumps(json_du["Lineas del DU"] , indent=2)}')

			if not any(l["Producto"] == "[TT] TRANSPORTE" for l in lineas_du):
				print("Se añade linea de TT")
				nueva_linea = {
					"Producto": "[TT] TRANSPORTE",
					"Envase": None,
					"Residuo": None,
					"Tipo_Producto": 'TRANSPORTE',
					"Unidades": 1
				} 	
				lineas_du.insert(0, nueva_linea)
		
		# Si viene un DU de estructura TT pero con el transporte equivocado(THORA/C/R)
		if not any(l["Producto"] == "[TT] TRANSPORTE" for l in lineas_du) and ('THORA' in linea['Producto'] or 'CAMBIO' in linea['Producto']) and any(linea["Tipo_Producto"] == "ENVASE" for linea in lineas_du) and all(linea["Producto"] not in envases_tc_cambio for linea in lineas_du):
			print(f"Debería ser TT porque es {linea['Producto']} y tiene reposiciones \n")
			linea['Producto'] = '[TT] TRANSPORTE'

		for linea in lineas_du[:]:  # Iterar con copia para eliminar elementos de la lista
			if linea['Producto'] == '[TC] CAMBIO':
				lineas_du = [l for l in reversed(lineas_du) if l['Producto'] not in tipos_thora]
				json_du["Lineas del DU"] = lineas_du
				print("Se ha eliminado la línea de THORA porque había un TC CAMBIO")
			if any(linea["Producto"] in envases_tc_cambio for linea in lineas_du):
				if linea['Producto'] in tipos_servicio:
					linea['Producto'] = '[TC] CAMBIO'
				lineas_du = [l for l in lineas_du if l['Producto'] not in envases_tc_cambio or (l['Producto'] != '[TC] CAMBIO' and l["Tipo_Producto"] == "TRANSPORTE")]
				json_du["Lineas del DU"] = lineas_du
		
		print("Líneas del DU después de la eliminación de THORA:", lineas_du)

		# Sí hay uno de estos envases, se aplica una de las siguientes reglas
		if any(word in linea['Producto'] for word in [
				'SANDACH',
				'MATERIAL ALIMENTACIÓN INADECUADO'
			]):
			for linea in lineas_du:
				if linea['Producto'] in ['[THORA] SERVICIO CAMIÓN HORA (PULPO/GRÚA)', '[THORAC] SERVICIO CAMIÓN HORA (CISTERNA)', '[THORAR] SERVICIO CAMIÓN HORA (RECOLECTOR)']:
					print('Por sus residuos debería ser TT, en cambio es: ', linea['Producto'])
					linea['Producto'] = '[TT] TRANSPORTE'
					break
	return json_du

def du_fixer():
	pending_hilos = mysql_execute_query("SELECT gda.id, id_hilo, du , h.mail_track_id FROM generated_dus_aida gda, hilos h WHERE id_hilo = h.id AND odoo_final_response IS NULL AND DATE(date_created) = CURDATE() AND odoo_processed = 0", None)

	#Hilos con al menos un DU de [TT]:
	dus_tt_unidos = []
	
	for du_id, hilo_id, aida_generated, mail_track_id in pending_hilos:
		print(f"Se está tratanto el DU {du_id}")
		if du_id not in dus_tt_unidos:
			try:
				json_du = json.loads(aida_generated)
				print("JSON cargado con éxito")
			except json.JSONDecodeError as e:
				print(f"Error al decodificar el JSON en el hilo {hilo_id}: {e}")
				print(f"Contenido de 'aida_generated': {aida_generated}")
				continue
			
			json_du["Track_Gmail_Uid"] = mail_track_id
			print(Fore.BLUE + f"EL MAIL TRACK ID DE ESTE CORREO ES: {mail_track_id}, en el du : {json_du['Track_Gmail_Uid']}" + Style.RESET_ALL)
			
			lineas_du = json_du["Lineas del DU"]
			print(f'DU ante de formatear las lineas {json.dumps(json_du, indent=2)}')
			query_format_du(json_du)

			json_du = change_du_type(json_du, lineas_du)

			print(f'Du antes de comprobar si se puede unificar: {json_du}')

			print(f'Estado hilo: {hilo_id}')

			# Si se está tratando un TT, une las lineas del resto de DUs de TT de la misma petición, si los hay.
			if any(linea["Producto"] == "[TT] TRANSPORTE" for linea in lineas_du):
				print("Es un DU de TT y se intentara mergear")
				for du_id_merge, hilo_id_merge, aida_generated_merge, mail_track_id in pending_hilos:
					if hilo_id_merge == hilo_id and du_id_merge != du_id and any(linea["Producto"] == "[TT] TRANSPORTE" for linea in lineas_du):
						print("chekpoint 1 ")
						try:
							json_du_merge = json.loads(aida_generated_merge)
						except json.JSONDecodeError as e:
							print(f"Error al decodificar el JSON en el hilo {hilo_id_merge}: {e}")
							continue
						
						query_format_du(json_du_merge)
      
						json_du_merge = change_du_type(json_du_merge, json_du_merge["Lineas del DU"])
							
						if json_du_merge["Lugar de recogida"] == json_du["Lugar de recogida"] and any(linea["Producto"] == "[TT] TRANSPORTE" for linea in json_du_merge["Lineas del DU"]):
							print(f"Se va a unir al du ({du_id}) el du({du_id_merge}) porque tienen el mismo lugar de recogida, {json_du['Lugar de recogida']} y {json_du_merge['Lugar de recogida']}")
							
							for linea_merge in json_du_merge["Lineas del DU"]:
									# Buscar si ya existe una línea igual en el DU principal
									encontrada = False
									for linea in reversed(json_du["Lineas del DU"]):
										if linea["Producto"] == linea_merge["Producto"]:
											print(f"Se suman las cantidades de {linea['Producto']}: {linea['Unidades']} y {linea_merge['Unidades']}")
											if linea_merge["Producto"] != "[TT] TRANSPORTE":
												linea["Unidades"] += linea_merge["Unidades"]
											else:
												linea["Unidades"] = 1
											encontrada = True
											break

									# Si no existe, agregar la línea
									if not encontrada:
										json_du["Lineas del DU"].append(linea_merge)
							dus_tt_unidos.append(du_id_merge)

			query_format_du(json_du)

			print("LLega a formatearse")
			
			print(Fore.BLUE + f"el du definitivo id {du_id} del hilo id {hilo_id} sería {json.dumps(json_du, indent=2)}" + Style.RESET_ALL)
			print("DU-------------------------------------------------------------------------------------------------------")
   
			# try:
			# 	save_file = open(f"./OdooConnector/dumps/savedata_{hilo_id}_{du_id}.json", "x", encoding="utf-8")  
			# 	json.dump(json_du, save_file, ensure_ascii= False, indent = 6)
			# 	save_file.close()
			# except FileExistsError:
			# 	print(Fore.YELLOW + f"¡savedata{hilo_id}_{du_id}.json ya existe!" + Style.RESET_ALL)

			print( Fore.CYAN + 'Intentando crear DU para', json_du['Titular'] ,', con el contrato', json_du['Contrato'], Style.RESET_ALL)
			
			# response, success = send_du_odoo(json_du)

			# print(f"UPDATE generated_dus_aida SET odoo_final_response = {response}, created = {success} WHERE id = {du_id}")
			
			# query = 'UPDATE generated_dus_aida SET du_sended = %s, odoo_final_response = %s, created = %s WHERE id = %s'
			# query_hilo = f'UPDATE hilos SET odoo_processed = 1 WHERE id = {hilo_id}'

			# try:
			# 	response = mysql_execute_query(query , params = [json.dumps(json_du), response, success, du_id])
			# 	print('Metido en la mysql!!!', response)
    
			# 	response = mysql_execute_query(query_hilo, None)
			# 	print('Metido en la mysql!!!', response)
			# except Exception as e:
			# 	print(f"Error al conectar a MySQL: {e}")
			
			# if success:
			# 	set_label_gmail(mail_track_id, 'Label_5337764771777216081')
		
	return(True)

if __name__ == "__main__":
	du_fixer()