# Retell Custom Function Integration

## Production Flow

```text
Customer browser
  -> POST /v1/retell/create-web-call
  -> Retell Web SDK
  -> Retell voice agent
  -> POST /v1/retell/function (nexgen_voice_turn)
  -> VoiceService
  -> IntentRouter
  -> VoiceCapabilityExecutor
  -> Tool Gateway
  -> Commerce services
  -> { "result": spoken_text, "spoken_text": spoken_text, ... }
  -> Retell agent speaks the result
```

`POST /v1/retell/webhook` is separate from the synchronous conversation path. It
verifies Retell signatures and acknowledges lifecycle notifications. It never
executes a voice turn. `call_ended` also releases the associated NexGen session.

## Retell Dashboard Configuration

Configure one Custom Function:

- Name: `nexgen_voice_turn`
- Method: `POST`
- URL: `https://<backend-domain>/v1/retell/function`
- Payload: keep **args only disabled** so Retell sends `name`, `call`, and `args`
- Wait for result: enabled
- Argument: `transcript`, required string containing the customer's latest request
- Speak after execution: enabled

Retell supplies `X-Retell-Signature`; the backend validates it before any
execution. Do not configure browser credentials or Tool Gateway credentials.
The web-call metadata carries `nexgen_session_id`, which restores the existing
VoiceService session for each function invocation.

Configure the agent webhook URL as:

`https://<backend-domain>/v1/retell/webhook`

Use lifecycle events `call_started`, `call_ended`, and `call_analyzed`. Do not use
`transcript_updated` to drive commerce execution.

## Retry and Duplicate Safety

Retell may retry a function request. The transport hashes the verified raw body
and reuses its completed result for five minutes. Commerce write operations keep
their existing confirmation and idempotency enforcement in the Tool Gateway.

## Response Contract

The synchronous function response includes `result` and `spoken_text`. Both use
the exact `VoiceService` spoken response. Execution status and confirmation flags
remain available to the Retell agent without exposing internal credentials.
