import json
import requests
import concurrent.futures

# =========================================================
# CONFIG
# =========================================================

BASE_RAW_URL = (
    "https://raw.githubusercontent.com/"
    "bitcoin/bips/master/bip-0039/"
)

LANGUAGE_FILES = {
    "english": "english.txt",
    "japanese": "japanese.txt",
    "korean": "korean.txt",
    "spanish": "spanish.txt",
    "chinese_simplified": "chinese_simplified.txt",
    "chinese_traditional": "chinese_traditional.txt",
    "french": "french.txt",
    "italian": "italian.txt",
    "czech": "czech.txt",
    "portuguese": "portuguese.txt"
}

OUTPUT_JSON_FILE = "bip39_words.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/148.0.0.0 Safari/537.36"
    )
}


# =========================================================
# DOWNLOAD SINGLE LANGUAGE FILE
# =========================================================
def download_language_words(language, filename):

    url = BASE_RAW_URL + filename

    print(f"[START] Downloading: {language}")

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=30
        )

        response.raise_for_status()

        # Split lines and remove empty lines
        words = [
            line.strip()
            for line in response.text.splitlines()
            if line.strip()
        ]

        print(
            f"[SUCCESS] {language} => "
            f"{len(words)} words downloaded"
        )

        return language, words

    except Exception as e:

        print(f"[FAILED] {language} => {e}")

        return language, []


# =========================================================
# MAIN
# =========================================================
def main():

    final_data = {}

    # =====================================================
    # DOWNLOAD ALL FILES IN BACKGROUND
    # =====================================================
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=10
    ) as executor:

        futures = []

        for language, filename in LANGUAGE_FILES.items():

            future = executor.submit(
                download_language_words,
                language,
                filename
            )

            futures.append(future)

        # =================================================
        # COLLECT RESULTS
        # =================================================
        for future in concurrent.futures.as_completed(futures):

            language, words = future.result()

            final_data[language] = words

    # =====================================================
    # SAVE JSON FILE
    # =====================================================
    with open(
        OUTPUT_JSON_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            final_data,
            file,
            ensure_ascii=False,
            indent=4
        )

    print("\n" + "=" * 60)
    print("ALL DOWNLOADS COMPLETED")
    print(f"JSON SAVED => {OUTPUT_JSON_FILE}")
    print("=" * 60)


# =========================================================
# RUN
# =========================================================
if __name__ == "__main__":
    main()