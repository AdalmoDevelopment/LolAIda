from AidaMailInterpreter.Aida_Mail_Interpreter import email_listener
from AidaMailInterpreter.extract_msg_id import get_message_by_id
from AidaMailInterpreter.obtain_token import obtain_token
from LolaDataProvider.Lola_Data_Provider import data_provider
from AidaDUMaker.MultipleDU_AIda_Assistant_Openai_SOA import process_pending_hilos
from OdooConnector.du_final_fixer import du_fixer
from OdooConnector.send_du_odoo import send_du_odoo
from FineTuning.fix_bad_answers import ft_process_pending_hilos
import sys
from load_params import get_config_by_name

def main(param):
    
    try:
        if get_config_by_name("Pausar la generacion de DUs")["active"] == 1:
            raise ValueError("¡La generación de DUs está pausada!")
        
        elif param != '-f':
            # Paso 1: Se interpreta y resume cada mail con AI y se crea un hilo(una línea en la base de datos).
            
            if param != '-m':
                interpretar_mails = email_listener()
                if not interpretar_mails:
                    raise ValueError("Error en el modulo email_listener.py")
            
            # Paso 2: Se extrae la información de la DB del cliente de cada hilo y se inserta en dicha línea.
            print('Paso 2')
            extraer_info_cliente = data_provider()
            if not extraer_info_cliente:
                raise ValueError("Error en el modulo data_provider.py")
            
            # Paso 3: Si procede, el modelo crea los DU's para el pedido en base a los datos del paso 1-2.
            
            crear_dus = process_pending_hilos()
            if not crear_dus:
                raise ValueError("Error en el modulo process_pending_hilos.py")
            
            # Paso 4: Se validan/formatean los DU's para asegurar su correcto formato y se envían a Odoo.
            
            formatear_y_enviar_dus = du_fixer()
            if not formatear_y_enviar_dus:
                raise ValueError("Error en el modulo du_fixer.py")
        else:
            ft_process_pending_hilos()
        
    except Exception as e :
        print(f'Error ejecutando el main. {e}')

if __name__ == '__main__':
    param = sys.argv[1] if len(sys.argv) > 1 else None
    main(param)
