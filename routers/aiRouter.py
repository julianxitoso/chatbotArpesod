from fastapi import APIRouter, HTTPException
from interfaces.chatinterfaces import InputMessage
import os
from openai import OpenAI
from duckduckgo_search import DDGS  # <--- Importamos la librería de búsqueda

router = APIRouter()

# --- BASE DE CONOCIMIENTO (MANUAL DE USUARIO) ---
# Esta es la "memoria" interna de nuestro chatbot sobre la plataforma.
manual_context = """
---
Manual de Usuario: Sistema de Gestión de Activos Tecnológicos
Empresa: ARPESOD ASOCIADOS SAS
---

1. Gestión de Cuenta de Usuario
1.1. Cómo Crear un Nuevo Usuario: Solo los Administradores pueden. Se accede desde "Administración" > "Usuarios", se completa el formulario con nombre, cédula, usuario, contraseña y rol, y se guarda.
1.2. Cómo Cambiar la Contraseña: El usuario inicia sesión, va a "Mi Perfil" o "Cambiar Contraseña", ingresa su contraseña actual y la nueva dos veces, y actualiza.

2. Gestión de Activos Tecnológicos
2.1. Cómo Buscar un Activo: Desde el menú "Buscar" o "Inventario", se puede usar la barra de búsqueda por número de serie, nombre o cédula del responsable, ID del activo o tipo de activo.
2.2. Cómo Crear un Nuevo Activo: Desde "Gestión de Activos" > "Crear Nuevo Activo". Se deben llenar campos como Tipo de Activo, Marca, Modelo, Número de Serie, y características como Procesador, RAM y Almacenamiento.
2.3. Cómo Editar un Activo: Primero se busca el activo. En los detalles, se hace clic en "Editar" (ícono de lápiz), se modifican los campos necesarios y se guardan los cambios. El cambio queda en el historial.
2.4. Cómo Trasladar un Activo: Se busca el activo y se hace clic en "Trasladar". Se busca y selecciona al nuevo responsable por nombre o cédula. Al confirmar, el sistema actualiza la custodia y lo registra en el historial.
2.5. Cómo Generar un Acta: Después de asignar o trasladar un activo, el sistema da la opción "Generar Acta de Entrega". Esto abre un documento formal con todos los datos para ser impreso y firmado.

3. Tareas Específicas
3.1. Cómo Buscar las Características de un Computador (en Windows):
- Procesador y RAM: Clic derecho en Inicio > "Sistema".
- Almacenamiento: Explorador de Archivos > "Este equipo" > Clic derecho en Disco C: > "Propiedades".
- Número de Serie: Abrir Símbolo de sistema (cmd) y ejecutar el comando: wmic bios get serialnumber
"""

# Configuración del cliente para OpenRouter

# client = OpenAI(api_key="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",
#                 base_url="https://openrouter.ai/api/v1")
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)



# --- Endpoint 1: Asistente Experto (Solo Manual) ---
# Este es el chatbot rápido y especializado que solo responde sobre la plataforma.
@router.post("/ai-chat")
def aiChat(data: InputMessage):
    user_message = data.model_dump()["message"]
    system_prompt = f"""
    Eres un asistente virtual experto llamado 'Asistente ARPESOD'. Tu única y exclusiva función es responder preguntas sobre el uso del "Sistema de Gestión de Activos Tecnológicos" de ARPESOD.
    Tu única fuente de información es el manual de usuario que te proporciono. No uses ningún otro conocimiento.
    Si el usuario te pregunta algo que no está en el manual, responde amablemente: "Lo siento, no tengo información sobre eso. Solo puedo ayudarte con el uso de la plataforma de gestión de activos."
    Responde siempre en español de Colombia, con un tono amable y profesional.
    --- INICIO DEL MANUAL DE USUARIO ---
    {manual_context}
    --- FIN DEL MANUAL DE USUARIO ---
    """
    try:
        completion = client.chat.completions.create(
            model="meta-llama/llama-3.3-8b-instruct:free",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
        )
        return {"reply": completion.choices[0].message.content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al generar respuesta: {str(e)}")


# --- Endpoint 2: Asistente Avanzado (Decide si usar Manual o Web) ---
# Este es el chatbot "inteligente". Primero clasifica la pregunta y luego actúa.
@router.post("/ai-chat-v2")
def aiChatV2(data: InputMessage):
    user_message = data.model_dump()["message"]

    # --- PASO 1: CLASIFICAR LA PREGUNTA ---
    # Usamos un prompt simple para que el AI decida qué hacer.
    classification_prompt = f"""
    Clasifica la siguiente pregunta del usuario en una de dos categorías: 'MANUAL' o 'TECNICA'.
    - 'MANUAL': si la pregunta es sobre cómo usar la plataforma de gestión de activos (crear activos, usuarios, traslados, actas, etc.).
    - 'TECNICA': si la pregunta es una consulta general de computación o tecnología (cómo ver la IP, qué es un procesador, etc.).
    Responde ÚNICAMENTE con la palabra 'MANUAL' o 'TECNICA'.

    Pregunta del usuario: "{user_message}"
    """
    try:
        classification_completion = client.chat.completions.create(
            model="google/gemma-3-4b-it:free", # Usamos un modelo rápido para clasificar
            messages=[{"role": "user", "content": classification_prompt}],
            max_tokens=5, # Solo necesitamos una palabra
        )
        classification = classification_completion.choices[0].message.content.strip().upper()
        print(f"Clasificación de la pregunta: {classification}")

        # --- PASO 2: ACTUAR SEGÚN LA CLASIFICACIÓN ---

        # CASO A: La pregunta es sobre el MANUAL
        if "MANUAL" in classification:
            print("Ruta de acción: Responder usando el manual.")
            return aiChat(data) # Reutilizamos la lógica del primer endpoint

        # CASO B: La pregunta es TÉCNICA y requiere búsqueda web
        elif "TECNICA" in classification:
            print("Ruta de acción: Realizando búsqueda web.")

            # --- PASO 2.1: BUSCAR EN LA WEB ---
            with DDGS() as ddgs:
                search_results = list(ddgs.text(user_message, max_results=3))
                if not search_results:
                    return {"reply": "Lo siento, no pude encontrar información sobre eso en la web."}

            web_context = "\n\n".join([f"Fuente {i+1}:\n{result['body']}" for i, result in enumerate(search_results)])
            print(f"Contexto web encontrado:\n{web_context[:500]}...") # Imprime los primeros 500 caracteres del contexto

            # --- PASO 2.2: RESPONDER BASADO EN LA BÚSQUEDA ---
            synthesis_prompt = f"""
            Eres un asistente técnico que responde de forma clara y concisa.
            Basándote únicamente en el siguiente contexto extraído de una búsqueda web, responde la pregunta del usuario.
            Cita los pasos o la información más relevante del contexto.

            --- INICIO DEL CONTEXTO WEB ---
            {web_context}
            --- FIN DEL CONTEXTO WEB ---

            Pregunta del usuario: "{user_message}"
            """
            synthesis_completion = client.chat.completions.create(
                model="meta-llama/llama-3.3-8b-instruct:free", # Usamos un modelo bueno para resumir
                messages=[{"role": "user", "content": synthesis_prompt}]
            )
            return {"reply": synthesis_completion.choices[0].message.content}
        
        else:
             return {"reply": "Lo siento, no pude entender la categoría de tu pregunta. ¿Puedes reformularla?"}

    except Exception as e:
        print(f"Error en el endpoint v2: {e}")
        raise HTTPException(status_code=500, detail=f"Error al procesar la solicitud: {str(e)}")