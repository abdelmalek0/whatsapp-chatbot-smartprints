import os
from typing import List

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_community.document_loaders import TextLoader
from langchain_community.embeddings.ollama import OllamaEmbeddings
from langchain_community.embeddings import JinaEmbeddings
from langchain_core.documents import Document
from dotenv import load_dotenv

from utility import normalize_distance_reversed

load_dotenv()

class ChromaService:
    def __init__(self, collection_name, persist_directory, embedding_model_name):
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        # self.embed_model = OllamaEmbeddings(model=embedding_model_name)
        self.embed_model = JinaEmbeddings(
            jina_api_key=os.getenv('EMBED_API_KEY'), 
            model_name="jina-embeddings-v3"
        )
        
        self.chroma = Chroma(
            collection_name=self.collection_name,
            embedding_function=self.embed_model,
            persist_directory=self.persist_directory,
            collection_metadata={"hnsw:space": "cosine"}
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            separators=["\n\n"], 
            chunk_size=1000, 
            chunk_overlap=200
        )

    def index_files(self, summarizer):
        print('Indexing files ...')
        documents: List[Document] = []
        for file in os.listdir("./docs/"):
            filepath = os.path.join("./docs/", file)
            document_loader = TextLoader(filepath, encoding='utf-8')
            docs = document_loader.load()
            documents.extend(docs)
        
        mini_documents = []
        for doc in documents:
            texts = [text for text in doc.page_content.split('$$$$$$$$$$$$$$$$') if text and text.strip('\n')]
            metadata = doc.metadata
            metadata['language'] = 'Arabic' if metadata['source'].split('.')[-2].endswith('ar') else 'English'
            print(metadata)
            for text in texts:
                mini_documents.append(Document(page_content=text, metadata=metadata))

        try:
            self.chroma.add_documents(mini_documents)
        except Exception as e:
            print(f"Error indexing files: {e}")
        else:
            print('Indexing files into the database: 🟩 Finished')

    def retrieve(self, query: str, language= 'English', score_threshold=.8, k=5) -> List[Document]:
        return self.chroma.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs={"score_threshold": score_threshold, 
                           "k": k, 
                           'filter':{'language': language}
                           }
            ).invoke(query)