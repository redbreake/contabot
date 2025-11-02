#!/usr/bin/env python
import os
import sys
import django

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'municipal_payments.settings')

django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()
try:
    user = User.objects.get(username='admin')
    user.set_password('password')
    user.save()
    print('Contraseña del superusuario cambiada exitosamente')
except User.DoesNotExist:
    print('Usuario admin no encontrado')