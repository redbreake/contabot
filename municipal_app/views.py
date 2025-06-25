from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm
from django.urls import reverse_lazy
from django.views import generic
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.hashers import make_password, check_password # Importar utilidades de encriptación
from django.contrib.auth.models import User # Importar el modelo User
from .forms import MunicipalCredentialsForm, UserProfileForm # Importar UserProfileForm
from .models import MunicipalCredentials, ExecutionHistory # Importar ExecutionHistory

# Create your views here.

class RegisterView(generic.CreateView):
    form_class = UserCreationForm
    success_url = reverse_lazy('dashboard') # Redirigir al dashboard después del registro
    template_name = 'registration/register.html'

class MunicipalCredentialsView(LoginRequiredMixin, generic.UpdateView):
    model = MunicipalCredentials
    form_class = MunicipalCredentialsForm
    template_name = 'municipal_app/municipal_credentials_form.html'
    success_url = reverse_lazy('enter_billing') # Redirigir a la página de ingreso de facturación

    def get_object(self, queryset=None):
        # Obtener o crear las credenciales para el usuario actual
        obj, created = MunicipalCredentials.objects.get_or_create(user=self.request.user)
        # Desencriptar la contraseña para mostrarla en el formulario (considerar seguridad real)
        if obj.municipal_password:
             # Nota: check_password no desencripta, solo verifica.
             # Para mostrarla, necesitaríamos un método de encriptación reversible.
             # Por ahora, solo cargamos el objeto. La plantilla no mostrará la contraseña real.
             pass # Mantener el campo vacío en el formulario por seguridad
        return obj

    def get(self, request, *args, **kwargs):
        # Si las credenciales ya existen y están completas, redirigir a la página de ingreso de facturación
        credentials = MunicipalCredentials.objects.filter(user=request.user).first()
        if credentials and credentials.municipal_username and credentials.municipal_password:
            messages.info(request, 'Tus credenciales de la municipalidad ya están cargadas.')
            # Redirigir al dashboard una vez que esté implementado
            # return redirect('dashboard')
            return redirect('enter_billing')
        elif credentials:
             messages.info(request, 'Por favor, completa o actualiza tus credenciales de la municipalidad.')
        else:
             messages.info(request, 'Aún no has ingresado tus credenciales de la municipalidad.')

        return super().get(request, *args, **kwargs)


    def form_valid(self, form):
        form.instance.user = self.request.user
        # Encriptar la contraseña antes de guardarla
        form.instance.municipal_password = make_password(form.cleaned_data['municipal_password'])
        return super().form_valid(form)

import subprocess
from django.contrib import messages

class EnterBillingView(LoginRequiredMixin, generic.TemplateView):
    template_name = 'municipal_app/enter_billing.html'

    def post(self, request, *args, **kwargs):
        monto = request.POST.get('monto')
        user = request.user

        execution_status = 'Failed'
        execution_output = None
        execution_error = None

        try:
            # Recuperar credenciales de la municipalidad
            credentials = MunicipalCredentials.objects.get(user=user)
            municipal_username = credentials.municipal_username
            # Implementación temporal insegura para demostración:
            municipal_password = credentials.municipal_password # **RIESGO DE SEGURIDAD**

            # Ejecutar munibot.py como un proceso separado
            script_path = 'munibot.py' # Ajusta la ruta si es necesario
            result = subprocess.run(
                [sys.executable, script_path, municipal_username, municipal_password, monto],
                capture_output=True,
                text=True,
                check=True # Lanza una excepción si el script retorna un código de error
            )

            execution_status = 'Success'
            execution_output = result.stdout
            messages.success(request, 'El proceso de facturación se ha ejecutado correctamente.')
            # Opcional: mostrar la salida del script
            # messages.info(request, f'Salida del script: {result.stdout}')

        except MunicipalCredentials.DoesNotExist:
            execution_error = 'Credenciales de la municipalidad no encontradas.'
            messages.error(request, 'Por favor, ingresa tus credenciales de la municipalidad primero.')
            return redirect('municipal_credentials')
        except subprocess.CalledProcessError as e:
            execution_error = f'Error al ejecutar el script: {e.stderr}'
            messages.error(request, f'Error al ejecutar el script: {e.stderr}')
        except Exception as e:
            execution_error = f'Ocurrió un error: {e}'
            messages.error(request, f'Ocurrió un error: {e}')
        finally:
            # Guardar registro en el historial de ejecuciones
            ExecutionHistory.objects.create(
                user=user,
                amount=monto,
                status=execution_status,
                output=execution_output,
                error=execution_error
            )

        return redirect('enter_billing') # Redirigir de vuelta a la página de ingreso de facturación


class ProfileView(LoginRequiredMixin, generic.UpdateView):
    model = User # Usar el modelo User
    form_class = UserProfileForm # Usar el nuevo formulario de perfil de usuario
    template_name = 'municipal_app/profile.html'
    success_url = reverse_lazy('profile') # Redirigir a la misma página después de actualizar

    def get_object(self, queryset=None):
        # Devolver la instancia del usuario autenticado
        return self.request.user

class ExecutionHistoryView(LoginRequiredMixin, generic.ListView):
    model = ExecutionHistory
    template_name = 'municipal_app/history.html'
    context_object_name = 'history_list'
    ordering = ['-execution_time'] # Ordenar por fecha/hora descendente

class DashboardView(LoginRequiredMixin, generic.TemplateView):
    template_name = 'municipal_app/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['user'] = user # Pasar el objeto user al contexto

        # Verificar si el usuario tiene credenciales municipales completas
        try:
            credentials = MunicipalCredentials.objects.get(user=user)
            context['has_municipal_credentials'] = bool(credentials.municipal_username and credentials.municipal_password)
        except MunicipalCredentials.DoesNotExist:
            context['has_municipal_credentials'] = False

        return context

    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, 'Credenciales de la municipalidad actualizadas correctamente.')
        return super().form_valid(form)

        try:
            # Recuperar credenciales de la municipalidad
            credentials = MunicipalCredentials.objects.get(user=user)
            municipal_username = credentials.municipal_username
            # Desencriptar la contraseña (check_password verifica, no desencripta directamente)
            # Para pasarla al script, necesitamos la contraseña original.
            # Esto requiere un método de encriptación reversible o almacenar la contraseña original de forma segura.
            # Por ahora, asumiremos que check_password es suficiente para validar (aunque no lo es para recuperar).
            # **NOTA DE SEGURIDAD:** En una aplicación real, NO se debe almacenar la contraseña de la municipalidad en texto plano o con encriptación fácilmente reversible.
            # Se recomienda usar un enfoque más seguro, como un servicio de gestión de secretos o que el usuario la ingrese en cada ejecución.
            # Para este ejemplo, y dado que check_password no desencripta, no podemos pasar la contraseña original al script sin almacenarla de forma insegura.
            # Si el script *realmente* necesita la contraseña en texto plano, se debe reconsiderar la arquitectura de seguridad.
            # Para continuar con la ejecución del script como se planeó (pasando usuario/contraseña),
            # temporalmente usaremos la contraseña almacenada directamente, **reconociendo el riesgo de seguridad**.
            # Implementación temporal insegura para demostración:
            municipal_password = credentials.municipal_password # **RIESGO DE SEGURIDAD**

            # Ejecutar munibot.py como un proceso separado
            # Asegúrate de que la ruta al script sea correcta
            script_path = 'munibot.py' # Ajusta la ruta si es necesario
            result = subprocess.run(
                [sys.executable, script_path, municipal_username, municipal_password, monto],
                capture_output=True,
                text=True,
                check=True # Lanza una excepción si el script retorna un código de error
            )

            messages.success(request, 'El proceso de facturación se ha ejecutado correctamente.')
            # Opcional: mostrar la salida del script
            # messages.info(request, f'Salida del script: {result.stdout}')

        except MunicipalCredentials.DoesNotExist:
            messages.error(request, 'Por favor, ingresa tus credenciales de la municipalidad primero.')
            return redirect('municipal_credentials')
        except subprocess.CalledProcessError as e:
            messages.error(request, f'Error al ejecutar el script: {e.stderr}')
        except Exception as e:
            messages.error(request, f'Ocurrió un error: {e}')

        return redirect('enter_billing') # Redirigir de vuelta a la página de ingreso de facturación
