# thesis-translation-backend/download_nltk.py

import nltk
import os

# Definiamo una cartella locale dove salvare i dati
DOWNLOAD_DIR = './nltk_data'

if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)
    print(f"Cartella '{DOWNLOAD_DIR}' creata.")

print(f"Inizio download dei pacchetti NLTK in '{DOWNLOAD_DIR}'...")

# 1. Scarica il pacchetto 'punkt' principale
print("Download di 'punkt'...")
nltk.download('punkt', download_dir=DOWNLOAD_DIR)

# 2. AGGIUNGI QUESTO: Scarica il pacchetto 'punkt_tab' richiesto dall'errore
print("Download di 'punkt_tab'...")
nltk.download('punkt_tab', download_dir=DOWNLOAD_DIR)

print("\nDownload completato.")
print(f"Ora la cartella '{DOWNLOAD_DIR}' contiene tutte le risorse necessarie.")