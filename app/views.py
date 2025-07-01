"""Definizione degli endpoint dell'API (Controller Layer).

Questo modulo implementa il "Controller Layer" dell'architettura, gestendo le
richieste HTTP in arrivo e orchestrando la logica di business. Utilizza i ViewSet
di Django REST Framework (DRF) per definire in modo strutturato gli endpoint
dell'API RESTful, separando le responsabilità di gestione delle richieste dalla
logica applicativa (delegata al "Service Layer") e dalla persistenza dei dati
(gestita dai "Model Layer" e dall'ORM di Django).
"""

# ========================================================================================
#                                  IMPORT E CONFIGURAZIONE
# ========================================================================================
import os
from django.http import HttpResponse
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny

from .models import File, Translation
from .serializers import FileSerializer, TranslationSerializer, UserSerializer
from .services.translation_service import translate, TranslationError

# ========================================================================================
#                                        VIEWSETS
# ========================================================================================
class FileViewSet(viewsets.ModelViewSet):
    """ViewSet per la gestione delle risorse 'File'.

    Espone un set completo di endpoint CRUD (Create, Retrieve, Update, Delete)
    per il modello `File`. L'uso di `ModelViewSet` astrae la logica ripetitiva,
    generando automaticamente gli handler per le operazioni standard.
    """
    queryset = File.objects.all()
    serializer_class = FileSerializer

    def perform_create(self, serializer):
        """Hook per associare l'utente autenticato durante la creazione del file.

        Questo metodo, fornito da DRF, viene invocato come "hook" nel ciclo di vita
        della creazione di un'istanza. Viene sovrascritto per iniettare l'utente
        autenticato (`self.request.user`) nel processo di salvataggio. Questa è una
        best practice di sicurezza che garantisce l'associazione corretta della
        proprietà del file, prevenendo che un utente possa impersonare un altro.
        """
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def translate(self, request, pk=None):
        """Azione personalizzata per avviare il processo di traduzione di un file.

        Questo endpoint orchestra il workflow di traduzione:
        1. Recupera l'oggetto File dal database.
        2. Valida i parametri della richiesta (lingue di origine e destinazione).
        3. Legge il contenuto testuale dal file fisico.
        4. Delega l'operazione computazionalmente intensiva al `translation_service`.
        5. Persiste il risultato della traduzione nel database.
        6. Restituisce una risposta con l'ID della nuova risorsa creata.

        Args:
            request: L'oggetto della richiesta HTTP, contenente i dati.
            pk (int): La chiave primaria del file da tradurre.

        Returns:
            Response: Una risposta DRF con status code e dati JSON.
        """
        # 1. Recupero dell'istanza del modello File.
        #    Il metodo `get_object()` gestisce automaticamente il lookup e le eccezioni 404.
        file_obj = self.get_object()

        # 2. Validazione dei parametri della richiesta.
        src = request.data.get('src_language')
        dst = request.data.get('dst_language')
        if not src or not dst:
            return Response(
                {"detail": "I campi 'src_language' e 'dst_language' sono obbligatori."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 3. Lettura del contenuto dal file system.
        file_path = file_obj.file.path
        with open(file_path, encoding='utf-8') as f:
            original_text = f.read()

        # 4. Invocazione del Service Layer per la logica di traduzione.
        #    Questa delega mantiene il ViewSet "leggero" e focalizzato sulla gestione HTTP.
        try:
            translated_text = translate(text=original_text, src=src, dst=dst)
        except TranslationError as e:
            # Gestione degli errori specifici del dominio sollevati dal service layer.
            return Response({"detail": f"Errore di traduzione: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 5. Creazione e persistenza della nuova risorsa 'Translation'.
        translation = Translation.objects.create(
            file=file_obj,
            src_language=src,
            dst_language=dst,
            original_text=original_text,
            translated_text=translated_text,
            status='done'
        )

        # 6. Formulazione della risposta HTTP 201 Created.
        return Response(
            {"translation_id": translation.id, "status": translation.status},
            status=status.HTTP_201_CREATED
        )
class TranslationViewSet(viewsets.ModelViewSet):
    """ViewSet per la gestione delle risorse 'Translation'.

    Fornisce endpoint CRUD standard per visualizzare, modificare o eliminare
    le traduzioni esistenti. Include anche un'azione custom per il download.
    """
    queryset = Translation.objects.all()
    serializer_class = TranslationSerializer

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Azione personalizzata per scaricare il testo tradotto come file.

        Costruisce dinamicamente una risposta HTTP di tipo `text/plain`.
        Utilizza l'header `Content-Disposition` con il valore `attachment` per
        indicare al browser di trattare la risposta come un file da scaricare,
        invece di visualizzarla direttamente.

        Args:
            request: L'oggetto della richiesta HTTP.
            pk (int): La chiave primaria della traduzione da scaricare.

        Returns:
            HttpResponse: Una risposta file che il browser interpreterà come download.
        """
        # 1. Recupero dell'istanza del modello Translation.
        translation = self.get_object()

        # 2. Costruzione dinamica del nome del file di output.
        original_name = os.path.basename(translation.file.file.name)
        base, _ext = os.path.splitext(original_name)
        filename = f"{base}_{translation.dst_language}.txt"

        # 3. Creazione della risposta HTTP con il testo tradotto.
        response = HttpResponse(
            translation.translated_text or "",
            content_type='text/plain; charset=utf-8'
        )

        # 4. Impostazione dell'header per forzare il download.
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
class UserRegistrationView(APIView):
    """Endpoint dedicato per la registrazione di nuovi utenti.

    A differenza dei ViewSet, utilizza la classe base `APIView` per una maggiore
    flessibilità. Fondamentalmente, la classe di permessi è impostata su `AllowAny`
    per consentire a utenti non autenticati di accedere a questo specifico endpoint
    e creare un nuovo account.
    """
    # Sovrascrive la policy di permessi di default (`IsAuthenticated`)
    # per rendere questo endpoint pubblico.
    permission_classes = [AllowAny]
    serializer_class = UserSerializer

    def post(self, request):
        """Gestisce la creazione di un nuovo utente."""
        # Il pattern è standard: deserializzare e validare i dati in ingresso.
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            # Il metodo `create` del serializer si occuperà di creare l'utente
            # con una password correttamente hashata.
            serializer.save()
            # Restituisce i dati dell'utente creato e uno status 201.
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        # In caso di dati non validi, restituisce gli errori e uno status 400.
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)