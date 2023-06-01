Endpoint: `wss://query.wssh.trade/ws/{collection}`

Websocket Message:

## Round 1 Auth

front: `Bearer token`

backend: `Hi,how can I help you?`

If authentication fails, backend will return `errors.unauthorized`, then websocket connection will be disconnected

## Round 2 Send UUID

front: `User UUID`

backend: `OK`

This round of communication is used to notify the backend to use the specified user's chat history

## Round n Chat

front: `{"question": "Is there a relationship between Windows 365 and Azure?"}`

backend: keep returning `content += chunck`

backend: send `end`

If the question does not conform to the json specification, returns `errors.invalidAskRequest`.


## Disconnect

front: `STOP`

Backend will disconnect websocket.