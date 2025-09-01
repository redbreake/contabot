import logging
import os
import sys # Import sys to print path
from decimal import Decimal, InvalidOperation # Added for amount validation

from cryptography.fernet import Fernet

from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm
from django.urls import reverse_lazy
from django.views import generic
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.contrib import messages
from django.conf import settings

# Print sys.path for debugging
print("sys.path in views.py:", sys.path)

from .forms import MunicipalCredentialsForm, UserProfileForm, MisionesCredentialsForm, MisionesRecordForm
from .models import MunicipalCredentials, ExecutionHistory, MisionesCredentials, MisionesRecord
from munibot import run_munibot

logger = logging.getLogger(__name__)

try:
    f = Fernet(settings.FERNET_KEY)
except Exception as e:
    logger.error(f"Error initializing Fernet: {e}. Ensure FERNET_KEY is set correctly in settings.py")
    f = None

class RegisterView(generic.CreateView):
    form_class = UserCreationForm
    success_url = reverse_lazy('dashboard')
    template_name = 'registration/register.html'

class MunicipalCredentialsView(LoginRequiredMixin, generic.UpdateView):
    model = MunicipalCredentials
    form_class = MunicipalCredentialsForm
    template_name = 'municipal_app/municipal_credentials_form.html'
    success_url = reverse_lazy('enter_billing')

    def get_object(self, queryset=None):
        logger.debug(f"MunicipalCredentialsView: get_object para usuario {self.request.user.username}")
        try:
            obj = MunicipalCredentials.objects.get(user=self.request.user)
            logger.info(f"MunicipalCredentialsView: Obtenidas credenciales existentes para {self.request.user.username}")
            return obj
        except MunicipalCredentials.DoesNotExist:
            logger.info(f"MunicipalCredentialsView: No existen credenciales para {self.request.user.username}. Se creará una nueva.")
            return None # Return None if no object exists, form_valid will handle creation

    def get(self, request, *args, **kwargs):
        logger.debug(f"MunicipalCredentialsView: GET request para usuario {request.user.username}")
        credentials = MunicipalCredentials.objects.filter(user=request.user).first()
        if credentials and credentials.municipal_username and credentials.municipal_password:
            logger.info(f"MunicipalCredentialsView: Credenciales completas para {request.user.username}. Mostrando formulario para modificación.")
            messages.info(request, 'Tus credenciales de la municipalidad ya están cargadas. Puedes modificarlas aquí.')
        elif credentials:
            logger.info(f"MunicipalCredentialsView: Credenciales incompletas para {request.user.username}. Solicitando actualización.")
            messages.info(request, 'Por favor, completa o actualiza tus credenciales de la municipalidad.')
        else:
            logger.info(f"MunicipalCredentialsView: No hay credenciales para {request.user.username}. Solicitando ingreso.")
            messages.info(request, 'Aún no has ingresado tus credenciales de la municipalidad.')

        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        logger.debug(f"MunicipalCredentialsView: form_valid para usuario {self.request.user.username}")
        
        # If no instance exists, create one
        if not form.instance.pk:
            form.instance.user = self.request.user
            logger.info(f"MunicipalCredentialsView: Creando nuevas credenciales para {self.request.user.username}")
        
        municipal_password_plain = form.cleaned_data.get('municipal_password_plain')
        
        if municipal_password_plain:
            if f:
                encrypted_password = f.encrypt(municipal_password_plain.encode())
                form.instance.municipal_password = encrypted_password
                logger.info(f"MunicipalCredentialsView: Contraseña cifrada para {self.request.user.username}.")
            else:
                logger.error(f"MunicipalCredentialsView: Fernet no inicializado. No se pudo cifrar la contraseña para {self.request.user.username}.")
                messages.error(self.request, 'Error de seguridad: No se pudo cifrar la contraseña. Contacta al administrador.')
                return self.form_invalid(form)
        elif not form.instance.pk: # If it's a new instance and no password was provided
            logger.error(f"MunicipalCredentialsView: No se proporcionó contraseña para un nuevo registro de credenciales para {self.request.user.username}.")
            messages.error(self.request, 'Por favor, ingresa la contraseña municipal.')
            return self.form_invalid(form)
        
        response = super().form_valid(form)
        logger.info(f"MunicipalCredentialsView: Credenciales guardadas/actualizadas para {self.request.user.username}. Username: {form.instance.municipal_username}")
        return response

    def form_invalid(self, form):
        logger.debug(f"MunicipalCredentialsView: form_invalid para usuario {self.request.user.username}")
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(self.request, f"{form.fields[field].label}: {error}")
        return self.render_to_response(self.get_context_data(form=form))

class EnterBillingView(LoginRequiredMixin, generic.TemplateView):
    template_name = 'municipal_app/enter_billing.html'

    def post(self, request, *args, **kwargs):
        monto = request.POST.get('monto')
        user = request.user

        logger.debug(f"EnterBillingView: POST request para usuario {user.username}")
        logger.debug(f"EnterBillingView: Monto recibido: {monto}")

        execution_status = 'Failed'
        execution_output = None
        execution_error = None

        try:
            credentials = MunicipalCredentials.objects.get(user=user)
            municipal_username = str(credentials.municipal_username or '')
            
            municipal_password_encrypted = credentials.municipal_password
            municipal_password = ''
            if f and municipal_password_encrypted:
                try:
                    municipal_password = f.decrypt(municipal_password_encrypted).decode()
                    logger.debug(f"EnterBillingView: Contraseña descifrada para {user.username}.")
                except Exception as decrypt_e:
                    execution_error = f'Error al descifrar la contraseña: {decrypt_e}'
                    logger.error(f"EnterBillingView: {execution_error}")
                    messages.error(request, 'Error de seguridad: No se pudo descifrar la contraseña. Contacta al administrador.')
                    raise
            else:
                execution_error = 'Error de seguridad: No se pudo descifrar la contraseña. Fernet no inicializado o contraseña vacía.'
                logger.error(f"EnterBillingView: {execution_error}")
                messages.error(request, 'Error de seguridad: No se pudo descifrar la contraseña. Contacta al administrador.')
                raise Exception("Fernet not initialized or encrypted password missing.")

            logger.debug(f"EnterBillingView: Credenciales recuperadas. Usuario: {municipal_username}, Contraseña (descifrada): {municipal_password[:10]}...")

            monto_str = str(monto) if monto is not None else ''
            logger.debug(f"EnterBillingView: Monto a pasar al script: {monto_str}")

            # Ruta al driver de Edge
            driver_path = os.path.join(settings.BASE_DIR, 'edgedriver_win64', 'msedgedriver.exe')
            logger.debug(f"EnterBillingView: Usando driver path: {driver_path}")

            # Ejecutar munibot.py directamente
            run_status, run_output, run_error = run_munibot(municipal_username, municipal_password, monto_str, driver_path)

            execution_status = run_status
            execution_output = run_output
            execution_error = run_error

            if execution_status == 'Success':
                logger.info(f"EnterBillingView: Script ejecutado con éxito. Salida: {execution_output}")
                messages.success(request, 'El proceso de declaración jurada mensual se ha ejecutado correctamente.')
            else:
                logger.error(f"EnterBillingView: Error al ejecutar el script. Error: {execution_error}")
                messages.error(request, f'Error al ejecutar el script: {execution_error}')

        except MunicipalCredentials.DoesNotExist:
            execution_error = 'Credenciales de la municipalidad no encontradas.'
            logger.error(f"EnterBillingView: Error: {execution_error}")
            messages.error(request, 'Por favor, ingresa tus credenciales de la municipalidad primero.')
            return redirect('municipal_credentials')
        except Exception as e:
            execution_error = f'Ocurrió un error inesperado: {e}'
            logger.error(f"EnterBillingView: Ocurrió un error inesperado: {e}")
            messages.error(request, f'Ocurrió un error: {e}')
        finally:
            logger.debug(f"EnterBillingView: Guardando historial de ejecución. Estado: {execution_status}, Monto: {monto}, Error: {execution_error}")

            amount_to_save = None
            if monto:
                try:
                    amount_to_save = Decimal(monto)
                except InvalidOperation:
                    # El monto no es un número válido, se guarda como nulo
                    logger.warning(f"Valor de monto no válido '{monto}' recibido del usuario {user.username}")
                    amount_to_save = None

            ExecutionHistory.objects.create(
                user=user,
                amount=amount_to_save, # Usar el valor validado
                status=execution_status,
                output=execution_output,
                error=execution_error
            )

        return redirect('enter_billing')

class ExecutionHistoryView(LoginRequiredMixin, generic.ListView):
    model = ExecutionHistory
    template_name = 'municipal_app/history.html'
    context_object_name = 'history_list'
    ordering = ['-execution_time']

class ProfileView(LoginRequiredMixin, generic.UpdateView):
    model = User
    form_class = UserProfileForm
    template_name = 'municipal_app/profile.html'
    success_url = reverse_lazy('profile')

    def get_object(self, queryset=None):
        return self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        try:
            municipal_credentials = MunicipalCredentials.objects.get(user=user)
            context['municipal_username'] = municipal_credentials.municipal_username
            context['has_municipal_credentials'] = bool(municipal_credentials.municipal_username and municipal_credentials.municipal_password)
            logger.debug(f"ProfileView: Credenciales encontradas para {user.username}. Username: {municipal_credentials.municipal_username}, Has password: {bool(municipal_credentials.municipal_password)}")
        except MunicipalCredentials.DoesNotExist:
            context['municipal_username'] = None
            context['has_municipal_credentials'] = False
            logger.debug(f"ProfileView: No se encontraron credenciales para {user.username}.")

        logger.debug(f"ProfileView: Valor final de has_municipal_credentials en contexto: {context.get('has_municipal_credentials')}, Tipo: {type(context.get('has_municipal_credentials'))}")
        return context

class MisionesCredentialsView(LoginRequiredMixin, generic.UpdateView):
    model = MisionesCredentials
    form_class = MisionesCredentialsForm
    template_name = 'municipal_app/misiones_credentials_form.html'
    success_url = reverse_lazy('enter_misiones')

    def get_object(self, queryset=None):
        logger.debug(f"MisionesCredentialsView: get_object para usuario {self.request.user.username}")
        try:
            obj = MisionesCredentials.objects.get(user=self.request.user)
            logger.info(f"MisionesCredentialsView: Credenciales existentes encontradas para {self.request.user.username}")
            return obj
        except MisionesCredentials.DoesNotExist:
            logger.info(f"MisionesCredentialsView: No existen credenciales para {self.request.user.username}. Se creará una nueva.")
            return None

    def get(self, request, *args, **kwargs):
        logger.debug(f"MisionesCredentialsView: GET request para usuario {request.user.username}")
        credentials = MisionesCredentials.objects.filter(user=request.user).first()
        if credentials and credentials.misiones_username and credentials.misiones_password:
            logger.info(f"MisionesCredentialsView: Credenciales completas para {request.user.username}. Mostrando formulario para modificación.")
            messages.info(request, 'Tus credenciales de Renta Misiones ya están cargadas. Puedes modificarlas aquí.')
        elif credentials:
            logger.info(f"MisionesCredentialsView: Credenciales incompletas para {request.user.username}. Solicitando actualización.")
            messages.info(request, 'Por favor, completa o actualiza tus credenciales de Renta Misiones.')
        else:
            logger.info(f"MisionesCredentialsView: No hay credenciales para {request.user.username}. Solicitando ingreso.")
            messages.info(request, 'Aún no has ingresado tus credenciales de Renta Misiones.')

        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        logger.debug(f"MisionesCredentialsView: form_valid para usuario {self.request.user.username}")

        if not form.instance.pk:
            form.instance.user = self.request.user
            logger.info(f"MisionesCredentialsView: Creando nuevas credenciales para {self.request.user.username}")

        misiones_password_plain = form.cleaned_data.get('misiones_password_plain')

        if misiones_password_plain:
            if f:
                encrypted_password = f.encrypt(misiones_password_plain.encode())
                form.instance.misiones_password = encrypted_password
                logger.info(f"MisionesCredentialsView: Contraseña cifrada para {self.request.user.username}.")
            else:
                logger.error(f"MisionesCredentialsView: Fernet no inicializado. No se pudo cifrar la contraseña para {self.request.user.username}.")
                messages.error(self.request, 'Error de seguridad: No se pudo cifrar la contraseña. Contacta al administrador.')
                return self.form_invalid(form)
        elif not form.instance.pk:
            logger.error(f"MisionesCredentialsView: No se proporcionó contraseña para un nuevo registro de credenciales para {self.request.user.username}.")
            messages.error(self.request, 'Por favor, ingresa la contraseña de Renta Misiones.')
            return self.form_invalid(form)

        response = super().form_valid(form)
        logger.info(f"MisionesCredentialsView: Credenciales guardadas/actualizadas para {self.request.user.username}. Username: {form.instance.misiones_username}")
        return response

    def form_invalid(self, form):
        logger.debug(f"MisionesCredentialsView: form_invalid para usuario {self.request.user.username}")
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(self.request, f"{form.fields[field].label}: {error}")
        return self.render_to_response(self.get_context_data(form=form))

class EnterMisionesView(LoginRequiredMixin, generic.FormView):
    form_class = MisionesRecordForm
    template_name = 'municipal_app/enter_misiones.html'
    success_url = reverse_lazy('misiones_history')

    def form_valid(self, form):
        logger.debug(f"EnterMisionesView: form_valid para usuario {self.request.user.username}")

        record = form.save(commit=False)
        record.user = self.request.user
        record.save()
        logger.info(f"EnterMisionesView: Registro de alquiler guardado para {self.request.user.username}")

        messages.success(self.request, 'Información de alquiler guardada correctamente.')
        return super().form_valid(form)

class MisionesHistoryView(LoginRequiredMixin, generic.ListView):
    model = MisionesRecord
    template_name = 'municipal_app/misiones_history.html'
    context_object_name = 'misiones_list'
    ordering = ['-record_date']

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

class DashboardView(LoginRequiredMixin, generic.TemplateView):
    template_name = 'municipal_app/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['user'] = user

        try:
            credentials = MunicipalCredentials.objects.get(user=user)
            context['has_municipal_credentials'] = bool(credentials.municipal_username and credentials.municipal_password)
        except MunicipalCredentials.DoesNotExist:
            context['has_municipal_credentials'] = False
        return context

