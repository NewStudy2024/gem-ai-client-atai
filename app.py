import os
import logging
import sqlite3
import time
from flask import Flask, request, jsonify, render_template
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Google Generative AI with the API key from environment variables
genai.configure(api_key=os.getenv('GENAI_API_KEY', ''))

# Define the generation configuration
generation_config = {
    "temperature": 1.0,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
}

# Load the default system instruction from environment variables
default_system_instruction = os.getenv('SYS_INSTRUCTION', '')

# Initialize the Generative Model once to avoid reinitialization on each request
try:
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash-exp",
        generation_config=generation_config,
        system_instruction=default_system_instruction,
    )
    logger.info("Generative model initialized successfully.")
except Exception as e:
    logger.error(f"Failed to initialize GenerativeModel: {e}")
    raise


# Функция подключения к SQLite
def get_db_connection():
    # request_logs.db будет создаваться в корневой папке /app внутри контейнера
    conn = sqlite3.connect('request_logs.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# Создадим таблицу при запуске, если её нет
with get_db_connection() as conn:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS request_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            response_time REAL
        )
    """)

def payload_parser(response_text):
    lines = response_text.splitlines()

    temp_title = lines[0].replace("`", "") if lines else ""

    if temp_title == "markdown":
        lower_text = response_text.lower()
        topic_index = lower_text.find("topic:")

        if topic_index != -1:
            topic_index_end = topic_index + len("topic:")

            next_newline_index = response_text.find("\n", topic_index_end)
            if next_newline_index == -1:
                next_newline_index = len(response_text)

            topic_value = response_text[topic_index_end:next_newline_index].strip()
            if topic_value:
                temp_title = topic_value

    temp_body = "\n".join(lines[1:]) if len(lines) > 1 else ""

    return jsonify({
        'title': temp_title,
        'body': temp_body
    }), 200


@app.route('/process', methods=['POST'])
def process_request():
    """
    Endpoint to process incoming POST requests.
    Expects JSON payload with 'system_instruction' (optional) and 'data'.
    Returns the model's response.
    """
    start_time = time.time()
    try:
        # Parse JSON payload from the request
        payload = request.get_json()
        if not payload:
            logger.warning("No JSON payload received.")
            return jsonify({'error': 'Invalid JSON payload.'}), 400

        # Extract 'system_instruction' and 'data' from the payload
        system_instruction = payload.get('system_instruction', default_system_instruction)
        user_input = payload.get('data')

        # Validate required field 'data'
        if user_input is None:
            logger.warning("Missing 'data' in the payload.")
            return jsonify({'error': "'data' field is required."}), 400

        logger.info("Received request with system_instruction and data.")

        # Update the model's system instruction if provided
        model.system_instruction = system_instruction
        logger.info("Updated system_instruction for the model.")

        # Start a new chat session with an empty history
        chat_session = model.start_chat(history=[])

        # Send the user input to the chat session and get the response
        response = chat_session.send_message(user_input)

        elapsed = time.time() - start_time
        logger.info(f"Request processed in {elapsed:.4f} seconds.")

        with get_db_connection() as conn:
            conn.execute(
                "INSERT INTO request_logs (response_time) VALUES (?)",
                (elapsed,)
            )

        if system_instruction != default_system_instruction:
            # Return the model's response as JSON
            return jsonify({
                'model_response' : response.text
            }), 200

        # Return the model's response as JSON

        return payload_parser(response.text)
        # return jsonify({
        #     'title': response.text.splitlines()[0].replace("`", ""),
        #     'body': "\n".join(response.text.splitlines()[1:])
        # }), 200

    except Exception as e:
        # Log the exception and return an error response
        logger.error(f"Error processing request: {e}")
        return jsonify({'error': 'An error occurred while processing your request.'}), 500


@app.route('/stats', methods=['GET'])
def get_stats():
    """
    Endpoint that returns basic metrics (JSON):
    - total_requests (int)
    - average_response_time (float)
    """
    try:
        with get_db_connection() as conn:
            row = conn.execute("""
                SELECT COUNT(*) as total_requests,
                       AVG(response_time) as average_response_time
                FROM request_logs
            """).fetchone()

        return jsonify({
            'total_requests': row['total_requests'] or 0,
            'average_response_time': round(row['average_response_time'] or 0, 4)
        })
    except Exception as e:
        logger.error(f"Error retrieving stats: {e}")
        return jsonify({'error': 'Could not retrieve stats.'}), 500

@app.route('/dashboard', methods=['GET'])
def dashboard():
    """
    Returns an HTML template that visualizes the data from /stats using Plotly.
    """
    return render_template('dashboard.html')



if __name__ == '__main__':
    app.run(
        host=os.getenv('FLASK_HOST', '0.0.0.0'),
        port=int(os.getenv('FLASK_PORT', 5000)),
        debug=os.getenv('FLASK_DEBUG', 'False').lower() in ['true', '1', 't']
    )
