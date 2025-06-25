# Questo file è il controllore del traffico URL principale del progetto. Quando arriva una richiesta per un certo URL, Django consulta questo 
# file per decidere quale "vista" deve gestirla.

"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from app.views import FileViewSet, TranslationViewSet

# DefaultRouter(), di DRF, semplifica la creazione delle rotte per le API. Registrando un ViewSet (es. FileViewSet), il router genera 
# automaticamente un set completo di URL per le operazioni standard (list, create, retrieve, update, delete).

router = DefaultRouter()

# Vengono registrati i due ViewSet dell'applicazione. Questo crea automaticamente gli URL sotto il prefisso /api/, come /api/files/, 
# /api/files/{id}/, /api/translations/, e le azioni personalizzate come /api/files/{id}/translate/.

router.register(r'files', FileViewSet, basename='file')
router.register(r'translations', TranslationViewSet, basename='translation')

# È la lista principale dei pattern URL.

urlpatterns = [
    path('admin/', admin.site.urls),                                                # Attiva l'interfaccia di amministrazione di Django all'URL /admin/.
    path('api/', include(router.urls)),                                             # Include tutti gli URL generati dal DefaultRouter sotto il prefisso /api/.
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
