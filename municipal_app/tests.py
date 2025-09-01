import os
from django.test import TestCase

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.conf import settings
from cryptography.fernet import Fernet
from unittest.mock import patch, MagicMock
from decimal import Decimal

from .models import MunicipalCredentials, ExecutionHistory
from .forms import MunicipalCredentialsForm

# Initialize Fernet for testing
# Ensure FERNET_KEY is set in settings for tests
if not hasattr(settings, 'FERNET_KEY'):
    settings.FERNET_KEY = Fernet.generate_key().decode()
f = Fernet(settings.FERNET_KEY)

class MunicipalCredentialsModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.plain_password = 'municipal_test_password'
        self.encrypted_password = f.encrypt(self.plain_password.encode()).decode()

    def test_create_municipal_credentials(self):
        credentials = MunicipalCredentials.objects.create(
            user=self.user,
            municipal_username='test_municipal_user',
            municipal_password=self.encrypted_password.encode()
        )
        self.assertEqual(credentials.user, self.user)
        self.assertEqual(credentials.municipal_username, 'test_municipal_user')
        self.assertEqual(credentials.municipal_password, self.encrypted_password.encode())

    def test_retrieve_municipal_credentials(self):
        MunicipalCredentials.objects.create(
            user=self.user,
            municipal_username='test_municipal_user',
            municipal_password=self.encrypted_password.encode()
        )
        retrieved_credentials = MunicipalCredentials.objects.get(user=self.user)
        self.assertEqual(retrieved_credentials.municipal_username, 'test_municipal_user')
        self.assertEqual(retrieved_credentials.municipal_password, self.encrypted_password.encode())

    def test_password_encryption_decryption(self):
        credentials = MunicipalCredentials.objects.create(
            user=self.user,
            municipal_username='test_municipal_user',
            municipal_password=self.encrypted_password.encode()
        )
        decrypted_password = f.decrypt(credentials.municipal_password).decode()
        self.assertEqual(decrypted_password, self.plain_password)

class ExecutionHistoryModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword')

    def test_create_execution_history(self):
        history = ExecutionHistory.objects.create(
            user=self.user,
            amount=Decimal('100.50'),
            status='Success',
            output='Bot ran successfully',
            error=None
        )
        self.assertEqual(history.user, self.user)
        self.assertEqual(history.amount, Decimal('100.50'))
        self.assertEqual(history.status, 'Success')
        self.assertEqual(history.output, 'Bot ran successfully')
        self.assertIsNone(history.error)
        self.assertIsNotNone(history.execution_time)

    def test_retrieve_execution_history(self):
        ExecutionHistory.objects.create(
            user=self.user,
            amount=Decimal('200.00'),
            status='Failed',
            output=None,
            error='Bot failed to run'
        )
        retrieved_history = ExecutionHistory.objects.get(user=self.user)
        self.assertEqual(retrieved_history.amount, Decimal('200.00'))
        self.assertEqual(retrieved_history.status, 'Failed')
        self.assertEqual(retrieved_history.error, 'Bot failed to run')

class MunicipalCredentialsViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.client.login(username='testuser', password='testpassword')
        self.credentials_url = reverse('municipal_credentials')
        self.plain_password = 'test_municipal_password'
        self.encrypted_password = f.encrypt(self.plain_password.encode()).decode()

    def test_get_municipal_credentials_form_new_user(self):
        response = self.client.get(self.credentials_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'municipal_app/municipal_credentials_form.html')
        self.assertContains(response, 'Aún no has ingresado tus credenciales de la municipalidad.')

    def test_get_municipal_credentials_form_existing_incomplete(self):
        MunicipalCredentials.objects.create(user=self.user, municipal_username='existing_user')
        response = self.client.get(self.credentials_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'municipal_app/municipal_credentials_form.html')
        self.assertContains(response, 'Por favor, completa o actualiza tus credenciales de la municipalidad.')

    def test_get_municipal_credentials_form_existing_complete(self):
        MunicipalCredentials.objects.create(
            user=self.user,
            municipal_username='existing_user',
            municipal_password=self.encrypted_password.encode()
        )
        response = self.client.get(self.credentials_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'municipal_app/municipal_credentials_form.html')
        self.assertContains(response, 'Tus credenciales de la municipalidad ya están cargadas. Puedes modificarlas aquí.')

    def test_post_municipal_credentials_create(self):
        response = self.client.post(self.credentials_url, {
            'municipal_username': 'new_municipal_user',
            'municipal_password_plain': self.plain_password
        })
        self.assertRedirects(response, reverse('enter_billing'))
        credentials = MunicipalCredentials.objects.get(user=self.user)
        self.assertEqual(credentials.municipal_username, 'new_municipal_user')
        self.assertEqual(f.decrypt(credentials.municipal_password).decode(), self.plain_password)

    def test_post_municipal_credentials_update(self):
        MunicipalCredentials.objects.create(
            user=self.user,
            municipal_username='old_user',
            municipal_password=f.encrypt(b'old_password').decode().encode()
        )
        response = self.client.post(self.credentials_url, {
            'municipal_username': 'updated_municipal_user',
            'municipal_password_plain': self.plain_password
        })
        self.assertRedirects(response, reverse('enter_billing'))
        credentials = MunicipalCredentials.objects.get(user=self.user)
        self.assertEqual(credentials.municipal_username, 'updated_municipal_user')
        self.assertEqual(f.decrypt(credentials.municipal_password).decode(), self.plain_password)

    def test_post_municipal_credentials_missing_password_for_new(self):
        response = self.client.post(self.credentials_url, {
            'municipal_username': 'new_municipal_user',
            'municipal_password_plain': ''
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Contraseña Municipal: This field is required.')
        self.assertFalse(MunicipalCredentials.objects.filter(municipal_username='new_municipal_user').exists())

    def test_post_municipal_credentials_invalid_form(self):
        response = self.client.post(self.credentials_url, {
            'municipal_username': '', # Invalid input
            'municipal_password_plain': self.plain_password
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'This field is required.') # Assuming form validation for username
        self.assertFalse(MunicipalCredentials.objects.filter(user=self.user, municipal_username='').exists())

class EnterBillingViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.client.login(username='testuser', password='testpassword')
        self.enter_billing_url = reverse('enter_billing')
        self.plain_password = 'test_municipal_password'
        self.encrypted_password = f.encrypt(self.plain_password.encode()).decode()
        self.credentials = MunicipalCredentials.objects.create(
            user=self.user,
            municipal_username='test_municipal_user',
            municipal_password=self.encrypted_password.encode()
        )

    @patch('municipal_app.views.run_munibot')
    def test_post_enter_billing_success(self, mock_run_munibot):
        mock_run_munibot.return_value = ('Success', 'Bot output', None)
        response = self.client.post(self.enter_billing_url, {'monto': '150.75'})
        self.assertRedirects(response, self.enter_billing_url)
        mock_run_munibot.assert_called_once_with(
            'test_municipal_user',
            self.plain_password,
            '150.75',
            os.path.join(settings.BASE_DIR, 'edgedriver_win64', 'msedgedriver.exe')
        )
        history = ExecutionHistory.objects.get(user=self.user)
        self.assertEqual(history.amount, Decimal('150.75'))
        self.assertEqual(history.status, 'Success')
        self.assertEqual(history.output, 'Bot output')
        self.assertIsNone(history.error)

    @patch('municipal_app.views.run_munibot')
    def test_post_enter_billing_script_failure(self, mock_run_munibot):
        mock_run_munibot.return_value = ('Failed', None, 'Script error')
        response = self.client.post(self.enter_billing_url, {'monto': '100.00'})
        self.assertRedirects(response, self.enter_billing_url)
        history = ExecutionHistory.objects.get(user=self.user)
        self.assertEqual(history.amount, Decimal('100.00'))
        self.assertEqual(history.status, 'Failed')
        self.assertIsNone(history.output)
        self.assertEqual(history.error, 'Script error')

    def test_post_enter_billing_no_credentials(self):
        MunicipalCredentials.objects.filter(user=self.user).delete()
        response = self.client.post(self.enter_billing_url, {'monto': '50.00'})
        self.assertRedirects(response, reverse('municipal_credentials'))
        self.assertEqual(ExecutionHistory.objects.count(), 1) # History should still be recorded
        history = ExecutionHistory.objects.get(user=self.user)
        self.assertEqual(history.status, 'Failed')
        self.assertEqual(history.error, 'Credenciales de la municipalidad no encontradas.')

    @patch('municipal_app.views.run_munibot')
    def test_post_enter_billing_invalid_monto(self, mock_run_munibot):
        mock_run_munibot.return_value = ('Success', 'Bot output', None)
        response = self.client.post(self.enter_billing_url, {'monto': 'invalid_amount'})
        self.assertRedirects(response, self.enter_billing_url)
        mock_run_munibot.assert_called_once() # Should still attempt to run bot
        history = ExecutionHistory.objects.get(user=self.user)
        self.assertIsNone(history.amount) # Invalid monto should be saved as None
        self.assertEqual(history.status, 'Success')

    @patch('municipal_app.views.f', new=None) # Mock Fernet to be None
    def test_post_enter_billing_fernet_not_initialized(self):
        response = self.client.post(self.enter_billing_url, {'monto': '10.00'})
        self.assertRedirects(response, self.enter_billing_url)
        history = ExecutionHistory.objects.get(user=self.user)
        self.assertEqual(history.status, 'Failed')
        self.assertIn('Fernet not initialized', history.error)

    @patch('municipal_app.views.f')
    def test_post_enter_billing_decryption_error(self, mock_fernet):
        mock_fernet.decrypt.side_effect = Exception("Decryption failed")
        response = self.client.post(self.enter_billing_url, {'monto': '20.00'})
        self.assertRedirects(response, self.enter_billing_url)
        history = ExecutionHistory.objects.get(user=self.user)
        self.assertEqual(history.status, 'Failed')
        self.assertIn('Ocurrió un error inesperado: Decryption failed', history.error)
