import os
import base64
import imaplib
import email
from email.header import decode_header
import openai
import time
import pymysql
import smtplib
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from datetime import datetime
import psycopg2
import pickle
import google.auth
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from colorama import Fore, Back, Style
from AidaMailInterpreter.extract_msg_id import get_message_by_id
from AidaMailInterpreter.diccionario import palabras

load_dotenv()

CREDENTIALS_FILE = 'AidaMailInterpreter/credentials.json'
TOKEN_PICKLE = 'AidaMailInterpreter/token.pickle'
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
SCOPES = ['https://mail.google.com/']

# def lambda_handler(event, context):
def obtener_credenciales():
	"""
		Autenticar y obtener credenciales OAuth2 para Gmail.
		Si ya existen credenciales almacenadas, se usan; de lo contrario, se solicitan.
	"""
	creds = None
	if os.path.exists(TOKEN_PICKLE):
		with open(TOKEN_PICKLE, 'rb') as token:
			creds = pickle.load(token)
	
	if not creds or not creds.valid:
		if creds and creds.expired and creds.refresh_token:
			creds.refresh(Request())
		else:
			flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
			creds = flow.run_local_server(port=0)
		with open(TOKEN_PICKLE, 'wb') as token:
			pickle.dump(creds, token)
	
	return creds

mail_user = os.getenv('MAIL_USER')

def connect_imap_oauth2(token):
	"""Conectar al servidor IMAP usando OAuth 2.0."""
	mail = imaplib.IMAP4_SSL("imap.gmail.com")
	
	# Crear la cadena de autenticación XOAUTH2
	auth_string = f'user={mail_user}\1auth=Bearer {token.token}\1\1'
	try:
		# Autenticar usando XOAUTH2
		mail.authenticate('XOAUTH2', lambda x: auth_string)
		print("Autenticado exitosamente con IMAP usando OAuth.")
		return mail
	except imaplib.IMAP4.error as e:
		print(f"Error al autenticar con OAuth: {e}")
		return None