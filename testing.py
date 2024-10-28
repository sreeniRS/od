# # Make the request
# import requests
# from requests.auth import HTTPBasicAuth
# import xml.etree.ElementTree as ET

# # Basic authentication credentials
# username = 'DEV_100'
# password = 'Nestle1330$'

# # Root element for the concatenated XML
# root = ET.Element("root")

# skip_token = 100
# request = f"http://INAWCONETPUT1.atrapa.deloitte.com:8000/sap/opu/odata/sap/ZSB_PO_GRN/ZC_GRN_PO_DET?$skiptoken({skip_token})"
# # Loop through responses while status code is not 400
# while requests.get(request, auth=HTTPBasicAuth(username, password)).status_code != 400 and skip_token:
#     response = requests.get("http://INAWCONETPUT1.atrapa.deloitte.com:8000/sap/opu/odata/sap/ZSB_PO_GRN/ZC_GRN_PO_DET?", auth=HTTPBasicAuth(username, password))
    
#     # Parse the XML content
#     response_xml = ET.fromstring(response.text)
    
#     # Add the response's root elements to the main root element
#     for element in response_xml:
#         root.append(element)
    
#     skip_token+=100

# # Convert the concatenated XML to a string and save to a file
# tree = ET.ElementTree(root)
# tree.write("concatenated_output.xml")

# print("Concatenated XML data has been saved to concatenated_output.xml")

# root = ET.fromstring(response.text)
# with open('./root.xml', 'w') as f:
#     f.write(response.text)

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



import requests
from requests.auth import HTTPBasicAuth
from fastapi import HTTPException

def call_odata_query(endpoint: str):
    # Basic authentication credentials
    username = 'RT_F_002'
    password = 'Teched@2024'
    # Make the request
    response = requests.get(endpoint, auth=HTTPBasicAuth(username, password))
    print(response.status_code)

    if response.status_code == 200:
        try:
            # Attempt to parse JSON content
            json_response = response.json()
            return json_response
        except ValueError:  # If JSON decoding fails
            print("Error: Response is not in JSON format.")
            raise HTTPException(status_code=500, detail="Response is not in JSON format")
    else:
        print(f"Error: Received response with status code {response.status_code}")
        print(response.text)
        raise HTTPException(status_code=response.status_code, detail="Error fetching OData")

    
result = f"$filter=CreateDate ge '20231001' and CreateDate le '20231231'"
endpoint = f"http://INAWCONETPUT1.atrapa.deloitte.com:8000/sap/opu/odata4/sap/zsb_po_grn_sb4/srvd_a2x/sap/zsd_po_grn_det/0001/ZC_GRN_PO_DET?"
api_url = endpoint + result + f"&$count=True"
    
# print(api_url)
    
# response_content = call_odata_query(api_url)

# print(response_content)  

# Okay so far, I have a working input of retrieving the response but that happens to have 2999 values within the array.
# Now I need to work on making this call asynchronous
# Using a simple for loop. How does it work
import datetime
import json

username = 'RT_F_002'
password = 'Teched@2024'

skiptoken = 100
response = requests.get(f"{api_url}&skiptoken={skiptoken}", auth=HTTPBasicAuth(username, password))
value = []
#need to keep a copy of a json file and then append the values section.

time = datetime.datetime.now()
while response.status_code != 400 and skiptoken < response.json().get("@odata.count", 101):
    try:
        print(skiptoken)
        data = response.json()  # Parse JSON response
        if "value" in data:
            value.extend(data["value"])  # Append the 'value' list from each response

        # Update the skiptoken for the next page request
        skiptoken += 100
        response = requests.get(f"{api_url}&skiptoken={skiptoken}", auth=HTTPBasicAuth(username, password))
    except Exception as e:
        print(f"An error occurred: {e}")
        break

string = json.dumps(value, indent=4)
# all_data now contains the aggregated results
with open('./values.json', 'w') as f:
    f.write(string)
wall_time = datetime.datetime.now()- time
print(wall_time) # It takes a linear complexity of O(n). 11 seconds for 3000 rows
