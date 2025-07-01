"""Configurazione centrale del progetto Django.

Questo modulo definisce tutte le impostazioni globali per l'applicazione, seguendo
i principi di "The Twelve-Factor App" per la creazione di software robusto e
scalabile. La configurazione è parametrizzata tramite variabili d'ambiente,
permettendo allo stesso codice di base di operare in modo sicuro e coerente in
diversi ambienti (es. sviluppo, testing, produzione) senza modifiche.
"""
import os
import dj_database_url
from pathlib import Path

# --- Configurazione dei Percorsi di Base ---
# Definisce la directory radice del progetto in modo assoluto e indipendente
# dal sistema operativo, garantendo la portabilità dei percorsi.
BASE_DIR = Path(__file__).resolve().parent.parent

# --- Gestione dei File Statici e Media ---
# URL pubblico per i file caricati dagli utenti (es. /media/file.txt).
MEDIA_URL = '/media/'
# Percorso fisico nel file system dove i file caricati vengono archiviati.
MEDIA_ROOT = BASE_DIR / 'media/'

# URL pubblico per i file statici dell'applicazione (CSS, JS, immagini).
STATIC_URL = '/static/'
# Percorso fisico dove il comando `collectstatic` aggregherà tutti i file
# statici per il deployment. WhiteNoise utilizzerà questa directory.
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# --- Configurazione di Sicurezza e Ambiente ---
# Questa sezione implementa una separazione critica tra configurazione e codice.
# I dati sensibili non sono hardcoded, ma iniettati tramite variabili d'ambiente.

# La chiave segreta di Django, fondamentale per la firma crittografica di sessioni
# e token, viene letta dall'ambiente di esecuzione.
SECRET_KEY = os.environ.get('SECRET_KEY')

# La modalità DEBUG viene derivata da una variabile d'ambiente. È un controllo
# cruciale: deve essere rigorosamente `False` in produzione per evitare l'esposizione
# di informazioni di debug sensibili.
DEBUG = os.environ.get('DEBUG') in ['1', 'True', 'true']

# Legge la lista degli host/domini autorizzati dall'ambiente. Questo previene
# attacchi di tipo "HTTP Host header poisoning".
ALLOWED_HOSTS_str = os.environ.get('ALLOWED_HOSTS', '')
ALLOWED_HOSTS = ALLOWED_HOSTS_str.split(',') if ALLOWED_HOSTS_str else []

# --- Applicazioni Installate ---
# Elenco delle applicazioni che compongono il progetto.
INSTALLED_APPS = [
    # Applicazioni built-in di Django.
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Applicazioni di terze parti.
    'rest_framework',                   # Django REST Framework per la creazione di API.
    'rest_framework_simplejwt',         # Per l'autenticazione basata su JSON Web Token (JWT).

    # Applicazioni locali del progetto.
    'app',                              # L'applicazione principale del progetto.
]

# --- Pipeline dei Middleware ---
# Sequenza di "hook" che processano le richieste e le risposte globalmente.
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # Middleware di WhiteNoise per il servizio efficiente dei file statici,
    # ottimizzato per ambienti di produzione containerizzati.
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# --- Configurazione URL e Template ---
# Punto di ingresso per il routing degli URL del progetto.
ROOT_URLCONF = 'core.urls'
# Configurazione del sistema di template di Django.
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# Punto di ingresso per i server applicativi conformi a WSGI.
WSGI_APPLICATION = 'core.wsgi.application'

# --- Configurazione del Database ---
# La configurazione del database è astratta tramite la variabile d'ambiente DATABASE_URL.
# Questa pratica, promossa dalla metodologia "Twelve-Factor App", permette di cambiare
# il database (es. da SQLite in sviluppo a PostgreSQL in produzione) senza
# modificare il codice, ma solo la configurazione dell'ambiente.
DATABASES = {
    'default': dj_database_url.config(
        # La libreria `dj_database_url` esegue il parsing dell'URL e restituisce
        # un dizionario di configurazione compatibile con Django.
        # Se DATABASE_URL non è presente nell'ambiente, viene utilizzato un fallback
        # a un database SQLite locale, ideale per lo sviluppo rapido.
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}"
    )
}

# --- Validatori di Password ---
# Set di regole per imporre una policy di complessità delle password,
# mitigando il rischio di password deboli.
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# --- Impostazioni di Internazionalizzazione (i18n) ---
LANGUAGE_CODE = 'it-it'
TIME_ZONE = 'Europe/Rome'
USE_I18N = True
USE_TZ = True

# --- Impostazioni Generali e di Framework ---
# Tipo di campo di default per le chiavi primarie auto-generate.
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Configurazione globale per Django REST Framework (DRF).
REST_FRAMEWORK = {
    # Definisce JWT come meccanismo di autenticazione predefinito per tutti
    # gli endpoint dell'API. Ogni richiesta dovrà presentare un token JWT valido
    # nell'header `Authorization`.
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    # Imposta la policy di permessi di default a 'IsAuthenticated'.
    # Questa è una scelta di design "secure-by-default": nessun endpoint
    # sarà accessibile a utenti anonimi, a meno che non venga esplicitamente
    # concesso un permesso più permissivo a livello di singola vista (es. per la registrazione).
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    )
}