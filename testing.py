import requests
from requests.auth import HTTPBasicAuth
    # Basic authentication credentials
username = 'DEV_100'
password = 'Nestle1330$'
    # Make the request
response = requests.get("http://INAWCONETPUT1.atrapa.deloitte.com:8000/sap/opu/odata/sap/ZSB_PO_GRN/ZC_GRN_PO_DET", auth=HTTPBasicAuth(username, password))

print(response)

