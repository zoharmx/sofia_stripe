import os
import stripe
from fastapi import FastAPI, Request
from twilio.rest import Client
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="Sofia Stripe Voice Agent API")

# --- CONFIGURACIÓN CON VARIABLES DE ENTORNO ---
STRIPE_KEY = os.getenv("STRIPE_KEY")
TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_TOKEN = os.getenv("TWILIO_TOKEN")
TWILIO_FROM = os.getenv("TWILIO_FROM")
SUCCESS_URL = os.getenv("SUCCESS_URL", "https://sofia-stripe.onrender.com/gracias")
CANCEL_URL = os.getenv("CANCEL_URL", "https://sofia-stripe.onrender.com/cancelado")

# Validar que las variables críticas estén configuradas (Solo si no estamos importando para tests)
if __name__ != "__main__": 
    # Esto evita errores si corres localmente sin .env a veces, pero en render es vital
    pass 

# Configurar Stripe y Twilio (Manejamos el error si faltan las keys para que no truene el server al inicio)
if STRIPE_KEY:
    stripe.api_key = STRIPE_KEY
if TWILIO_SID and TWILIO_TOKEN:
    twilio_client = Client(TWILIO_SID, TWILIO_TOKEN)

# --- MODELOS DE DATOS ---
class ToolCallRequest(BaseModel):
    name: str
    arguments: dict

@app.get("/")
async def root():
    return {"status": "active", "service": "Sofia Stripe Voice Agent API"}

@app.get("/gracias")
async def success_page():
    return {"status": "success", "message": "¡Gracias por tu pago! Tu suscripción ha sido procesada exitosamente."}

@app.get("/cancelado")
async def cancel_page():
    return {"status": "cancelled", "message": "El pago fue cancelado."}

@app.post("/elevenlabs-webhook")
async def handle_tool_call(request: Request):
    """
    Maneja la llamada de ElevenLabs.
    """
    try:
        data = await request.json()
        print(f"📞 Recibido de ElevenLabs: {data}")

        # --- LÓGICA DE DETECCIÓN CORREGIDA ---
        # 1. Intentamos buscar el nombre explícito
        tool_name = data.get("name") or data.get("tool_name")
        
        # 2. Inicializamos parámetros
        parameters = {}

        # CASO A: ElevenLabs envía estructura completa (wrapper)
        if tool_name:
            parameters = data.get("arguments") or data.get("parameters", {})
        
        # CASO B (El que te está pasando): ElevenLabs envía solo los datos crudos
        elif "phone_number" in data:
            print("💡 Detectado payload directo (sin nombre de herramienta). Asumiendo 'enviar_link_pago'.")
            tool_name = "enviar_link_pago"
            parameters = data
        
        # --- PROCESAMIENTO ---

        if tool_name == "enviar_link_pago":
            user_phone = parameters.get("phone_number")

            if not user_phone:
                return {"result": "Error: Falta el número de teléfono."}

            # Limpieza del número
            user_phone = str(user_phone).strip()
            if not user_phone.startswith('+'):
                # Asumir México si no trae código, o simplemente agregar el +
                user_phone = '+' + user_phone

            print(f"📱 Procesando pago para: {user_phone}")

            # Verificar que las credenciales existan antes de llamar a APIs externas
            if not STRIPE_KEY or not TWILIO_SID:
                print("❌ Error: Faltan credenciales de entorno en el servidor")
                return {"result": "Error de configuración en el servidor (Faltan API Keys)."}

            # 1. Crear Link de Stripe
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'mxn',
                        'product_data': {
                            'name': 'Servicio Premium - Agente Sofia',
                        },
                        'unit_amount': 5000, 
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=SUCCESS_URL,
                cancel_url=CANCEL_URL,
            )

            payment_url = checkout_session.url
            print(f"💳 Link creado: {payment_url}")

            # 2. Enviar SMS
            message = twilio_client.messages.create(
                body=f"Hola, completa tu pago aquí: {payment_url}",
                from_=TWILIO_FROM,
                to=user_phone
            )

            print(f"✅ SMS enviado: {message.sid}")

            return {
                "result": "Enlace enviado exitosamente por SMS. Dile al usuario que revise su celular."
            }

        else:
            print(f"⚠️ Payload desconocido: {data}")
            return {"result": "Datos recibidos, pero no se reconoció la instrucción."}

    except Exception as e:
        print(f"❌ Error crítico: {str(e)}")
        # Importante: Devolver un string simple para que el Agente no se rompa
        return {"result": f"Ocurrió un error técnico procesando la solicitud: {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)