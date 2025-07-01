"""
Definisce la configurazione per l'applicazione Django 'app'.
"""

from django.apps import AppConfig
class AppConfig(AppConfig):
    """
    Classe di configurazione per l'applicazione 'app'.
    Eredita dalla classe base AppConfig di Django e ne definisce i metadati.
    """

    # Imposta il tipo di campo predefinito per le chiavi primarie auto-generate
    # a BigAutoField, un intero a 64-bit, garantendo la compatibilità con un
    # elevato numero di record nel database.
    default_auto_field = 'django.db.models.BigAutoField'

    # Specifica il nome dell'applicazione a cui questa configurazione si applica.
    # Questo nome deve corrispondere a quello registrato in INSTALLED_APPS.
    name = 'app'

    def ready(self):
        """Esegue codice di inizializzazione quando l'applicazione è pronta.

        Questo metodo viene invocato da Django una volta che il registro delle
        applicazioni è stato completamente popolato. In questa architettura a
        microservizi, il caricamento del modello AI è delegato al servizio
        'vllm-server' dedicato. Pertanto, questo metodo viene utilizzato per stampare
        messaggi informativi a console che confermano il corretto avvio
        dell'applicazione Django e chiariscono la separazione delle responsabilità.
        """
        # Stampa messaggi informativi nello standard output per confermare
        # l'avvio del worker Gunicorn e il suo ruolo nell'architettura.
        print(">>> Applicazione Django 'app' avviata e pronta a ricevere richieste. <<<")
        print(">>> Il modello di traduzione AI è gestito dal servizio vLLM separato. <<<")

        # L'istruzione 'pass' è implicitamente presente alla fine di una funzione
        # Python, ma viene lasciata per chiarezza esplicita del fatto che non
        # sono necessarie ulteriori operazioni di inizializzazione.
        pass