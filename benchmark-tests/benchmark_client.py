"""Client per stress-test e benchmark di concorrenza.

Questo script funge da client per la generazione di carico (load testing) verso
un endpoint HTTP. Utilizza un modello di concorrenza basato su multi-threading
per simulare accessi simultanei da parte di più utenti.

La sua finalità è misurare metriche di performance chiave di un servizio web
sotto carico, quali:
  - Throughput: il numero di richieste al secondo (RPS) che il server è in grado di gestire.
  - Latenza media: il tempo medio di risposta per una singola richiesta.

Il client è configurabile tramite argomenti da riga di comando per specificare
l'URL target, il numero totale di richieste e il livello di concorrenza (numero di thread).
"""

# ========================================================================================
#                                  IMPORT E CONFIGURAZIONE
# ========================================================================================
import requests
import threading
import time
import argparse
import random
from queue import Queue

# --- Configurazione Globale ---
# Nome del file contenente le frasi di test da utilizzare come payload realistico.
PERFORMANCE_TEST_FILE = "performance_test.txt"

# --- Caricamento dei Dati di Test ---
# Legge le frasi di test dal file. Questo permette di inviare dati variabili
# ad ogni richiesta, simulando uno scenario più realistico rispetto a un payload statico.
try:
    with open(PERFORMANCE_TEST_FILE, 'r', encoding='utf-8') as f:
        sentences = [line.strip() for line in f if line.strip()]
    print(f"Caricate {len(sentences)} frasi di test dal file '{PERFORMANCE_TEST_FILE}'.")
except FileNotFoundError:
    print(f"ATTENZIONE: File '{PERFORMANCE_TEST_FILE}' non trovato. Uso una frase di default.")
    sentences = ["Traduci questa frase in inglese per favore."]

# --- Strutture Dati Condivise tra i Thread ---
# Dizionario globale per aggregare i risultati provenienti da tutti i thread.
results = {"success": 0, "failure": 0, "total_time": 0.0}
# Un `Lock` (o "semaforo binario") per garantire l'accesso mutuamente esclusivo
# al dizionario 'results'. È fondamentale per prevenire race condition quando
# più thread tentano di aggiornare simultaneamente i contatori.
results_lock = threading.Lock()

# ========================================================================================
#                                  LOGICA DEL WORKER
# ========================================================================================

def worker(url: str, q: Queue):
    """La funzione eseguita da ogni thread worker.

    Ogni worker esegue un ciclo in cui preleva un "task" dalla coda condivisa,
    invia una richiesta HTTP all'URL target e registra il risultato. Il ciclo
    termina quando la coda dei task è vuota.

    Args:
        url (str): L'URL dell'endpoint da testare.
        q (Queue): La coda condivisa da cui i worker prelevano i task.
    """
    while not q.empty():
        try:
            _ = q.get()  # Preleva un elemento dalla coda per segnalare l'inizio di un task.

            # Seleziona una frase casuale per diversificare il payload.
            text_to_translate = random.choice(sentences)
            payload = {"text_to_translate": text_to_translate}

            # Misura il tempo di risposta della singola richiesta.
            start_time = time.perf_counter()
            response = requests.post(url, json=payload, timeout=120)
            end_time = time.perf_counter()

            # --- Sezione Critica: Aggiornamento dei risultati condivisi ---
            # Il blocco 'with' acquisisce il lock prima di entrare e lo rilascia
            # automaticamente all'uscita, garantendo la thread-safety.
            with results_lock:
                if response.status_code in [200, 201]:
                    results["success"] += 1
                    results["total_time"] += (end_time - start_time)
                else:
                    results["failure"] += 1
            
            q.task_done() # Segnala alla coda che il task è stato completato.
        except Exception as e:
            # Gestisce eccezioni (es. timeout, errori di connessione) e le registra.
            with results_lock:
                results["failure"] += 1
            q.task_done()

# ========================================================================================
#                                  ORCHESTRAZIONE DEL TEST
# ========================================================================================

def main():
    """Funzione principale che orchestra l'intero processo di benchmark."""
    # --- Parsing degli Argomenti da Riga di Comando ---
    parser = argparse.ArgumentParser(description="Client per il benchmark di concorrenza.")
    parser.add_argument("--url", required=True, help="URL dell'endpoint da testare.")
    parser.add_argument("--requests", type=int, default=100, help="Numero totale di richieste da inviare.")
    parser.add_argument("--concurrency", type=int, default=10, help="Numero di richieste concorrenti (threads).")
    args = parser.parse_args()

    # Resetta la struttura dei risultati per ogni esecuzione.
    global results
    results = {"success": 0, "failure": 0, "total_time": 0.0}

    print("--- INIZIO BENCHMARK con Dati Reali ---")
    print(f"URL: {args.url}")
    print(f"Richieste totali: {args.requests}")
    print(f"Concorrenza: {args.concurrency}")
    print("-" * 26)

    # --- Preparazione del Test ---
    # Popola la coda con un numero di "task" pari al numero di richieste da inviare.
    q = Queue()
    for _ in range(args.requests):
        q.put(1)

    # Avvia il cronometro generale per misurare la durata totale del test.
    overall_start_time = time.perf_counter()

    # --- Esecuzione Concorrente ---
    # Crea e avvia il pool di thread worker.
    threads = []
    for _ in range(args.concurrency):
        thread = threading.Thread(target=worker, args=(args.url, q))
        thread.start()
        threads.append(thread)

    # Attende la terminazione di tutti i thread. Il flusso principale si blocca
    # qui finché l'ultimo worker non ha finito il suo lavoro.
    for thread in threads:
        thread.join()

    # Ferma il cronometro generale.
    overall_end_time = time.perf_counter()
    total_duration = overall_end_time - overall_start_time

    # --- Calcolo e Stampa dei Risultati ---
    print("\n--- RISULTATI BENCHMARK ---")
    print(f"Tempo totale: {total_duration:.2f} secondi")
    print(f"Richieste completate con successo: {results['success']}")
    print(f"Richieste fallite: {results['failure']}")

    if results["success"] > 0:
        # Throughput (Requests Per Second)
        rps = results["success"] / total_duration
        # Latenza media
        avg_latency = results["total_time"] / results["success"]
        print(f"Throughput (RPS): {rps:.2f} richieste/secondo")
        print(f"Latenza media per richiesta (lato client): {avg_latency:.2f} secondi")
    print("-" * 27)

# Idioma standard di Python: il codice viene eseguito solo se lo script
# è lanciato direttamente, non se viene importato come modulo.
if __name__ == "__main__":
    main()