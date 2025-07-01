# **thesis-translation-backend**

Questo documento fornisce una guida completa al backend del progetto di traduzione, dalla sua filosofia architetturale alle procedure pratiche per il testing e la verifica funzionale.

-----

## **Panoramica del Progetto**

`thesis-translation-backend` è un'applicazione web progettata per offrire traduzioni automatiche di alta qualità partendo da file di testo. L'obiettivo è fornire a utenti e aziende uno strumento per efficientare i flussi di lavoro legati alla localizzazione di contenuti, come materiali di marketing, documentazione tecnica o configurazioni di prodotto.

Lo spirito del progetto si basa su principi di ingegneria del software moderni:

  * **Architettura a Microservizi**: Il sistema è disaccoppiato in servizi indipendenti e specializzati (gestione API, inferenza AI, database), garantendo scalabilità, manutenibilità e resilienza.
  * **Containerizzazione**: L'intero stack applicativo è containerizzato tramite Docker e orchestrato con Docker Compose. Questo assicura un ambiente di esecuzione riproducibile e portabile, annullando le problematiche di compatibilità tra macchina di sviluppo e di produzione.
  * **Performance**: L'utilizzo di `vLLM` per l'inferenza del modello linguistico e l'accesso diretto alle GPU NVIDIA garantiscono traduzioni rapide, anche per grandi volumi di testo.
  * **Caching Intelligente**: Per ottimizzare le performance e ridurre i costi computazionali, è stato implementato un meccanismo di cache a livello di servizio. Le richieste di traduzione identiche vengono servite istantaneamente dalla memoria, bypassando la costosa chiamata al modello AI.

-----

## **Architettura e Servizi Principali**

L'applicazione è composta dai seguenti servizi containerizzati, definiti nel file `docker-compose.yml`:

1.  **`web` (Django Application)**

      * È il cuore dell'applicazione, che espone le API RESTful per la gestione degli utenti, dei file e delle traduzioni.
      * Gestisce l'autenticazione tramite JSON Web Tokens (JWT).
      * Implementa la logica di business, incluso il *chunking* (suddivisione) di testi lunghi per rispettare i limiti dei modelli AI.

2.  **`vllm-server` (AI Inference Server)**

      * Un servizio specializzato che esegue il modello linguistico (`google/gemma-2b-it`) con performance ottimizzate grazie a vLLM e all'accelerazione hardware su GPU.
      * Espone un'API compatibile con lo standard OpenAI per ricevere i testi da tradurre e restituire i risultati.

3.  **`db` (Database PostgreSQL)**

      * Un'istanza del database relazionale PostgreSQL per la persistenza dei dati relativi a utenti, file e traduzioni.

4.  **`benchmark-service` (Test Service)**

      * Un servizio ausiliario basato su FastAPI per eseguire test di performance e qualità in un ambiente isolato.

-----

## **Guida al Deployment e Verifica Funzionale**

Questa sezione contiene i comandi essenziali per gestire l'ambiente e un workflow dettagliato per testare le funzionalità principali dell'API.

### **Comandi di Gestione dell'Ambiente**

  * **Avviare l'ambiente (in background):**
    ```bash
    docker-compose up -d --build
    ```
  * **Fermare l'ambiente:**
    ```bash
    docker-compose down
    ```
  * **Visualizzare i log di un servizio (es. `web`):**
    ```bash
    docker-compose logs -f web
    ```
  * **Visualizzare i log di tutti i servizi:**
    ```bash
    docker-compose logs -f
    ```
  * **Creazione di un SuperUser:**
    ```bash
    docker-compose exec web python manage.py createsuperuser
    ```
    

### **Workflow di Verifica Funzionale**

Questo workflow testa il ciclo di vita completo di un'interazione utente. Per eseguirlo, copia l'intero blocco di codice seguente, salvalo in un file (es. `test_workflow.sh`), rendilo eseguibile (`chmod +x test_workflow.sh`) ed eseguilo (`./test_workflow.sh`).

**Preparazione:**
Assicurati di avere tre file, `test1.txt`, `test2.txt` e `test3.txt` nella stessa cartella in cui eseguirai lo script.

```bash
#!/bin/bash

# ===================================================================
#           SCRIPT DI TEST FUNZIONALE AUTOMATIZZATO
# ===================================================================

# Imposta il nome del file da testare (cambia a "test2.txt" per il secondo test)
FILE_TO_TEST="test3.txt"
BASE_URL="http://localhost:8000"

# --- 1. Creazione di un utente per i test ---
echo "--- 1. Creazione utente 'admin' ---"
curl -s -X POST $BASE_URL/api/register/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin"}' > /dev/null
echo "Utente creato."

# --- 2. Prova di accesso senza token (fallimento atteso) ---
echo -e "\n--- 2. Tentativo di accesso senza token (atteso 401 Unauthorized) ---"
curl -s -i -X GET $BASE_URL/api/files/ | head -n 1
echo ""

# --- 3. Ottenimento di un token di autorizzazione ---
echo -e "\n--- 3. Ottenimento Token JWT ---"
TOKENS_JSON=$(curl -s -X POST $BASE_URL/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin"}')
ACCESS_TOKEN=$(echo $TOKENS_JSON | jq -r '.access')
REFRESH_TOKEN=$(echo $TOKENS_JSON | jq -r '.refresh')
echo "Access Token ottenuto!"

# --- 4. Accesso all'endpoint protetto con il token ---
echo -e "\n--- 4. Accesso a endpoint protetto (successo) ---"
curl -s -X GET $BASE_URL/api/files/ \
  -H "Authorization: Bearer $ACCESS_TOKEN"
echo -e "\nAccesso riuscito."

# --- 5. Caricamento di un file ---
echo -e "\n--- 5. Caricamento file: $FILE_TO_TEST ---"
FILE_SIZE=$(wc -c < "$FILE_TO_TEST")
UPLOAD_RESPONSE=$(curl -s -X POST $BASE_URL/api/files/ \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "file=@$FILE_TO_TEST" \
  -F "name=$FILE_TO_TEST" \
  -F "size=$FILE_SIZE")
FILE_ID=$(echo $UPLOAD_RESPONSE | jq -r '.id')
echo "File caricato con ID: $FILE_ID"

# --- 6. Richiesta di traduzione del file ---
echo -e "\n--- 6. Richiesta di traduzione (Italiano -> Inglese) ---"
TRANSLATE_RESPONSE=$(curl -s -X POST $BASE_URL/api/files/$FILE_ID/translate/ \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"src_language": "it", "dst_language": "en"}')
TRANSLATION_ID=$(echo $TRANSLATE_RESPONSE | jq -r '.translation_id')
echo "Traduzione avviata con ID: $TRANSLATION_ID"

# --- 7. Verifica dello Stato della Traduzione (Polling) ---
echo -e "\n--- 7. Attesa completamento traduzione... ---"
while true; do
  STATUS_RESPONSE=$(curl -s -X GET $BASE_URL/api/translations/$TRANSLATION_ID/ \
    -H "Authorization: Bearer $ACCESS_TOKEN")
  STATUS=$(echo $STATUS_RESPONSE | jq -r '.status')
  echo "Stato attuale: $STATUS"
  if [ "$STATUS" == "done" ]; then
    echo "Traduzione completata!"
    break
  fi
  sleep 5
done

# --- 8. Download del file tradotto ---
echo -e "\n--- 8. Download del file tradotto ---"
curl -s -X GET $BASE_URL/api/translations/$TRANSLATION_ID/download/ \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -o "tradotto_${FILE_TO_TEST}"
echo "File salvato in 'tradotto_${FILE_TO_TEST}'. Contenuto:"
cat "tradotto_${FILE_TO_TEST}"
echo ""

# --- BONUS: Refresh di Access Token ---
echo -e "\n--- BONUS. Refresh del Token ---"
NEW_TOKEN_JSON=$(curl -s -X POST $BASE_URL/api/token/refresh/ \
  -H "Content-Type: application/json" \
  -d "{\"refresh\": \"$REFRESH_TOKEN\"}")
NEW_ACCESS_TOKEN=$(echo $NEW_TOKEN_JSON | jq -r '.access')
echo "Nuovo Access Token ottenuto!"
echo "Verifica nuovo token accedendo a /api/files/..."
curl -s -X GET $BASE_URL/api/files/ \
  -H "Authorization: Bearer $NEW_ACCESS_TOKEN"
echo -e "\nVerifica con nuovo token riuscita.\n"

echo "Workflow di test completato."
```

-----

## **Guida ai Test di Performance e Qualità**

Questo workflow utilizza gli script presenti nella cartella `benchmark-tests` per valutare il sistema.

### **Fase 1: Esecuzione dei Test di Performance**

**Obiettivo:** Misurare la velocità (Throughput in Richieste/Secondo).
**Script:** `benchmark_client.py`

#### **SCENARIO A: Test su vLLM**

1.  **Pulisci e Avvia:**
    ```bash
    docker-compose down -v && docker-compose up -d vllm-server benchmark-service
    ```
2.  **Attendi:** Lascia ai servizi circa 2 minuti per avviarsi. Controlla lo stato con `docker-compose logs -f vllm-server` e attendi che il modello sia caricato.
3.  **Esegui il Test di Performance:**
    ```bash
    python3 benchmark-tests/benchmark_client.py --url http://localhost:8002/benchmark/with-vllm --requests 100 --concurrency 10
    ```
4.  **Annota** i risultati (specialmente il valore **Throughput (RPS)**).

#### **SCENARIO B: Test su Transformers (Senza vLLM)**

1.  **Pulisci e Avvia:** (Passaggio Fondamentale\!)
    ```bash
    docker-compose down -v && docker-compose up -d benchmark-service
    ```
2.  **Riscalda il Modello:** Attendi che questo comando finisca. Sarà lento.
    ```bash
    python3 benchmark-tests/benchmark_client.py --url http://localhost:8002/benchmark/without-vllm --requests 1 --concurrency 1
    ```
3.  **Esegui il Test di Performance:**
    ```bash
    python3 benchmark-tests/benchmark_client.py --url http://localhost:8002/benchmark/without-vllm --requests 100 --concurrency 10
    ```
4.  **Salva e confronta** i risultati con quelli dello Scenario A.

-----

### **Fase 2: Esecuzione dei Test di Qualità**

**Obiettivo:** Misurare la correttezza delle traduzioni (punteggi BLEU e COMET).
**Script:** `quality_checker.py`

#### **SCENARIO A: Test su vLLM**

1.  **Pulisci e Avvia:**
    ```bash
    docker-compose down -v && docker-compose up -d vllm-server benchmark-service
    ```
2.  **Attendi:** Aspetta che `vllm-server` sia completamente avviato.
3.  **Configura ed Esegui:**
      * Apri il file `benchmark-tests/quality_checker.py` e assicurati che la variabile `API_URL` sia impostata su `".../with-vllm"`.
      * Lancia lo script:
        ```bash
        python3 benchmark-tests/quality_checker.py
        ```
4.  **Annota** i punteggi **BLEU** e **COMET**.

#### **SCENARIO B: Test su Transformers (Senza vLLM)**

1.  **Pulisci e Avvia:**
    ```bash
    docker-compose down -v && docker-compose up -d benchmark-service
    ```
2.  **Riscalda il Modello:**
    ```bash
    python3 benchmark-tests/benchmark_client.py --url http://localhost:8002/benchmark/without-vllm --requests 1 --concurrency 1
    ```
3.  **Configura ed Esegui:**
      * Modifica il file `benchmark-tests/quality_checker.py` e imposta la variabile `API_URL` su `".../without-vllm"`.
      * Lancia lo script:
        ```bash
        python3 benchmark-tests/quality_checker.py
        ```
4.  **Salva e confronta** i punteggi con quelli dello Scenario A.

##### **Guida ai Test Automatici (Unitari e di Integrazione)**

Questa sezione descrive come eseguire la suite di test automatici definita in `app/tests.py`. Questi test verificano la logica interna dell'applicazione (modelli, servizi) e gli endpoint API in un ambiente controllato. Utilizzano un database di test temporaneo e simulano le chiamate ai servizi esterni (mocking), quindi **non richiedono che i container Docker siano in esecuzione**.

**Prerequisiti:**

  * Un ambiente virtuale (`venv`) deve essere stato creato.

**Procedura di Esecuzione:**

1.  **Attiva l'ambiente virtuale**
    Assicurati di essere nella cartella principale del progetto, poi esegui:

    ```bash
    source venv/bin/activate
    ```

2.  **Installa le dipendenze**
    Questo comando installerà Django e le altre librerie necessarie all'interno del tuo `venv`.

    ```bash
    pip install -r requirements.txt
    ```

3.  **Lancia la suite di test**
    Esegui il comando di test di Django, fornendo una `SECRET_KEY` fittizia per la durata del comando.

    ```bash
    SECRET_KEY='dummy-key-for-testing' python manage.py test app
    ```

4.  **Interpreta i risultati**

      * Un output di successo terminerà con `OK`, indicando che tutti i test sono stati superati.
      * In caso di fallimento, vedrai un riepilogo degli errori (`FAILED`) con i dettagli per ogni test non superato.

5.  **Disattiva l'ambiente virtuale**
    Una volta terminato, puoi disattivare l'ambiente con il comando:

    ```bash
    deactivate
    ```