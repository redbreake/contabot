from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class MunicipalCredentials(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    municipal_username = models.CharField(max_length=100)
    # Considerar encriptar la contraseña antes de guardarla
    municipal_password = models.CharField(max_length=100)

    def __str__(self):
        return f"Credentials for {self.user.username}"

class ExecutionHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    execution_time = models.DateTimeField(auto_now_add=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20) # Ej: 'Success', 'Failed'
    output = models.TextField(blank=True, null=True)
    error = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Execution for {self.user.username} at {self.execution_time.strftime('%Y-%m-%d %H:%M')}"
