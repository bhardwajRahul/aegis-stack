# API Reference

Complete REST API documentation for the Communications Service.

## Base URL

All endpoints are prefixed with `/api/v1/comms`.

## Email Endpoints

### Send Email

Send an email via Resend.

```http
POST /api/v1/comms/email/send
```

**Request Body**

```json
{
  "to": ["user@example.com"],
  "subject": "Welcome to Our Service",
  "text": "Hello! Welcome to our platform.",
  "html": "<h1>Welcome!</h1><p>Hello! Welcome to our platform.</p>",
  "from_email": "custom@yourdomain.com",
  "cc": ["cc@example.com"],
  "bcc": ["bcc@example.com"],
  "reply_to": "support@example.com",
  "tags": [{"name": "category", "value": "welcome"}]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `to` | `array[string]` | Yes | List of recipient email addresses |
| `subject` | `string` | Yes | Email subject line |
| `text` | `string` | No* | Plain text body |
| `html` | `string` | No* | HTML body |
| `from_email` | `string` | No | Override default sender |
| `cc` | `array[string]` | No | CC recipients |
| `bcc` | `array[string]` | No | BCC recipients |
| `reply_to` | `string` | No | Reply-to address |
| `tags` | `array[object]` | No | Email tags for analytics |

*Either `text` or `html` is required.

**Response**

```json
{
  "id": "email-123456",
  "to": ["user@example.com"],
  "status": "sent",
  "message": "Email sent successfully"
}
```

**Status Codes**

| Code | Description |
|------|-------------|
| 200 | Email sent successfully |
| 400 | Invalid request (missing fields, invalid email) |
| 502 | Email provider error |
| 503 | Email service not configured |

**Example**

```bash
curl -X POST http://localhost:8000/api/v1/comms/email/send \
  -H "Content-Type: application/json" \
  -d '{
    "to": ["user@example.com"],
    "subject": "Welcome",
    "text": "Hello, welcome to our service!",
    "html": "<h1>Welcome!</h1><p>Hello, welcome to our service!</p>"
  }'
```

## SMS Endpoints

### Send SMS

Send an SMS via Twilio.

```http
POST /api/v1/comms/sms/send
```

**Request Body**

```json
{
  "to": "+15559876543",
  "body": "Your verification code is 123456",
  "from_number": "+15551234567"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `to` | `string` | Yes | Recipient phone number (E.164 format) |
| `body` | `string` | Yes | Message text (max 1600 chars) |
| `from_number` | `string` | No | Override default sender |

**Response**

```json
{
  "sid": "SM1234567890abcdef",
  "to": "+15559876543",
  "status": "sent",
  "segments": 1,
  "message": "SMS sent successfully"
}
```

**Status Codes**

| Code | Description |
|------|-------------|
| 200 | SMS sent successfully |
| 400 | Invalid request (invalid phone number, message too long) |
| 502 | SMS provider error |
| 503 | SMS service not configured |

**Example**

```bash
curl -X POST http://localhost:8000/api/v1/comms/sms/send \
  -H "Content-Type: application/json" \
  -d '{
    "to": "+15559876543",
    "body": "Your verification code is 123456"
  }'
```

### SMS Segments

Messages longer than 160 characters are split into multiple segments:

| Message Length | Segments |
|---------------|----------|
| 1-160 chars | 1 |
| 161-306 chars | 2 |
| 307-459 chars | 3 |

The response includes `segments` count for billing reference.

## Voice Call Endpoints

### Make Call

Initiate a voice call via Twilio.

```http
POST /api/v1/comms/call/make
```

**Request Body**

```json
{
  "to": "+15559876543",
  "twiml_url": "https://example.com/twiml/greeting.xml",
  "from_number": "+15551234567",
  "timeout": 30
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `to` | `string` | Yes | Recipient phone number (E.164 format) |
| `twiml_url` | `string` | Yes | URL returning TwiML instructions |
| `from_number` | `string` | No | Override default caller ID |
| `timeout` | `integer` | No | Ring timeout in seconds (default: 30) |

**Response**

```json
{
  "sid": "CA1234567890abcdef",
  "to": "+15559876543",
  "status": "queued",
  "message": "Call initiated successfully"
}
```

**Call Status Values**

| Status | Description |
|--------|-------------|
| `queued` | Call is queued to be made |
| `ringing` | Call is ringing |
| `in-progress` | Call is active |
| `completed` | Call completed successfully |
| `busy` | Recipient busy |
| `failed` | Call failed |
| `no-answer` | No answer |

**Status Codes**

| Code | Description |
|------|-------------|
| 200 | Call initiated successfully |
| 400 | Invalid request (invalid phone number, invalid URL) |
| 502 | Voice provider error |
| 503 | Voice service not configured |

**Example**

```bash
curl -X POST http://localhost:8000/api/v1/comms/call/make \
  -H "Content-Type: application/json" \
  -d '{
    "to": "+15559876543",
    "twiml_url": "http://demo.twilio.com/docs/voice.xml"
  }'
```

### TwiML Example

Your `twiml_url` should return valid TwiML:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="alice">Hello! This is a call from your application.</Say>
  <Pause length="1"/>
  <Say voice="alice">Goodbye!</Say>
</Response>
```

## Health & Status Endpoints

### Health Check

Get comprehensive health status for all communication channels.

```http
GET /api/v1/comms/health
```

**Response**

```json
{
  "service": "communications",
  "status": "healthy",
  "channels": {
    "email": {
      "configured": true,
      "provider": "resend",
      "errors": []
    },
    "sms": {
      "configured": true,
      "provider": "twilio",
      "errors": []
    },
    "voice": {
      "configured": true,
      "provider": "twilio",
      "errors": []
    }
  },
  "total_errors": 0
}
```

### Status

Get current configuration status for all channels.

```http
GET /api/v1/comms/status
```

**Response**

```json
{
  "email": {
    "configured": true,
    "api_key_set": true,
    "from_email_set": true,
    "from_email": "noreply@example.com"
  },
  "sms": {
    "configured": true,
    "account_sid_set": true,
    "auth_token_set": true,
    "phone_number_set": true,
    "phone_number": "+15551234567"
  },
  "voice": {
    "configured": true,
    "account_sid_set": true,
    "auth_token_set": true,
    "phone_number_set": true
  }
}
```

### Version

Get service version and feature information.

```http
GET /api/v1/comms/version
```

**Response**

```json
{
  "service": "communications",
  "version": "1.0",
  "features": [
    "email_send",
    "sms_send",
    "voice_call",
    "webhook_handlers"
  ],
  "providers": {
    "email": "resend",
    "sms": "twilio",
    "voice": "twilio"
  },
  "endpoints": [
    "POST /comms/email/send",
    "POST /comms/sms/send",
    "POST /comms/call/make",
    "GET /comms/health",
    "GET /comms/status"
  ]
}
```

## Error Responses

All error responses follow this format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

### Common Errors

**503 Service Not Configured**
```json
{
  "detail": "Email not configured: RESEND_API_KEY is not set"
}
```

**502 Provider Error**
```json
{
  "detail": "SMS provider error: Invalid phone number format"
}
```

**400 Bad Request**
```json
{
  "detail": "Either text or html content is required"
}
```

## Python Client Examples

### Using httpx

```python
import httpx

async def send_email():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/comms/email/send",
            json={
                "to": ["user@example.com"],
                "subject": "Hello",
                "text": "Hello from the API!",
            }
        )
        return response.json()

async def send_sms():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/comms/sms/send",
            json={
                "to": "+15559876543",
                "body": "Your code: 123456",
            }
        )
        return response.json()
```

### Using requests

```python
import requests

# Send email
response = requests.post(
    "http://localhost:8000/api/v1/comms/email/send",
    json={
        "to": ["user@example.com"],
        "subject": "Hello",
        "text": "Hello from the API!",
    }
)
print(response.json())

# Send SMS
response = requests.post(
    "http://localhost:8000/api/v1/comms/sms/send",
    json={
        "to": "+15559876543",
        "body": "Your code: 123456",
    }
)
print(response.json())
```
