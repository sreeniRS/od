# Make the request
import requests
from requests.auth import HTTPBasicAuth
import xml.etree.ElementTree as ET

# Basic authentication credentials
username = 'DEV_100'
password = 'Nestle1330$'

# Root element for the concatenated XML
root = ET.Element("root")

skip_token = 100
request = f"http://INAWCONETPUT1.atrapa.deloitte.com:8000/sap/opu/odata/sap/ZSB_PO_GRN/ZC_GRN_PO_DET?$skiptoken({skip_token})"
# Loop through responses while status code is not 400
while requests.get(request, auth=HTTPBasicAuth(username, password)).status_code != 400 and skip_token:
    response = requests.get("http://INAWCONETPUT1.atrapa.deloitte.com:8000/sap/opu/odata/sap/ZSB_PO_GRN/ZC_GRN_PO_DET?", auth=HTTPBasicAuth(username, password))
    
    # Parse the XML content
    response_xml = ET.fromstring(response.text)
    
    # Add the response's root elements to the main root element
    for element in response_xml:
        root.append(element)
    
    skip_token+=100

# Convert the concatenated XML to a string and save to a file
tree = ET.ElementTree(root)
tree.write("concatenated_output.xml")

print("Concatenated XML data has been saved to concatenated_output.xml")

root = ET.fromstring(response.text)
with open('./root.xml', 'w') as f:
    f.write(response.text)

# print(response.status_code)

# # Check if the response is successful
# if response.status_code == 200:
#     # Convert XML to Python dictionary
#     try:
#         xml_data = xmltodict.parse(response.text)
        
#         # Convert the dictionary to a JSON string
#         json_data = json.dumps(xml_data, indent=4)
        
#         # Print or work with the JSON data
#         print("JSON Output:", json_data)
#     except Exception as e:
#         print("Error parsing XML:", str(e))
# else:
#     print(f"Error: Received response with status code {response.status_code}")

