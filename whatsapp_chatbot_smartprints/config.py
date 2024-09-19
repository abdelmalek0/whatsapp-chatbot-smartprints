import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    WEBHOOK_VERIFY_TOKEN = os.environ.get('WEBHOOK_VERIFY_TOKEN')
    GRAPH_API_TOKEN = os.environ.get('GRAPH_API_TOKEN')
    MODEL_NAME = 'llama-3.1-70b-versatile'
    EMBED_MODEL_NAME = 'mxbai-embed-large:latest'
    CHROMA_DB = './chromadb/'
    AUDIO_STORAGE = './audio/'
    COLLECTION_NAME = 'smartprints'