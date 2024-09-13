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
from bs4 import BeautifulSoup
from datetime import datetime
import psycopg2

load_dotenv()

# Configuración IMAP
mail_imap_server = "imap.gmail.com"
mail_user = os.getenv('MAIL_USER')
mail_password = os.getenv('MAIL_PASSWORD')

dbname = os.getenv('DB_NAME')
postgres_user = os.getenv('DB_USER')
postgres_password = os.getenv('DB_PASSWORD')
postgres_host = os.getenv('DB_HOST')
postgres_port = os.getenv('DB_PORT')
postgres_conn_params = {
    'dbname': dbname,
    'user': postgres_user,
    'password': postgres_password,
    'host': postgres_host,
    'port': postgres_port
}

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
        email_ids.reverse()
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
    """Analizar el correo y extraer el remitente y el cuerpo sin etiquetas HTML."""
    try:
        subject = decode_header(msg["Subject"])[0][0]
        if isinstance(subject, bytes):
            subject = subject.decode()
        
        from_ = msg.get("From")
        if "<" in from_ and ">" in from_:
            from_ = from_.split("<")[1].split(">")[0]
        
        date_str = msg.get("Date")
        date = None

        # Probar diferentes formatos de fecha
        date_formats = [
            '%a, %d %b %Y %H:%M:%S %z',  # Formato con día de la semana
            '%d %b %Y %H:%M:%S %z'       # Formato sin día de la semana
        ]

        for fmt in date_formats:
            try:
                date = datetime.strptime(date_str, fmt)
                break
            except ValueError:
                continue
        
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))

                if "attachment" not in content_disposition:
                    if content_type == "text/plain":
                        body += part.get_payload(decode=True).decode()
                    elif content_type == "text/html":
                        html = part.get_payload(decode=True).decode()
                        soup = BeautifulSoup(html, "html.parser")
                        body += soup.get_text()
        else:
            if msg.get_content_type() == "text/plain":
                body = msg.get_payload(decode=True).decode()
            elif msg.get_content_type() == "text/html":
                html = msg.get_payload(decode=True).decode()
                soup = BeautifulSoup(html, "html.parser")
                body = soup.get_text()
        
        MAX_LENGTH = 2000  # para que no de error por exceso de tokens
        if len(body) > MAX_LENGTH:
            body = body[:MAX_LENGTH] + '...'
        
        return from_, subject, body, date
    except Exception as e:
        print(f"Error al analizar el correo: {e}")
        return None, None, None, None

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
    
def get_pending_hilos(mysql_conn_params):
    try:
        conn = pymysql.connect(**mysql_conn_params)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, aida_request FROM hilos WHERE lola_generated = 0 AND aida_response LIKE 'Lola%'")
        hilos = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return hilos
    except pymysql.MySQLError as e:
        print(f"Error al conectar a MySQL: {e}")
        return []
    
def execute_query(from_, conn_params):
    try:
        # Establecer la conexión con la base de datos
        conn = psycopg2.connect(**conn_params)
        cursor = conn.cursor()
        print(from_)
        # Modificar el valor de 'from_' para que funcione con LIKE
        
        if "@gmail" in from_:
            from_ = f"{from_.split('@')[0]}"
            from_ = f"%{from_}%"
        else:
            from_ = f"{from_.split('@')[1]}"
            from_ = f"{from_.split('.')[0]}"    
            from_ = f"%{from_}%"                                                    
                
        print(from_)

        query = """
            SELECT count(*)
            FROM public.pnt_agreement_agreement paa
            INNER JOIN res_partner rp ON paa.pnt_holder_id = rp.id
            INNER JOIN pnt_agreement_partner_pickup_rel pappr ON paa.id = pappr.pnt_agreement_id
            INNER JOIN res_partner rprecog ON pappr.partner_id = rprecog.id
            WHERE paa.state = 'done'
            AND paa.pnt_holder_id IN (
                SELECT id FROM res_partner WHERE email ILIKE %s AND is_company = true
            )
            GROUP BY rp.display_name
            ORDER BY rp.display_name
            LIMIT 1;
        """
        # Ejecutar la consulta con el parámetro correctamente (como tupla)
        cursor.execute(query, (from_,) )  # El parámetro from_ debe estar dentro de una tupla
        
        result = cursor.fetchone()  # Solo obtendremos un resultado
        print(result)
        # Cerrar la conexión
        cursor.close()
        conn.close()
        
        return result
    except Exception as e:
        return str(e)


def generate_response(from_, body):
    """Generar una respuesta utilizando gpt-4."""
    result = execute_query( from_, postgres_conn_params)
    try:
        openai.api_key = OPENAI_API_KEY

        if result[0] > 1:  
            multiple_lugar_recogida = "y el lugar de recogida"
        else:
            multiple_lugar_recogida = ""
            
        messages = [
            {"role": "system", "content": f"Me llamo AIda. Reviso los datos de cada mail que me llega, si no interpreto que me están solicitando una entrega, cambio, o recogida de residuo/recipiente o vaciado de estos, no respondo nada. Si es una solicitud y no contiene material (puede ser un residuo o envase también){multiple_lugar_recogida} en el cuerpo los pediré hasta que los tenga, una vez los tenga responderé 'Lola. Dame la información de {from_} (siempre el mail del remitente)''"},
            {"role": "user", "content": f"Usuario: {from_}\nPregunta: {body}\nRespuesta:"}
        ]
        
        print(messages)
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
                    # print(email_count)
                    if email_count == 100:
                        break
                    msg = fetch_email(mail, email_id)
                    if msg:
                        from_, subject, body, date = parse_email(msg)
                        if from_ and subject and body and "adalmo" not in from_:
                            print(f"Nuevo correo de {from_}: {subject}\n\n")
                            add_memory(user_id=from_, text=body, metadata={"subject": subject})
                            # print(body, '\n')
                            
                            all_memories = m.get_all() 
                            memory_id = all_memories[0]["id"] # get a memory_id
                            # print(memory_id)
                            # print("Correo almacenado en la memoria.\n")
                            
                            response = generate_response(from_, body)
                            # print(f"Respuesta generada para SQLCoder:\n{response}")
                            # print(date)
                            mycursor = mydb.cursor()
                            if response:
                                try:
                                    if "adalmo" not in from_:
                                        if "@gmail" in from_:
                                            from_ = f"{from_.split('@')[0]}"
                                            print(from_)
                                        else:
                                            from_ = f"{from_.split('@')[1]}"
                                            from_ = f"{from_.split('.')[0]}"
                                            print(from_)
                                        print("mail para aida", from_)                                           
                                        
                                        query = "INSERT INTO hilos(date, date_created, aida_correo, aida_response, aida_request) VALUES (%s, curdate(),%s,%s,%s)"
                                        mycursor.execute(query, (date,body, response, from_))
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
