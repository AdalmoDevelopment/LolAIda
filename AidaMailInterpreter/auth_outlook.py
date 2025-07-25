import os
import requests
from msal import ConfidentialClientApplication
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("OUTLOOK_CLIENT_ID")
CLIENT_SECRET = os.getenv("OUTLOOK_CLIENT_SECRET")
TENANT_ID = os.getenv("OUTLOOK_TENANT_ID")
USER_ID = os.getenv("OUTLOOK_USER_ID")

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPE = ["https://graph.microsoft.com/.default"]

def get_access_token():
	app = ConfidentialClientApplication(
		CLIENT_ID,
		authority=AUTHORITY,
		client_credential=CLIENT_SECRET
	)
	result = app.acquire_token_silent(SCOPE, account=None)
	if not result:
		result = app.acquire_token_for_client(scopes=SCOPE)
	if "access_token" in result:
		return result["access_token"]
	else:
		raise Exception(f"Error obteniendo token: {result.get('error_description')}")


def list_all_folders():
    access_token = get_access_token()
    url = f"https://graph.microsoft.com/v1.0/users/{USER_ID}/mailFolders"
    headers = {"Authorization": f"Bearer {access_token}"}

    print("Carpetas de correo encontradas:")
    while url:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            for folder in data.get("value", []):
                print(f"- {folder['displayName']} (ID: {folder['id']})")
            url = data.get("@odata.nextLink")  # Sigue a la siguiente página si existe
        else:
            print(f"Error: {response.status_code} {response.text}")
            break

if __name__ == "__main__":
    list_all_folders()