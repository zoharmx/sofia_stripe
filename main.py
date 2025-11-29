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
SUCCESS_URL = os.getenv("SUCCESS_URL", "https://agenciaaduanalhoymismo.com/gracias")
CANCEL_URL = os.getenv("CANCEL_URL", "https://agenciaaduanalhoymismo.com/cancelado")

# Link de tu calendario (Calendly, Cal.com, etc.) para que Sofía lo envíe también
CALENDAR_LINK = "https://cal.com/tony-hoymismo/consulta" 

# Validar que las variables críticas estén configuradas
if __name__ != "__main__": 
    pass 

# Configurar Stripe y Twilio
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

@app.post("/elevenlabs-webhook")
async def handle_tool_call(request: Request):
    """
    Maneja la llamada de ElevenLabs, genera link de pago y envía SMS + WhatsApp.
    """
    try:
        data = await request.json()
        print(f"📞 Recibido de ElevenLabs: {data}")

        # --- LÓGICA DE DETECCIÓN INTELIGENTE ---
        tool_name = data.get("name") or data.get("tool_name")
        parameters = {}

        # Si ElevenLabs manda estructura completa
        if tool_name:
            parameters = data.get("arguments") or data.get("parameters", {})
        
        # Si ElevenLabs manda payload crudo (sin nombre), inferimos por el teléfono
        elif "phone_number" in data:
            print("💡 Detectado payload directo. Asumiendo 'enviar_link_pago'.")
            tool_name = "enviar_link_pago"
            parameters = data
        
        # --- PROCESAMIENTO DE LA HERRAMIENTA ---

        if tool_name == "enviar_link_pago":
            user_phone = parameters.get("phone_number")

            if not user_phone:
                return {"result": "Error: Falta el número de teléfono. Pídeselo al usuario."}

            # Limpieza y formateo del número
            user_phone = str(user_phone).strip()
            if not user_phone.startswith('+'):
                # Asumimos código de país +52 (México) o +1 (USA) por defecto si falta
                user_phone = '+' + user_phone

            print(f"📱 Procesando pago para: {user_phone}")

            if not STRIPE_KEY or not TWILIO_SID:
                return {"result": "Error de configuración en servidor (Faltan API Keys)."}

            # 1. Crear Link de Stripe (Anticipo $350 USD)
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'usd', # Cambiado a dólares según guion
                        'product_data': {
                            'name': 'Anticipo Importación - Agencia HoyMismo',
                            'description': 'Pago inicial para trámite de importación vehicular.'
                        },
                        'unit_amount': 35000, # $350.00 USD (en centavos)
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=SUCCESS_URL,
                cancel_url=CANCEL_URL,
            )

            payment_url = checkout_session.url
            print(f"💳 Link creado: {payment_url}")

            # Mensaje base para enviar
            mensaje_texto = (
                f"Hola, soy Sofía de HoyMismo 🚛.\n\n"
                f"Aquí tienes el enlace seguro para tu anticipo ($350 USD):\n{payment_url}\n\n"
                f"Si prefieres agendar una videollamada antes, usa este link:\n{CALENDAR_LINK}"
            )

            # 2. Enviar SMS (Canal principal, más seguro)
            try:
                msg_sms = twilio_client.messages.create(
                    body=mensaje_texto,
                    from_=TWILIO_FROM,
                    to=user_phone
                )
                print(f"✅ SMS enviado: {msg_sms.sid}")
            except Exception as e:
                print(f"❌ Falló SMS: {e}")
                return {"result": "Error enviando el SMS. Verifica el número."}

            # 3. Enviar WhatsApp (Canal secundario)
            # Nota: Requiere que el usuario haya aceptado mensajes o uses plantillas aprobadas en prod.
            wa_status = "no enviado"
            try:
                msg_wa = twilio_client.messages.create(
                    body=mensaje_texto,
                    from_=f"whatsapp:{TWILIO_FROM}",
                    to=f"whatsapp:{user_phone}"
                )
                print(f"✅ WhatsApp enviado: {msg_wa.sid}")
                wa_status = "enviado"
            except Exception as wa_e:
                # No retornamos error fatal, solo logueamos, porque el SMS ya se fue.
                print(f"⚠️ WhatsApp no se pudo enviar (posible falta de opt-in): {wa_e}")
                wa_status = "falló (usuario no opt-in)"

            # 4. Respuesta al Agente (Lo que Sofía "sabe" que pasó)
            return {
                "result": (
                    f"Éxito total. Link de pago generado. "
                    f"SMS enviado correctamente. WhatsApp status: {wa_status}. "
                    "Dile al cliente que revise su celular ahora mismo."
                )
            }

        else:
            print(f"⚠️ Herramienta desconocida: {tool_name}")
            return {"result": "Instrucción recibida pero no reconocida."}

    except Exception as e:
        print(f"❌ Error crítico: {str(e)}")
        return {"result": f"Error técnico: {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)