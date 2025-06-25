# Il Dockerfile serve per costruire una singola immagine Docker. Un'immagine è un pacchetto autonomo, leggero e portabile che contiene tutto 
# il necessario per eseguire un'applicazione: codice, Python, librerie di sistema, variabili d'ambiente e file di configurazione.

# Si inizia da un'immagine base ufficiale di NVIDIA che contiene CUDA e Ubuntu 22.04.
# Questa è la scelta ideale per applicazioni di AI che necessitano della GPU.
FROM nvidia/cuda:12.1.1-runtime-ubuntu22.04

# Imposta variabili d'ambiente per evitare che le installazioni richiedano input manuali.
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Si imposta /code come directory di lavoro predefinita all'interno dell'immagine.
WORKDIR /code

# Installa le dipendenze di sistema necessarie per il progetto: Python 3.11 e il suo package manager (pip).
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Crea un link simbolico per poter usare il comando "python" invece di "python3.11" per comodità.
RUN ln -s /usr/bin/python3.11 /usr/bin/python

# Si copiano e si installano prima solo le dipendenze, che vengono salvate in uno strato (layer) separato.
# Questo sfrutta la cache di Docker per velocizzare build successive se il file requirements.txt non cambia.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Ora si copia tutto il resto del codice sorgente del progetto nella directory di lavoro.
COPY . .

# Copia lo script di avvio personalizzato (entrypoint.sh) e lo rende eseguibile.
# Usare un entrypoint è una pratica migliore perché permette di eseguire comandi preparatori (es. migrazioni DB) prima di avviare l'app.
COPY ./entrypoint.sh /code/entrypoint.sh
RUN chmod +x /code/entrypoint.sh

# Specifica lo script di entrypoint come comando di default da eseguire quando un container viene avviato da questa immagine.
ENTRYPOINT ["/code/entrypoint.sh"]