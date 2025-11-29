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

# Validar que las variables críticas estén configuradas
if not STRIPE_KEY:
    raise ValueError("STRIPE_KEY environment variable is required")
if not TWILIO_SID:
    raise ValueError("TWILIO_SID environment variable is required")
if not TWILIO_TOKEN:
    raise ValueError("TWILIO_TOKEN environment variable is required")
if not TWILIO_FROM:
    raise ValueError("TWILIO_FROM environment variable is required")

# Configurar Stripe y Twilio
stripe.api_key = STRIPE_KEY
twilio_client = Client(TWILIO_SID, TWILIO_TOKEN)

# --- MODELOS DE DATOS ---
class ToolCallRequest(BaseModel):
    name: str
    arguments: dict

@app.get("/")
async def root():
    """
    Endpoint de verificación de salud del servicio.
    """
    return {
        "status": "active",
        "service": "Sofia Stripe Voice Agent API",
        "version": "1.0.0"
    }

@app.get("/gracias")
async def success_page():
    """
    Página de éxito después de completar el pago.
    """
    return {
        "status": "success",
        "message": "¡Gracias por tu pago! Tu suscripción ha sido procesada exitosamente."
    }

@app.get("/cancelado")
async def cancel_page():
    """
    Página cuando el usuario cancela el pago.
    """
    return {
        "status": "cancelled",
        "message": "El pago fue cancelado. Si cambias de opinión, puedes contactarnos nuevamente."
    }

@app.post("/elevenlabs-webhook")
async def handle_tool_call(request: Request):
    """
    Este endpoint es el que ElevenLabs llamará cuando el agente
    necesite ejecutar la herramienta de envío de link de pago.
    """
    try:
        data = await request.json()
        print(f"📞 Recibido de ElevenLabs: {data}")

        # ElevenLabs puede enviar diferentes estructuras
        tool_name = data.get("name") or data.get("tool_name")
        parameters = data.get("arguments") or data.get("parameters", {})

        if tool_name == "enviar_link_pago":
            user_phone = parameters.get("phone_number")

            # Validar que tengamos el teléfono
            if not user_phone:
                print("❌ Error: No se proporcionó número de teléfono")
                return {
                    "result": "Error: No tengo el número de teléfono del usuario. Por favor, solicítalo nuevamente."
                }

            # Normalizar el número si es necesario
            if not user_phone.startswith('+'):
                user_phone = '+' + user_phone

            print(f"📱 Procesando pago para: {user_phone}")

            # 1. Crear Link de Pago en Stripe
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'mxn',
                        'product_data': {
                            'name': 'Servicio Premium - Agente IA Sofia',
                            'description': 'Acceso al servicio premium con agente de voz inteligente'
                        },
                        'unit_amount': 5000,  # $50.00 MXN (en centavos)
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=SUCCESS_URL,
                cancel_url=CANCEL_URL,
                phone_number_collection={'enabled': True},
            )

            payment_url = checkout_session.url
            print(f"💳 Link de Stripe creado: {payment_url}")

            # 2. Enviar SMS con Twilio
            message = twilio_client.messages.create(
                body=f"¡Hola! 👋\n\nPara completar tu suscripción al Servicio Premium, usa este enlace seguro:\n\n{payment_url}\n\nGracias por confiar en nosotros.\n- Equipo Sofia",
                from_=TWILIO_FROM,
                to=user_phone
            )

            print(f"✅ SMS enviado exitosamente. SID: {message.sid}")

            # 3. Retornar respuesta al Agente
            return {
                "result": "Perfecto, el enlace de pago fue enviado exitosamente por SMS al número proporcionado. Por favor, pídele al usuario que revise sus mensajes de texto para completar el pago de manera segura."
            }

        else:
            print(f"⚠️ Herramienta no reconocida: {tool_name}")
            return {
                "result": "Herramienta no reconocida. Verifica la configuración en ElevenLabs."
            }

    except stripe.error.StripeError as e:
        print(f"❌ Error de Stripe: {str(e)}")
        return {
            "result": f"Hubo un error procesando el pago con Stripe. Por favor, intenta nuevamente en unos momentos."
        }

    except Exception as e:
        print(f"❌ Error general: {str(e)}")
        return {
            "result": "Ocurrió un error técnico. Por favor, contacta al soporte técnico."
        }

@app.post("/stripe-webhook")
async def stripe_webhook(request: Request):
    """
    Endpoint para recibir notificaciones de Stripe sobre pagos completados.
    """
    try:
        data = await request.json()
        event_type = data.get("type")

        print(f"🔔 Webhook de Stripe recibido: {event_type}")

        if event_type == "checkout.session.completed":
            session = data.get("data", {}).get("object", {})
            customer_email = session.get("customer_details", {}).get("email")
            amount_total = session.get("amount_total", 0) / 100

            print(f"✅ Pago completado: {customer_email} - ${amount_total} MXN")

        return {"received": True}

    except Exception as e:
        print(f"❌ Error procesando webhook de Stripe: {str(e)}")
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
