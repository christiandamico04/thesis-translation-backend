"""Configurazione centrale del routing URL per il progetto 'core'.

Questo modulo, noto come URLconf, agisce come il "controllore di traffico"
principale per l'applicazione Django. La lista `urlpatterns` mappa specifici
percorsi URL (es. '/api/files/') a viste (handler logici) che processeranno
la richiesta. Questo disaccoppia la struttura degli URL dalla logica di business
implementata nelle viste.
"""
# ========================================================================================
#                                        IMPORT
# ========================================================================================
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from app.views import FileViewSet, TranslationViewSet, UserRegistrationView

# ========================================================================================
#                     CONFIGURAZIONE DEL ROUTER PER L'API RESTFUL
# ========================================================================================
# L'uso di un Router di Django REST Framework (DRF) automatizza la creazione degli
# URL per un ViewSet. Registrando un ViewSet con il router, vengono generati
# automaticamente tutti gli endpoint standard per le operazioni CRUD.
router = DefaultRouter()

# Registra il 'FileViewSet' sotto il prefisso 'files'.
# Questo genera automaticamente URL come:
#   - /api/files/ (per GET list e POST create)
#   - /api/files/{pk}/ (per GET retrieve, PUT update, DELETE destroy)
#   - /api/files/{pk}/translate/ (per l'azione personalizzata 'translate')
router.register(r'files', FileViewSet, basename='file')

# Registra il 'TranslationViewSet' sotto il prefisso 'translations'.
router.register(r'translations', TranslationViewSet, basename='translation')

# ========================================================================================
#                       DEFINIZIONE DEI PATTERN URL PRINCIPALI
# ========================================================================================
# La lista `urlpatterns` è la configurazione di routing primaria che Django utilizza.
urlpatterns = [
    # URL per l'interfaccia di amministrazione di Django.
    path('admin/', admin.site.urls),

    # Include tutti gli URL generati dal router DRF sotto il prefisso '/api/'.
    # Questo modularizza la configurazione, mantenendo tutti gli URL dell'API
    # sotto un unico namespace.
    path('api/', include(router.urls)),

    # --- Endpoint per l'Autenticazione e la Registrazione (Flusso JWT) ---

    # 1. Endpoint per la registrazione di un nuovo utente.
    #    Mappa l'URL '/api/register/' alla vista 'UserRegistrationView'.
    path('api/register/', UserRegistrationView.as_view(), name='user_registration'),

    # 2. Endpoint per l'ottenimento del token.
    #    L'utente invia le proprie credenziali (username, password) a questo URL
    #    e, se valide, riceve una coppia di token (access e refresh).
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),

    # 3. Endpoint per l'aggiornamento del token.
    #    L'utente invia un refresh token valido per ottenere un nuovo access token
    #    senza dover reinserire le credenziali.
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]

# ========================================================================================
#                  CONFIGURAZIONE URL SPECIFICA PER L'AMBIENTE DI SVILUPPO
# ========================================================================================

# Questa sezione aggiunge pattern URL ausiliari solo quando l'applicazione
# è in esecuzione in modalità DEBUG (`DEBUG = True` in settings.py).
if settings.DEBUG:
    # Aggiunge il pattern per servire i file caricati dagli utenti (media files)
    # direttamente dal server di sviluppo di Django. In produzione, questa
    # responsabilità è tipicamente delegata a un web server come Nginx.
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Aggiunge i pattern per servire i file statici (CSS, JS) in sviluppo.
# Anche in questo caso, in produzione, il servizio è gestito da WhiteNoise
# o da un web server esterno.
urlpatterns += staticfiles_urlpatterns()