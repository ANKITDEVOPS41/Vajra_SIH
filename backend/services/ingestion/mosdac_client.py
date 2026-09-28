import asyncio
import httpx
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MosdacClient:
    def __init__(self, token="DUMMY_TOKEN", max_retries=3):
        self.base_url = "https://mosdac.gov.in/api/v1/"
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }
        self.max_retries = max_retries

    async def fetch_insat_data(self, product_type: str, time_slice: str_):
        url = f"{self.base_url}/data/{product_type}?time={time_slice}"
        
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(url, headers=self.headers, timeout=10.0)
                    if response.status_code == 200:
                        logger.info(f"Successfully fetched {product_type} for {time_slice}")
                        # Return dummy binary data to represent HDF5/GeoTIFF frame
                        return b"dummy_hdf5_or_geotiff_binary_payload"
                    elif response.status_code == 429:
                        # Rate limit reached, exponential backoff
                        backoff = 2 ** attempt
                        logger.warning(f"Rate limited by MOSDAC. Retrying in {backoff} seconds...")
                        await asyncio.sleep(backoff)
                    else:
                        response.raise_for_status()
            except httpx.RequestError as exc:
                logger.error(f"Error fetching data from {exc.request.url!r}.")
                await asyncio.sleep(2 ** attempt)

        raise Exception(f"Failed to fetch data from MOSDAC after {self.max_retries} attempts.")

if __name__ == "__main__":
    async def main():
        client = MosdacClient()
        data = await client.fetch_insat_data("TIR1", "2023-08-10T12:00:00Z")
        print(f"Data length: {len(data)}")
    
    asyncio.run(main())
