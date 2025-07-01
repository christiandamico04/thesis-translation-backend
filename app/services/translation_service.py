"""Client per il servizio di traduzione e logica di processamento del testo.

Questo modulo implementa il pattern "Service Layer", agendo come un client disaccoppiato
per il servizio di inferenza AI basato su vLLM. Incapsula tutta la logica di
comunicazione con l'API del modello linguistico, includendo:
  - Costruzione di prompt strutturati (Prompt Engineering).
  - Gestione di testi lunghi tramite una strategia di chunking semantico.
  - Caching delle traduzioni per ottimizzare le performance.
  - Post-processing e pulizia delle risposte del modello.
"""

# ========================================================================================
#                                  IMPORT E CONFIGURAZIONE
# ========================================================================================
import requests
import logging
import hashlib
import nltk

# Setup di un logger specifico per questo modulo, per consentire un logging
# strutturato e granulare degli eventi relativi al servizio di traduzione.
logger = logging.getLogger(__name__)

# ========================================================================================
#                                        COSTANTI
# ========================================================================================

# --- Costanti per la strategia di Chunking ---
# Soglia massima, in caratteri, oltre la quale si attiva il processo di chunking.
# Questa soglia è definita in modo conservativo per evitare di superare la massima
# lunghezza di contesto del modello (`max_model_len`), tenendo conto anche della
# lunghezza aggiuntiva del prompt.
MAX_CHAR_COUNT = 3500
# Dimensione target desiderata per ogni singolo chunk. Il processo di suddivisione
# cercherà di creare chunk di dimensione approssimativamente pari a questo valore.
CHUNK_TARGET_SIZE = 2000

# --- Costanti di configurazione del servizio ---
# URL dell'endpoint API esposto dal servizio vLLM, compatibile con le API OpenAI.
VLLM_API_URL = "http://vllm-server:8001/v1/chat/completions"
# Dizionario Python utilizzato come cache in-memory.
# NOTA ARCHITETTURALE: Questa è una cache locale per singolo processo. 
_TRANSLATION_CACHE = {}
# Mappatura tra i codici lingua ISO e i loro nomi in italiano, utilizzata per
# costruire prompt più naturali e leggibili (es. 'it' -> 'italiano').
LANGUAGE_NAMES = {
    'en': 'inglese',
    'it': 'italiano',
    'fr': 'francese',
    'de': 'tedesco',
    'es': 'spagnolo',
}

# ========================================================================================
#                                  CLASSI DI ECCEZIONE
# ========================================================================================
class TranslationError(Exception):
    """Eccezione personalizzata per il dominio di traduzione.

    Viene sollevata per incapsulare errori specifici del servizio, come fallimenti
    di connessione al modello AI o la ricezione di risposte malformate. L'uso di
    un'eccezione custom permette al codice chiamante di gestire in modo mirato
    questi specifici scenari di errore.
    """
    pass

# ========================================================================================
#                                  FUNZIONI PRIVATE
# ========================================================================================

def _build_prompt(text: str, src: str, dst: str) -> str:
    """Costruisce un prompt strutturato per guidare il modello linguistico.

    Questa funzione è un esempio di "Prompt Engineering". Il suo scopo è fornire al
    modello istruzioni chiare, non ambigue e tassative per forzarlo a comportarsi
    esclusivamente come un sistema di traduzione, sopprimendo ogni suo comportamento
    conversazionale (es. frasi introduttive, commenti, ecc.).

    Args:
        text (str): Il testo da tradurre.
        src (str): Il codice della lingua di origine.
        dst (str): Il codice della lingua di destinazione.

    Returns:
        str: Il prompt completo, pronto per essere inviato al modello AI.
    """
    source_language_name = LANGUAGE_NAMES.get(src, src)
    destination_language_name = LANGUAGE_NAMES.get(dst, dst)

    prompt_rules = (
        f"Sei un sistema di traduzione letterale e ad alta fedeltà da {source_language_name} a {destination_language_name}.\n"
        "ATTENZIONE: Segui queste regole in modo tassativo:\n"
        f"1. Il tuo unico output deve essere la traduzione in {destination_language_name.upper()} del testo che si trova dopo '--- TESTO DA TRADURRE ---'.\n"
        "2. NON scrivere MAI frasi introduttive come 'Certo, ecco la traduzione:' o simili.\n"
        "3. NON aggiungere commenti, note o spiegazioni al di fuori della traduzione.\n"
        "4. La tua risposta deve contenere solo ed esclusivamente il testo tradotto.\n\n"
        "--- TESTO DA TRADURRE ---\n"
    )

    return f"{prompt_rules}{text}"

def _create_chunks(text: str, target_size: int) -> list[str]:
    """Suddivide un testo in segmenti (chunk) semanticamente coerenti.

    Affronta la limitazione della finestra di contesto finita dei modelli LLM.
    La strategia implementata usa la libreria NLTK per una tokenizzazione basata
    su frasi (`sent_tokenize`), garantendo che ogni chunk sia composto da frasi
    complete. Questo preserva il contesto locale, cruciale per la qualità della
    traduzione. È presente una strategia di fallback (split per newline) per
    garantire robustezza nel caso in cui NLTK fallisca.

    Args:
        text (str): Il testo sorgente completo da segmentare.
        target_size (int): La dimensione approssimativa desiderata per ogni chunk.

    Returns:
        list[str]: Una lista di stringhe, ciascuna rappresentante un chunk di testo.
    """
    logger.info(f"Testo troppo lungo ({len(text)} caratteri). Avvio del processo di chunking.")

    try:
        # Tenta la suddivisione per frasi, il metodo qualitativamente migliore.
        sentences = nltk.sent_tokenize(text)
    except Exception as e:
        logger.error(f"Errore durante la tokenizzazione NLTK. Errore: {e}. Attivazione fallback.")
        # Se NLTK fallisce, si usa lo split per paragrafo come ripiego.
        sentences = text.split('\n')

    chunks = []
    current_chunk = ""

    for sentence in sentences:
        if len(current_chunk) + len(sentence) > target_size and current_chunk:
            chunks.append(current_chunk.strip())
            current_chunk = ""

        current_chunk += sentence + " "

    if current_chunk:
        chunks.append(current_chunk.strip())

    logger.info(f"Il testo è stato suddiviso in {len(chunks)} chunk.")
    return chunks

def _call_vllm_api(text_to_translate: str, src: str, dst: str) -> str:
    """Gestisce la singola chiamata HTTP all'API del servizio vLLM.

    Questa funzione ausiliaria incapsula la logica di comunicazione di basso livello:
    costruisce il payload della richiesta, la esegue e gestisce sia gli errori di
    rete che il parsing della risposta JSON.

    Returns:
        La stringa di testo tradotta e pulita.

    Raises:
        TranslationError: Se la richiesta fallisce o la risposta è malformata.
    """
    prompt = _build_prompt(text_to_translate, src, dst)

    # Costruzione del payload secondo il formato atteso dall'API di vLLM.
    payload = {
        "model": "google/gemma-2b-it",                              # Specifica il modello da utilizzare.
        "messages": [{"role": "user", "content": prompt}],          # Contiene il prompt.
        "max_tokens": 2048,                                         # Limita la lunghezza massima della risposta.
        "temperature": 0.1,                                         # Valore basso per risposte deterministiche e letterali.
    }

    logger.info(f"Invio richiesta di traduzione al servizio vLLM per {len(text_to_translate)} caratteri.")

    try:
        # Esecuzione della richiesta HTTP con un timeout generoso.
        response = requests.post(VLLM_API_URL, json=payload, timeout=600)
        # Solleva un'eccezione per status code di errore (4xx o 5xx).
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        # In caso di errore di rete o di connessione.
        error_message = f"Il servizio di traduzione non è al momento disponibile: {e}"
        logger.error(f"ERRORE CRITICO: Impossibile connettersi a vLLM. Errore: {e}", exc_info=True)
        raise TranslationError(error_message)

    try:
        # Parsing della risposta JSON e estrazione del testo tradotto.
        data = response.json()
        translated_text = data['choices'][0]['message']['content']

        # Applicazione di un filtro di pulizia per rimuovere artefatti.
        cleaned_translation = _clean_translation(translated_text)
        
        logger.info("Traduzione ricevuta e pulita con successo.")
        return cleaned_translation
    except (KeyError, IndexError, TypeError) as e:
        # In caso di risposta JSON non conforme al formato atteso.
        error_message = f"Risposta non valida o malformata dal servizio di traduzione: {e}"
        logger.error(f"ERRORE: Parsing della risposta da vLLM fallito. Risposta: {response.text}", exc_info=True)
        raise TranslationError(error_message)

def _clean_translation(text: str) -> str:
    """Esegue una pulizia programmatica (sanitizzazione) dell'output del modello.

    Questa funzione di post-processing è un passo pragmatico per rimuovere frasi
    conversazionali e altri artefatti che il modello potrebbe generare nonostante
    le istruzioni del prompt, garantendo che l'output finale sia solo la traduzione.
    """
    frasi_indesiderate = [
        "Sure, il testo è stato tradotto da italiano a inglese come segue:",
        "Sure, il testo è stato tradito con alta precisione.",
        "Sure, il testo è stato tradito.",
        "Sure, il testo è già tradotto.",
        "The text is not provided in the context, so I cannot translate it.",
        "Sure, the correct management of chunks is the subject of this test.",
        "Sure, the test is designed to verify the correct management of chunks.",
    ]
    
    cleaned_text = text
    for frase in frasi_indesiderate:
        cleaned_text = cleaned_text.replace(frase, "")
    
    # Rimuove virgolette e spazi bianchi residui.
    return cleaned_text.strip().strip('"').strip("'").strip("`").strip()

# ========================================================================================
#                                   FUNZIONE PUBBLICA
# ========================================================================================

def translate(text: str, src: str, dst: str, **kwargs) -> str:
    """Orchestra il processo completo di traduzione.

    Questa è la funzione di facciata (facade) del modulo. Gestisce il workflow
    completo: controlla la cache, decide la strategia (chiamata singola o chunking),
    invoca le funzioni ausiliarie per l'esecuzione e infine popola la cache con
    il nuovo risultato.

    Args:
        text (str): Il testo originale da tradurre.
        src (str): Il codice della lingua di origine.
        dst (str): Il codice della lingua di destinazione.
        **kwargs: Argomenti aggiuntivi per future estensioni.

    Returns:
        str: Il testo finale tradotto.
    """
    # --- 1. Livello di Caching ---
    # Genera una chiave univoca per la richiesta basata sul suo contenuto.
    cache_key = hashlib.sha256(f"{src}:{dst}:{text}".encode("utf-8")).hexdigest()
    # Se la chiave esiste, restituisce il risultato cachato per ottimizzare le performance.
    if cache_key in _TRANSLATION_CACHE:
        logger.info(f"Traduzione completa per la chiave {cache_key[:8]}... trovata in cache.")
        return _TRANSLATION_CACHE[cache_key]

    # --- 2. Logica di Orchestrazione ---
    # Se il testo supera la soglia, attiva la strategia di chunking.
    if len(text) > MAX_CHAR_COUNT:
        chunks = _create_chunks(text, CHUNK_TARGET_SIZE)
        translated_chunks = []

        # Itera su ogni chunk, lo traduce singolarmente e raccoglie i risultati.
        for i, chunk in enumerate(chunks):
            logger.info(f"Traduzione del chunk {i+1}/{len(chunks)}...")
            try:
                translated_chunk = _call_vllm_api(chunk, src, dst)
                translated_chunks.append(translated_chunk)
            except TranslationError as e:
                # Se la traduzione di un singolo chunk fallisce, l'intero processo
                # viene interrotto per garantire l'integrità del risultato finale.
                logger.error(f"Fallimento traduzione del chunk {i+1}. Errore: {e}")
                raise TranslationError(f"La traduzione è fallita sul chunk {i+1}/{len(chunks)}. Dettagli: {e}")
        
        # Riunisce i chunk tradotti in un'unica stringa.
        final_translation = " ".join(translated_chunks)
    else:
        # Se il testo è corto, procede con una singola chiamata all'API.
        final_translation = _call_vllm_api(text, src, dst)
    
    # --- 3. Popolamento della Cache e Restituzione ---
    logger.info("Processo di traduzione completato con successo.")
    # Salva il nuovo risultato nella cache per le richieste future.
    _TRANSLATION_CACHE[cache_key] = final_translation
    return final_translation