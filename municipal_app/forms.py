from django import forms
from django.contrib.auth.forms import UserChangeForm # Importar UserChangeForm
from django.contrib.auth.models import User # Importar el modelo User
from .models import MunicipalCredentials

class MunicipalCredentialsForm(forms.ModelForm):
    class Meta:
        model = MunicipalCredentials
        fields = ['municipal_username', 'municipal_password']
        widgets = {
            'municipal_password': forms.PasswordInput(),
        }

class UserProfileForm(UserChangeForm):
    password = None # No incluir el campo de contraseña aquí

    class Meta:
        model = User
        fields = ['username', 'email'] # Permitir editar nombre de usuario y correo