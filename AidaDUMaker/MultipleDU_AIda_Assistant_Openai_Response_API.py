from openai import OpenAI
import os
import re
import json
import time
from AidaDUMaker.funcs.funcs import get_pending_hilos, mark_as_processed, mysql_conn_params
from load_params import get_config_by_name

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def process_pending_hilo_responses():
    hilos = get_pending_hilos(mysql_conn_params)
    print(f"🔍 Se encontraron {len(hilos)} hilos pendientes.")
    
    for hilo in hilos:
        hilo_id, mensaje = hilo
        print(f"\n➡️ Procesando hilo ID: {hilo_id}")
        # print(f"📩 Mensaje:\n{mensaje}")

        try: 
            response = client.responses.create(
            prompt={
                "id": "pmpt_686fa9862ab081979abacef972a9ab050c84af80129b8110",
                "version": "62"
            },
            
            input=[    
                {
                    "role": "user",
                    "content": [
                    {
                        "type": "input_text",
                        "text": mensaje
                    }
                    ]
                },      
            ],
            reasoning={},
            max_output_tokens=2048,
            store=False
            )
            print("✅ Solicitud enviada correctamente a `responses.create`")
        except Exception as e:
            print(f"❌ ERROR en client.responses.create: {e}")
            mark_as_processed(mysql_conn_params, hilo_id, None, f"[ERROR create] {e}")
            continue
        # print(f"🔎 Respuesta completa del modelo:\n{response}") 
        # Paso 1: verificar si hay contenido plano en response.output
        mark_as_processed(mysql_conn_params, hilo_id, None, None)
        
        du_function_calls = [
        item for item in response.output
            if item.type == "function_call" and getattr(item, "name", "") == "generate_du"
        ]

        if du_function_calls:
            for call in du_function_calls:
                try:
                    arguments = json.loads(call.arguments)
                    print(f"✅ DU capturado desde function_call:\n{json.dumps(arguments, indent=2)}")
                    mark_as_processed(mysql_conn_params, hilo_id, json.dumps(arguments, indent=2), json.dumps([c.model_dump() if hasattr(c, "model_dump") else c.__dict__ if hasattr(c, "__dict__") else str(c) for c in response.output], indent=2))
                except json.JSONDecodeError as e:
                    print(f"❌ Error al parsear argumentos de function_call: {e}")
                    mark_as_processed(mysql_conn_params, hilo_id, None, f"[ERROR func_call] {e}")
        else:        
            if hasattr(response, "output") and isinstance(response.output, list):
                all_text_blocks = []

                for msg in response.output:
                    if hasattr(msg, "content"):
                        for item in msg.content:
                            if hasattr(item, "text") and isinstance(item.text, str):
                                all_text_blocks.append(item.text)

                raw_text = "\n".join(all_text_blocks).strip()

                if raw_text:
                    print(f"✅ Texto plano detectado: \n{raw_text[:300]}...")

                    # Buscar llamadas a generate_du(...) con JSON válido
                    matches = re.findall(r'generate_du\s*\(\s*({.*?})\s*\)', raw_text, re.DOTALL)

                    if not matches:
                        matches = re.findall(r'```json\s*({.*?})\s*```', raw_text, re.DOTALL)

                    if matches:
                        dus_extraidos = [] 
                        for match in matches:
                            
                            try:
                                json_obj = json.loads(match.strip())
                                print(f"✅ DU extraído:\n{json.dumps(json_obj, indent=2)}")
                                dus_extraidos.append(json_obj)
                            except json.JSONDecodeError as e:
                                print(f"❌ Error al parsear JSON: {e}")
                                continue  # continúa con los demás

                        if dus_extraidos:
                            for du in dus_extraidos:
                                mark_as_processed(mysql_conn_params, hilo_id, json.dumps(du), raw_text)
                        else:
                            mark_as_processed(mysql_conn_params, hilo_id, None, raw_text)
                    else:
                        print("❌ No se encontraron bloques generate_du válidos.")
                        if hasattr(response, "output") and response.output:
                                raw_text = None
                                if hasattr(response.output, "text") and response.output.text:
                                    raw_text = getattr(response.output.text, "value", None)

                                if raw_text:
                                    print(f"⚠️ Fallback text mode activated:\n{raw_text}")

                                    # Buscar bloques JSON válidos dentro del texto
                                    matches = re.findall(r'generate_du\s*\(\s*({.*?})\s*\)', raw_text, re.DOTALL)
                                    if not matches:
                                        matches = re.findall(r'```json\s*(.*?)```', raw_text, re.DOTALL)

                                    if matches:
                                        for match in matches:
                                            try:
                                                du = match.strip()
                                                if not du.startswith('{'):
                                                    du = '{' + du
                                                if not du.endswith('}'):
                                                    du += '}'

                                                json_obj = json.loads(du)
                                                print(f"✅ DU extraído:\n{json.dumps(json_obj, indent=2)}")
                                                mark_as_processed(mysql_conn_params, hilo_id, json.dumps(json_obj), raw_text)
                                            except json.JSONDecodeError as e:
                                                print(f"❌ Error parseando JSON del fallback: {e}")
                                                mark_as_processed(mysql_conn_params, hilo_id, None, raw_text)
                                    else:
                                        print("❌ No se encontraron DUs en texto plano.")
                                        mark_as_processed(mysql_conn_params, hilo_id, None, raw_text)
                                else:
                                    print("❌ No hay texto en response.output.text")
                                    mark_as_processed(mysql_conn_params, hilo_id, None, None)
                else:
                    print("❌ No se pudo extraer texto plano desde response.output.")
                    mark_as_processed(mysql_conn_params, hilo_id, None, None)

    return True
