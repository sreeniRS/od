import requests
from requests.auth import HTTPBasicAuth
import xmltodict
import json
    # Basic authentication credentials
username = 'DEV_100'
password = 'Nestle1330$'

# Make the request
response = requests.get("http://INAWCONETPUT1.atrapa.deloitte.com:8000/sap/opu/odata/sap/ZSB_PO_GRN/ZC_GRN_PO_DET?$filter=ORDER_NO eq '4500000000'", auth=HTTPBasicAuth(username, password))

print(response.status_code)

# Check if the response is successful
if response.status_code == 200:
    # Convert XML to Python dictionary
    try:
        xml_data = xmltodict.parse(response.text)
        
        # Convert the dictionary to a JSON string
        json_data = json.dumps(xml_data, indent=4)
        
        # Print or work with the JSON data
        print("JSON Output:", json_data)
    except Exception as e:
        print("Error parsing XML:", str(e))
else:
    print(f"Error: Received response with status code {response.status_code}")

