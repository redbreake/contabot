from django.db import models
from django.contrib.auth.models import User
from cryptography.fernet import Fernet # Importar Fernet

# Create your models here.

class MunicipalCredentials(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    municipal_username = models.CharField(max_length=100)
    # ADVERTENCIA DE SEGURIDAD: La contraseña municipal se almacena cifrada.
    # La clave de cifrado debe gestionarse de forma segura (ej. variables de entorno).
    municipal_password = models.BinaryField(max_length=256) # Cambiado a BinaryField para almacenar datos cifrados

    def __str__(self):
        return f"Credentials for {self.user.username}"

class ExecutionHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    execution_time = models.DateTimeField(auto_now_add=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20) # Ej: 'Success', 'Failed'
    output = models.TextField(blank=True, null=True)
    error = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Execution for {self.user.username} at {self.execution_time.strftime('%Y-%m-%d %H:%M')}"

class MisionesCredentials(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    misiones_username = models.CharField(max_length=100)
    # ADVERTENCIA DE SEGURIDAD: La contraseña de Renta Misiones se almacena cifrada.
    # La clave de cifrado debe gestionarse de forma segura (ej. variables de entorno).
    misiones_password = models.BinaryField(max_length=256)

    def __str__(self):
        return f"Misiones Credentials for {self.user.username}"

class MisionesRecord(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    record_date = models.DateTimeField(auto_now_add=True)
    tenant_name = models.CharField(max_length=100)
    tenant_email = models.EmailField(blank=True)
    rental_period_start = models.DateField()
    rental_period_end = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    STATUS_CHOICES = [
        ('Pendiente', 'Pendiente'),
        ('Pagado', 'Pagado'),
        ('Vencido', 'Vencido'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pendiente')
    attachment = models.FileField(upload_to='misiones_attachments/', blank=True, null=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"Misiones Record for {self.user.username}: {self.tenant_name}"
