from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
import time
import sys

# Obtener usuario, contraseña y monto desde argumentos de línea de comandos
# sys.argv[0] es el nombre del script
# sys.argv[1] será el usuario de la municipalidad
# sys.argv[2] será la contraseña de la municipalidad
# sys.argv[3] será el monto imponible
if len(sys.argv) != 4:
    print("Uso: python munibot.py <usuario_municipalidad> <contraseña_municipalidad> <monto_imponible>")
    sys.exit(1)

municipal_username = sys.argv[1]
municipal_password = sys.argv[2]
monto = sys.argv[3]

service = Service("E:\\MunicipalidadBot\\driver\\msedgedriver.exe")
driver = webdriver.Edge(service=service)

wait = WebDriverWait(driver, 10)

driver.get("https://sistema.posadas.gov.ar/mp_sistemas/autogestion/login")

# Esperar que el input usuario esté presente
input_usuario = wait.until(
    EC.presence_of_element_located((By.ID, "username"))
)  # supongo que el id es usuario
input_usuario.send_keys(municipal_username)

input_contraseña = driver.find_element(
    By.ID, "password"
)  # supongo que el id es password
input_contraseña.send_keys(municipal_password)

# Hacer clic en login
login_btn = driver.find_element(
    By.XPATH, '//*[@id="wrapper"]/div/div/div[1]/form/div[3]/button'
)
login_btn.click()

print("Login hecho. Esperando redirección...")

# Paso 2: Ir a relaciones propias
wait.until(
    EC.presence_of_element_located((By.TAG_NAME, "body"))
)  # Asegura que la página cargó
driver.get("https://sistema.posadas.gov.ar/mp_sistemas/autogestion/relacionesPropias")
print("Entramos a relacionesPropias")

# Paso 3: Ir a sección de declaración jurada mensual
wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
driver.get("https://sistema.posadas.gov.ar/mp_sistemas/autogestion/seccion/4/show")
print("Entramos a sección 4 (declaración jurada mensual)")

# Esperamos a que el <select> esté presente
wait.until(
    EC.presence_of_element_located(
        (
            By.XPATH,
            '//*[@id="wrapper"]/div[2]/div/div/div[2]/table/tbody/tr[1]/td[6]/div/select',
        )
    )
)
selector = driver.find_element(
    By.XPATH,
    '//*[@id="wrapper"]/div[2]/div/div/div[2]/table/tbody/tr[1]/td[6]/div/select',
)

# Esperamos específicamente a que la opción 2 esté presente (opcional pero más robusto)
wait.until(lambda d: len(selector.find_elements(By.TAG_NAME, "option")) > 1)

# Ahora sí seleccionamos
select = Select(selector)
select.select_by_index(1)  # La segunda opción (índice 1)
print("Seleccionada opción: Declaración Jurada Mensual")

# Guardamos la ventana original
ventana_original = driver.current_window_handle

# Esperamos a que se abra una ventana nueva
wait.until(lambda d: len(d.window_handles) > 1)

# Cambiamos el foco a la ventana nueva
ventanas = driver.window_handles
for ventana in ventanas:
    if ventana != ventana_original:
        driver.switch_to.window(ventana)
        break

print("Cambiamos a la ventana nueva")


# Paso 5: Ingresar el monto imponible
wait.until(EC.presence_of_element_located((By.ID, "monto_imponible"))).send_keys(monto)
print(f"Escrito el monto: {monto}")

# Paso 6: Hacer clic en "Agregar"
driver.find_element(By.ID, "addRow").click()
print("Clic en Agregar")

# Paso 7: Hacer clic en "Presentar declaración jurada"
wait.until(EC.element_to_be_clickable((By.ID, "send"))).click()
print("Declaración presentada con éxito.")

# Paso: Ir a la página de boletas
driver.get("https://djm.posadas.gov.ar/index.php/boletas")
time.sleep(5)  # Espera que cargue

# Paso: Seleccionar "Pagos360" del menú desplegable
try:
    selector_pago = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located(
            (By.XPATH, '//*[@id="example"]/tbody/tr[1]/td[7]/select')
        )
    )
    selector_pago.click()
    time.sleep(1)

    opcion_pago360 = driver.find_element(
        By.XPATH, '//*[@id="example"]/tbody/tr[1]/td[7]/select/option[3]'
    )
    opcion_pago360.click()
    print("Pagos360 seleccionado. Esperando que se abra la nueva pestaña...")
except Exception as e:
    print("Error al seleccionar Pagos360:", e)

# Listo, a partir de acá el pago se hace manualmente por seguridad


# Acá se debería redirigir o cargar otra cosa. Pausa para inspeccionar
input("Presioná Enter para cerrar...")
driver.quit()
