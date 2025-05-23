from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
CREDENTIALS_FILE = 'AidaMailInterpreter/credentials.json'
TOKEN_FILE = 'AidaMailInterpreter/token.json'

def obtain_token():
    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
    creds = flow.run_local_server(port=0)
    with open(TOKEN_FILE, 'w') as token:
        token.write(creds.to_json())

if __name__ == '__main__':
    obtain_token()