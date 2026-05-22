import os
import json
import time
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
# SAVE STATE INTERVAL
# =========================================================
STATE_SAVE_INTERVAL = 100

# =========================================================
# GLOBAL COUNTERS
# =========================================================
TOTAL_SCANNED = 0

TOTAL_CONFIRMED_FOUND = 0


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
# SERIAL NUMBER TO ENTROPY
# =========================================================
def serial_to_entropy(serial_number, entropy_bytes=16):

    logger.info(f"GENERATING ENTROPY => " f"Serial={serial_number}")

    serial_bytes = str(serial_number).encode()

    hashed = sha256(serial_bytes).digest()

    entropy = hashed[:entropy_bytes]

    logger.info(f"ENTROPY GENERATED => " f"{len(entropy)} bytes")

    return entropy


# =========================================================
# GENERATE MNEMONIC
# =========================================================
def generate_mnemonic_from_serial(serial_number, language="english", words=12):

    logger.info(
        f"GENERATING MNEMONIC => " f"Serial={serial_number} | " f"Language={language}"
    )

    entropy_size_map = {
        12: 16,
        15: 20,
        18: 24,
        21: 28,
        24: 32,
    }

    entropy_bytes = entropy_size_map[words]

    entropy = serial_to_entropy(serial_number, entropy_bytes)

    mnemonic = Bip39MnemonicGenerator(LANGUAGE_MAP[language]).FromEntropy(entropy)

    mnemonic = str(mnemonic)

    logger.info(f"MNEMONIC GENERATED => " f"{language}")

    return mnemonic


# =========================================================
# SAVE CURRENT STATE
# =========================================================
def save_current_state(current_serial):

    logger.info(f"SAVING STATE => " f"Serial={current_serial}")

    state_data = {
        "_id": "wallet_generator_state",
        "current_serial": current_serial,
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

        logger.info(f"LAST STATE FOUND => " f"{state['current_serial']}")

        return state["current_serial"]

    logger.info("NO PREVIOUS STATE FOUND")

    return 1


# =========================================================
# CHECK SINGLE ADDRESS
# =========================================================
def check_single_address(serial_number, language, word_length, address, mnemonic):

    global TOTAL_SCANNED
    global TOTAL_CONFIRMED_FOUND

    try:

        TOTAL_SCANNED += 1

        logger.info(f"CHECKING ADDRESS => " f"{address}")

        result = get_wallet_info(address)

        confirmed = result.get("confirmed", 0)

        unconfirmed = result.get("unconfirmed", 0)

        logger.info(f"CONFIRMED => {confirmed} | " f"UNCONFIRMED => {unconfirmed}")

        # =================================================
        # SAVE ONLY IF CONFIRMED BALANCE > 0
        # =================================================
        if confirmed > 0:

            TOTAL_CONFIRMED_FOUND += 1

            logger.info(f"CONFIRMED POSITIVE BALANCE FOUND => " f"{address}")

            save_data = {
                "serial_number": serial_number,
                "language": language,
                "word_length": word_length,
                "mnemonic": mnemonic,
                "address": address,
                "wallet_data": result,
                "created_at": datetime.utcnow(),
            }

            save_positive_wallet(save_data)

            message = (
                f"CONFIRMED BALANCE FOUND\n\n"
                f"Serial Number: {serial_number}\n"
                f"Language: {language}\n"
                f"Words: {word_length}\n\n"
                f"Address:\n"
                f"{address}\n\n"
                f"Confirmed: {confirmed}\n"
                f"Unconfirmed: {unconfirmed}\n"
                f"TX Count: {result.get('txCount')}\n"
                f"Received: {result.get('received')}\n\n"
                f"TOTAL SCANNED: {TOTAL_SCANNED}\n"
                f"TOTAL CONFIRMED FOUND: "
                f"{TOTAL_CONFIRMED_FOUND}"
            )

            send_telegram_message(message)

        else:

            logger.info(f"NO CONFIRMED BALANCE => " f"{address}")

    except Exception as e:

        logger.exception(f"ADDRESS CHECK FAILED => " f"{address} => {e}")


# =========================================================
# SEND INTERVAL STATUS
# =========================================================
def send_interval_status(current_serial):

    try:

        message = (
            f"SCANNING STATUS UPDATE\n\n"
            f"CURRENT SERIAL: {current_serial}\n"
            f"TOTAL ADDRESSES SCANNED: "
            f"{TOTAL_SCANNED}\n"
            f"TOTAL CONFIRMED BALANCES FOUND: "
            f"{TOTAL_CONFIRMED_FOUND}\n\n"
            f"STATUS: RUNNING"
        )

        send_telegram_message(message)

        logger.info("INTERVAL STATUS MESSAGE SENT")

    except Exception as e:

        logger.exception(f"FAILED TO SEND STATUS => {e}")


# =========================================================
# MAIN GENERATOR
# =========================================================
def generate_wallets(
    start_serial=None,
    stop_serial=None,
    languages=None,
    sleep_between_serial=10,
):

    logger.info("MAIN GENERATOR STARTED")

    if languages is None:

        logger.info("NO LANGUAGES PROVIDED")

        languages = list(LANGUAGE_MAP.keys())

    logger.info(f"LANGUAGES => {languages}")

    if start_serial is None:

        logger.info("START SERIAL NONE => " "LOADING FROM DB")

        start_serial = load_last_state()

    logger.info(f"START SERIAL => {start_serial}")

    current_serial = start_serial

    try:

        logger.info("ENTERING MAIN LOOP")

        while True:

            logger.info(f"CURRENT SERIAL => " f"{current_serial}")

            if stop_serial is not None and current_serial > stop_serial:

                logger.info(f"STOP LIMIT REACHED => " f"{current_serial}")

                break

            for language in languages:

                logger.info("=" * 60)

                logger.info(f"START LANGUAGE => " f"{language}")

                for word_length in [12, 15, 18, 21, 24]:

                    logger.info(
                        f"GENERATING => "
                        f"Language={language} | "
                        f"Words={word_length}"
                    )

                    mnemonic = generate_mnemonic_from_serial(
                        serial_number=current_serial,
                        language=language,
                        words=word_length,
                    )

                    logger.info(f"GENERATING ADDRESSES => " f"{language}")

                    addresses = generate_bitcoin_addresses(mnemonic)

                    logger.info(f"ADDRESSES GENERATED => " f"{language}")

                    address_list = list(addresses.values())

                    logger.info(f"TOTAL ADDRESSES => " f"{len(address_list)}")

                    logger.info("STARTING BALANCE CHECK")

                    with concurrent.futures.ThreadPoolExecutor(
                        max_workers=10
                    ) as executor:

                        futures = []

                        for address in address_list:

                            future = executor.submit(
                                check_single_address,
                                current_serial,
                                language,
                                word_length,
                                address,
                                mnemonic,
                            )

                            futures.append(future)

                        concurrent.futures.wait(futures)

                    logger.info(
                        f"BALANCE CHECK COMPLETED => " f"{language} | " f"{word_length}"
                    )

            # =================================================
            # SAVE STATE + SEND STATUS EVERY INTERVAL
            # =================================================
            if current_serial % STATE_SAVE_INTERVAL == 0:

                logger.info(f"SAVING INTERVAL STATE => " f"{current_serial}")

                save_current_state(current_serial)

                send_interval_status(current_serial)

            logger.info(f"ROUND COMPLETED => " f"Serial={current_serial}")

            current_serial += 1

            logger.info(f"SLEEPING FOR " f"{sleep_between_serial} SECONDS")

            time.sleep(sleep_between_serial)

    except KeyboardInterrupt:

        logger.warning("MANUALLY STOPPED")

        save_current_state(current_serial)

        send_telegram_message(
            f"SCANNER STOPPED MANUALLY\n\n"
            f"LAST SERIAL: {current_serial}\n"
            f"TOTAL SCANNED: {TOTAL_SCANNED}\n"
            f"TOTAL CONFIRMED FOUND: "
            f"{TOTAL_CONFIRMED_FOUND}"
        )

    except Exception as e:

        logger.exception(f"GENERATOR CRASHED => {e}")

        save_current_state(current_serial)

        send_telegram_message(
            f"SCANNER CRASHED\n\n"
            f"ERROR: {e}\n\n"
            f"LAST SERIAL: {current_serial}\n"
            f"TOTAL SCANNED: {TOTAL_SCANNED}\n"
            f"TOTAL CONFIRMED FOUND: "
            f"{TOTAL_CONFIRMED_FOUND}"
        )


# =========================================================
# RUN
# =========================================================
if __name__ == "__main__":

    logger.info("STARTING APPLICATION")

    generate_wallets(
        start_serial=None,
        stop_serial=None,
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
        sleep_between_serial=10,
    )

    logger.info("APPLICATION FINISHED")
