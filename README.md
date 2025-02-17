# Flask Generative AI API

This is a Flask-based web application that integrates with Google's Generative AI to process user requests and return responses. It also logs request metrics (response time) into an SQLite database and provides an endpoint to retrieve statistics.

## Features

- **Generative AI Integration**: Uses Google's Generative AI (`gemini-2.0-flash-exp`) to generate responses based on user input.
- **Request Logging**: Logs response times for each request into an SQLite database.
- **Metrics Endpoint**: Provides a `/stats` endpoint to retrieve total requests and average response time.
- **Dashboard**: Includes a `/dashboard` endpoint to visualize metrics using Plotly (requires a template file `dashboard.html`).
- **Customizable System Instruction**: Allows overriding the default system instruction for the AI model via the `system_instruction` field in the request payload.

## Setup

1. **Clone the repository**
2. **Add env file**
   ```
   GENAI_API_KEY "Your API key from Gemini"
   SYS_INSTRUCTION "Instructions for AI"
   FLASK_HOST "App IP address"
   FLASK_PORT "App port"
   FLASK_DEBUG "Debuging mode"
      
   #Gunicorn configs
   GUNICORN_WORKERS=4
   GUNICORN_BIND=0.0.0.0:5001
      
   #Default model
   DEFAULT_MODEL_NAME=gemini-2.0-flash-exp
   ```
3. **Run the docker compose**

        docker compose up

Congrats now you have a Gemini AI API client!!!