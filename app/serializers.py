# Si pensi a un Serializer come a un traduttore. Django lavora internamente con oggetti Python complessi (istanze di modelli). 
# Il mondo esterno non comprende gli oggetti Python,arla un linguaggio universale per le API web: il JSON (JavaScript Object Notation).

# Il Serializer ha il compito di tradurre in entrambe le direzioni.
# - Serializzazione (Dati in Uscita). Quando l'API deve inviare dati al client, il serializer prende gli oggetti File dal database e li 
# converte in formato JSON.
# - Deserializzazione (Dati in Entrata). Quando un client invia dati all'API (es. richiesta POST), il serializer prende i dati grezzi in 
# formato JSON, li valida per assicurarsi che siano corretti, e li converte in un oggetto Python che Django può capire e salvare nel database.

from rest_framework import serializers                              # Importa gli strumenti necessari da Django REST Framework.
from .models import File, Translation

# La classe ModelSerializer, fornita da DRF, semplifica enormemente la creazione di serializer per i modelli Django. Invece di definire 
# manualmente ogni campo, ModelSerializer ispeziona il modello associato e genera automaticamente i campi corrispondenti con le validazioni 
# di base (es. un CharField nel modello diventa un campo stringa nel JSON).
class FileSerializer(serializers.ModelSerializer):
    class Meta:
        model = File                                                # Indica a ModelSerializer quale modello del database deve usare come riferimento.
        fields = '__all__'                                          # È una scorciatoia per dire "includi tutti i campi del modello File nel processo di traduzione".
        
        # Questa impostazione rende il campo user di sola lettura. Il campo user sarà incluso quando i dati vengono inviati al client 
        # (serializzazione), ma sarà ignorato e non considerato quando i dati arrivano dal client (deserializzazione e validazione).
        # Ciò impedisce a un utente malintenzionato di specificare l'ID di un altro utente nel JSON inviato per tentare di caricare un 
        # file a nome di qualcun altro. La responsabilità di associare il file all'utente corretto spetta al backend, che sa chi è l'utente 
        # autenticato dalla richiesta. Ciò è in accordo con la logica in app/views.py nel metodo perform_create, dove viene impostato l'utente 
        # con serializer.save(user=self.request.user). 
        
        read_only_fields = ('user',)                

# Questo è un altro ModelSerializer standard per il modello Translation. In questo caso, tutti i campi vengono esposti sia in lettura che in 
# scrittura, senza restrizioni particolari.
class TranslationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Translation
        fields = '__all__'
