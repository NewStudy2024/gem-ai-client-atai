import os
import logging
from flask import Flask, request, jsonify
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

@app.route('/process', methods=['POST'])
def process_request():
    """
    Endpoint to process incoming POST requests.
    Expects JSON payload with 'system_instruction' (optional) and 'data'.
    Returns the model's response.
    """
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


        if system_instruction != default_system_instruction:
            # Return the model's response as JSON
            return jsonify({
                'model_response' : response.text
            }), 200

        # Return the model's response as JSON
        return jsonify({
            'title': response.text.splitlines()[0].replace("`", ""),
            'body': "\n".join(response.text.splitlines()[1:])
        }), 200

    except Exception as e:
        # Log the exception and return an error response
        logger.error(f"Error processing request: {e}")
        return jsonify({'error': 'An error occurred while processing your request.'}), 500

if __name__ == '__main__':
    app.run(
        host=os.getenv('FLASK_HOST', '0.0.0.0'),
        port=int(os.getenv('FLASK_PORT', 5000)),
        debug=os.getenv('FLASK_DEBUG', 'False').lower() in ['true', '1', 't']
    )
