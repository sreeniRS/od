import os
from os.path import join, dirname, exists
from dotenv import load_dotenv
from cfenv import AppEnv
import json

class AppConfig:
    def __init__(self):
        #Prints the variables provided by User
        dotenv_path = join(dirname(__file__),'../..', '.env')
        if exists(dotenv_path):
            load_dotenv(dotenv_path=dotenv_path)
        else:
            print(f"Warning: .env file not found at {dotenv_path}")

        self.LOCAL_ENV = os.getenv("ENV", "PROD").upper() == "LOCAL"

        if self.LOCAL_ENV:
            self._load_local_env()
        else:
            self._load_production_env()

    def _load_local_env(self):
        self._load_common_env()
        # POSTGRES Details for local environment
        # self.DB_CONN_URL = self.get_env_var("DB_CONN_URL")
        self.SAP_PROVIDER_URL = self.get_env_var("SAP_PROVIDER_URL")
        self.SAP_CLIENT_ID = self.get_env_var("SAP_CLIENT_ID")
        self.SAP_CLIENT_SECRET = self.get_env_var("SAP_CLIENT_SECRET")
        self.SAP_ENDPOINT_URL_GPT4O = self.get_env_var("SAP_ENDPOINT_URL_GPT4O")
        self.SAP_EMBEDDING_ENDPOINT_URL = self.get_env_var("SAP_EMBEDDING_ENDPOINT_URL")
        self.HDB_USER = self.get_env_var("HDB_USER")
        self.HDB_HOST = self.get_env_var("HDB_HOST")
        self.HDB_PASSWORD = self.get_env_var("HDB_PASSWORD")
        self.HDB_PORT = self.get_env_var("HDB_PORT")

    def _load_production_env(self):
        cenv = AppEnv()
        self._load_common_env()

        hana = cenv.get_service(name=os.getenv("HANA_SERVICE_NAME", 'hdb-schema'))
        if hana:
            self.HDB_USER = hana.credentials["user"]
            self.HDB_PASSWORD = hana.credentials["password"]
            self.HDB_HOST = hana.credentials["host"]
            self.HDB_PORT = hana.credentials["port"]
        else:
            raise ValueError("HANA service not found. Please check your environment configuration.")

        genai = cenv.get_service(name=os.getenv("AICORE_SERVICE_NAME", "aicore"))
        if genai:
            self.SAP_PROVIDER_URL = f"{genai.credentials['url']}/oauth/token"
            self.SAP_CLIENT_ID = genai.credentials["clientid"]
            self.SAP_CLIENT_SECRET = genai.credentials["clientsecret"]
            
            #Model Endpoints
            # self.SAP_ENDPOINT_URL_GPT35 = f"{genai.credentials['serviceurls']['AI_API_URL']}/v2/inference/deployments/{self.get_env_var('AZURE_DEPLOYMENT_ID')}/chat/completions?api-version={self.SAP_API_VERSION}"
            self.SAP_ENDPOINT_URL_GPT4O = f"{genai.credentials['serviceurls']['AI_API_URL']}/v2/inference/deployments/{self.get_env_var('AZURE_DEPLOYMENT_ID_4O')}/chat/completions?api-version={self.SAP_API_VERSION}"
            
            #Embedding Endpoints
            self.SAP_EMBEDDING_ENDPOINT_URL = f"{genai.credentials['serviceurls']['AI_API_URL']}/v2/inference/deployments/{self.get_env_var('AZURE_EMBEDDING_DEPLOYMENT_ID')}/embeddings?api-version={self.SAP_API_VERSION}"
        else:
            raise ValueError("AI Core service not found. Please check your environment configuration.")

    def _load_common_env(self):
        # Common SAP GPT Details
        # self.SAP_GPT35_MODEL = self.get_env_var("SAP_GPT35_MODEL")
        # self.SAP_GPT35_MAX_TOKENS = self.get_env_var("SAP_GPT35_MAX_TOKENS")
        self.SAP_GPT4O_MODEL = self.get_env_var("SAP_GPT4O_MODEL")
        self.SAP_API_VERSION = self.get_env_var("API_VERSION", "2023-05-15")
        self.LEEWAY = self.get_env_var("LEEWAY")

    def get_env_var(self, key, default=None):
        value = os.getenv(key, default)
        if value is None:
            raise ValueError(f"Missing required environment variable: {key}")
        return value
    
    def _print_env(self):
        for key, value in os.environ.items():
            print(f"{key}={value}")

    def to_json(self):
        data = self.__dict__.copy()
        return json.dumps(data, indent=4)
    

if __name__ == "__main__":
    app = AppConfig()
    print(f"If LOCAL? : {app.LOCAL_ENV}")