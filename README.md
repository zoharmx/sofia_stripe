# Sofia Stripe - Agente de Voz con Pagos Integrados

API de integración entre ElevenLabs Voice Agent, Twilio y Stripe para procesamiento de pagos mediante conversación de voz.

## Características

- Agente de voz conversacional (ElevenLabs)
- Procesamiento de pagos con Stripe
- Envío automático de links de pago por SMS (Twilio)
- Arquitectura "Push-to-Link"
- Desplegado en Render

## Arquitectura

```
Usuario → Llamada Telefónica (Twilio) → Agente de Voz (ElevenLabs)
                                              ↓
                                    Webhook → FastAPI (Render)
                                              ↓
                                    Stripe + Twilio SMS
                                              ↓
                                    Link de Pago → Usuario
```

## Configuración Rápida

### 1. Instalación Local

```bash
# Clonar el repositorio
git clone https://github.com/zoharmx/sofia_stripe
cd sofia_stripe

# Instalar dependencias
pip install -r requirements.txt

# Copiar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales
```

### 2. Ejecutar Localmente

```bash
# Iniciar servidor
uvicorn main:app --reload

# En otra terminal, exponer con ngrok
ngrok http 8000
```

### 3. Configurar ElevenLabs

1. Ve a tu agente en ElevenLabs Dashboard
2. Navega a "Analysis & Tools" → "Add Tool"
3. Selecciona "Webhook"
4. Configura así:

**Name:** `enviar_link_pago`

**Description:**
```
Úsala cuando el usuario confirme explícitamente que quiere comprar el servicio o realizar el pago. Esta herramienta enviará un enlace de Stripe por SMS.
```

**Webhook URL:**
```
https://sofia-stripe.onrender.com/elevenlabs-webhook
```

**Schema (JSON):**
```json
{
  "type": "object",
  "properties": {
    "phone_number": {
      "type": "string",
      "description": "The user's phone number strictly in E.164 format (e.g., +52811...). If the user hasn't provided it, ask for it."
    }
  },
  "required": ["phone_number"]
}
```

### 4. Configurar Twilio con ElevenLabs

1. En ElevenLabs Agent → Settings → Phone Number
2. Selecciona "Import from Twilio"
3. Ingresa tus credenciales de Twilio (disponibles en el archivo contexto.txt)

## Despliegue en Render

### Variables de Entorno en Render

Configurar en Render Dashboard → Environment (usa las credenciales del archivo contexto.txt):

```
STRIPE_KEY=tu_clave_secreta_de_stripe
TWILIO_SID=tu_account_sid_de_twilio
TWILIO_TOKEN=tu_auth_token_de_twilio
TWILIO_FROM=tu_numero_de_twilio
SUCCESS_URL=https://sofia-stripe.onrender.com/gracias
CANCEL_URL=https://sofia-stripe.onrender.com/cancelado
PORT=10000
```

### Build & Start Commands

**Build Command:**
```bash
pip install -r requirements.txt
```

**Start Command:**
```bash
uvicorn main:app --host 0.0.0.0 --port 10000
```

## Endpoints

### `GET /`
Health check del servicio.

### `POST /elevenlabs-webhook`
Recibe llamadas del agente de ElevenLabs cuando detecta intención de pago.

**Request esperado:**
```json
{
  "name": "enviar_link_pago",
  "arguments": {
    "phone_number": "+521234567890"
  }
}
```

**Response:**
```json
{
  "result": "Perfecto, el enlace de pago fue enviado exitosamente..."
}
```

### `POST /stripe-webhook`
Recibe notificaciones de Stripe sobre pagos completados.

### `GET /gracias`
Página de éxito post-pago.

### `GET /cancelado`
Página cuando el usuario cancela.

## Flujo de Uso

1. **Usuario llama** al número de Twilio: `+18779209282`
2. **Agente responde** y conversa sobre el servicio
3. **Usuario confirma** que quiere pagar
4. **Agente pregunta** por el número de teléfono (si no lo tiene)
5. **Sistema dispara** el webhook a FastAPI
6. **FastAPI crea** link de pago en Stripe
7. **Twilio envía** SMS con el link
8. **Usuario completa** el pago en Stripe
9. **Stripe notifica** vía webhook al sistema

## Recursos del Proyecto

### Render
- URL: https://sofia-stripe.onrender.com

### GitHub
- Repo: https://github.com/zoharmx/sofia_stripe

### Credenciales
Las credenciales de API están disponibles en el archivo `contexto.txt` (no incluido en el repositorio por seguridad).

Para configurar el proyecto necesitarás:
- Stripe Secret Key (modo test)
- Twilio Account SID, Auth Token y número toll-free
- ElevenLabs API Key y Agent ID

## Pruebas

### Probar el Agente

1. Llama al `+18779209282`
2. Di: "Hola, me interesa el servicio premium"
3. Agente: "¿Te gustaría proceder con el pago?"
4. Tú: "Sí, por favor"
5. Agente: "¿A qué número te envío el enlace?"
6. Tú: "Al +52 811 123 4567"
7. Recibes SMS con link de pago

### Verificar Logs

```bash
# Ver logs en Render
# Dashboard → Logs (tiempo real)
```

## Troubleshooting

### El agente no dispara el webhook
- Verifica que la URL en ElevenLabs sea correcta
- Revisa que el schema JSON esté bien configurado
- Checa los logs del agente en ElevenLabs

### SMS no llega
- Verifica que el número esté en formato E.164 (+521234567890)
- Revisa el balance de Twilio
- Checa que TWILIO_FROM esté correcto

### Error de Stripe
- Verifica que STRIPE_KEY sea válida
- Asegúrate de estar en modo test si usas claves de test
- Revisa los logs en Stripe Dashboard

## Siguiente Paso

Para modo producción:
1. Cambiar a claves de producción de Stripe
2. Actualizar SUCCESS_URL y CANCEL_URL a tu dominio real
3. Configurar webhook signatures de Stripe para seguridad
4. Implementar logging más robusto

## Soporte

Para problemas o preguntas, revisa los logs en:
- Render Dashboard
- ElevenLabs Console
- Stripe Dashboard
- Twilio Console
