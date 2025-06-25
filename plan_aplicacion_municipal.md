# Plan Ampliado para Aplicación Django de Pago Municipal

**Objetivo:** Desarrollar una aplicación web con Django, segura y profesional, que permita a los usuarios gestionar sus pagos municipales automatizados, con un sistema de autenticación completo, manejo seguro de credenciales externas, historial de operaciones y una interfaz atractiva con Bootstrap.

**Plan de Acción Detallado:**

1.  **Refinamiento del Flujo de Usuario Post-Login:**
    *   Asegurar que, tras iniciar sesión, el usuario sea redirigido a la página de ingreso de credenciales de la municipalidad (`/municipal-credentials/`) si aún no las ha guardado.
    *   Si las credenciales ya existen, redirigir al usuario a una página de inicio o dashboard (que crearemos) o directamente a la página de ingreso de facturación (`/enter-billing/`).

2.  **Implementación de Página de Perfil de Usuario:**
    *   Crear una nueva vista y URL (`/profile/`) para mostrar un perfil de usuario.
    *   Esta página mostrará información del usuario y permitirá ver (parcialmente enmascaradas por seguridad) y editar las credenciales de la municipalidad asociadas.
    *   Crear una plantilla HTML (`profile.html`) para esta página, utilizando formularios de modelo para la edición de credenciales.

3.  **Mejora de la Seguridad de Credenciales de la Municipalidad:**
    *   Investigar e implementar un método robusto para encriptar la contraseña de la municipalidad antes de guardarla en la base de datos. Se puede usar la criptografía integrada de Django o una librería externa recomendada.
    *   Modificar el modelo `MunicipalCredentials` para almacenar la contraseña encriptada.
    *   Actualizar la vista `MunicipalCredentialsView` para encriptar la contraseña al guardar y desencriptarla al cargar para edición (si se muestra).
    *   Modificar la vista `EnterBillingView` para desencriptar la contraseña antes de pasarla al script `munibot.py`.

4.  **Implementación de Historial de Ejecuciones:**
    *   Crear un nuevo modelo (`ExecutionHistory`) para registrar cada intento de ejecución del script `munibot.py`. Este modelo incluirá campos como el usuario, la fecha/hora de ejecución, el monto imponible, el estado (éxito/fallo), y posiblemente la salida o mensajes de error del script.
    *   Modificar la vista `EnterBillingView` para crear un registro en `ExecutionHistory` después de cada intento de ejecución del script, guardando los detalles relevantes.
    *   Crear una nueva vista y URL (`/history/`) para mostrar una lista del historial de ejecuciones del usuario autenticado.
    *   Crear una plantilla HTML (`history.html`) para mostrar el historial en un formato legible (por ejemplo, una tabla).

5.  **Adición de Navegación (Menú):**
    *   Modificar la plantilla base (`base.html`) para incluir una barra de navegación responsiva utilizando componentes de Bootstrap (Navbar).
    *   El menú mostrará enlaces condicionalmente:
        *   Usuarios autenticados: Enlaces a "Inicio/Dashboard", "Perfil", "Ingresar Facturación", "Historial", "Cerrar Sesión".
        *   Usuarios no autenticados: Enlaces a "Registrarse", "Iniciar Sesión".

6.  **Creación de Página de Inicio/Dashboard (Post-Login):**
    *   Crear una vista y URL (`/dashboard/` o `home/`) que sirva como página de aterrizaje después de que el usuario inicie sesión (si ya tiene las credenciales de la municipalidad guardadas).
    *   Esta página podría mostrar un saludo, un resumen rápido (ej. último monto ingresado, enlace rápido a ingresar facturación o historial).
    *   Crear una plantilla HTML (`dashboard.html`) para esta página.
    *   Ajustar `LOGIN_REDIRECT_URL` en `settings.py` para apuntar a esta nueva página de inicio/dashboard.

7.  **Mejora de la Apariencia Profesional (Estilización Avanzada):**
    *   Revisar todas las plantillas HTML y aplicar clases de Bootstrap de manera más extensiva y consistente para lograr un diseño moderno y profesional.
    *   Considerar el uso de componentes de Bootstrap como tarjetas (cards), tablas estilizadas, alertas mejoradas, etc.
    *   Asegurar la responsividad en diferentes tamaños de pantalla.
    *   Agregar un favicon al proyecto para que se muestre en la pestaña del navegador.

8.  **Validación de Formularios y Manejo de Errores Mejorado:**
    *   Asegurar que todos los formularios (`UserCreationForm`, `MunicipalCredentialsForm`, y el formulario de monto en `enter_billing.html`) tengan validación adecuada tanto en el frontend (HTML5) como en el backend (Django forms).
    *   Presentar los errores de formulario de manera clara y amigable para el usuario utilizando los estilos de Bootstrap para validación.

9.  **Adaptación Final de `munibot.py` (Consideraciones):**
    *   Aunque ya acepta argumentos, considerar si la salida del script necesita ser estructurada de alguna manera para ser fácilmente parseada por la vista de Django y guardada en el historial.

**Diagrama del Flujo de la Aplicación (Actualizado y Ampliado):**

```mermaid
graph TD
    A[Usuario] --> B(Accede a la App Django)
    B --> C{¿Autenticado?}
    C -- No --> D(Página de Login)
    C -- Sí --> E{¿Credenciales Muni Guardadas?}
    D --> F(Página de Registro)
    F --> D
    D --> G(Autenticación)
    G --> E
    E -- No --> H(Página Ingreso Credenciales Muni)
    E -- Sí --> I(Dashboard/Inicio)
    H --> J(Guarda Credenciales Muni)
    J --> I
    I --> K(Navegación)
    K --> L(Página Ingreso Monto)
    K --> M(Página Perfil)
    K --> N(Página Historial)
    L --> O(Ingresa Monto Imponible)
    O --> P(Vista Django: Procesar Monto)
    P --> Q(Recupera y Desencripta Credenciales Muni)
    Q --> R(Ejecuta munibot.py con subprocess)
    R --> S(munibot.py)
    S --> T(Resultado/Estado)
    T --> U(Guarda en Historial)
    U --> V(Muestra Mensaje al Usuario)
    V --> L
    M --> W(Edita Credenciales Muni)
    W --> J
    N --> X(Muestra Historial)