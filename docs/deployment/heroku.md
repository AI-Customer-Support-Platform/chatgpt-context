# Deploying to Heroku

## Set Heroku Env Variables

You should set Heroku App Env. You can find this in `Settings >  Config Vars`:

- `BEARER_TOKEN` Requests Bearer Token
- `DATASTORE` must be `qdrant`
- `OPENAI_API_KEY`
- `QDRANT_API_KEY` Qdrant DataBase API Key
- `QDRANT_URL` Qdrant DataBase Url

## Set Github Action

Set the following in the `github repository > setting > Secrets and variables > Actions`:

- `HEROKU_API_KEY` Your Heroku API Key
- `HEROKU_APP_NAME` Deploy app name
- `HEROKU_EMAIL` Your Heroku Email

Github Action will perform CI/CD on every `dev` or `main` branch commit. 