# app/tests.py

from django.test import TestCase, override_settings
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
import os
import tempfile
from unittest.mock import patch

from rest_framework.test import APITestCase
from rest_framework import status

from .models import File, Translation
from .services.translation_service import translate

# ===================================================================
#                          TEST UNITARI
# ===================================================================

@override_settings(MEDIA_ROOT=tempfile.gettempdir())
class FileModelTests(TestCase):
    """
    Test unitari per il modello File, in particolare per la logica custom.
    """
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.test_file = SimpleUploadedFile("test_file.txt", b"file content")
        self.file_instance = File.objects.create(
            user=self.user,
            name=self.test_file.name,
            file=self.test_file,
            size=self.test_file.size
        )

    def test_file_delete_also_deletes_physical_file(self):
        """
        Verifica che la cancellazione di un'istanza del modello File
        cancelli anche il file fisico dal disco.
        """
        file_path = self.file_instance.file.path
        self.assertTrue(os.path.exists(file_path))
        self.file_instance.delete()
        self.assertFalse(os.path.exists(file_path))


@override_settings(MEDIA_ROOT=tempfile.gettempdir()) 
class TranslationServiceTests(TestCase):
    """
    Test unitari per il servizio di traduzione, con mocking delle chiamate esterne.
    """
    @patch('app.services.translation_service._call_vllm_api')
    def test_translate_function_with_mocked_api(self, mock_call_vllm_api):
        """
        Verifica che la funzione 'translate' orchestri correttamente la logica
        e chiami il servizio esterno simulato (mock).
        """
        mocked_translation = "This is a mocked translation."
        mock_call_vllm_api.return_value = mocked_translation

        test_user = User.objects.create(username='mockuser')
        dummy_file = SimpleUploadedFile("mock_file.txt", b"mock content")
        file_instance = File.objects.create(
            user=test_user,
            name=dummy_file.name,
            file=dummy_file,
            size=dummy_file.size
        )

        translated_text = translate(text="Questo è un testo di prova.", src="it", dst="en")

        translation_obj = Translation.objects.create(
            file=file_instance,
            original_text="Questo è un testo di prova.",
            translated_text=translated_text,
            status='done',
            src_language="it",
            dst_language="en",
        )

        self.assertEqual(translation_obj.translated_text, mocked_translation)
        mock_call_vllm_api.assert_called_once()

# ===================================================================
#                        TEST DI INTEGRAZIONE
# ===================================================================

@override_settings(MEDIA_ROOT=tempfile.gettempdir())
class APIIntegrationTests(APITestCase):
    """
    Test di integrazione per gli endpoint dell'API.
    Verifica il flusso completo dalla richiesta alla risposta.
    """
    def setUp(self):
        self.user = User.objects.create_user(username='api_user', password='password123')
        self.client.force_authenticate(user=self.user)

    def test_unauthenticated_access_fails(self):
        self.client.force_authenticate(user=None)
        response = self.client.get('/api/files/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_file_upload_and_listing(self):
        test_file = SimpleUploadedFile("api_test_file.txt", b"api content")
        response = self.client.post('/api/files/', {
            'name': 'api_test_file.txt',
            'file': test_file,
            'size': test_file.size
        }, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(File.objects.count(), 1)
        self.assertEqual(File.objects.first().user, self.user)
        list_response = self.client.get('/api/files/')
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data), 1)

    @patch('app.services.translation_service._call_vllm_api')
    def test_full_translation_workflow(self, mock_call_vllm_api):
        mocked_translation = "This is the final translated text."
        mock_call_vllm_api.return_value = mocked_translation
        
        file_to_translate = SimpleUploadedFile("translate_me.txt", b"Testo da tradurre")
        upload_response = self.client.post('/api/files/', {
            'name': 'translate_me.txt',
            'file': file_to_translate,
            'size': file_to_translate.size
        }, format='multipart')
        file_id = upload_response.data['id']

        translate_response = self.client.post(f'/api/files/{file_id}/translate/', {
            'src_language': 'it', 'dst_language': 'en'
        }, format='json')
        self.assertEqual(translate_response.status_code, status.HTTP_201_CREATED)
        translation_id = translate_response.data['translation_id']

        translation_obj = Translation.objects.get(id=translation_id)
        self.assertEqual(translation_obj.translated_text, mocked_translation)
        
        download_response = self.client.get(f'/api/translations/{translation_id}/download/')
        self.assertEqual(download_response.status_code, status.HTTP_200_OK)
        self.assertEqual(download_response.content.decode('utf-8'), mocked_translation)