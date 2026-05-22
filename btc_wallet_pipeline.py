import os
import json
import logging
import requests
import concurrent.futures

from hashlib import sha256
from datetime import datetime

from pymongo import MongoClient

from bip_utils import (
    Bip39MnemonicGenerator,
    Bip39Languages,
)

from btc_address_generator import generate_bitcoin_addresses
from check_bal import get_wallet_info

from dotenv import load_dotenv

load_dotenv()

# =========================================================
# LOGGING CONFIG
# =========================================================
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)

logger.info("STEP 1 => SCRIPT STARTED")

# =========================================================
# MONGODB CONFIG
# =========================================================
logger.info("STEP 2 => LOADING MONGODB CONFIG")

MONGO_URI = os.getenv("MONGO_URI")

DB_NAME = "btc_wallets"

STATE_COLLECTION = "generator_state"

RESULT_COLLECTION = "generated_wallets"

POSITIVE_BALANCE_COLLECTION = "positive_balance_wallets"

logger.info(f"MONGO URI FOUND => {bool(MONGO_URI)}")

# =========================================================
# TELEGRAM CONFIG
# =========================================================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# =========================================================
# CONNECT MONGODB
# =========================================================
logger.info("STEP 3 => CONNECTING MONGODB")

client = MongoClient(MONGO_URI)

db = client[DB_NAME]

state_col = db[STATE_COLLECTION]

result_col = db[RESULT_COLLECTION]

positive_bal_col = db[POSITIVE_BALANCE_COLLECTION]

logger.info("STEP 4 => MONGODB CONNECTED")

# =========================================================
# LOAD WORD LIST JSON
# =========================================================
logger.info("STEP 5 => LOADING bip39_words.json")

with open("bip39_words.json", "r", encoding="utf-8") as file:

    WORD_DATA = json.load(file)

logger.info(f"STEP 6 => WORD DATA LOADED => " f"{len(WORD_DATA)} languages")

# =========================================================
# LANGUAGE MAP
# =========================================================
logger.info("STEP 7 => CREATING LANGUAGE MAP")

LANGUAGE_MAP = {
    "english": Bip39Languages.ENGLISH,
    "korean": Bip39Languages.KOREAN,
    "spanish": Bip39Languages.SPANISH,
    "chinese_simplified": Bip39Languages.CHINESE_SIMPLIFIED,
    "chinese_traditional": Bip39Languages.CHINESE_TRADITIONAL,
    "french": Bip39Languages.FRENCH,
    "italian": Bip39Languages.ITALIAN,
    "czech": Bip39Languages.CZECH,
    "portuguese": Bip39Languages.PORTUGUESE,
}

logger.info(f"STEP 8 => SUPPORTED LANGUAGES => " f"{list(LANGUAGE_MAP.keys())}")


# =========================================================
# TELEGRAM MESSAGE
# =========================================================
def send_telegram_message(message):

    try:

        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:

            logger.warning("TELEGRAM CONFIG MISSING")

            return

        url = f"https://api.telegram.org/bot" f"{TELEGRAM_BOT_TOKEN}" f"/sendMessage"

        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
        }

        response = requests.post(url, json=payload, timeout=30)

        logger.info(f"TELEGRAM SENT => " f"{response.status_code}")

    except Exception as e:

        logger.exception(f"TELEGRAM FAILED => {e}")


# =========================================================
# SAVE POSITIVE BALANCE
# =========================================================
def save_positive_wallet(data):

    try:

        positive_bal_col.insert_one(data)

        logger.info("POSITIVE WALLET SAVED")

    except Exception as e:

        logger.exception(f"SAVE FAILED => {e}")


# =========================================================
# CHECK SINGLE ADDRESS
# =========================================================
def check_single_address(fib_index, fib_number, language, word_length, address):

    try:

        logger.info(f"CHECKING ADDRESS => " f"{address}")

        result = get_wallet_info(address)

        confirmed = result.get("confirmed", 0)

        unconfirmed = result.get("unconfirmed", 0)

        total_balance = confirmed + unconfirmed

        logger.info(f"BALANCE => " f"{total_balance}")

        if total_balance > 0:

            logger.info(f"POSITIVE BALANCE FOUND => " f"{address}")

            save_data = {
                "fib_index": fib_index,
                "fib_number": str(fib_number),
                "language": language,
                "word_length": word_length,
                "address": address,
                "wallet_data": result,
                "created_at": datetime.utcnow(),
            }

            save_positive_wallet(save_data)

            message = (
                f"BALANCE FOUND\n\n"
                f"Fib Index: "
                f"{fib_index}\n"
                f"Fib Number: "
                f"{fib_number}\n"
                f"Language: "
                f"{language}\n"
                f"Words: "
                f"{word_length}\n\n"
                f"Address:\n"
                f"{address}\n\n"
                f"Confirmed: "
                f"{confirmed}\n"
                f"Unconfirmed: "
                f"{unconfirmed}\n"
                f"TX Count: "
                f"{result.get('txCount')}\n"
                f"Received: "
                f"{result.get('received')}"
            )

            send_telegram_message(message)

        else:

            logger.info(f"NO BALANCE => " f"{address}")

    except Exception as e:

        logger.exception(f"ADDRESS CHECK FAILED => " f"{address} => {e}")


# =========================================================
# FIBONACCI GENERATOR
# =========================================================
def fibonacci(start_index=1):

    logger.info(f"FIBONACCI GENERATOR STARTED => " f"StartIndex={start_index}")

    a = 0
    b = 1

    current_index = 1

    while True:

        if current_index >= start_index:

            logger.info(f"YIELDING => " f"Index={current_index} | " f"Fib={b}")

            yield current_index, b

        a, b = b, a + b

        current_index += 1


# =========================================================
# GENERATE ENTROPY
# =========================================================
def fibonacci_to_entropy(fib_number, entropy_bytes=16):

    logger.info(f"GENERATING ENTROPY => " f"Fib={fib_number}")

    fib_bytes = str(fib_number).encode()

    hashed = sha256(fib_bytes).digest()

    entropy = hashed[:entropy_bytes]

    logger.info(f"ENTROPY GENERATED => " f"{len(entropy)} bytes")

    return entropy


# =========================================================
# GENERATE MNEMONIC
# =========================================================
def generate_mnemonic_from_fibonacci(fib_number, language="english", words=12):

    logger.info(
        f"GENERATING MNEMONIC => " f"Fib={fib_number} | " f"Language={language}"
    )

    entropy_size_map = {
        12: 16,
        15: 20,
        18: 24,
        21: 28,
        24: 32,
    }

    entropy_bytes = entropy_size_map[words]

    logger.info(f"ENTROPY BYTES => " f"{entropy_bytes}")

    entropy = fibonacci_to_entropy(fib_number, entropy_bytes)

    mnemonic = Bip39MnemonicGenerator(LANGUAGE_MAP[language]).FromEntropy(entropy)

    mnemonic = str(mnemonic)

    logger.info(f"MNEMONIC GENERATED => " f"{language}")

    return mnemonic


# =========================================================
# SAVE CURRENT STATE
# =========================================================
def save_current_state(current_index, fib_number):

    logger.info(f"SAVING STATE => " f"Index={current_index}")

    state_data = {
        "_id": "wallet_generator_state",
        "current_index": current_index,
        "fib_number": str(fib_number),
        "updated_at": datetime.utcnow(),
    }

    state_col.replace_one({"_id": "wallet_generator_state"}, state_data, upsert=True)

    logger.info("STATE SAVED SUCCESSFULLY")


# =========================================================
# LOAD LAST STATE
# =========================================================
def load_last_state():

    logger.info("LOADING LAST STATE")

    state = state_col.find_one({"_id": "wallet_generator_state"})

    if state:

        logger.info(f"LAST STATE FOUND => " f"{state['current_index']}")

        return state["current_index"]

    logger.info("NO PREVIOUS STATE FOUND")

    return 1


# =========================================================
# SAVE GENERATED RESULT
# =========================================================
def save_wallet_result(fib_index, fib_number, addresses_object):

    logger.info(f"SAVING RESULT => " f"FibIndex={fib_index}")

    document = {
        "fib_index": fib_index,
        "fib_number": str(fib_number),
        "addresses": addresses_object,
        "created_at": datetime.utcnow(),
    }

    result_col.insert_one(document)

    logger.info("RESULT SAVED SUCCESSFULLY")


# =========================================================
# MAIN GENERATOR
# =========================================================
def generate_wallets(
    start_index=None,
    stop_fib_number=None,
    languages=None,
    words=12,
    sleep_between_fib=10,  # <-- ADDED SLEEP CONTROL
):

    logger.info("MAIN GENERATOR STARTED")

    if languages is None:

        logger.info("NO LANGUAGES PROVIDED")

        languages = list(LANGUAGE_MAP.keys())

    logger.info(f"LANGUAGES => {languages}")

    if start_index is None:

        logger.info("START INDEX NONE => LOADING FROM DB")

        start_index = load_last_state()

    logger.info(f"START INDEX => {start_index}")

    fib_gen = fibonacci(start_index)

    logger.info("FIB GENERATOR CREATED")

    try:

        logger.info("ENTERING MAIN LOOP")

        while True:

            logger.info("GETTING NEXT FIB NUMBER")

            fib_index, fib_number = next(fib_gen)

            logger.info(f"CURRENT => Index={fib_index} | Fib={fib_number}")

            if stop_fib_number is not None and fib_number > stop_fib_number:

                logger.info(f"STOP LIMIT REACHED => {fib_number}")

                break

            logger.info("CREATING RESULT OBJECT")

            all_language_addresses = {}

            for language in languages:

                logger.info("=" * 60)

                logger.info(f"START LANGUAGE => {language}")

                for word_length in [12, 15, 18, 21, 24]:

                    logger.info(
                        f"GENERATING => "
                        f"Language={language} | "
                        f"Words={word_length}"
                    )

                    mnemonic = generate_mnemonic_from_fibonacci(
                        fib_number=fib_number, language=language, words=word_length
                    )

                    logger.info(f"GENERATING ADDRESSES => {language}")

                    addresses = generate_bitcoin_addresses(mnemonic)

                    logger.info(f"ADDRESSES GENERATED => {language}")

                    address_list = list(addresses.values())

                    logger.info(f"TOTAL ADDRESSES => {len(address_list)}")

                    if language not in all_language_addresses:

                        all_language_addresses[language] = {}

                    all_language_addresses[language][str(word_length)] = address_list

                    logger.info("STARTING BALANCE CHECK")

                    with concurrent.futures.ThreadPoolExecutor(
                        max_workers=10
                    ) as executor:

                        futures = []

                        for address in address_list:

                            future = executor.submit(
                                check_single_address,
                                fib_index,
                                fib_number,
                                language,
                                word_length,
                                address,
                            )

                            futures.append(future)

                        concurrent.futures.wait(futures)

                    logger.info(
                        f"BALANCE CHECK COMPLETED => " f"{language} | {word_length}"
                    )

                    logger.info(f"COMPLETED => " f"{language} | {word_length} words")

            logger.info("SAVING COMPLETE RESULT")

            save_wallet_result(
                fib_index=fib_index,
                fib_number=fib_number,
                addresses_object=all_language_addresses,
            )

            logger.info("SAVING CURRENT STATE")

            save_current_state(current_index=fib_index, fib_number=fib_number)

            logger.info(f"ROUND COMPLETED => Fib={fib_number}")

            # =================================================
            # SLEEP BETWEEN EACH FIBONACCI INDEX
            # =================================================
            logger.info(
                f"SLEEPING FOR {sleep_between_fib} SECONDS "
                f"BEFORE NEXT FIBONACCI INDEX"
            )

            time.sleep(sleep_between_fib)

    except KeyboardInterrupt:

        logger.warning("MANUALLY STOPPED")

        save_current_state(current_index=fib_index, fib_number=fib_number)

    except Exception as e:

        logger.exception(f"GENERATOR CRASHED => {e}")

        save_current_state(current_index=fib_index, fib_number=fib_number)


# =========================================================
# RUN
# =========================================================
if __name__ == "__main__":

    logger.info("STARTING APPLICATION")

    generate_wallets(
        start_index=None,
        stop_fib_number=None,
        languages=[
            "english",
            "spanish",
            "french",
            "italian",
            "korean",
            "portuguese",
            "czech",
            "chinese_simplified",
            "chinese_traditional",
        ],
        words=12,
        sleep_between_fib=10,  # <-- CHANGE THIS VALUE
    )

    logger.info("APPLICATION FINISHED")
