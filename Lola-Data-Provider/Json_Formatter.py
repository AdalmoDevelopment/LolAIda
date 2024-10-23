import json


def json_formatter(results1, results2):
    
    titulares = {}
    for row in results1:
        cliente, contrato, producto, envase, residuo, categoria_producto = row
        
        if cliente not in titulares:
            titulares[cliente] = {
                "Contratos": {}
            }
        
        if contrato not in titulares[cliente]["Contratos"]:
            titulares[cliente]["Contratos"][contrato] = {
                "Productos" : []
            }
            
        producto_obj = {
            "Producto" : producto,
            "Envase" : envase,
            "Residuo" : residuo,
            "Categoria producto" : categoria_producto
        }
        
        titulares[cliente]["Contratos"][contrato]["Productos"].append(producto_obj)
    
    contratos = {"Contratos": []}
    for row in results2:
        contrato, lugar_de_recogida = row
        contrato_existente = next((c for c in contratos["Contratos"] if c["Contrato"] == contrato), None)
        
        if contrato_existente is None:
            contratos["Contratos"].append({
                "Contrato" : contrato,
                "Lugares_de_recogida" : [lugar_de_recogida]
            })
        else:
            if lugar_de_recogida not in contrato_existente["Lugares_de_recogida"]:
                contrato_existente["Lugares_de_recogida"].append(lugar_de_recogida)
    
    json_combinado = {
    "Titulares": titulares,
    "Lugares de recogida": contratos
    }

    # Luego conviertes a JSON con 'json.dumps'
    json_final = json.dumps(json_combinado, ensure_ascii=False, indent=4)
    
    return (json_final)