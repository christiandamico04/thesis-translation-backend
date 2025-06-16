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

# Create your views here.
class FileViewSet(viewsets.ModelViewSet):
    queryset = File.objects.all()
    serializer_class = FileSerializer

    @action(detail=True, methods=['post'])
    def translate(self, request, pk=None):
        # 1) Prendi il File dal DB
        file_obj = self.get_object()

        # 2) Recupera i parametri
        src = request.data.get('src_language')
        dst = request.data.get('dst_language')
        if not src or not dst:
            return Response(
                {"detail": "src_language e dst_language sono obbligatori"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 3) Leggi il contenuto testo 
        file_path = file_obj.file.path
        with open(file_path, encoding='utf-8') as f:
            original_text = f.read()

        # 4) Chiama il tuo service (mock per ora)
        try:
            translated_text = translate(text=original_text, src=src, dst=dst)
        except TranslationError as e:
            return Response({"detail": f"Errore di traduzione: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 5) Salva in DB la traduzione
        translation = Translation.objects.create(
            file=file_obj,
            src_language=src,
            dst_language=dst,
            original_text=original_text,
            translated_text=translated_text,
            status='done'
        )

        # 6) Rispondi con l’ID e lo status
        return Response(
            {"translation_id": translation.id, "status": translation.status},
            status=status.HTTP_201_CREATED
        )
class TranslationViewSet(viewsets.ModelViewSet):
    queryset = Translation.objects.all()
    serializer_class = TranslationSerializer

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        # 1) Recupera l’istanza di Translation
        translation = self.get_object()

        # 2) Costruisci il nome del file in uscita
        original_name = os.path.basename(translation.file.file.name)
        base, _ext = os.path.splitext(original_name)
        filename = f"{base}_{translation.dst_language}.txt"

        # 3) Crea la response con testo tradotto
        response = HttpResponse(
            translation.translated_text or "",
            content_type='text/plain; charset=utf-8'
        )
        
        # 4) Forza il download dal browser
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
