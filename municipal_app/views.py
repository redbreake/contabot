import logging
import os
import sys # Import sys to print path
from decimal import Decimal, InvalidOperation # Added for amount validation

from cryptography.fernet import Fernet

from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm
from django.urls import reverse_lazy, reverse
from django.views import generic
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.contrib import messages
from django.conf import settings

# Print sys.path for debugging
print("sys.path in views.py:", sys.path)

from .forms import MunicipalCredentialsForm, UserProfileForm, MisionesCredentialsForm, FileUploadForm
from .models import MunicipalCredentials, ExecutionHistory, MisionesCredentials, MisionesExecutionHistory
from .utils import extract_total_from_file
from munibot import run_munibot
try:
    from rentabot import run_rentabot
except ImportError:
    run_rentabot = None

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

        # Manejar carga de archivo
        uploaded_file = request.FILES.get('file')
        if uploaded_file:
            try:
                extracted_monto = extract_total_from_file(uploaded_file)
                monto = str(extracted_monto)
                messages.info(request, f'Monto extraído del archivo: {monto}')
                logger.debug(f"EnterBillingView: Monto extraído del archivo: {monto}")
            except ValueError as e:
                messages.error(request, f'Error procesando archivo: {e}')
                logger.error(f"EnterBillingView: Error procesando archivo: {e}")
                return redirect('enter_billing')
        elif not monto:
            messages.error(request, 'Debes ingresar un monto manualmente o subir un archivo.')
            logger.error(f"EnterBillingView: No se proporcionó monto ni archivo")
            return redirect('enter_billing')

        logger.debug(f"EnterBillingView: POST request para usuario {user.username}")
        logger.debug(f"EnterBillingView: Monto final: {monto}")

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

        try:
            misiones_credentials = MisionesCredentials.objects.get(user=user)
            context['misiones_username'] = misiones_credentials.misiones_username
            context['has_misiones_credentials'] = bool(misiones_credentials.misiones_username and misiones_credentials.misiones_password)
            logger.debug(f"ProfileView: Credenciales de misiones encontradas para {user.username}. Username: {misiones_credentials.misiones_username}, Has password: {bool(misiones_credentials.misiones_password)}")
        except MisionesCredentials.DoesNotExist:
            context['misiones_username'] = None
            context['has_misiones_credentials'] = False
            logger.debug(f"ProfileView: No se encontraron credenciales de misiones para {user.username}.")

        logger.debug(f"ProfileView: Valor final de has_municipal_credentials en contexto: {context.get('has_municipal_credentials')}, Tipo: {type(context.get('has_municipal_credentials'))}")
        return context

class MisionesCredentialsView(LoginRequiredMixin, generic.UpdateView):
    model = MisionesCredentials
    form_class = MisionesCredentialsForm
    template_name = 'municipal_app/misiones_credentials_form.html'
    success_url = reverse_lazy('enter_misiones')

    def get_object(self, queryset=None):
        if not self.request.user.is_authenticated:
            return None
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

class EnterMisionesBillingView(LoginRequiredMixin, generic.TemplateView):
    template_name = 'municipal_app/enter_misiones_billing.html'

    def post(self, request, *args, **kwargs):
        monto = request.POST.get('monto')
        user = self.request.user

        # Manejar carga de archivo
        uploaded_file = request.FILES.get('file')
        if uploaded_file:
            try:
                extracted_monto = extract_total_from_file(uploaded_file)
                monto = str(extracted_monto)
                messages.info(request, f'Monto extraído del archivo: {monto}')
                logger.debug(f"EnterMisionesBillingView: Monto extraído del archivo: {monto}")
            except ValueError as e:
                messages.error(request, f'Error procesando archivo: {e}')
                logger.error(f"EnterMisionesBillingView: Error procesando archivo: {e}")
                return redirect('enter_missions')
        elif not monto:
            messages.error(request, 'Debes ingresar un monto manualmente o subir un archivo.')
            logger.error(f"EnterMisionesBillingView: No se proporcionó monto ni archivo")
            return redirect('enter_missions')

        logger.debug(f"EnterMisionesBillingView: POST request para usuario {user.username}")
        logger.debug(f"EnterMisionesBillingView: Monto final: {monto}")

        execution_status = 'Failed'
        execution_output = None
        execution_error = None

        try:
            credentials = MisionesCredentials.objects.get(user=user)
            misiones_username = str(credentials.misiones_username or '')
            
            misiones_password_encrypted = credentials.misiones_password
            misiones_password = ''
            if f and misiones_password_encrypted:
                try:
                    misiones_password = f.decrypt(misiones_password_encrypted).decode()
                    logger.debug(f"EnterMisionesBillingView: Contraseña descifrada para {user.username}.")
                except Exception as decrypt_e:
                    execution_error = f'Error al descifrar la contraseña: {decrypt_e}'
                    logger.error(f"EnterMisionesBillingView: {execution_error}")
                    messages.error(self.request, 'Error de seguridad: No se pudo descifrar la contraseña. Contacta al administrador.')
                    raise
            else:
                execution_error = 'Error de seguridad: No se pudo descifrar la contraseña. Fernet no inicializado o contraseña vacía.'
                logger.error(f"EnterMisionesBillingView: {execution_error}")
                messages.error(self.request, 'Error de seguridad: No se pudo descifrar la contraseña. Contacta al administrador.')
                raise Exception("Fernet not initialized or encrypted password missing.")

            logger.debug(f"EnterMisionesBillingView: Credenciales recuperadas. Usuario: {misiones_username}, Contraseña (descifrada): {misiones_password[:10]}...")

            monto_str = str(monto) if monto is not None else ''
            logger.debug(f"EnterMisionesBillingView: Monto a pasar al script: {monto_str}")

            # Ruta al driver de Edge
            driver_path = os.path.join(settings.BASE_DIR, 'edgedriver_win64', 'msedgedriver.exe')
            logger.debug(f"EnterMisionesBillingView: Usando driver path: {driver_path}")

            # Ejecutar rentabot.py directamente
            if run_rentabot:
                run_status, run_output, run_error = run_rentabot(misiones_username, misiones_password, monto_str, driver_path)
            else:
                run_status, run_output, run_error = ('Failed', 'rentabot not implemented yet', 'rentabot module not found')

            execution_status = run_status
            execution_output = run_output
            execution_error = run_error

            if execution_status == 'Success':
                logger.info(f"EnterMisionesBillingView: Script ejecutado con éxito. Salida: {execution_output}")
                messages.success(self.request, 'El proceso de declaración de facturación mensual en Renta Misiones se ha ejecutado correctamente.')
            else:
                logger.error(f"EnterMisionesBillingView: Error al ejecutar el script. Error: {execution_error}")
                messages.error(self.request, f'Error al ejecutar el script: {execution_error}')

        except MisionesCredentials.DoesNotExist:
            execution_error = 'Credenciales de Renta Misiones no encontradas.'
            logger.error(f"EnterMisionesBillingView: Error: {execution_error}")
            messages.error(self.request, 'Por favor, ingresa tus credenciales de Renta Misiones primero.')
            return redirect('misiones_credentials')
        except Exception as e:
            execution_error = f'Ocurrió un error inesperado: {e}'
            logger.error(f"EnterMisionesBillingView: Ocurrió un error inesperado: {e}")
            messages.error(self.request, f'Ocurrió un error: {e}')
        finally:
            logger.debug(f"EnterMisionesBillingView: Guardando historial de ejecución. Estado: {execution_status}, Monto: {monto}, Error: {execution_error}")

            amount_to_save = None
            if monto:
                try:
                    amount_to_save = Decimal(monto)
                except InvalidOperation:
                    # El monto no es un número válido, se guarda como nulo
                    logger.warning(f"Valor de monto no válido '{monto}' recibido del usuario {user.username}")
                    amount_to_save = None

            MisionesExecutionHistory.objects.create(
                user=user,
                amount=amount_to_save, # Usar el valor validado
                status=execution_status,
                output=execution_output,
                error=execution_error
            )

        return redirect('enter_missions')

class MisionesHistoryView(LoginRequiredMixin, generic.ListView):
    model = MisionesExecutionHistory
    template_name = 'municipal_app/misiones_history.html'
    context_object_name = 'misiones_list'
    ordering = ['-id']

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

class CombinedHistoryView(LoginRequiredMixin, generic.TemplateView):
    template_name = 'municipal_app/combined_history.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        history_type = self.request.GET.get('type', 'municipal')  # Default to municipal

        if history_type == 'municipal':
            context['history_list'] = ExecutionHistory.objects.filter(user=user).order_by('-execution_time')
            context['history_title'] = 'Historial de Ejecuciones Municipales'
        elif history_type == 'misiones':
            context['history_list'] = MisionesExecutionHistory.objects.filter(user=user).order_by('-execution_time')
            context['history_title'] = 'Historial de Ejecuciones Renta Misiones'
        else:
            context['history_list'] = ExecutionHistory.objects.filter(user=user).order_by('-execution_time')
            context['history_title'] = 'Historial de Ejecuciones Municipales'

        context['current_type'] = history_type
        return context

    def post(self, request, *args, **kwargs):
        user = request.user

        # Verificar si es una eliminación masiva
        if request.POST.get('delete_all'):
            history_type = request.POST.get('current_type', 'municipal')
            try:
                if history_type == 'municipal':
                    count = ExecutionHistory.objects.filter(user=user).delete()[0]
                    messages.success(request, f'Se eliminaron {count} registros municipales exitosamente.')
                elif history_type == 'misiones':
                    count = MisionesExecutionHistory.objects.filter(user=user).delete()[0]
                    messages.success(request, f'Se eliminaron {count} registros de Renta Misiones exitosamente.')
                else:
                    messages.error(request, 'Tipo de historial no válido.')
            except Exception as e:
                messages.error(request, f'Error al eliminar los registros: {str(e)}')

            return redirect(f'{reverse("history")}?type={history_type}')

        # Eliminación individual
        record_id = request.POST.get('record_id')
        record_type = request.POST.get('record_type')

        if not record_id or not record_type:
            messages.error(request, 'ID de registro o tipo no especificado.')
            return redirect(request.META.get('HTTP_REFERER', 'history'))

        try:
            if record_type == 'municipal':
                record = ExecutionHistory.objects.get(id=record_id, user=user)
                record.delete()
                messages.success(request, 'Registro municipal eliminado exitosamente.')
            elif record_type == 'misiones':
                record = MisionesExecutionHistory.objects.get(id=record_id, user=user)
                record.delete()
                messages.success(request, 'Registro de Renta Misiones eliminado exitosamente.')
            else:
                messages.error(request, 'Tipo de registro no válido.')
        except (ExecutionHistory.DoesNotExist, MisionesExecutionHistory.DoesNotExist):
            messages.error(request, 'Registro no encontrado o no tienes permisos para eliminarlo.')
        except Exception as e:
            messages.error(request, f'Error al eliminar el registro: {str(e)}')

        # Redirigir manteniendo el tipo de historial actual
        history_type = request.POST.get('current_type', 'municipal')
        return redirect(f'{reverse("history")}?type={history_type}')

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

        try:
            misiones_credentials = MisionesCredentials.objects.get(user=user)
            context['has_misiones_credentials'] = bool(misiones_credentials.misiones_username and misiones_credentials.misiones_password)
        except MisionesCredentials.DoesNotExist:
            context['has_misiones_credentials'] = False

        return context


class AdminDashboardView(LoginRequiredMixin, generic.TemplateView):
    template_name = 'municipal_app/admin_dashboard.html'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if 'toggle_superuser' in request.POST:
            user_id = request.POST.get('user_id')
            try:
                user_to_toggle = User.objects.get(id=user_id)
                if user_to_toggle != request.user:
                    user_to_toggle.is_superuser ^= True
                    user_to_toggle.save()
                    status = "removido" if not user_to_toggle.is_superuser else "asignado"
                    messages.success(request, f'Privilegio de superusuario {status} para {user_to_toggle.username}.')
                else:
                    messages.error(request, 'No puedes cambiar tu propio privilegio.')
            except User.DoesNotExist:
                messages.error(request, 'Usuario no encontrado.')
        return redirect('admin_dashboard')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Estadísticas básicas
        context['users_count'] = User.objects.count()
        context['municipal_credentials_count'] = MunicipalCredentials.objects.count()
        context['misiones_credentials_count'] = MisionesCredentials.objects.count()
        context['execution_history_count'] = ExecutionHistory.objects.count()
        context['misiones_execution_history_count'] = MisionesExecutionHistory.objects.count()

        # Usuario activos (último login en últimos 30 días)
        from django.utils import timezone
        from datetime import timedelta
        active_threshold = timezone.now() - timedelta(days=30)
        context['active_users_count'] = User.objects.filter(last_login__gte=active_threshold).count()

        # Gráfico de ejecuciones por mes (últimos 6 meses)
        from django.db.models import Count
        from django.db.models.functions import TruncMonth

        six_months_ago = timezone.now() - timedelta(days=180)

        executions_monthly = ExecutionHistory.objects.filter(
            execution_time__gte=six_months_ago
        ).annotate(
            month=TruncMonth('execution_time')
        ).values('month').annotate(count=Count('id')).order_by('month')

        misiones_executions_monthly = MisionesExecutionHistory.objects.filter(
            execution_time__gte=six_months_ago
        ).annotate(
            month=TruncMonth('execution_time')
        ).values('month').annotate(count=Count('id')).order_by('month')

        # Para gráficos
        context['executions_labels'] = [e['month'].strftime('%Y-%m') for e in executions_monthly]
        context['executions_data'] = [e['count'] for e in executions_monthly]
        context['misiones_executions_labels'] = [e['month'].strftime('%Y-%m') for e in misiones_executions_monthly]
        context['misiones_executions_data'] = [e['count'] for e in misiones_executions_monthly]

        # Success/Fail rate
        success_count = ExecutionHistory.objects.filter(status='Success').count()
        fail_count = ExecutionHistory.objects.filter(status__in=['Failed', '']).count()
        total_execs = ExecutionHistory.objects.count()
        context['success_rate'] = (success_count / total_execs) * 100 if total_execs > 0 else 0
        context['success_fail_labels'] = ['Éxito', 'Fallo']
        context['success_fail_data'] = [success_count, fail_count]

        # Todos los usuarios para gestionar privilegios (últimos 50 por fecha)
        context['all_users'] = User.objects.all().order_by('-date_joined')[:50]

        # Logins recientes
        recent_logins = User.objects.exclude(last_login__isnull=True).order_by('-last_login')[:5]
        context['recent_logins'] = recent_logins

        return context
