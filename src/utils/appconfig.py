import os
from os.path import join, dirname, exists
from dotenv import load_dotenv
from cfenv import AppEnv
import json, base64, requests

config_instance = None

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
        
        self.ODATA_USERNAME = self.get_env_var("ODATA_USERNAME")
        self.ODATA_PASSWORD = self.get_env_var("ODATA_PASSWORD")
        self.ODATA_ENDPOINT = self.get_env_var("ODATA_ENDPOINT")

    def _load_production_env(self):
        cenv = AppEnv()
        self._load_common_env()

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
        
        #Setting up the Destination service variable
        destination_service = cenv.get_service(name = "odata-service")
        destination_name = "odata-service"

        if destination_service:
            client_url = destination_service.credentials['clientid']+":"+ destination_service.credentials["clientsecret"]
            basic_auth_header = 'Basic ' + base64.b64encode(client_url.encode()).decode()
            self.ODATA_HEADERS = {'Authorization': basic_auth_header}
            r = requests.get(destination_service.credentials["uri"] + '/destination-configuration/v1/destinations/' + destination_name, headers=self.ODATA_HEADERS)
            
            #get the details of auth
            destination = r.json()
            self.ODATA_ENDPOINT = destination["destinationConfiguration"]["URL"] + "/secure/"
        else:
            raise ValueError("Desination Service Not Found. Please Check your Configurations")

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
    
def get_config_instance():
       global config_instance
       if config_instance is None:
            config_instance = AppConfig()
       
       return config_instance

if __name__ == "__main__":
    app = get_config_instance()
    print(f"If LOCAL? : {app.LOCAL_ENV}")