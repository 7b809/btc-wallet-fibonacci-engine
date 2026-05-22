import logging
import time
import requests
from requests.exceptions import HTTPError, ConnectionError, Timeout, RequestException

# =========================================================
# LOGGING CONFIG
# =========================================================
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)

# =========================================================
# CONFIG
# =========================================================
URL = "https://api.blockchain.info/explorer-gateway-kt/btc/address"

HEADERS = {
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


# =========================================================
# SINGLE REQUEST FUNCTION
# =========================================================
def get_wallet_info(wallet_address):

    payload = {"address": wallet_address}

    try:
        response = requests.post(url=URL, headers=HEADERS, json=payload, timeout=30)

        logger.info(f"Status Code: {response.status_code}")

        response.raise_for_status()

        data = response.json()

        return {"success": True, "status_code": response.status_code, "data": data}

    except HTTPError as http_err:

        logger.error(f"HTTP ERROR: {http_err}")

        return {
            "success": False,
            "status_code": response.status_code if response else None,
            "error": str(http_err),
        }

    except ConnectionError as conn_err:

        logger.error(f"CONNECTION ERROR: {conn_err}")

        return {"success": False, "error": str(conn_err)}

    except Timeout as timeout_err:

        logger.error(f"TIMEOUT ERROR: {timeout_err}")

        return {"success": False, "error": str(timeout_err)}

    except RequestException as req_err:

        logger.error(f"REQUEST ERROR: {req_err}")

        return {"success": False, "error": str(req_err)}

    except Exception as e:

        logger.exception(f"UNEXPECTED ERROR: {e}")

        return {"success": False, "error": str(e)}


# =========================================================
# BATCH TEST FUNCTION
# =========================================================
def test_request_limit(
    wallet_address,
    total_requests=50,
    batch_size=10,
    delay_between_requests=0.5,
    delay_between_batches=5,
):

    logger.info("=" * 80)
    logger.info("STARTING RATE LIMIT TEST")
    logger.info("=" * 80)

    logger.info(f"Wallet Address       : {wallet_address}")
    logger.info(f"Total Requests       : {total_requests}")
    logger.info(f"Batch Size           : {batch_size}")
    logger.info(f"Delay Per Request    : {delay_between_requests} sec")
    logger.info(f"Delay Between Batch  : {delay_between_batches} sec")

    success_count = 0
    fail_count = 0

    request_number = 0

    start_time = time.time()

    # =====================================================
    # LOOP THROUGH BATCHES
    # =====================================================
    for batch_start in range(0, total_requests, batch_size):

        batch_number = (batch_start // batch_size) + 1

        logger.info("\n")
        logger.info("=" * 60)
        logger.info(f"STARTING BATCH {batch_number}")
        logger.info("=" * 60)

        # =================================================
        # LOOP INSIDE EACH BATCH
        # =================================================
        for _ in range(batch_size):

            request_number += 1

            if request_number > total_requests:
                break

            logger.info("\n")
            logger.info("-" * 60)
            logger.info(f"REQUEST {request_number}/{total_requests}")
            logger.info("-" * 60)

            result = get_wallet_info(wallet_address)

            if result["success"]:

                success_count += 1

                logger.info("REQUEST SUCCESS")

                data = result["data"]

                logger.info(f"Confirmed: {data.get('confirmed')}")

                logger.info(f"Tx Count: {data.get('txCount')}")

            else:

                fail_count += 1

                logger.error("REQUEST FAILED")

                logger.error(f"Error: {result.get('error')}")

                # Check for rate limit
                if result.get("status_code") == 429:

                    logger.warning("RATE LIMIT DETECTED (429)")

            # Delay between requests
            time.sleep(delay_between_requests)

        # =================================================
        # BATCH COMPLETED
        # =================================================
        logger.info("\n")
        logger.info("=" * 60)
        logger.info(f"BATCH {batch_number} COMPLETED")
        logger.info("=" * 60)

        logger.info(f"Current Success: {success_count}")
        logger.info(f"Current Failed : {fail_count}")

        # Delay between batches
        if request_number < total_requests:

            logger.info(
                f"Sleeping {delay_between_batches} sec " f"before next batch..."
            )

            time.sleep(delay_between_batches)

    # =====================================================
    # FINAL SUMMARY
    # =====================================================
    end_time = time.time()

    total_time = round(end_time - start_time, 2)

    logger.info("\n")
    logger.info("=" * 80)
    logger.info("FINAL SUMMARY")
    logger.info("=" * 80)

    logger.info(f"Total Requests : {total_requests}")
    logger.info(f"Success Count  : {success_count}")
    logger.info(f"Failed Count   : {fail_count}")
    logger.info(f"Total Time     : {total_time} sec")

    success_rate = round((success_count / total_requests) * 100, 2)

    logger.info(f"Success Rate   : {success_rate}%")

    logger.info("=" * 80)


# =========================================================
# MAIN
# =========================================================
if __name__ == "__main__":

    wallet = "bc1qn2cpj0hrl37wqh5q94kwrlhtj2lx8ahtw7ef5rg35tswxsqtvufqfmmrq2"

    test_request_limit(
        wallet_address=wallet,
        total_requests=100,  # Total requests
        batch_size=20,  # 10 requests per batch
        delay_between_requests=0.2,  # Delay between each request
        delay_between_batches=3,  # Delay after each batch
    )
