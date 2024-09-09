import os
from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS
from threading import Thread
from config import Config
from routes import webhook_bp
from services.chroma_service import ChromaService
from services.llm_service import LLMService
from services.webhook_service import WebhookService

def create_app(config_class=Config):
    load_dotenv()
    app = Flask(__name__)
    app.config.from_object(config_class)
    CORS(app)

    # Initialize services
    chroma_service = ChromaService(
        collection_name=app.config['COLLECTION_NAME'],
        persist_directory=app.config['CHROMA_DB'],
        embedding_model_name=app.config['EMBED_MODEL_NAME']
    )

    # Thread(target=chroma_service.index_files).start()
    if not os.path.exists(app.config['CHROMA_DB']) and \
        app.config['COLLECTION_NAME'] not in [collection.name \
                for collection in chroma_service.chroma._client.list_collections()]:
        Thread(target=chroma_service.index_files).start()
    else:
        print('Database is already set up!')

    llm_service = LLMService(
        model_name=app.config['MODEL_NAME'],
        chroma_service=chroma_service
    )
    webhook_service = WebhookService(
        graph_api_token=app.config['GRAPH_API_TOKEN'],
        llm_service=llm_service
    )

    # Register blueprints
    app.register_blueprint(webhook_bp)

    # Inject services into blueprint
    webhook_bp.webhook_service = webhook_service

    return app

if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get('PORT', 1337))
    app.run(port=port)