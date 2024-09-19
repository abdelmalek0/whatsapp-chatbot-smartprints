# WhatsApp Chatbot - SmartPrints

**WhatsApp Chatbot SmartPrints** is an AI-powered customer support agent by **SmartPrints** for handling customer interactions via WhatsApp.

## Prerequisites

- **Python** 3.11
- **Poetry** for dependency management

## Setup

1. Clone the repository:

   ```bash
   git clone https://github.com/abdelmalek0/whatsapp-chatbot-smartprints.git
   cd whatsapp-chatbot-smartprints
   ```
2. Install dependencies:

    ```bash
    poetry install
    ```

3. Create a .env file inside the whatsapp-chatbot-smartprints directory with:

    ```bash
    GRAPH_API_TOKEN=your_facebook_graph_api_token
    WEBHOOK_VERIFY_TOKEN=your_webhook_verify_token
    GROQ_API_KEY=your_groq_api_key
    PORT=your_desired_port
    ```

4. Run the app:

    ```bash
    poetry run python main.py
    ```