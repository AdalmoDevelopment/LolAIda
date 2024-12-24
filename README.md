# LolAIda
GPT-4(FineTuning + RAG) + Python + API Gmail Stack para generar documentos únicos con conocimiento inyectado de casuísticas internas.

Deploy en AWS Lambda.

Flowchart:

![Proceso LolAida (1)](https://github.com/user-attachments/assets/32b7c864-cfe6-44ac-aa6e-0afd1a0fe267)

## Lanzamiento Manual :shipit:

Hay que asegurarse de tener instaladas todas las librerias necesarias en el **requirements.txt**, preferiblemente en un entorno de ejecución:

```bash
pip install -r requirements.txt
```

Una vez instaladas, basta ejecutar el **main.py**, que llamará a las funciones para leer los correos del día, filtrarlos con el diccionario y procesarlos hasta su integración final en Odoo.

```bash
python3 main.py
```

## FineTuning

### Generar y corregir líneas para el finetuning

Para finetunear el model hay que ejecutar el **main.py**, pero esta vez con el parámetro **-f**

```bash
python3 main.py -f
```

Esto lanzará en consola una revisión de todas los hilos de petición de DU que no esten aprobados/finalizados correctamente(approved != true), pudiendo responder para corriga los DUs de su primera respuesta, o simplemente dar **Enter** para pasar al siguiente.

### Crear archivo de finetuning jsonl

Ejecutando el siguiente comando obtenemos el archivo **.jsonl** para luego finetunear el modelo en OpenAI.

```bash
python3 ./FineTuning/finetuning_file_generator.py 
```


