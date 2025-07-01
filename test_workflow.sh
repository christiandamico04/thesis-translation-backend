#!/bin/bash

# ===================================================================
#           SCRIPT DI TEST FUNZIONALE AUTOMATIZZATO
# ===================================================================

# Imposta il nome del file da testare (cambia a "test2.txt" per il secondo test)
FILE_TO_TEST="test3.txt"
BASE_URL="http://localhost:8000"

# --- 1. Creazione di un utente per i test ---
echo "--- 1. Creazione utente 'testuser' ---"
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