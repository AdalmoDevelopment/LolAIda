import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://mail.google.com/","https://www.googleapis.com/auth/gmail.modify"]

def set_label_gmail(msg_id, label_id):
  print(f"Mensaje id {msg_id} label_id {label_id}")
  creds = None
  if os.path.exists("AidaMailInterpreter/token.json"):
    creds = Credentials.from_authorized_user_file("AidaMailInterpreter/token.json", SCOPES)
  # If there are no (valid) credentials available, let the user log in.
  if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
      creds.refresh(Request())
    else:
      flow = InstalledAppFlow.from_client_secrets_file(
          "AidaMailInterpreter/credentials.json", SCOPES
      )
      creds = flow.run_local_server(port=0)
    # Save the credentials for the next run
    with open("AidaMailInterpreter/token.json", "w") as token:
      token.write(creds.to_json())

  try:
    # Call the Gmail API
    service = build("gmail", "v1", credentials=creds)
    results = service.users().labels().list(userId="me").execute()
    labels = results.get("labels", [])

    if not labels:
      print("No labels found.")
      return
  
  except HttpError as error:
    # TODO(developer) - Handle errors from gmail API.
    print(f"An error occurred: {error}")
  
  try:
      # Etiquetar el mensaje con la nueva etiqueta
      msg = service.users().messages().modify(userId='me', id=msg_id, body={
          'addLabelIds': [label_id]
      }).execute()

      print(f"Mensaje etiquetado con {label_id}")
      # service.users().messages().delete(userId='me', id=msg_id).execute()
      # print("Mensaje original eliminado")

  except Exception as e:
        print(f"Error: {e}")
        
if __name__ == '__main__':
    set_label_gmail('194929410a7cb1a4', 'Label_5337764771777216081')