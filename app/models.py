from django.db import models
from django.contrib.auth.models import User

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
