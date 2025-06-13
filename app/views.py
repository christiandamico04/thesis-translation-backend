from django.shortcuts import render
from rest_framework import viewsets
from .models import File, Translation
from .serializers import FileSerializer, TranslationSerializer

# Create your views here.
class FileViewSet(viewsets.ModelViewSet):
    queryset = File.objects.all()
    serializer_class = FileSerializer
class TranslationViewSet(viewsets.ModelViewSet):
    queryset = Translation.objects.all()
    serializer_class = TranslationSerializer
