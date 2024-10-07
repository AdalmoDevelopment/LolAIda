import tiktoken

# Load the finetuning data from your file
file_path = 'finetuning_data.jsonl'

models = ['gpt-3.5-turbo', 'gpt-4', 'gpt-4o' ]

for model in models:
    # Load the tokenizer for GPT-3.5-turbo
    tokenizer = tiktoken.encoding_for_model(model)

    # Count the number of tokens in the dataset
    total_tokens = 0

    # Open the JSONL file and calculate tokens per line
    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            total_tokens += len(tokenizer.encode(line))

    print(f"Total tokens {model}: {total_tokens}")
