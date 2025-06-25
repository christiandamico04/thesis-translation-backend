# Questo file serve a configurare l'Interfaccia di Amministrazione di Django. Django fornisce un'area di amministrazione web 
# "pronta all'uso" che permette agli sviluppatori di visualizzare, creare, modificare e cancellare i record nel database attraverso 
# un'interfaccia grafica, senza dover accedere direttamente al database. Per poter gestire i modelli (File e Translation) in questa 
# interfaccia, essi devono essere prima registrati e questo file è il posto in cui ciò avviene.

from django.contrib import admin                                                            # Importa il modulo principale dell'interfaccia di amministrazione.
from .models import File, Translation                                                       # Importa i modelli che si desidera rendere disponibili nell'area admin.

# Questo è un "decoratore" Python. È una sintassi per dire: "Registra il modello File nell'area di amministrazione e usa la classe 
# che segue (FileAdmin) per personalizzarne l'aspetto e il comportamento".
@admin.register(File)
class FileAdmin(admin.ModelAdmin):

    # Questa è una delle personalizzazioni più utili. Specifica quali campi del modello File devono essere mostrati come colonne nella 
    # pagina di elenco degli oggetti. Rende la lista molto più leggibile e informativa. 

    list_display = ('id', 'user', 'name', 'status', 'created_at')

    # Aggiunge un pannello di filtri sulla destra della pagina di elenco. Questo permette all'amministratore di filtrare rapidamente i 
    # file per stato (es. "uploaded", "processing") o per data di creazione.

    list_filter = ('status', 'created_at')

# Viene usato sempre lo stesso "decoratore". Questa classe permette di personalizzare come il modello File viene visualizzato.
@admin.register(Translation)

# La classe TranslationAdmin fa esattamente la stessa cosa per il modello Translation, personalizzando la sua visualizzazione nell'area admin.

class TranslationAdmin(admin.ModelAdmin):
    list_display = ('id', 'file', 'src_language', 'dst_language', 'status', 'created_at')
    list_filter = ('status', 'src_language', 'dst_language')
