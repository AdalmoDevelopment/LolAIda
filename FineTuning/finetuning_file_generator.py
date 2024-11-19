import pymysql, os, json
from dotenv import load_dotenv

load_dotenv()

mysql_conn_params = {
	'host': os.getenv('MYSQL_HOST'),
	'user': os.getenv('MYSQL_USER'),
	'password': os.getenv('MYSQL_PASSWORD'),
	'database': os.getenv('MYSQL_DATABASE')
}

def get_pending_hilos(mysql_conn_params):
	try:
		conn = pymysql.connect(**mysql_conn_params)
		cursor = conn.cursor()
		
		query = "SELECT aida_correo, lola_response_json, aida_generated_du, user_for_wrong_examples, model_for_wrong_examples FROM hilos WHERE approved AND lola_response_json IS NOT NULL "
		cursor.execute(query)
		results = cursor.fetchall()
		
		cursor.close()
		conn.close()
		
		return results
	except pymysql.MySQLError as e:
		print(f"Error al conectar a MySQL: {e}")
		return []

def finetuning_file_generator():
	results = get_pending_hilos(mysql_conn_params)
	for result in results:	
		aida_correo, lola_response_json, aida_generated_du, user_for_wrong_examples, model_for_wrong_examples = result
		
		user_prompt = f"Me haces este/estos DU? Mail: {aida_correo}, Info: {lola_response_json}"
		gpt_response = aida_generated_du
		
		if user_for_wrong_examples is None:
			template = {
				"messages": [
					{"role": "user", "content": user_prompt},
					{"role": "assistant", "content": gpt_response}
				]
			}
		else:
			template = {
				"messages": [
					{"role": "user", "content": user_prompt},
					{"role": "assistant", "content": gpt_response},
					{"role": "user", "content": user_for_wrong_examples}, 	
					{"role": "assistant", "content": model_for_wrong_examples}
				]
			}
		
		json_template = json.dumps(template,  ensure_ascii= False)
		with open('./finetuning_dumpy.jsonl', 'a', encoding='utf-8') as f:
			f.write(json_template + '\n')
			print("metido")

if __name__ == "__main__":
	finetuning_file_generator()