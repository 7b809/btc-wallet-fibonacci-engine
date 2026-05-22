import logging
import requests
from requests.exceptions import (
    HTTPError,
    ConnectionError,
    Timeout,
    RequestException
)


# =========================================================
# LOGGING CONFIG
# =========================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)


# =========================================================
# MAIN FUNCTION
# =========================================================
def get_wallet_info(wallet_address):
    url = "https://api.blockchain.info/explorer-gateway-kt/btc/address"

    headers = {
        "accept": "application/json, text/plain, */*",
        "content-type": "application/json",
        "origin": "https://www.blockchain.com",
        "referer": "https://www.blockchain.com/",
        "user-agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/148.0.0.0 Safari/537.36"
        ),
    }

    payload = {
        "address": wallet_address
    }

    try:
        logger.info("=" * 60)
        logger.info(f"Starting wallet lookup")
        logger.info(f"Wallet Address: {wallet_address}")

        logger.info(f"Sending POST request to: {url}")

        response = requests.post(
            url=url,
            headers=headers,
            json=payload,
            timeout=30
        )

        logger.info(f"Response Status Code: {response.status_code}")

        # Raise HTTP error if status is not 200
        response.raise_for_status()

        logger.info("Successfully received response")

        data = response.json()

        logger.info("Successfully parsed JSON response")

        # # Extract details safely
        # confirmed = data.get("confirmed", 0)
        # unconfirmed = data.get("unconfirmed", 0)
        # utxo = data.get("utxo", 0)
        # tx_count = data.get("txCount", 0)
        # received = data.get("received", 0)

        # logger.info("-" * 60)
        # logger.info(f"Confirmed Balance : {confirmed} satoshi")
        # logger.info(f"Unconfirmed       : {unconfirmed} satoshi")
        # logger.info(f"UTXO Count        : {utxo}")
        # logger.info(f"Transaction Count : {tx_count}")
        # logger.info(f"Total Received    : {received} satoshi")
        # logger.info("-" * 60)

        return data

    except HTTPError as http_err:
        logger.error(f"HTTP ERROR: {http_err}")

        if response is not None:
            logger.error(f"Response Text: {response.text}")

    except ConnectionError as conn_err:
        logger.error(f"CONNECTION ERROR: {conn_err}")

    except Timeout as timeout_err:
        logger.error(f"TIMEOUT ERROR: {timeout_err}")

    except ValueError as json_err:
        logger.error(f"JSON PARSE ERROR: {json_err}")

    except RequestException as req_err:
        logger.error(f"REQUEST ERROR: {req_err}")

    except Exception as e:
        logger.exception(f"UNEXPECTED ERROR: {e}")

    return None


# # =========================================================
# # EXAMPLE USAGE
# # =========================================================
# if __name__ == "__main__":

#     wallet = "bc1qn2cpj0hrl37wqh5q94kwrlhtj2lx8ahtw7ef5rg35tswxsqtvufqfmmrq2"

#     result = get_wallet_info(wallet)

#     if result:
#         print("\nFINAL RESPONSE:")
#         print(result)
#     else:
#         print("\nFailed to fetch wallet data.")