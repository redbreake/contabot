from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.views.generic.base import RedirectView
from .views import RegisterView, MunicipalCredentialsView, EnterBillingView, ProfileView, ExecutionHistoryView, DashboardView, MisionesCredentialsView, EnterMisionesBillingView, MisionesHistoryView, AdminDashboardView, CombinedHistoryView, ChatbotView, chatbot_api

urlpatterns = [
    # URL raíz que redirige a login
    path('', DashboardView.as_view(), name='index'), # Redirigir a dashboard si está logueado, o a login si no

    # URLs de autenticación
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),

    # URL para credenciales de la municipalidad
    path('municipal-credentials/', MunicipalCredentialsView.as_view(), name='municipal_credentials'),

    # URL para ingreso de facturación
    path('enter-billing/', EnterBillingView.as_view(), name='enter_billing'),

    # URL para perfil de usuario
    path('profile/', ProfileView.as_view(), name='profile'),

    # URL para historial de ejecuciones combinado
    path('history/', CombinedHistoryView.as_view(), name='history'),

    # URL para el dashboard
    path('dashboard/', DashboardView.as_view(), name='dashboard'),

    # URL para admin dashboard
    path('admin-dashboard/', AdminDashboardView.as_view(), name='admin_dashboard'),

    # URLs para Renta Misiones
    path('misiones-credentials/', MisionesCredentialsView.as_view(), name='misiones_credentials'),
    path('enter-misiones/', EnterMisionesBillingView.as_view(), name='enter_misiones'),
    path('misiones-history/', MisionesHistoryView.as_view(), name='misiones_history'),

    # URL para el chatbot
    path('chatbot/', ChatbotView.as_view(), name='chatbot'),

    # API del Chatbot
    path('api/chatbot/', chatbot_api, name='chatbot_api'),
]