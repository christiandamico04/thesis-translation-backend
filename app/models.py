from django.db import models
from django.contrib.auth.models import User
from django.core.files.storage import default_storage

# Create your models here.

class File(models.Model):
    # PK id generata automaticamente
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='files'
    )  # FK user_id
    name = models.CharField(max_length=255)
    file = models.FileField(upload_to='uploads/')
    size = models.PositiveIntegerField()
    status = models.CharField(max_length=20, default='uploaded')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def delete(self, *args, **kwargs):
        # Controlla se c'è un file associato prima di fare qualsiasi cosa
        if self.file:
            # Memorizza il nome del file prima di cancellare l'oggetto
            file_name = self.file.name
            
            # Cancella il record dal DB
            super().delete(*args, **kwargs)
            
            # Ora, usa l'API di storage per cancellare il file fisico
            if default_storage.exists(file_name):
                default_storage.delete(file_name)
        else:
            # Se non c'era nessun file, cancella solo il record
            super().delete(*args, **kwargs)

class Translation(models.Model):
    # PK id generata automaticamente
    file = models.ForeignKey(
        File,
        on_delete=models.CASCADE,
        related_name='translations'
    )  # FK file_id
    src_language = models.CharField(max_length=8)
    dst_language = models.CharField(max_length=8)
    original_text = models.TextField()
    translated_text = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
