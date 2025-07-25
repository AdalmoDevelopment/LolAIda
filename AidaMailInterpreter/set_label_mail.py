import os.path
import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from AidaMailInterpreter.auth_outlook import get_access_token, USER_ID

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://mail.google.com/","https://www.googleapis.com/auth/gmail.modify"]

# def set_label_gmail(msg_id, label_id):
# 	print(f"Mensaje id {msg_id} label_id {label_id}")
# 	creds = None
# 	if os.path.exists("AidaMailInterpreter/token.json"):
# 		creds = Credentials.from_authorized_user_file("AidaMailInterpreter/token.json", SCOPES)
# 	# If there are no (valid) credentials available, let the user log in.
# 	if not creds or not creds.valid:
# 		if creds and creds.expired and creds.refresh_token:
# 			creds.refresh(Request())
# 		else:
# 			flow = InstalledAppFlow.from_client_secrets_file(
# 					"AidaMailInterpreter/credentials.json", SCOPES
# 			)
# 			creds = flow.run_local_server(port=0)
# 		# Save the credentials for the next run
# 		with open("AidaMailInterpreter/token.json", "w") as token:
# 			token.write(creds.to_json())

# 	try:
# 		# Call the Gmail API
# 		service = build("gmail", "v1", credentials=creds)
# 		results = service.users().labels().list(userId="me").execute()
# 		labels = results.get("labels", [])

# 		if not labels:
# 			print("No labels found.")
# 			return
	
# 	except HttpError as error:
# 		# TODO(developer) - Handle errors from gmail API.
# 		print(f"An error occurred: {error}")
	
# 	try:
# 			# Etiquetar el mensaje con la nueva etiqueta
# 			msg = service.users().messages().modify(userId='me', id=msg_id, body={
# 					'addLabelIds': [label_id]
# 			}).execute()

# 			print(f"Mensaje etiquetado con {label_id}")
# 			# service.users().messages().delete(userId='me', id=msg_id).execute()
# 			# print("Mensaje original eliminado")

# 	except Exception as e:
# 				print(f"Error: {e}")
				
def set_label_outlook(message_id, destination_folder_id):
		access_token = get_access_token()
		headers = {
			"Authorization": f"Bearer {access_token}",
			"Prefer": 'outlook.body-content-type="text"'
		}
		url = f"https://graph.microsoft.com/v1.0/users/{USER_ID}/messages/{message_id}/move"
		data = {"destinationId": destination_folder_id}
		
		response = requests.post(url, headers=headers, json=data)
		
		if response.status_code == 201:
				print(f"Correo {message_id} movido a carpeta correctamente.")
		else:
				print(f"Error al mover el correo {message_id}:", response.status_code, response.json())

if __name__ == '__main__':
		set_label_gmail('194929410a7cb1a4', 'AQMkADU2MjBlZjhiLTUyZjYtNDQANzgtOTQ2Ny1lZGY3OTM5YTcwN2QALgAAA75zQKy2BSpOujZQqy03r3sBALuxnWChS2FKrToCbg5rxI0AAAIBOAAAAA==')