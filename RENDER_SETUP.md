# Configuración en Render

## Paso 1: Crear Web Service en Render

1. Ve a [Render Dashboard](https://dashboard.render.com/)
2. Click en "New +" → "Web Service"
3. Conecta el repositorio: `https://github.com/zoharmx/sofia_stripe`

## Paso 2: Configuración del Service

### General Settings

- **Name:** `sofia-stripe`
- **Region:** Oregon (US West) o la más cercana
- **Branch:** `master`
- **Root Directory:** (dejar en blanco)
- **Runtime:** `Python 3`

### Build Settings

**Build Command:**
```bash
pip install -r requirements.txt
```

**Start Command:**
```bash
uvicorn main:app --host 0.0.0.0 --port 10000
```

## Paso 3: Variables de Entorno

Ve a la pestaña "Environment" y agrega las siguientes variables (usa los valores del archivo `contexto.txt`):

### Variables Requeridas

**IMPORTANTE:** Usa los valores del archivo `contexto.txt` (no incluido en el repositorio por seguridad).

| Variable | Ejemplo | Descripción |
|----------|---------|-------------|
| `STRIPE_KEY` | `sk_test_xxxxx...` | Clave secreta de Stripe (test mode) |
| `TWILIO_SID` | `ACxxxxxxxx...` | Account SID de Twilio |
| `TWILIO_TOKEN` | `your_auth_token` | Auth Token de Twilio |
| `TWILIO_FROM` | `+1234567890` | Número toll-free de Twilio |

### Variables Opcionales

| Variable | Valor por Defecto | Descripción |
|----------|-------------------|-------------|
| `SUCCESS_URL` | `https://sofia-stripe.onrender.com/gracias` | URL de redirección después del pago exitoso |
| `CANCEL_URL` | `https://sofia-stripe.onrender.com/cancelado` | URL cuando el usuario cancela el pago |
| `PORT` | `10000` | Puerto del servidor (Render usa 10000 por defecto) |

### Cómo agregar las variables:

1. En Render Dashboard → Tu servicio → "Environment"
2. Click en "Add Environment Variable"
3. Agrega cada variable con su nombre y valor
4. Click "Save Changes"

## Paso 4: Deploy

1. Render automáticamente desplegará cuando hagas click en "Create Web Service"
2. Espera a que el deploy termine (verás logs en tiempo real)
3. La URL final será: `https://sofia-stripe.onrender.com`

## Paso 5: Verificar el Deploy

### Probar el endpoint de salud

```bash
curl https://sofia-stripe.onrender.com/
```

Deberías recibir:
```json
{
  "status": "active",
  "service": "Sofia Stripe Voice Agent API",
  "version": "1.0.0"
}
```

### Ver los logs

1. En Render Dashboard → Tu servicio → "Logs"
2. Deberías ver:
   ```
   Application startup complete.
   Uvicorn running on http://0.0.0.0:10000
   ```

## Paso 6: Configurar Webhook en ElevenLabs

Ahora que el servicio está en producción:

1. Ve a [ElevenLabs Dashboard](https://elevenlabs.io/)
2. Navega a tu agente
3. Ve a "Analysis & Tools" → "Add Tool" (o edita el existente)
4. Configura el webhook:

**URL del Webhook:**
```
https://sofia-stripe.onrender.com/elevenlabs-webhook
```

**Configuración completa:**

```json
{
  "name": "enviar_link_pago",
  "description": "Úsala cuando el usuario confirme explícitamente que quiere comprar el servicio o realizar el pago. Esta herramienta enviará un enlace de Stripe por SMS.",
  "webhook_url": "https://sofia-stripe.onrender.com/elevenlabs-webhook",
  "schema": {
    "type": "object",
    "properties": {
      "phone_number": {
        "type": "string",
        "description": "The user's phone number strictly in E.164 format (e.g., +52811...). If the user hasn't provided it, ask for it."
      }
    },
    "required": ["phone_number"]
  }
}
```

## Paso 7: Prueba End-to-End

1. Llama al número de Twilio configurado en tu cuenta
2. Conversa con el agente
3. Cuando confirmes que quieres pagar, el agente te pedirá tu número
4. Proporciona tu número en formato internacional (ej: +52 811 123 4567)
5. Deberías recibir un SMS con el link de pago
6. Completa el pago en Stripe
7. Verifica en Render logs que todo funcionó

### Verificar logs en tiempo real

```bash
# En Render Dashboard → Logs, deberías ver:
📞 Recibido de ElevenLabs: {...}
📱 Procesando pago para: +521234567890
💳 Link de Stripe creado: https://checkout.stripe.com/...
✅ SMS enviado exitosamente. SID: SM...
```

## Troubleshooting

### Error: "Environment variable is required"

**Problema:** El servicio no inicia porque faltan variables de entorno.

**Solución:**
1. Ve a Environment en Render
2. Verifica que todas las variables requeridas estén configuradas
3. Haz un "Manual Deploy" para reiniciar con las nuevas variables

### Error 500 en el webhook

**Problema:** ElevenLabs recibe error al llamar el webhook.

**Solución:**
1. Revisa los logs en Render para ver el error específico
2. Verifica que las credenciales de Stripe y Twilio sean correctas
3. Asegúrate de que el número de teléfono esté en formato E.164

### SMS no llega

**Problema:** El usuario no recibe el SMS.

**Solución:**
1. Verifica el balance de Twilio
2. Revisa que el número esté en formato E.164 (+52...)
3. Checa los logs de Twilio en su console
4. Verifica que TWILIO_FROM sea correcto

### El agente no dispara el webhook

**Problema:** El agente no ejecuta la herramienta.

**Solución:**
1. Verifica que la URL del webhook en ElevenLabs sea correcta
2. Revisa que el schema JSON esté bien configurado
3. Asegúrate de que el agente tenga la herramienta habilitada
4. Prueba la descripción de la herramienta (debe ser clara sobre cuándo usarla)

## Actualizaciones Futuras

### Para actualizar el código:

1. Haz cambios localmente
2. Commit y push a GitHub:
   ```bash
   git add .
   git commit -m "Descripción de los cambios"
   git push origin master
   ```
3. Render automáticamente detectará el push y desplegará la nueva versión

### Para cambiar a producción:

1. Obtén las claves de producción de Stripe
2. Actualiza `STRIPE_KEY` en Environment con la clave de producción
3. Actualiza `SUCCESS_URL` y `CANCEL_URL` si tienes dominio custom
4. Configura Stripe webhooks para recibir notificaciones de pagos

## Monitoreo

### Métricas en Render

- Dashboard muestra CPU, memoria y ancho de banda
- Logs en tiempo real disponibles 24/7
- Puedes configurar alertas por email

### Stripe Dashboard

- Ve pagos en tiempo real en [Stripe Dashboard](https://dashboard.stripe.com/)
- Revisa logs de API calls
- Configura webhooks para notificaciones

### Twilio Console

- Revisa mensajes enviados en [Twilio Console](https://console.twilio.com/)
- Monitorea balance y uso
- Ve logs de SMS

## Soporte

Si tienes problemas:

1. Revisa los logs en Render primero
2. Verifica las credenciales en Environment
3. Prueba los endpoints individualmente
4. Revisa la configuración en ElevenLabs

Para más información, consulta el [README.md](README.md) principal.
