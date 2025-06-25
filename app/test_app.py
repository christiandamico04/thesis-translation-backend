# Questo file contiene la suite di test automatici per l'applicazione. Lo scopo dei test è verificare la correttezza del codice, prevenire 
# errori futuri (regressioni) e documentare il comportamento atteso dei vari componenti. La suite è divisa in test di integrazione per il 
# servizio di traduzione e test per gli endpoint dell'API.

import os
import unittest
from django.test import TestCase
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase
from unittest.mock import patch

from .models import File, Translation
from .services.translation_service import translate, TranslationError, model, tokenizer

# -- Test di Integrazione per il Servizio di Traduzione (no Mock) --
# Questa classe di test si concentra sul verificare l'integrazione reale con il modello MODLAD400-3b-mt.
class TranslationServiceTests(TestCase):

    # Questo test verifica l'intero flusso di traduzione in modo reale, senza alcuna simulazione. Carica il vero modello google/madlad400-3b-mt 
    # in memoria, gli fornisce una stringa di testo in inglese e controlla che l'output in italiano sia corretto. Fornisce il massimo livello 
    # di confidenza sul fatto che il componente più critico dell'applicazione funzioni come previsto.

    @unittest.skipUnless(os.environ.get('RUN_SLOW_TESTS'), "Skipping slow model integration test.")     # Questo decoratore rende il test opzionale.
                                                                                                        # Verrà eseguito solo se RUN_SLOW_TESTS=1
    def test_real_translation_en_to_it(self):
        """
        Verifica una traduzione reale dall'inglese all'italiano caricando il modello.
        Questo test è lento e richiede molte risorse (RAM/GPU).
        """
        # Ci si assicura che il modello sia stato caricato prima di eseguire il test. Se il caricamento fallisce all'avvio dell'app, questo 
        # test fallirà qui.
        self.assertIsNotNone(model, "Il modello di traduzione non è stato caricato.")
        self.assertIsNotNone(tokenizer, "Il tokenizer non è stato caricato.")

        original_text = "Hello, how are you?"
        expected_translation = "Ciao, come stai?"                                                      

        translated_text = translate(text=original_text, src="en", dst="it")                             # Si esegue la traduzione reale
        self.assertEqual(translated_text, expected_translation)                                         # Si verifica che il risultato sia quello atteso
    
    # Lo scopo di questo test unitario è verificare che, se per qualche motivo, il modello non venisse caricato all'avvio, la funzione 
    # translate fallisca correttamente sollevando un'eccezione TranslationError.
    # Usa @patch per simulare temporaneamente che la variabile model nel servizio sia None. Questo isola il test e verifica solo la logica 
    # di gestione dell'errore, senza tentare di caricare il modello reale.

    @patch('app.services.translation_service.model', None)
    def test_translation_fails_if_model_not_loaded(self):
        """
        Verifica che venga sollevata un'eccezione se il modello non è inizializzato.
        Questo è un test unitario veloce che usa un mock.
        """
        with self.assertRaises(TranslationError, msg="Il modello di traduzione non è inizializzato."):
            translate(text="Testo di prova", src="it", dst="en")

# -- Test per gli Endpoint API (Mock) --
# Si verifica che gli endpoint dell'API (/api/files/, /api/files/{id}/translate/, etc.) si comportino correttamente, gestendo l'autenticazione, 
# l'upload dei file e le interazioni con il database.

# È importante notare che questi test continuano a usare @patch per simulare la chiamata alla funzione translate. Questa è una scelta deliberata 
# e corretta: lo scopo di FileViewSetTests è testare la logica della vista (gestione della richiesta HTTP, i permessi, la risposta), non 
# la logica interna del servizio di traduzione. 

# Mantenere il mock qui assicura che i test dell'API rimangano estremamente veloci e affidabili, indipendentemente dal funzionamento del modello AI.
class FileViewSetTests(APITestCase):

    def setUp(self):
        """Metodo eseguito prima di ogni test in questa classe."""
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.test_file = SimpleUploadedFile(
            "test_file.txt",
            b"This is the content of the file.",
            content_type="text/plain"
        )
        self.client.force_authenticate(user=self.user)

    def test_file_upload_success(self):
        """Verifica che un utente autenticato possa caricare un file."""
        url = '/api/files/'
        data = {'file': self.test_file, 'name': 'test_file.txt', 'size': self.test_file.size}
        response = self.client.post(url, data, format='multipart')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(File.objects.count(), 1)
        self.assertEqual(File.objects.first().user, self.user)

    def test_request_translation_success(self):
        """Verifica che si possa richiedere una traduzione per un file esistente."""
        file_instance = File.objects.create(
            user=self.user,
            file=self.test_file,
            name="file_to_translate.txt",
            size=123
        )
        url = f'/api/files/{file_instance.id}/translate/'
        data = {'src_language': 'it', 'dst_language': 'en'}

        with patch('app.views.translate', return_value="[MOCKED] Translation") as mock_translate:
            response = self.client.post(url, data, format='json')
            self.assertEqual(response.status_code, 201)
            self.assertEqual(Translation.objects.count(), 1)
            translation = Translation.objects.first()
            self.assertEqual(translation.file, file_instance)
            self.assertEqual(translation.status, 'done')
            mock_translate.assert_called_once()

    def test_file_deletion_success(self):
        """Verifica che un file e le sue traduzioni vengano cancellate."""
        file_instance = File.objects.create(
            user=self.user, file=self.test_file, name="to_delete.txt", size=123
        )
        Translation.objects.create(
            file=file_instance, src_language='it', dst_language='en', original_text='test'
        )
        self.assertEqual(File.objects.count(), 1)
        self.assertEqual(Translation.objects.count(), 1)
        url = f'/api/files/{file_instance.id}/'
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(File.objects.count(), 0)
        self.assertEqual(Translation.objects.count(), 0)