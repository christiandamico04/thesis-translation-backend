from django.shortcuts import render
from rest_framework import viewsets
from .models import File, Translation
from .serializers import FileSerializer, TranslationSerializer
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from .services.translation_service import translate

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
        translated_text = translate(original_text, src, dst)

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
