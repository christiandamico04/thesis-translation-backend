#!/bin/bash

# ==============================================================================
# Script per creare un dump testuale di un progetto, includendo la struttura
# delle cartelle e il contenuto dei file rilevanti.
# VERSIONE CORRETTA SULLA BASE DELLA DIAGNOSI
# ==============================================================================

# Nome del file di output
OUTPUT_FILE="project_dump.txt"

# Directory del progetto (usiamo la directory corrente)
PROJECT_ROOT="."

# --- Pulisce il file di output se esiste già ---
> "$OUTPUT_FILE"

echo "===========================================================" >> "$OUTPUT_FILE"
echo " DUMP DEL PROGETTO: thesis-translation-backend" >> "$OUTPUT_FILE"
echo " Generato il: $(date)" >> "$OUTPUT_FILE"
echo "===========================================================" >> "$OUTPUT_FILE"
echo -e "\n" >> "$OUTPUT_FILE"

# --- 1. Aggiunge la struttura del progetto con 'tree' ---
echo "-----------------------------------------------------------" >> "$OUTPUT_FILE"
echo " STRUTTURA DEL PROGETTO" >> "$OUTPUT_FILE"
echo "-----------------------------------------------------------" >> "$OUTPUT_FILE"
if command -v tree &> /dev/null
then
    # CORREZIONE: Esclusa la cartella 'venv'
    tree -a -I ".git|venv|__pycache__|migrations|nltk_data|media|db.sqlite3|*.pyc|benchmark-service|quality_test.csv|$OUTPUT_FILE" "$PROJECT_ROOT" >> "$OUTPUT_FILE"
else
    echo "[INFO] Il comando 'tree' non è installato. Struttura non generata." >> "$OUTPUT_FILE"
    echo "[INFO] Puoi installarlo con: sudo apt-get update && sudo apt-get install tree" >> "$OUTPUT_FILE"
fi
echo -e "\n\n" >> "$OUTPUT_FILE"

# --- 2. Aggiunge il contenuto dei file ---
echo "-----------------------------------------------------------" >> "$OUTPUT_FILE"
echo " CONTENUTO DEI FILE" >> "$OUTPUT_FILE"
echo "-----------------------------------------------------------" >> "$OUTPUT_FILE"

find "$PROJECT_ROOT" -type f | while read -r file; do
    # Logica di esclusione potenziata
    case "$file" in
        # --- ESCLUSIONE DI INTERE CARTELLE ---
        # CORREZIONE: Esclusi i file dentro 'venv' (il nome corretto)
        */.git/*|*/venv/*|*/__pycache__/*|*/migrations/*|*/nltk_data/*|*/media/*|*/benchmark-service/*)
            continue
            ;;

        # --- ESCLUSIONE DI FILE SPECIFICI O PER ESTENSIONE ---
        # Esclusioni di sicurezza per file di dati/modelli di grandi dimensioni
        *db.sqlite3|*.pyc|*.log|*.env*|./$OUTPUT_FILE|*quality_test.csv|*.bin|*.model|*.pt|*.pth|*.safetensors|*.onnx|*.h5)
            continue
            ;;

        # Escludi lo script stesso
        *copia_progetto.sh)
            continue
            ;;
    esac

    # Aggiungi il contenuto del file all'output
    echo "--- FILE: $file ---" >> "$OUTPUT_FILE"
    cat "$file" >> "$OUTPUT_FILE"
    echo -e "\n\n" >> "$OUTPUT_FILE"
done

# --- 3. Aggiunge note per le cartelle omesse ---
echo "-----------------------------------------------------------" >> "$OUTPUT_FILE"
echo " NOTE SULLE CARTELLE E FILE OMESSI" >> "$OUTPUT_FILE"
echo "-----------------------------------------------------------" >> "$OUTPUT_FILE"
echo "--- NOTA: Il contenuto delle seguenti cartelle è stato omesso intenzionalmente:" >> "$OUTPUT_FILE"
echo "    'venv' (ambiente virtuale)" >> "$OUTPUT_FILE"
echo "    'media' (file caricati dagli utenti)" >> "$OUTPUT_FILE"
echo "    'benchmark-service' (servizio di benchmark, potenziale fonte di file di grandi dimensioni)" >> "$OUTPUT_FILE"
echo "    '.git', '__pycache__', 'migrations', 'nltk_data'" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"
echo "--- NOTA: File di dati di grandi dimensioni (es. quality_test.csv) e modelli (.bin, .pt, ecc.) sono stati esclusi." >> "$OUTPUT_FILE"
echo "-----------------------------------------------------------" >> "$OUTPUT_FILE"


echo "Fatto! L'output del progetto è stato salvato in: $OUTPUT_FILE"