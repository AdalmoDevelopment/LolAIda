import os, re, json, requests
from dotenv import load_dotenv
from colorama import Fore, Back, Style

load_dotenv()

du = {
  "Titular": "AENA SME SA",
  "Contrato": "AA2403673",
  "Lugar de recogida": "AENA SME SA, Planta de Transferencia",
  "Categoria de vehiculo": "Contenedores/Cadenas",
  "Lineas del DU": [
	{
	  "Producto": "[TC] CAMBIO",
	  "Unidades": 1,
	  "Envase": "[EKT] CONTENEDOR TAPADO C (28 m3)",
	  "Residuo": None,
	  "product_id": 2603,
	  "container_id": 2681,
	  "waste_id": 2554
	}
  ],
  "holder_id": 10815,
  "agreement_id": 4340,
  "pickup_id": 33435,
  "category_fleet_id": 7,
  "Track_Gmail_Uid": "1929ea310218f554"
}

headers = {
	'API-KEY': os.getenv('ODOO_API_KEY'),
	'Content-Type': 'application/json'
}

def send_du_odoo(du):
	du = json.dumps(du, indent=1)
	print(du)
	r = requests.request("POST", url = os.getenv('ODOO_ENDPOINT'), headers=headers, data=du, verify=False)
	try:
		r = json.loads(r.text)
		if r['result']['result'] == 'OK':
			print( Fore.CYAN + 'Éxito:', r , Style.RESET_ALL )
			return ((int(re.search(r'\d+', r['result']['sd_id']).group())), True)
		else:
			raise Exception
	except:
		print( Fore.RED + 'Error:', r , Style.RESET_ALL)
		r = 'Error'
		return(r, False)

if __name__ == "__main__" :
	send_du_odoo(du)