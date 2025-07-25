import argparse
import sys

from AidaMailInterpreter.Aida_Mail_Interpreter_Outlook import email_listener
from AidaMailInterpreter.extract_msg_id import get_message_by_id
from AidaMailInterpreter.obtain_token import obtain_token
from LolaDataProvider.Lola_Data_Provider import data_provider
from AidaDUMaker.MultipleDU_AIda_Assistant_Openai_SOA import process_pending_hilos
from AidaDUMaker.MultipleDU_AIda_Assistant_Openai_Response_API import process_pending_hilo_responses
from OdooConnector.du_final_fixer import du_fixer
from OdooConnector.send_du_odoo import send_du_odoo
from FineTuning.fix_bad_answers import ft_process_pending_hilos
from load_params import get_config_by_name

# python main.py               # Ejecuta todo normalmente
# python main.py -m            # Salta interpretación de mails
# python main.py -m -d         # Salta interpretación y extracción de datos
# python main.py -f            # Solo ejecuta Fine Tuning (fix_bad_answers)

def main(args):
    try:
        if get_config_by_name("Pausar la generacion de DUs")["active"] == 1:
            raise ValueError("¡La generación de DUs está pausada!")
        
        if args.f:
            ft_process_pending_hilos()
            return

        if not args.m:
            if not email_listener():
                raise ValueError("Error en el módulo email_listener.py")

        if not args.d:
            if not data_provider():
                raise ValueError("Error en el módulo data_provider.py")

        if not process_pending_hilo_responses():
            raise ValueError("Error en el módulo process_pending_hilos.py")

        if not du_fixer():
            raise ValueError("Error en el módulo du_fixer.py")

    except Exception as e:
        print(f'Error ejecutando el main. {e}')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Proceso de gestión de correos y generación de DUs.')

    parser.add_argument('-m', action='store_true', help='Saltar el paso de interpretación de mails')
    parser.add_argument('-d', action='store_true', help='Saltar el paso de extracción de datos del cliente')
    parser.add_argument('-f', action='store_true', help='Ejecutar solo el fix de respuestas fallidas (Fine Tuning)')

    args = parser.parse_args()
    main(args)
