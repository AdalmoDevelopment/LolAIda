import torch 
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
import psycopg2
from psycopg2 import sql

# Función para generar el prompt
def generate_prompt(question, prompt_file="prompt.md", metadata_file="metadata.sql"):
    with open(prompt_file, "r") as f:
        prompt = f.read()
    
    with open(metadata_file, "r") as f:
        table_metadata_string = f.read()

    prompt = prompt.format(
        user_question=question, table_metadata_string=table_metadata_string
    )
    return prompt

# Función para cargar el tokenizador y el modelos
def get_tokenizer_model(model_name):
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        trust_remote_code=True,
        torch_dtype=torch.float32,
        device_map="auto",
        use_cache=True,
        load_in_4bit=True 
    )
    return tokenizer, model

# Función para ejecutar la inferencia
def run_inference(question, tokenizer, model):
    prompt = generate_prompt(question)
    
    pipe = pipeline(
        "text-generation",
        model=model,
        tokenizer=tokenizer,
        max_new_tokens=380,
        do_sample=False,
        return_full_text=False,
        num_beams=5,
    )
    
    eos_token_id = tokenizer.eos_token_id
    generated_query = (
        pipe(
            prompt,
            num_return_sequences=1,
            eos_token_id=eos_token_id,
            pad_token_id=eos_token_id,
        )[0]["generated_text"]
        .split(";")[0]
        .split("```")[0]
        .strip()
        + ";"
    )
    return generated_query

# Función para ejecutar una consulta SQL en la base de datos PostgreSQL
def execute_query(query, conn_params):
    try:
        # Establecer la conexión con la base de datos
        conn = psycopg2.connect(**conn_params)
        cursor = conn.cursor()
        
        # Ejecutar la consulta
        cursor.execute(query)
        results = cursor.fetchall()
        
        # Cerrar la conexión
        cursor.close()
        conn.close()
        
        return results
    except Exception as e:
        return str(e)

def main():
    print("Loading model...")
    tokenizer, model = get_tokenizer_model("defog/sqlcoder-7b-2")
    print("Model loaded. You can now start asking questions.\n")

    # Parámetros de conexión a la base de datos PostgreSQL
    conn_params = {
        'dbname': 'STA',
        'user': 'odoo_sql',
        'password': 'P7!mcAhEXVhRS',
        'host': '195.170.165.123',
        'port': '5440'
    }

    while True:
        question = input("Enter your question (or type 'exit' to quit): ")
        if question.lower() == 'exit':
            print("Exiting the chatbot. Goodbye!")
            break
        
        print("Generating SQL query...")
        sql_query = run_inference(question, tokenizer, model)
        
        
        print("Executing SQL query...")
        results = execute_query(sql_query, conn_params)
            
        if isinstance(results, str):
            print(f"Error executing query: {results}\n")
        else:
            print('Resultados:',results)
            print(f"Generated SQL query:\n{sql_query}\n")

if __name__ == "__main__":
    main()