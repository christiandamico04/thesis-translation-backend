# Le "Viste" contengono la logica che gestisce le richieste HTTP in arrivo. Utilizzano i ViewSet di Django REST Framework per definire gli 
# endpoint dell'API.

import os
from django.http import HttpResponse, FileResponse
from django.shortcuts import render
from rest_framework import viewsets
from .models import File, Translation
from .serializers import FileSerializer, TranslationSerializer
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from .services.translation_service import translate, TranslationError

# Gestisce tutto ciò che riguarda i file. ModelViewSet fornisce automaticamente le operazioni di base (creazione, lettura, aggiornamento, 
# cancellazione).
class FileViewSet(viewsets.ModelViewSet):
    queryset = File.objects.all()
    serializer_class = FileSerializer

    # Metodo chiamato durante la creazione di un file. Viene usato per associare automaticamente il file all'utente autenticato
    # (self.request.user), garantendo che un utente non possa caricare file per conto di un altro.

    def perform_create(self, serializer):
        """Associa l'utente autenticato al file durante la creazione."""
        serializer.save(user=self.request.user)

    # Questo decoratore crea un endpoint API personalizzato (POST /api/files/{id}/translate/)

    @action(detail=True, methods=['post'])
    def translate(self, request, pk=None):

        # 1. Viene preso il File dal DB

        file_obj = self.get_object()

        # 2. Vengono recuperati i parametri

        src = request.data.get('src_language')
        dst = request.data.get('dst_language')
        if not src or not dst:
            return Response(
                {"detail": "src_language e dst_language sono obbligatori"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 3. Viene letto il contenuto testo 

        file_path = file_obj.file.path
        with open(file_path, encoding='utf-8') as f:
            original_text = f.read()

        # 4. Viene chiamata translate da translation_service.py

        try:
            translated_text = translate(text=original_text, src=src, dst=dst)
        except TranslationError as e:
            return Response({"detail": f"Errore di traduzione: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 5. Si salva la traduzione all'interno del database

        translation = Translation.objects.create(
            file=file_obj,
            src_language=src,
            dst_language=dst,
            original_text=original_text,
            translated_text=translated_text,
            status='done'
        )

        # 6. In risposta viene restituito l'ID e lo status

        return Response(
            {"translation_id": translation.id, "status": translation.status},
            status=status.HTTP_201_CREATED
        )

# Gestisce le operazioni sulle traduzioni.
class TranslationViewSet(viewsets.ModelViewSet):
    queryset = Translation.objects.all()
    serializer_class = TranslationSerializer

    # Questo decoratore crea un altro endpoint custom (GET /api/translations/{id}/download/).

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):

        # 1. Si recupera l’istanza di Translation
        
        translation = self.get_object()

        # 2. Viene costruito il nome del file in uscita

        original_name = os.path.basename(translation.file.file.name)
        base, _ext = os.path.splitext(original_name)
        filename = f"{base}_{translation.dst_language}.txt"

        # 3. Si crea la response con testo tradotto

        response = HttpResponse(
            translation.translated_text or "",
            content_type='text/plain; charset=utf-8'
        )
        
        # 4. Viene forzato il download dal browser

        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
