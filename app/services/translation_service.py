import hashlib
import requests # type: ignore
import time

# Cache in memoria: { chiave_hash: translated_text }
_TRANSLATION_CACHE = {}

class TranslationError(Exception):
    pass

def translate(text: str, src: str, dst: str, retry: int = 3, backoff: float = 0.5) -> str:
    """
    Traduci `text` da `src` a `dst` usando LibreTranslate.
    - text: stringa da tradurre
    - src, dst: codici lingua ISO-639
    - retry: numero di tentativi in caso di errore
    - backoff: tempo di attesa esponenziale (in secondi)
    """
    
    # 1) Cache key
    key = hashlib.sha256(f"{src}:{dst}:{text}".encode("utf-8")).hexdigest()
    if key in _TRANSLATION_CACHE:
        return _TRANSLATION_CACHE[key]

    url = "https://libretranslate.de/translate"
    payload = {
        "q": text,
        "source": src,
        "target": dst,
        "format": "text"
    }

    # 2) Retry loop
    for attempt in range(1, retry+1):
        try:
            resp = requests.post(url, data=payload, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                translated = data.get("translatedText")
                if not translated:
                    raise TranslationError("Nessun testo tradotto ricevuto")
                # 3) Salva in cache e ritorna
                _TRANSLATION_CACHE[key] = translated
                return translated
            elif 500 <= resp.status_code < 600:
                # Errore server: retry
                time.sleep(backoff * attempt)
                continue
            else:
                # Errore client o limite
                raise TranslationError(f"Errore API {resp.status_code}: {resp.text}")
        except requests.RequestException as e:
            if attempt == retry:
                raise TranslationError(f"Richiesta fallita: {e}")
            time.sleep(backoff * attempt)

    raise TranslationError("Traduzione non riuscita dopo retry")
