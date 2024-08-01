import os
import imaplib
import email
from email.header import decode_header
from mem0 import Memory
import openai
import time
import pymysql
import smtplib
from dotenv import load_dotenv
import os

load_dotenv()

# Configuración IMAP
mail_imap_server = "imap.gmail.com"
mail_user = os.getenv('MAIL_USER')
mail_password = os.getenv('MAIL_PASSWORD')

mysql_host = os.getenv('MYSQL_HOST')
mysql_user = os.getenv('MYSQL_USER')
mysql_password = os.getenv('MYSQL_PASSWORD')
mysql_database = os.getenv('MYSQL_DATABASE')

mydb = pymysql.connect(
  host = mysql_host,
  user = mysql_user,
  password = mysql_password,
  database = mysql_database,
  port=3306
)

# Establecer la clave de API desde una variable de entorno
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Inicializar Mem0
m = Memory()

def connect_imap():
    """Conectar y autenticar con el servidor IMAP."""
    try:
        mail = imaplib.IMAP4_SSL(mail_imap_server)
        mail.login(mail_user, mail_password)
        return mail
    except imaplib.IMAP4.error as e:
        print(f"Error al conectar al servidor IMAP: {e}")
        return None

def check_inbox(mail):
    """Revisar la bandeja de entrada en busca de correos no leídos."""
    try:
        mail.select("inbox")
        status, messages = mail.search(None, '(SEEN)')
        if status != "OK":
            print("No hay mensajes nuevos.")
            return []
        email_ids = messages[0].split()
        return email_ids
    except Exception as e:
        print(f"Error al revisar la bandeja de entrada: {e}")
        return []

def fetch_email(mail, email_id):
    """Recuperar un correo específico."""
    try:
        status, msg_data = mail.fetch(email_id, "(RFC822)")
        if status != "OK":
            print("No se pudo recuperar el correo.")
            return None
        msg = email.message_from_bytes(msg_data[0][1])
        return msg
    except Exception as e:
        print(f"Error al recuperar el correo: {e}")
        return None

def parse_email(msg):
    """Analizar el correo y extraer el remitente y el cuerpo."""
    try:
        subject = decode_header(msg["Subject"])[0][0]
        if isinstance(subject, bytes):
            subject = subject.decode()
        
        from_ = msg.get("From")
        if "<" in from_ and ">" in from_:
            from_ = from_.split("<")[1].split(">")[0]

        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))

                if "attachment" not in content_disposition:
                    if content_type == "text/plain":
                        body += part.get_payload(decode=True).decode()
        else:
            body = msg.get_payload(decode=True).decode()
        
        return from_, subject, body
    except Exception as e:
        print(f"Error al analizar el correo: {e}")
        return None, None, None

def add_memory(user_id, text, metadata=None):
    """Añadir una nueva memoria automáticamente para el usuario dado."""
    try:
        if metadata is None:
            metadata = {}
        result = m.add(text, user_id=user_id, metadata=metadata)
        return result
    except Exception as e:
        print(f"Error al añadir memoria: {e}")
        return None

def generate_response(from_, body):
    """Generar una respuesta utilizando gpt-4."""
    
    try:
        openai.api_key = OPENAI_API_KEY
        messages = [
            {"role": "system", "content": "Me llamo AIda. Reviso los datos de cada mail que me llega, si no interpreto que me estan solicitando una entrega, cambio, o recogida no respondo nada. Si es una solicitud y no contiene ambos material(puede ser un residuo o envase también) y lugar de recogida/cambio en el cuerpo los pediré hasta que los tenga, una vez los tenga responderé 'Lola. Dame la información de {from_}(siempre el mail del remitente)''"},
            {"role": "user", "content": f"Usuario: {from_}\nPregunta: {body}\nRespuesta:"}
        ]
        
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=messages,
            max_tokens=200
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error al generar la respuesta: {e}")
        return "Error al generar la respuesta."

def email_listener():
    while True:
        mail = connect_imap()
        if mail:
            email_ids = check_inbox(mail)
            if email_ids:
                email_count = 0
                for email_id in email_ids:
                    email_count += 1
                    print(email_count)
                    if email_count == 1000:
                        break
                    msg = fetch_email(mail, email_id)
                    if msg:
                        from_, subject, body = parse_email(msg)
                        if from_ and subject and body:
                            print(f"Nuevo correo de {from_}: {subject}\n\n")
                            add_memory(user_id=from_, text=body, metadata={"subject": subject})
                            print(body, '\n')
                            
                            all_memories = m.get_all() 
                            memory_id = all_memories[0]["id"] # get a memory_id
                            print(memory_id)
                            print("Correo almacenado en la memoria.\n")
                            response = generate_response(from_, body)
                            print(f"Respuesta generada para SQLCoder:\n{response}")
                            
                            if "Lola." in response:
                                try:
                                    if "@adalmo" not in from_:
                                        if "@gmail" in from_:
                                            from_ = f"@{from_.split('@')[0]}"
                                        else:
                                            from_ = f"@{from_.split('@')[1]}"
                                        
                                        mycursor = mydb.cursor()
                                        query = "INSERT INTO hilos(aida_correo, aida_request) VALUES (%s,%s)"
                                        mycursor.execute(query, (body, from_))
                                        mydb.commit()  # Asegúrate de hacer commit para guardar los cambios
                                        print("Correo guardado en la base de datos")

                                except pymysql.MySQLError as e:
                                    print(f"Error al ejecutar la consulta SQL: {e}")
                                    return False

                                finally:
                                    mycursor.close()
                                    time.sleep(5)  # Esperar 1 minuto antes de revisar nuevamente


if __name__ == "__main__":
    email_listener()
