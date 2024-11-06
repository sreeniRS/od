import time
from fastapi import HTTPException
import asyncio
from aiohttp import ClientSession, BasicAuth
from concurrent.futures import ThreadPoolExecutor
from src.utils.appconfig import get_config_instance


config = get_config_instance()

async def fetch_data(session, url):
    async with session.get(url) as response:
        if response.status == 200:
            try:
                return await response.json()
            except Exception:
                print("Error: Response is not in JSON format.")
                raise HTTPException(status_code=500, detail="Response is not in JSON format")
        else:
            print(f"Error: Received response with status code {response.status}")
            raise HTTPException(status_code=response.status, detail="Error fetching OData")

async def call_odata_query(endpoint: str):
    aggregated_data = []
    skiptoken = 0
    total_count = None  # Will be set to @odata.count from the first response
    batch_size = 5  # Number of requests to send concurrently

    if config.LOCAL_ENV:
        auth = BasicAuth(config.ODATA_USERNAME, config.ODATA_PASSWORD)
        headers = None
    else:
        headers = config.ODATA_HEADERS
        auth = None

    async with ClientSession(auth = auth, headers=headers) as session:
        while True:
            # Create batch of requests
            tasks = [
                fetch_data(session, f"{endpoint}&$skip={skiptoken + i * 100}")
                for i in range(batch_size)
            ]
            responses = await asyncio.gather(*tasks)

            for response_data in responses:
                if response_data:
                    # Initialize total_count from the first response
                    if total_count is None and "@odata.count" in response_data:
                        total_count = response_data["@odata.count"]

                    # Append values if they exist in the response
                    if "value" in response_data:
                        aggregated_data.extend(response_data["value"])

                    # Stop fetching if skiptoken exceeds total_count
                    if total_count is not None and skiptoken >= total_count:
                        break

            # Move to the next set of data by increasing skiptoken by batch_size * 100
            skiptoken += batch_size * 100

            # Stop if all data has been fetched
            if total_count is not None and skiptoken >= total_count:
                break

    return aggregated_data

def run_fetch_data(api_url):
    return asyncio.run(call_odata_query(api_url))


def call_odata(filter: str):
    # Get the username and password from the config
    endpoint = config.ODATA_ENDPOINT

    api_url = endpoint + filter
    # Using ThreadPolExecutor for running async function in a synchronous context
    with ThreadPoolExecutor(max_workers=5) as executor:
        # Track start time
        start_time = time.time()

        # Call the async function
        future = executor.submit(run_fetch_data, api_url)
        response_content = future.result()  # Get the result of the future

        # Print wall time
        wall_time = time.time() - start_time
        print(f"Total execution time: {wall_time:.2f} seconds")
        
    return response_content