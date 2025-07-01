"""Script per la valutazione quantitativa della qualità della traduzione.

Questo modulo implementa un protocollo di test per valutare oggettivamente la
qualità delle traduzioni generate dall'API di benchmark. A differenza dei test di
performance, l'obiettivo qui è misurare quanto le traduzioni prodotte dal modello
siano "buone" rispetto a traduzioni di riferimento umane.

La valutazione si basa su due metriche standard nel campo della Machine Translation (MT):
1.  **BLEU (Bilingual Evaluation Understudy)**: Una metrica classica basata sulla
    precisione degli n-grammi, che misura la sovrapposizione tra la traduzione
    automatica e quella di riferimento.
2.  **COMET (Cross-lingual Optimized Metric for Evaluation of Translation)**:
    Una metrica moderna basata su modelli neurali, che ha dimostrato una maggiore
    correlazione con il giudizio umano rispetto a BLEU.
"""

# ========================================================================================
#                                  IMPORT E CONFIGURAZIONE
# ========================================================================================
import requests
import csv
import torch
import os  # Aggiunto per l'interazione con il sistema operativo (gestione percorsi).
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
from comet import download_model, load_from_checkpoint


# --- Blocco per la gestione di percorsi di file robusti ---
# Questa modifica rende lo script più robusto e portabile. Invece di fare affidamento
# sulla directory di lavoro corrente, il percorso del file di test viene costruito
# in modo relativo alla posizione dello script stesso.
# Ottiene il percorso assoluto della directory in cui si trova questo script.
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))

# Costruisce il percorso completo e indipendente dal sistema operativo per il file CSV.
# Questo garantisce che lo script trovi il file 'quality_test.csv' anche se viene
# eseguito da una directory differente.
QUALITY_TEST_FILE = os.path.join(SCRIPT_DIR, "quality_test.csv")

# --- Configurazione Globale ---
# L'URL dell'endpoint API di cui si vuole valutare la qualità delle traduzioni.
API_URL = "http://localhost:8002/benchmark/without-vllm"
# In alternativa: "http://localhost:8002/benchmark/with-vllm"

# ========================================================================================
#                                  FUNZIONI DI UTILITÀ
# ========================================================================================

def get_translation(text: str) -> str:
    """Funzione client per recuperare una singola traduzione dall'API di benchmark."""
    payload = {"text_to_translate": text, "source_language": "Italiano", "target_language": "Inglese"}
    try:
        response = requests.post(API_URL, json=payload, timeout=90)
        response.raise_for_status()
        data = response.json()
        return data["translated_text"]
    except Exception as e:
        print(f"Errore durante la traduzione di '{text}': {e}")
        return ""

# ========================================================================================
#                                  ORCHESTRAZIONE DEL TEST DI QUALITÀ
# ========================================================================================

def main():
    """Funzione principale che orchestra l'intero processo di valutazione."""
    print(f"--- Inizio Test di Qualità Avanzato sull'endpoint: {API_URL} ---")

    print("Caricamento del modello COMET in corso... (potrebbe richiedere tempo la prima volta)")
    model_path = download_model("Unbabel/wmt22-comet-da")
    comet_model = load_from_checkpoint(model_path)
    print("Modello COMET caricato.")

    bleu_scores = []
    comet_data = []
    smoothie = SmoothingFunction().method4

    # Apertura del file di test utilizzando la variabile `QUALITY_TEST_FILE`.
    # Questo assicura che il percorso del file sia sempre corretto,
    # indipendentemente dalla directory da cui viene lanciato lo script.
    with open(QUALITY_TEST_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            source_text = row['italiano']
            reference_translation = row['inglese_riferimento']

            print(f"\nTesto Originale: {source_text}")
            model_translation = get_translation(source_text)
            print(f"Traduzione del Modello: {model_translation}")

            reference_tokenized = reference_translation.split()
            model_tokenized = model_translation.split()

            bleu_score = sentence_bleu([reference_tokenized], model_tokenized, smoothing_function=smoothie)
            bleu_scores.append(bleu_score)
            print(f"Punteggio BLEU: {bleu_score:.4f}")

            comet_data.append({
                "src": source_text,
                "mt": model_translation,
                "ref": reference_translation
            })

    print("\nCalcolo del punteggio COMET in corso...")
    model_output = comet_model.predict(comet_data, batch_size=8, gpus=1 if torch.cuda.is_available() else 0, progress_bar=False)
    comet_score = model_output.system_score
    print("Calcolo COMET completato.")

    if bleu_scores:
        average_bleu = sum(bleu_scores) / len(bleu_scores)
        print(f"\n--- RISULTATI FINALI DI QUALITÀ ---")
        print(f"Punteggio BLEU medio su {len(bleu_scores)} frasi: {average_bleu:.4f}")
        print(f"Punteggio COMET di sistema: {comet_score:.4f}")
        print("---------------------------------------")

if __name__ == "__main__":
    main()