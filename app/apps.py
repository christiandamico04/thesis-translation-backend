# Questo file contiene la configurazione specifica per l'applicazione Django chiamata app. Ogni applicazione in un progetto 
# Django può avere la sua classe di configurazione. Nella maggior parte dei casi, questo file viene generato automaticamente 
# da Django.

from django.apps import AppConfig


class AppConfig(AppConfig):                                         # Definisce la classe di configurazione per la nostra applicazione, 
                                                                    # ereditando dalla classe base AppConfig di Django.

    default_auto_field = 'django.db.models.BigAutoField'            # Questa impostazione indica a Django quale tipo di campo utilizzare 
                                                                    # per le chiavi primarie (id) che vengono create automaticamente nei 
                                                                    # modelli di questa app.
                                                                    # BigAutoField corrisponde a un intero a 64-bit (in SQL, BIGINT).

    name = 'app'                                                    # Specifica il nome dell'applicazione a cui questa configurazione si 
                                                                    # riferisce. Questo nome deve corrispondere al nome della directory 
                                                                    # dell'app e a come è stata inserita nella lista INSTALLED_APPS nel 
                                                                    # file core/settings.py.
