from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

def get_message_by_id( message_id):
    
    # Configura las credenciales y el servicio de Gmail
    creds = Credentials.from_authorized_user_file('token.json', ['https://www.googleapis.com/auth/gmail.readonly'])
    service = build('gmail', 'v1', credentials=creds)
    
    try:
        # Realiza la solicitud a la API para obtener el mensaje
        message = service.users().messages().list(userId='me', q=f'rfc822msgid:{message_id}').execute()
        messages = message.get('messages', [])
        if messages:
            mail_track_id = messages[0]['id']
            msg = service.users().messages().get(userId='me', id=mail_track_id).execute()
            return mail_track_id
        else:
            print("No se encontró el mensaje.")
            return None
    except Exception as e:
        print(f"Error al buscar el mensaje: {e}")
        return None

# # Obtener el mensaje
# msg_id = get_message_by_id(service, message_id)
# if msg_id:
#     print(f"Mensaje encontrado: {msg_id}")
