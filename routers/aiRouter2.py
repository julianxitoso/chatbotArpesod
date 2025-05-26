from fastapi import APIRouter
from openai import OpenAI
from interfaces.chatinterfaces import InputMessage

router = APIRouter()

client = OpenAI(api_key="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",
                base_url="https://openrouter.ai/api/v1")

@router.post("/ai-chat")
def aiChat(data: InputMessage):
    data = data.model_dump()
    print("message" + data["message"])

    prompt = "Por favor response de manera concreta, clara y siempre en castellano."

    try:
        completion = ChatCompletionResponse = client.chat.completions.create(
            model="cognitivecomputations/dolphin3.0-r1-mistral-24b:free",
            messages=[
                {
                    "role": "system",
                    "content":"Eres un asistente que siempre responde en castellano de forma clara y breve"
                },

                {
                    "role": "user", ""
                    "content":prompt+ "responde a esta pregunta: "+data["message"]
                }
            ]
        )
        print("response "+completion.choices[0].message.content)
        return {"reply": completion.choices[0].message.content}
    except Exception as e:
        print(f"Error: {e}")
        return {"status":str(e)}

