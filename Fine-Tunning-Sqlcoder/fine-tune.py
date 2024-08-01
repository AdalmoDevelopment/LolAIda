from transformers import Trainer, TrainingArguments, AutoModelForCausalLM, AutoTokenizer
from datasets import load_dataset, DatasetDict

# Cargar el modelo y el tokenizador
model_name = "defog/sqlcoder-7b-2"
model = AutoModelForCausalLM.from_pretrained(model_name)
tokenizer = AutoTokenizer.from_pretrained(model_name)

# Cargar el dataset
dataset = load_dataset('json', data_files='training_data.jsonl')

# Preprocesar el dataset
def preprocess(data):
    # Asegurarse de que ambas columnas existan en el dataset
    if 'prompt' in data and 'completion' in data:
        return tokenizer(data['prompt'], text_target=data['completion'], truncation=True, padding='max_length', max_length=512)
    else:
        return {}

tokenized_dataset = dataset.map(preprocess, batched=True, remove_columns=dataset['train'].column_names)

# Dividir el dataset en entrenamiento y validación
dataset = DatasetDict({
    'train': tokenized_dataset['train'].train_test_split(test_size=0.1)['train'],
    'validation': tokenized_dataset['train'].train_test_split(test_size=0.1)['test']
})

# Configurar los argumentos de entrenamiento
training_args = TrainingArguments(
    output_dir='./results',
    evaluation_strategy="epoch",
    learning_rate=2e-5,
    per_device_train_batch_size=1,  # Reducido para evitar problemas de memoria
    per_device_eval_batch_size=1,
    num_train_epochs=3,
    weight_decay=0.01,
    logging_dir='./logs',
    logging_steps=10,
    save_total_limit=2,
    save_steps=500,
    eval_steps=500
)

# Inicializar el entrenador
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=dataset['train'],
    eval_dataset=dataset['validation']
)

# Entrenar el modelo
trainer.train()
