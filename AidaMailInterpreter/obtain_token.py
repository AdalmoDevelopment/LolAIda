from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
CREDENTIALS_FILE = 'AidaMailInterpreter/credentials.json'
TOKEN_FILE = 'AidaMailInterpreter/token.json'

def obtain_token_console():
    """
    Obtiene un token de autenticación OAuth2 para Gmail.
    Se solicita la autenticación en la consola.
    """
    # Crear flujo de autenticación desde el archivo de credenciales
    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
    
    # Obtener el URL de autorización
    auth_url, _ = flow.authorization_url()

    print("Ve a este URL en tu navegador para autorizar la aplicación:", auth_url)
    auth_code = input("Introduce el código de autorización aquí: ")

    # Intercambiar el código por el token
    creds = flow.fetch_token(authorization_response=auth_code)

    # Guardar las credenciales en formato JSON en el archivo TOKEN_FILE
    with open(TOKEN_FILE, 'w') as token:
        token.write(creds.to_json())
    print(f"Token guardado correctamente en {TOKEN_FILE}")

if __name__ == '__main__':
    obtain_token_console()
