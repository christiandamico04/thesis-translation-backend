from django.test import TestCase
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase                     # Strumento specifico per testare le API
from unittest.mock import patch                                 # Per "mockare" (simulare) le chiamate esterne

from .models import File, Translation
from .services.translation_service import translate, TranslationError

# --- Test per il Servizio di Traduzione ---
# Questi test verificano la logica del servizio in isolamento.
class TranslationServiceTests(TestCase):

    # Usiamo @patch per intercettare e simulare `requests.post`
    # In questo modo non chiamiamo la vera API di LibreTranslate durante i test.
    @patch('app.services.translation_service._USE_MOCK', False) 
    @patch('app.services.translation_service.requests.post')

    def test_translate_success(self, mock_post):
        """Verifica che il servizio ritorni il testo tradotto in caso di successo."""
        
        # Configuriamo il "falso" oggetto di risposta che requests.post dovrà restituire
        mock_response = mock_post.return_value
        mock_response.status_code = 200
        mock_response.json.return_value = {"translatedText": "Hello"}

        # Chiamiamo la nostra funzione
        # _USE_MOCK deve essere False nel servizio per eseguire questa logica
        translated = translate(text="Ciao", src="it", dst="en")

        # Verifichiamo il risultato
        self.assertEqual(translated, "Hello")
        # Verifichiamo che requests.post sia stato chiamato una volta
        mock_post.assert_called_once()
       
    @patch('app.services.translation_service._USE_MOCK', False) 
    @patch('app.services.translation_service.requests.post')

    def test_translate_api_error_raises_exception(self, mock_post):
        """Verifica che venga sollevata un'eccezione se l'API esterna dà errore."""
        
        # Configuriamo la risposta per simulare un errore del server
        mock_response = mock_post.return_value
        mock_response.status_code = 500 

        # Verifichiamo che chiamando `translate` venga sollevata la nostra eccezione custom
        with self.assertRaises(TranslationError):
            translate(text="Testo problematico", src="it", dst="en")


# --- Test per gli Endpoint API ---
# Questi test simulano le chiamate HTTP al nostro backend.

class FileViewSetTests(APITestCase):

    def setUp(self):
        """Metodo eseguito prima di ogni test in questa classe."""
        # Creiamo un utente di test
        self.user = User.objects.create_user(username='testuser', password='password123')
        # Creiamo un file finto da caricare in memoria
        self.test_file = SimpleUploadedFile(
            "test_file.txt",
            b"Questo e' il contenuto del file.", 
            content_type="text/plain"
        )
        # Forziamo l'autenticazione per tutte le richieste in questa classe
        self.client.force_authenticate(user=self.user)

    def test_file_upload_success(self):
        """Verifica che un utente autenticato possa caricare un file."""
        url = '/api/files/'
        data = {'file': self.test_file, 'name': 'test_file.txt', 'size': self.test_file.size}
        
        response = self.client.post(url, data, format='multipart')

        self.assertEqual(response.status_code, 201) # 201 CREATED
        self.assertEqual(File.objects.count(), 1) # Controlla che il file sia stato creato nel DB
        self.assertEqual(File.objects.first().user, self.user)

    def test_request_translation_success(self):
        """Verifica che si possa richiedere una traduzione per un file esistente."""
        # 1. Creiamo un file su cui lavorare
        file_instance = File.objects.create(
            user=self.user,
            file=self.test_file,
            name="file_to_translate.txt",
            size=123
        )
        url = f'/api/files/{file_instance.id}/translate/'
        data = {'src_language': 'it', 'dst_language': 'en'}

        # Usiamo @patch anche qui per non dipendere dal servizio esterno
        with patch('app.views.translate', return_value="[MOCKED] Translation") as mock_translate:
            response = self.client.post(url, data, format='json')

            self.assertEqual(response.status_code, 201) # 201 CREATED
            self.assertEqual(Translation.objects.count(), 1)
            
            # Recupera la traduzione creata e controlla che sia corretta
            translation = Translation.objects.first()
            self.assertEqual(translation.file, file_instance)
            self.assertEqual(translation.dst_language, 'en')
            self.assertEqual(translation.status, 'done')
            
            # Verifica che la funzione di traduzione sia stata chiamata
            mock_translate.assert_called_once()

    def test_file_deletion_success(self):
        """Verifica che un file e le sue traduzioni vengano cancellate."""
        # 1. Creiamo un file
        file_instance = File.objects.create(
            user=self.user, file=self.test_file, name="to_delete.txt", size=123
        )
        # 2. Creiamo una traduzione associata
        Translation.objects.create(
            file=file_instance, src_language='it', dst_language='en', original_text='test'
        )

        self.assertEqual(File.objects.count(), 1)
        self.assertEqual(Translation.objects.count(), 1)

        # 3. Chiamiamo l'endpoint di cancellazione
        url = f'/api/files/{file_instance.id}/'
        response = self.client.delete(url)
        
        # 4. Verifichiamo i risultati
        self.assertEqual(response.status_code, 204)             # 204 NO CONTENT
        self.assertEqual(File.objects.count(), 0)               # Il file è stato cancellato dal DB
        self.assertEqual(Translation.objects.count(), 0)        # Anche la traduzione (effetto cascata)