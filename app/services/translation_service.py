# Questo è il cuore "intelligente" dell'applicazione. È un modulo di servizio che incapsula tutta la logica di interazione con il modello di 
# traduzione AI. Isolare questa logica rende il resto del codice (le viste) più pulito e facile da mantenere. Se in futuro si volesse cambiare 
# modello o usare un'API esterna, basterebbe modificare solo questo file.

import hashlib
import logging
import torch
import nltk
from tqdm import tqdm
from transformers import T5ForConditionalGeneration, T5Tokenizer

# 1. Setup del Logger, che viene preferito alla semplice print.

logger = logging.getLogger(__name__)

# 2. Configurazione del Modello e delle costanti

MODEL_NAME = "google/madlad400-3b-mt"

# Le variabili del modello, del tokenizer e del device vengono inizializzate a None. Verranno popolate una sola volta all'avvio dell'
# applicazione.
model = None
tokenizer = None
device = None

# Si prova a scaricare il tokenizer per le frasi di NLTK ("punkt"). Questa operazione è necessaria solo al primo avvio dopo l'installazione 
# di NLTK.
try:
    nltk.data.find('tokenizers/punkt')
except nltk.downloader.DownloadError:
    logger.info("Download del tokenizer 'punkt' di NLTK in corso...")
    nltk.download('punkt', quiet=True)
    logger.info("Download del tokenizer 'punkt' completato.")


# 3. Blocco di caricamento del modello e del tokenizer all'avvio dell'app

try:
    
    # 3.1. Selezione del dispositivo (GPU o CPU)

    if torch.backends.mps.is_available():
        device = torch.device("mps")
        logger.info("Dispositivo MPS trovato. Si utilizzerà la GPU Apple.")
    elif torch.cuda.is_available():
        device = torch.device("cuda")
        logger.info("Dispositivo CUDA trovato. Si utilizzerà la GPU NVIDIA.")
    else:
        device = torch.device("cpu")
        logger.info("Nessuna GPU accelerata trovata. Si utilizzerà la CPU.")

    # 3.2. Caricamento del tokenizer

    logger.info(f"Caricamento del tokenizer: {MODEL_NAME}...")
    tokenizer = T5Tokenizer.from_pretrained(MODEL_NAME)
    
    # 3.3. Caricamento del modello

    logger.info(f"Caricamento del modello: {MODEL_NAME}. Questo potrebbe richiedere tempo e RAM ...")
    # 'device_map="auto"' distribuisce il modello tra GPU e RAM se necessario.
    model = T5ForConditionalGeneration.from_pretrained(MODEL_NAME, device_map="auto")
    
    logger.info("Modello e tokenizer caricati con successo.")

except Exception as e:
    logger.error(f"ERRORE CRITICO: Impossibile caricare il modello di traduzione. L'applicazione funzionerà senza traduzioni. Errore: {e}", exc_info=True)

# 4. Cache in memoria per le traduzioni. Salva le traduzioni già eseguite per evitare di ricalcolarle. Si resetta al riavvio del server.

_TRANSLATION_CACHE = {}                                                                  

# 5. Eccezione personalizzata per errori di traduzione
class TranslationError(Exception):
    """Eccezione custom lanciata quando la traduzione fallisce."""
    pass

# 6. Funzione principale di traduzione con logica di segmentazione

def translate(text: str, src: str, dst: str, **kwargs) -> str:
    """
    Traduci `text` da `src` a `dst`, gestendo testi lunghi tramite segmentazione
    automatica in blocchi (chunking).

    - text: stringa da tradurre
    - src: codice lingua sorgente (non usato dal modello ma utile per la cache)
    - dst: codice lingua destinazione ISO-639 (es. 'en', 'de', 'fr')
    """

    # Controllo preliminare. Il modello deve essere stato caricato.
    if not model or not tokenizer:
        raise TranslationError("Il modello di traduzione non è inizializzato.")

    # A. Controllo della cache. Si calcola un hash del testo completo e si controlla se è già stato tradotto.

    cache_key = hashlib.sha256(f"{src}:{dst}:{text}".encode("utf-8")).hexdigest()
    if cache_key in _TRANSLATION_CACHE:
        logger.info(f"Traduzione completa per la chiave {cache_key[:8]}... trovata in cache. Salto l'elaborazione.")
        return _TRANSLATION_CACHE[cache_key]

    # B. Logica di segmentazione (Chunking). Definiamo una lunghezza massima di TOKEN (non caratteri) per segmento. 512 è una scelta sicura 
    # per modelli T5, per garantire che l'input non superi la context window.
    
    MAX_TOKENS_PER_CHUNK = 512

    # Utilizzo di NLTK per dividere il testo in frasi in modo intelligente.
    sentences = nltk.sent_tokenize(text, language='english') 

    chunks = []
    current_chunk_sentences = []
    current_chunk_tokens = 0
    logger.info(f"Inizio segmentazione del testo ({len(sentences)} frasi totali) in blocchi da max {MAX_TOKENS_PER_CHUNK} token.")

    for sentence in sentences:

        # Calcolo del numero di token che la frase aggiungerebbe.
        sentence_tokens = len(tokenizer.encode(sentence))

        # Se aggiungere la nuova frase supera il limite e il chunk corrente non è vuoto, allora si salva il chunk corrente e se ne inizia uno nuovo.
        if current_chunk_tokens + sentence_tokens > MAX_TOKENS_PER_CHUNK and current_chunk_sentences:
            chunks.append(" ".join(current_chunk_sentences))
            current_chunk_sentences = [sentence]
            current_chunk_tokens = sentence_tokens
        else:

            # Si aggiunge la frase al chunk corrente.
            current_chunk_sentences.append(sentence)
            current_chunk_tokens += sentence_tokens

    # Si aggiunge l'ultimo chunk rimasto.
    if current_chunk_sentences:
        chunks.append(" ".join(current_chunk_sentences))

    logger.info(f"Testo diviso in {len(chunks)} segmenti pronti per la traduzione.")

    # C. Traduzione di ogni segmento

    translated_chunks = []
    try:

        # Si usa tqdm per avere una barra di progresso visibile nei log del server.
        for chunk in tqdm(chunks, desc=f"Traduzione da '{src}' a '{dst}'"):

            # Si prepara l'input per MADLAD-400 con il prefisso della lingua.
            prompt = f"<2{dst}> {chunk}"
            
            # Si tokenizza e si sposta sul dispositivo corretto (GPU/CPU).
            input_ids = tokenizer(prompt, return_tensors="pt").input_ids.to(device)
            
            # Si genera la traduzione.
            outputs = model.generate(input_ids=input_ids, max_length=1024)
            
            # Si decodificano i token di output in una stringa di testo.
            translated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
            translated_chunks.append(translated_text)
            
    except Exception as e:
        logger.error(f"Errore durante l'inferenza del modello su un segmento: {e}", exc_info=True)
        raise TranslationError(f"Inferenza fallita su un segmento: {e}")

    # D. Ricomposizione e salvataggio in cache. Si uniscono i segmenti tradotti con uno spazio.

    full_translated_text = " ".join(translated_chunks)
    
    logger.info("Traduzione di tutti i segmenti completata con successo.")
    
    # Si salva il risultato completo nella cache per richieste future.
    _TRANSLATION_CACHE[cache_key] = full_translated_text
    
    return full_translated_text