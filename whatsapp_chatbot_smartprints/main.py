import os
from threading import Thread

from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS

from config import Config
from routes import webhook_bp
from services.chroma_service import ChromaService
from services.llm_service import LLMService
from services.webhook_service import \
    WebhookService


def create_app(config_class=Config):
    load_dotenv()
    
    app = Flask(__name__)
    app.config.from_object(config_class)
    CORS(app)

    data_init = False

    if not os.path.exists(app.config['AUDIO_STORAGE']):
        os.makedirs(app.config['AUDIO_STORAGE'])
    if not os.path.exists(app.config['CHROMA_DB']):
        data_init = True

    # Initialize services
    chroma_service = ChromaService(
        collection_name=app.config['COLLECTION_NAME'],
        persist_directory=app.config['CHROMA_DB'],
        embedding_model_name=app.config['EMBED_MODEL_NAME']
    )

    llm_service = LLMService(
        model_name=app.config['MODEL_NAME'],
        chroma_service=chroma_service
    )

    if data_init:
        Thread(
            target=chroma_service.index_files, 
            args=[llm_service.summarizer]
        ).start()
    else:
        print('Database is already set up!')

    webhook_service = WebhookService(
        graph_api_token=app.config['GRAPH_API_TOKEN'],
        verify_token=app.config['WEBHOOK_VERIFY_TOKEN'],
        llm_service=llm_service,
        audio_storage=app.config['AUDIO_STORAGE']
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
