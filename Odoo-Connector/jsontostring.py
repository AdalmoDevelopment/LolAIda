import json

# a Python object (dict):
x = {
 "Titular": "Werkhaus SL",
 "Contrato": "AA2300079",
 "Lugar de recogida": "Werkhaus SL, Bauhaus Mallorca",
 "Categoria de vehiculo": "RPs",
 "Lineas del DU": [
  {
   "Producto": "[TT] TRANSPORTE",
   "Unidades": 1,
   "Envase": None,
   "Residuo": None,
   "product_id": 2601,
   "container_id": None,
   "waste_id": None
  },
  {
   "Producto": "[RFR5SPP] RAEE FR5 PEQUE\u00d1OS CON S.P. PROFESIONAL",
   "Unidades": 3,
   "Envase": "[EBBH1M3] BIG BAG HOMOLOGADO RP 1 m3",
   "Residuo": None,
   "product_id": 2591,
   "container_id": 2707,
   "waste_id": None
  },
  {
   "Producto": "[EBBH1M3] BIG BAG HOMOLOGADO RP 1 m3",
   "Unidades": 3,
   "Envase": None,
   "Residuo": None,
   "product_id": 2707,
   "container_id": None,
   "waste_id": None
  }
 ],
 "holder_id": 28274,
 "agreement_id": 324,
 "pickup_id": 30812,
 "category_fleet_id": 14,
 "Track_Gmail_Uid": "192adabf7b7fbb49"
}

# convert into JSON:
y = json.dumps(x)

# the result is a JSON string:
print(str(y))