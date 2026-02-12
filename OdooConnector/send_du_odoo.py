import os, re, json, requests
from dotenv import load_dotenv
from colorama import Fore, Back, Style
from load_params import get_config_by_name

load_dotenv()

headers = {
	'API-KEY': os.getenv('ODOO_API_KEY'),
	'Content-Type': 'application/json'
}

def send_du_odoo(du):
	du = json.dumps(du, indent=1)
	print(du)
	url = os.getenv('ODOO_ENDPOINT_PRO') if get_config_by_name('Pasar a produccion')['active'] == 1 else os.getenv('ODOO18_ENDPOINT_DEV')
	r = requests.post(url, headers=headers, data=du, verify=False)
 
	print(f"Enviando DU a {url}")
 
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