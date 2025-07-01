# ========================================================================================
#                DOCKERFILE PER IL SERVIZIO DI BENCHMARK
# ========================================================================================
# Questo Dockerfile definisce l'ambiente di esecuzione per il 'benchmark-service',
# un'applicazione FastAPI ausiliaria utilizzata per il testing di performance e qualità.
# -----------------------------------------------------------------------------------------

# --- FASE 1: Immagine di Base ---
# Si parte da un'immagine base ufficiale di Python, versione 3.11.
# La variante '-slim' è stata scelta in quanto è ottimizzata per ridurre la
# dimensione finale dell'immagine, omettendo pacchetti di sistema non essenziali.
# Questa è una best practice per la creazione di microservizi leggeri.
FROM python:3.11-slim

# --- FASE 2: Configurazione dell'Ambiente ---
# Imposta la directory di lavoro predefinita all'interno del container.
# Tutti i comandi successivi (COPY, RUN, CMD) verranno eseguiti a partire
# da questo percorso, migliorando la leggibilità e la manutenibilità del file.
WORKDIR /code

# --- FASE 3: Installazione delle Dipendenze ---
# Questa sezione è strutturata per ottimizzare il sistema di caching a layer di Docker.

# Copia *unicamente* il file delle dipendenze. Questo passo crea un layer
# che verrà invalidato e rieseguito solo se il file 'requirements.txt' cambia.
COPY requirements.txt .

# Installa le librerie Python elencate in requirements.txt.
# L'opzione '--no-cache-dir' riduce la dimensione dell'immagine finale, evitando
# di salvare la cache di pip. Questo layer verrà riutilizzato nelle build successive
# se le dipendenze non sono cambiate, accelerando significativamente il processo.
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# --- FASE 4: Aggiunta del Codice dell'Applicazione ---
# Copia il resto del codice sorgente del servizio nella directory di lavoro.
# Questo comando viene eseguito dopo l'installazione delle dipendenze per
# sfruttare il caching: le modifiche al codice (più frequenti) non
# invalideranno il layer delle dipendenze (meno frequenti).
COPY . .