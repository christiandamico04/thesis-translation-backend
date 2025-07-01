"""Servizio API per il benchmark comparativo di modelli di traduzione.

Questo modulo implementa un'applicazione web basata su FastAPI, progettata
specificamente per eseguire test di benchmark comparativi. L'obiettivo è misurare
e confrontare le performance (latenza) e l'utilizzo di risorse (CPU, RAM, GPU)
di un modello linguistico (`google/gemma-2b-it`) in due scenari di inferenza distinti:
1.  Con vLLM: Inferenza delegata a un server ottimizzato (il 'vllm-server').
2.  Senza vLLM: Inferenza eseguita direttamente in-process tramite la libreria
    standard `transformers` di Hugging Face.

L'API espone due endpoint per simulare questi scenari e restituisce dati strutturati
utili all'analisi quantitativa dei risultati.
"""

# ========================================================================================
#                                  IMPORT E CONFIGURAZIONE
# ========================================================================================
import time
import requests
import torch
import psutil
import pynvml
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForCausalLM

# --- Configurazione dell'applicazione FastAPI ---
# Inizializza l'applicazione FastAPI, fornendo metadati che verranno utilizzati
# per la generazione automatica della documentazione OpenAPI (es. /docs).
app = FastAPI(
    title="Servizio di Benchmark per Traduzione AI",
    description="Un'API per confrontare le prestazioni di 'google/gemma-2b-it' con e senza vLLM."
)

# --- Configurazione delle dipendenze e cache ---
# Cache in-memory per il modello e il tokenizer. Questo evita di ricaricare i pesanti
# artefatti del modello dalla memoria ad ogni richiesta all'endpoint "without-vllm",
# permettendo di misurare la latenza di inferenza pura dopo il primo caricamento.
model_cache = {}

# Inizializzazione della libreria di monitoraggio NVIDIA (pynvml).
# Viene verificata la disponibilità di una GPU e impostato un flag globale.
try:
    pynvml.nvmlInit()
    GPU_AVAILABLE = True
except pynvml.NVMLError:
    GPU_AVAILABLE = False

# ========================================================================================
#                     MODELLI DI DATI (Pydantic Schemas)
# ========================================================================================
# Questi modelli definiscono la struttura, i tipi di dati e la validazione automatica
# per i corpi delle richieste e delle risposte API.

class BenchmarkRequest(BaseModel):
    """Schema per i dati in ingresso di una richiesta di benchmark."""
    text_to_translate: str = "Ciao mondo, come stai?"
    source_language: str = "Italiano"
    target_language: str = "Inglese"

class ResourceUsage(BaseModel):
    """Schema per rappresentare l'utilizzo delle risorse di sistema in un dato istante."""
    cpu_percent: float
    ram_percent: float
    gpu_percent: float | None = None
    gpu_mem_percent: float | None = None

class BenchmarkResult(BaseModel):
    """Schema per i dati in uscita, contenente i risultati completi del benchmark."""
    method: str
    translated_text: str
    time_seconds: float
    first_request: bool = False
    resources_before: ResourceUsage
    resources_after: ResourceUsage

# ========================================================================================
#                          FUNZIONI DI UTILITÀ E MONITORAGGIO
# ========================================================================================

def get_resource_usage() -> ResourceUsage:
    """Cattura e restituisce l'utilizzo corrente delle risorse di sistema.

    Utilizza la libreria 'psutil' per l'utilizzo di CPU e RAM e 'pynvml' per
    le metriche della GPU NVIDIA, se disponibile.

    Returns:
        ResourceUsage: Un oggetto Pydantic con le metriche di utilizzo.
    """
    gpu_percent = None
    gpu_mem_percent = None
    if GPU_AVAILABLE:
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        util = pynvml.nvmlDeviceGetUtilizationRates(handle)
        mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
        gpu_percent = util.gpu
        gpu_mem_percent = (mem.used / mem.total) * 100

    return ResourceUsage(
        cpu_percent=psutil.cpu_percent(),
        ram_percent=psutil.virtual_memory().percent,
        gpu_percent=gpu_percent,
        gpu_mem_percent=gpu_mem_percent,
    )

def build_prompt(text: str, src_lang: str, dst_lang: str) -> str:
    """Costruisce un prompt di traduzione standardizzato."""
    return (
        f"Sei un traduttore professionista. Il tuo unico compito è tradurre il testo fornito. "
        f"Traduci la seguente frase da {src_lang} a {dst_lang}. "
        f"Restituisci solo ed esclusivamente il testo tradotto, senza alcuna spiegazione o frase aggiuntiva.\n\n"
        f"Testo da tradurre: \"{text}\""
    )

# ========================================================================================
#                            ENDPOINT DELL'API E LOGICA DI BENCHMARK
# ========================================================================================

@app.post("/benchmark/with-vllm", response_model=BenchmarkResult)
def run_benchmark_with_vllm(request: BenchmarkRequest):
    """Endpoint per il benchmark con inferenza delegata al servizio vLLM.

    Questo metodo misura le performance di una chiamata di rete a un servizio esterno
    ottimizzato. Il tempo misurato include la latenza di rete e il tempo di
    elaborazione del server vLLM.
    """
    vllm_api_url = "http://vllm-server:8001/v1/chat/completions"
    prompt = build_prompt(request.text_to_translate, request.source_language, request.target_language)
    
    payload = {
        "model": "google/gemma-2b-it",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 2048,
        "temperature": 0.1,
    }

    resources_before = get_resource_usage()
    start_time = time.perf_counter()

    try:
        response = requests.post(vllm_api_url, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        translated_text = data['choices'][0]['message']['content'].strip()
    except requests.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Errore di comunicazione con vLLM-server: {e}")
    except (KeyError, IndexError) as e:
        raise HTTPException(status_code=500, detail=f"Risposta non valida da vLLM: {e}")

    end_time = time.perf_counter()
    resources_after = get_resource_usage()

    return BenchmarkResult(
        method="Con vLLM (fp16)",
        translated_text=translated_text,
        time_seconds=(end_time - start_time),
        resources_before=resources_before,
        resources_after=resources_after,
    )

@app.post("/benchmark/without-vllm", response_model=BenchmarkResult)
def run_benchmark_without_vllm(request: BenchmarkRequest):
    """Endpoint per il benchmark con inferenza eseguita direttamente in-process.

    Questo metodo carica il modello utilizzando la libreria 'transformers' standard
    e lo esegue sulla GPU locale. La prima richiesta a questo endpoint misurerà
    anche il tempo di caricamento del modello (cold start), mentre le successive
    misureranno solo la latenza di inferenza (warm start).
    """
    model_name = "google/gemma-2b-it"
    first_request = False

    resources_before = get_resource_usage()
    
    # Logica di caching: carica il modello solo se non è già in memoria.
    if "model" not in model_cache:
        print(f"Scenario 'senza vLLM': Prima richiesta. Inizio caricamento del modello {model_name} in fp16 su GPU...")
        first_request = True
        
        if not torch.cuda.is_available():
            raise HTTPException(status_code=500, detail="CUDA non è disponibile. Impossibile eseguire test su GPU.")

        try:
            # Carica il tokenizer e il modello.
            model_cache["tokenizer"] = AutoTokenizer.from_pretrained(model_name)
            # Carica il modello in float16 per coerenza con vLLM e lo mappa automaticamente sulla GPU.
            model_cache["model"] = AutoModelForCausalLM.from_pretrained(
                model_name,
                torch_dtype=torch.float16,
                device_map="auto",
            )
            print("Scenario 'senza vLLM': Modello caricato con successo.")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Errore durante il caricamento del modello: {e}")
    
    tokenizer = model_cache["tokenizer"]
    model = model_cache["model"]
    device = model.device

    prompt = build_prompt(request.text_to_translate, request.source_language, request.target_language)
    inputs = tokenizer(prompt, return_tensors="pt").to(device)

    start_time = time.perf_counter()
    # Esegue l'inferenza in un contesto `torch.no_grad()` per disabilitare il
    # calcolo dei gradienti, ottimizzando le performance e riducendo l'uso di memoria.
    with torch.no_grad():
        outputs = model.generate(**inputs, max_new_tokens=512)
    
    # Esegue il decoding dell'output per ottenere il testo tradotto.
    translated_text = tokenizer.decode(outputs[0][len(inputs.input_ids[0]):], skip_special_tokens=True)
    end_time = time.perf_counter()
    resources_after = get_resource_usage()

    return BenchmarkResult(
        method="Senza vLLM (fp16)",
        translated_text=translated_text.strip(),
        time_seconds=(end_time - start_time),
        first_request=first_request,
        resources_before=resources_before,
        resources_after=resources_after,
    )

@app.get("/", include_in_schema=False)
def root():
    """Endpoint radice per un semplice health check."""
    return {"message": "Servizio di benchmark attivo. Usa gli endpoint POST /benchmark/with-vllm o /benchmark/without-vllm."}