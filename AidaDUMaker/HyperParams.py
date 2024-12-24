model = 'ft:gpt-4o-2024-08-06:personal:cuartofinetuning:Ahf5TKcF'
# ft:gpt-4o-2024-08-06:personal:segundofinetuning:ADtQlEw4
# ft:gpt-4o-2024-08-06:personal:cuartofinetuning:Ahf5TKcF
assistant_id =  'asst_5ZarbjA6POT814f7nIJvbEWu'

vector_store_id = 'vs_iV73bKFND6aIR2Wg1bja0ktM'

instructions = '''Instruction:

Only use the information provided. You must not invent, assume, or infer any information that is not clearly present in the contracts use only what is explicitly given.

Strict DU Format:
When generating the DU or DU's, follow this strict JSON format:

```json{
  "Titular": "",
  "Contrato": "",
  "Lugar de recogida": (it's supossed to be declared on mail, if not, try to infer it and choose one from contracts)
  "Lineas del DU": [
    {
      "Producto": (could be a service, envase or waste),
      "Unidades": (if not specified in the email, set it to 1),
      "Envase": (same as set in the line you chose),
      "Residuo": (null if "Producto" is not "[TC] CAMBIO", in that case depends on the waste selected),
    }
  ]
}```

PLEASE, IMPORTANT, give me each json involved in ```json {du}```.

IMPORTANT:

Only use the information exactly as it appears in the contracts.
If any category, product, or other data is not in the contracts, leave it blank or use the default value (e.g., Unidades: 1).

Logic for Container Replenishments:
Whenever a container (Envase) is specified in a line, if it's not [EGRA] GRANEL(you will never replenish GRANEL) or Service Line is not [THORAR] SERVICIO CAMIÓN HORA (RECOLECTOR), automatically add an additional line for the replenishment of that container, ALWAYS. The quantity should match the original (e.g. if you use 8 containers for contaminated plastic waste, replenish 8 containers).

Service Line:
Service lines can only be: [TT] TRANSPORTE, [THORA] SERVICIO CAMIÓN HORA (PULPO/GRÚA) and [THORAR] SERVICIO CAMIÓN HORA (RECOLECTOR), [TC] CAMBIO.

You will just put [TC] CAMBIO  in case you find an [TA] ALQUILER with the same "Envase" in contratos provided. Example: to put a "[TC] CAMBIO" "Envase":"BIDÓN 60L" you must be provided with a "[TA] ALQUILER", "BIDÓN 60L", if not the case, put a Waste line and an Envase one to replenish it)

You can, exclusively with this type of service, include more than one [TC] CAMBIO in a DU or even use it as an Envase line in cases like replenishing a JAULA, though not replenishing the main service line.

You always put at least TWO Lineas del DU, 1 for a service and 1 for a Product(Waste or Containers).

Try to not write identical lines(e.g.:  3 [RH] HIERRO lines), instead write one line with "Unidades"=3.

DO multiple DU's when:
If the requested waste or containers require different types of services(For example, you're forced to make a DU with two Envases provided but a Envase requires a [TT] TRANSPORTE and the other one a [THORAC] SERVICIO CAMIÓN HORA (CISTERNA) ), create each DU's you can. If there are any limitations in the contract that prevent you from creating all necessary DU's, create as many as you can and clearly explain why the remaining DU's could not be generated. 
IMPORTANT: Don't make more than 1 DU with same Service Line, do not make two DUs with [TT] TRANSPORTE, merge them in 1 DU. 

The info I'm providing you follows the next structure:
*You won't take info from categoria_producto, just to classify and make decisions*
{"Titular", "Contrato", "Producto", "Envase", “Residuo” , "Categoria_producto”}, and you must fill the DU with the equivalent fields. 

'''

