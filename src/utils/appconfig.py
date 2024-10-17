import os
from os.path import join, dirname, exists
from dotenv import load_dotenv
from cfenv import AppEnv
import json

class AppConfig:
    def __init__(self):
        dotenv_path = join(dirname(__file__), '.env')
        if exists(dotenv_path):
            load_dotenv(dotenv_path)
        else:
            print(f"Warning: .env file not found at {dotenv_path}")

        self.print_env()

        self.LOCAL_ENV = os.getenv("ENV", "PROD").upper() == "LOCAL"

        self.load_env_vars()

    def load_env_vars(self):
        for key, value in os.environ.items():
            setattr(self, key, value)

        if not self.LOCAL_ENV:
            self.load_production_env()


    def load_production_env(self):
        env = AppEnv()
        """
        hana = env.get_service(name=self.get_env_var('HANA_SERVICE_NAME', 'hana-schema'))
        if hana:
            self.HDB_USER = hana.credentials["user"]
            self.HDB_PASSWORD = hana.credentials["password"]
            self.HDB_HOST = hana.credentials["host"]
            self.HDB_PORT = hana.credentials["port"]
        else:
            raise ValueError("HANA service not found. Please check your environment configuration.")
        """
        
        genai = env.get_service(name=self.get_env_var('AICORE_SERVICE_NAME', 'aicore'))
        if genai:
            self.SAP_PROVIDER_URL = f"{genai.credentials['url']}/oauth/token"
            self.SAP_CLIENT_ID = genai.credentials["clientid"]
            self.SAP_CLIENT_SECRET = genai.credentials["clientsecret"]
            #self.SAP_ENDPOINT_URL_GPT35 = f"{genai.credentials['serviceurls']['AI_API_URL']}/v2/inference/deployments/{self.get_env_var('AZURE_DEPLOYMENT_ID')}/chat/completions?api-version={self.get_env_var('SAP_API_VERSION')}"
            self.SAP_ENDPOINT_URL_GPT4O = f"{genai.credentials['serviceurls']['AI_API_URL']}/v2/inference/deployments/{self.get_env_var('AZURE_DEPLOYMENT_ID_4O')}/chat/completions?api-version={self.get_env_var('SAP_API_VERSION')}"
            #self.SAP_EMBEDDING_ENDPOINT_URL = f"{genai.credentials['serviceurls']['AI_API_URL']}/v2/inference/deployments/{self.get_env_var('AZURE_EMBEDDING_DEPLOYMENT_ID')}/embeddings?api-version={self.get_env_var('SAP_API_VERSION')}"
        else:
            raise ValueError("AI Core service not found. Please check your environment configuration.")

    def get_env_var(self, key, default=None):
        value = os.getenv(key, default)
        if value is None:
            raise ValueError(f"Missing required environment variable: {key}")
        return value
    
    def to_json(self):
        
        data = {key: value for key, value in self.__dict__.items() if key is not None and not key.startswith('__')}
        return json.dumps(data, indent=4)
    
    def print_env(self):
        for key, value in os.environ.items():
            print(f"{key}={value}")
    