from django import forms
from django.contrib.auth.forms import UserChangeForm # Importar UserChangeForm
from django.contrib.auth.models import User # Importar el modelo User
from .models import MunicipalCredentials, MisionesCredentials, MisionesRecord

class MunicipalCredentialsForm(forms.ModelForm):
    class Meta:
        model = MunicipalCredentials
        fields = ['municipal_username']
    municipal_username = forms.CharField(max_length=100, required=True, label="Municipal username")
    municipal_password_plain = forms.CharField(max_length=100, widget=forms.PasswordInput(), required=False, label="Contraseña Municipal")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Si la instancia existe y tiene una contraseña, no la precargamos en el campo de texto plano
        # Esto es para evitar mostrar la contraseña cifrada o un valor sin sentido.
        # El usuario deberá reingresar la contraseña si desea cambiarla.
        if self.instance and self.instance.pk: # If instance exists (editing)
            self.fields['municipal_password_plain'].required = False # Make password optional
        else: # If no instance (creating new)
            self.fields['municipal_password_plain'].required = True # Make password required

class UserProfileForm(UserChangeForm):
    password = None # No incluir el campo de contraseña aquí

    class Meta:
        model = User
        fields = ['username', 'email'] # Permitir editar nombre de usuario y correo

class MisionesCredentialsForm(forms.ModelForm):
    class Meta:
        model = MisionesCredentials
        fields = ['misiones_username']
    misiones_username = forms.CharField(max_length=100, required=True, label="Usuario Renta Misiones")
    misiones_password_plain = forms.CharField(max_length=100, widget=forms.PasswordInput(), required=False, label="Contraseña Renta Misiones")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['misiones_password_plain'].required = False
        else:
            self.fields['misiones_password_plain'].required = True

class MisionesRecordForm(forms.ModelForm):
    class Meta:
        model = MisionesRecord
        fields = ['tenant_name', 'tenant_email', 'rental_period_start', 'rental_period_end', 'amount', 'status', 'attachment', 'notes']

    tenant_name = forms.CharField(max_length=100, required=True, label="Nombre del Inquilino")
    tenant_email = forms.EmailField(required=False, label="Correo del Inquilino")
    rental_period_start = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), required=True, label="Fecha Inicio Alquiler")
    rental_period_end = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), required=True, label="Fecha Fin Alquiler")
    amount = forms.DecimalField(max_digits=10, decimal_places=2, required=True, label="Monto")
    status = forms.ChoiceField(choices=MisionesRecord.STATUS_CHOICES, required=True, label="Estado")
    attachment = forms.FileField(required=False, label="Adjunto")
    notes = forms.CharField(widget=forms.Textarea(), required=False, label="Notas")