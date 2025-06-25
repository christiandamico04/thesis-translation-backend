# Questo file definisce la struttura del database tramite l'ORM (Object-Relational Mapper) di Django. Ogni classe corrisponde 
# a una tabella nel database e i suoi attributi alle colonne della tabella.

from django.db import models
from django.contrib.auth.models import User
from django.core.files.storage import default_storage

# File: rappresenta un file caricato da un utente.
class File(models.Model):

    # Crea una relazione con il modello Utente standard di Django. on_delete=models.CASCADE è una regola cruciale: se un utente 
    # viene cancellato, tutti i file a lui associati vengono automaticamente cancellati a cascata.
    # Costituisce la FK user_id.

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='files'
    ) 
    name = models.CharField(max_length=255)
    file = models.FileField(upload_to='uploads/')
    size = models.PositiveIntegerField()
    status = models.CharField(max_length=20, default='uploaded')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Questo metodo è stato sovrascritto per aggiungere una funzionalità importante. Quando un record File viene eliminato dal database, 
    # questo codice si assicura che anche il file fisico corrispondente venga cancellato dal disco (/media/uploads/). Questo previene 
    # l'accumulo di file "orfani" sul server.

    def delete(self, *args, **kwargs):
        if self.file:                                               # Si controlla se c'è un file associato prima di fare qualsiasi cosa
            file_name = self.file.name                              # Si memorizza il nome del file prima di cancellare l'oggetto
            super().delete(*args, **kwargs)                         # Il record dal database viene cancellato
            
            if default_storage.exists(file_name):                   # Si usa l'API di storage per cancellare il file fisico
                default_storage.delete(file_name)
        else:
            super().delete(*args, **kwargs)                         # Qualora non ci sia alcun file, viene cancellato solo il record

# Translation: rappresenta il risultato di una traduzione
class Translation(models.Model):

    # Collega ogni traduzione al suo file sorgente. Anche qui, on_delete=models.CASCADE assicura che cancellando un file vengano eliminate 
    # anche tutte le sue traduzioni associate.
    # Costituisce la FK file_id.

    file = models.ForeignKey(
        File,
        on_delete=models.CASCADE,
        related_name='translations'
    ) 
    src_language = models.CharField(max_length=8)
    dst_language = models.CharField(max_length=8)
    original_text = models.TextField()
    translated_text = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

# N.B. Le PK di File e di Translation sono generate automaticamente.