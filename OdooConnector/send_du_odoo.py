import os, re, json, requests
from dotenv import load_dotenv
from colorama import Fore, Back, Style

load_dotenv()

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