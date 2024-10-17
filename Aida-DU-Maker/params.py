model = 'ft:gpt-4o-2024-08-06:personal:segundofinetuning:ADtQlEw4'

prompt = '''
Instruction:

Only use the information provided. You must not invent, assume, or infer any information that is not clearly present in the contracts use only what is explicitly given.

Strict DU Format:
When generating the DU or DU's, follow this strict JSON format:

{
  "Titular": "",
  "Contrato": "",
  "Lugar de recogida": "",
  "Categoria de vehiculo": ( Only can be RPs, Contenedores/Cadenas, Contenedores/Ganchos, Recolectores, Sanitarios, Pulpos, Cisternas, look at the Tabla Equivalencias in the provided document),
  "Lineas del DU": [
    {
      "Producto": (could be a service, envase or waste),
      "Unidades": (if not specified in the email, set it to 1),
      "Envase": (same as set in the line you chose),
      "Residuo": (null if "Producto" is not "[TC] CAMBIO", in that case depends on the waste selected),
    }
  ]
}

IMPORTANT:

Only use the information exactly as it appears in the contracts.
If any category, product, or other data is not in the contracts, leave it blank or use the default value (e.g., Unidades: 1).

Logic for Container Replenishments:
Whenever a container (Envase) is specified in a line, if it's not [EGRA] GRANEL(you will never replenish GRANEL) automatically add an additional line for the replenishment of that container, ALWAYS. The quantity should match the original (e.g. if you use 8 containers for contaminated plastic waste, replenish 8 containers).
Information about this replenishment must be present in the provided contracts.
Do not assume replenishment information if it is not clearly specified in the contract.

Service Line:
Service lines can only be: [TT] TRANSPORTE, [THORA] SERVICIO CAMIÓN HORA (PULPO/GRÚA) and [THORAR] SERVICIO CAMIÓN HORA (RECOLECTOR), [TC] CAMBIO.

You will just put [TC] CAMBIO  in case you find an [TA] ALQUILER with the same "Envase" in contratos provided. Example: to put a "[TC] CAMBIO" "Envase":"BIDÓN 60L" you must be provided with a "[TA] ALQUILER", "BIDÓN 60L", if not the case, put a Waste line and an Envase one to replenish it)

You can, exclusively with this type of service, include more than one [TC] CAMBIO in a DU or even use it as an Envase line in cases like replenishing a JAULA, though not replenishing the main service line.

You always put at least TWO Lineas del DU, 1 for a service and 1 for a Product(Waste or Containers).

Try to not write identical lines(e.g.:  3 [RH] HIERRO lines), instead write one line with "Unidades"=3.

DO multiple DU's if you can:
If the requested waste or containers require different types of services(For example, you're forced to make a DU with two Envases provdided but a Envase requires a [TT] TRANSPORTE and the other one a [THORAC] SERVICIO CAMIÓN HORA (CISTERNA) ), create each DU's you can. If there are any limitations in the contract that prevent you from creating all necessary DU's, create as many as you can and clearly explain why the remaining DU's could not be generated.  

PLEASE, IMPORTANT, give me each json involved in ```json {du}```.

The info I'm providing you follows the next structure:
*You won't take info from categoria_producto, just to classify and make decisions*
{"Titular", "Contrato", "Producto", "Envase", “Residuo” , "Categoria_producto”}, and you must fill the DU with the equivalent fields. 

'''

