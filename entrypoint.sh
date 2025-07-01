#!/bin/sh
# ========================================================================================
#                SCRIPT DI ENTRYPOINT PER IL CONTAINER 'web'
# ========================================================================================
# Questo script funge da punto di ingresso per il container dell'applicazione Django.
# Il suo scopo è eseguire una sequenza di operazioni di inizializzazione *al runtime*,
# prima di avviare il processo principale dell'applicazione (il server Gunicorn).
# Questo garantisce che l'ambiente sia correttamente preparato.
#-----------------------------------------------------------------------------------------

# Questa operazione preliminare assicura che lo script ausiliario 'wait-for-it.sh'
# abbia i permessi di esecuzione. È una misura di robustezza, utile specialmente
# quando si lavora con volumi montati da sistemi operativi come Windows (via WSL)
# che possono non preservare correttamente i permessi dei file. 
chmod +x /code/wait-for-it.sh

# Imposta l'opzione 'exit on error'. Se un qualsiasi comando dello script fallisce
# (restituisce un codice di uscita diverso da zero), lo script terminerà immediatamente.
# Questo previene comportamenti imprevisti e assicura un fail-fast.
set -e

# --- 1. Attesa della Disponibilità del Database ---
# Questa è una fase critica per la stabilità dell'architettura a microservizi.
# Risolve una classica "race condition" in cui l'applicazione potrebbe avviarsi
# prima che il database sia pronto a ricevere connessioni.
echo "Waiting for database to be ready..."
# Utilizza lo script 'wait-for-it.sh' per mettere in pausa l'esecuzione finché
# la porta 5432 del servizio 'db' non diventa disponibile, con un timeout di 90 secondi. 
/code/wait-for-it.sh db:5432 -t 90

# --- 2. Applicazione delle Migrazioni del Database ---
# Una volta che il database è confermato come disponibile, si procede con le operazioni su di esso.
echo "Database is ready. Applying migrations..."
# Esegue il comando di migrazione di Django. Questo assicura che lo schema del
# database sia sempre sincronizzato con i modelli definiti nel codice dell'applicazione
# ad ogni avvio del container.
python manage.py migrate

# --- 3. Avvio del Server Applicativo ---
echo "Starting Gunicorn web server..."
# Avvia il server Gunicorn per servire l'applicazione Django.
# La parola chiave 'exec' è fondamentale: sostituisce il processo corrente (lo shell script)
# con il processo di Gunicorn. Questo rende Gunicorn il processo principale (PID 1)
# del container, permettendogli di ricevere correttamente i segnali dal Docker daemon
# (es. SIGTERM) per uno spegnimento controllato (graceful shutdown).
# Parametri di Gunicorn:
#   --bind 0.0.0.0:8000: Ascolta le richieste su tutte le interfacce di rete sulla porta 8000.
#   --workers 2: Avvia 2 processi worker per gestire le richieste in parallelo.
#   --threads 4: Ogni worker utilizzerà 4 thread, aumentando ulteriormente la concorrenza.
#   --timeout 600: Imposta un timeout di 600 secondi per le richieste lente.
exec gunicorn core.wsgi:application --bind 0.0.0.0:8000 --workers 2 --threads 4 --timeout 600