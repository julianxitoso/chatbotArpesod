from openai import OpenAI

client = OpenAI(api_key="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",
                base_url="https://openrouter.ai/api/v1")


messages = input("Cual es tu pregunta: ")

prompt = (
    "Por favor responde de manera clara y sin simbolos innecesarios"
    "Evita usar otros idiomas que no sean el castellano y escribe una respuesta concisa"
    f"Pregunta del usaurio: {messages}"
)

completion = client.chat.completions.create(
    model="cognitivecomputations/dolphin3.0-r1-mistral-24b:free",
    messages=[
        {
            "role": "user",
            "content":prompt   
        }
    ]
)

print(completion.choices[0].message.content)