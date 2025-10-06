# Pago Municipal

Este es un proyecto de aplicación web Django para gestionar pagos municipales.

## Características

- Registro e inicio de sesión de usuarios.
- Ingreso de credenciales de la municipalidad.
- Ingreso de facturación mensual (a través de la ejecución de un script `munibot.py`).
- Historial de ejecuciones.
- Edición de perfil de usuario.

## Requisitos

- Python 3.x
- Django
- Otras dependencias listadas en `requirements.txt`

## Instalación

1. Clona el repositorio:
   ```bash
   git clone <URL_del_repositorio>
   cd DJANGOMUNI
   ```

2. Crea y activa un entorno virtual:
   ```bash
   python -m venv venv
   # En Windows
   .\venv\Scripts\activate
   # En macOS/Linux
   source venv/bin/activate
   ```

3. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```

4. Aplica las migraciones de la base de datos:
   ```bash
   python manage.py migrate
   ```

5. Crea un superusuario (opcional, para acceder al panel de administración):
   ```bash
   python manage.py createsuperuser
   ```

6. Ejecuta el servidor de desarrollo:
   ```bash
   python manage.py runserver
   ```

La aplicación estará disponible en `http://127.0.0.1:8000/`.

## Configuración Adicional

- Asegúrate de tener el script `munibot.py` en la raíz del proyecto.
- Configura las credenciales de la municipalidad a través de la interfaz de usuario después de iniciar sesión.

## Uso de Scripts

### `rentabot.py`

Este script se encarga de procesar las facturas de rentas municipales. Se ejecuta automáticamente cuando se ingresan los datos de facturación correspondientes a través de la interfaz web.

### `munibot.py` y `munibot2py`

Scripts utilizados para la interacción con sistemas municipales y procesamiento de datos relacionados con los pagos. Ambos deben estar ubicados en la raíz del proyecto para su correcto funcionamiento.

## Contribución

Si deseas contribuir a este proyecto, por favor, sigue los siguientes pasos:
1. Haz un fork del repositorio.
2. Crea una rama para tu nueva funcionalidad (`git checkout -b feature/nueva-funcionalidad`).
3. Realiza tus cambios y commitea (`git commit -m 'feat: añade nueva funcionalidad'`).
4. Haz push a tu rama (`git push origin feature/nueva-funcionalidad`).
5. Abre un Pull Request.

## Licencia

Este proyecto está bajo la Licencia MIT. Consulta el archivo `LICENSE` para más detalles.