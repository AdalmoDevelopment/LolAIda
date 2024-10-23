import os, re, json, requests
from dotenv import load_dotenv

load_dotenv()

du = json.dumps({
	"Titular": "MAC Insular SL",
	"Contrato": "AA2400378",
	"Lugar de recogida": "MAC Insular SL, PT1 Bunyola",
	"Categoria de vehiculo": "Contenedores/Ganchos",
	"Lineas del DU": [
		{
			"Producto": "[TC] CAMBIO",
			"Unidades": 1,
			"Envase": "[EC] CONTENEDOR C (28 m3)",
			"Residuo": None,
			"product_id": 2603,
			"container_id": 2681,
			"waste_id": 2510
		},
		{
			"Producto": "[RH] HIERRO",
			"Unidades": 1,
			"Envase": "[EC] CONTENEDOR C (28 m3)",
			"Residuo": None,
			"product_id": 2510,
			"container_id": 2681,
			"waste_id": None
		}
	],
	"holder_id": 12373,
	"agreement_id": 6,
	"pickup_id": 12374,
	"category_fleet_id": 6,
	"Track_Gmail_Uid": "192ada08e0db4c20"
})

headers = {
	'API-KEY': os.getenv('ODOO_API_KEY'),
	'Content-Type': 'application/json'
}

def send_du_odoo(du):
	du = json.dumps(du)
	r = requests.request("POST", url = os.getenv('ODOO_ENDPOINT'), headers=headers, data = du, verify=False)
	
	try:
		r = json.loads(r.text)
		print(int(re.search(r'\d+', r['result']['sd_id']).group()))
		return(int(re.search(r'\d+', r['result']['result']).group())) 
	except:
		print(r)
		return(r)

if __name__ == "__main__" :
	send_du_odoo(du)