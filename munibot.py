from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
import time
import sys

# Función principal que encapsula la lógica del bot
def run_munibot(municipal_username, municipal_password, monto, driver_path):
    """
    Automatiza el proceso de declaración jurada mensual en el sistema municipal.

    Args:
        municipal_username (str): Nombre de usuario para el sistema municipal.
        municipal_password (str): Contraseña para el sistema municipal.
        monto (str): Monto imponible a declarar.
        driver_path (str): Ruta al ejecutable del Edge WebDriver.

    Returns:
        tuple: (status, output, error)
               status (str): 'Success' o 'Failed'.
               output (str): Mensajes de éxito o información.
               error (str): Mensajes de error si la ejecución falla.
    """
    output_messages = []
    error_messages = []
    status = 'Failed'
    driver = None

    try:
        service = Service(driver_path)
        driver = webdriver.Edge(service=service)
        wait = WebDriverWait(driver, 10)

        driver.get("https://sistema.posadas.gov.ar/mp_sistemas/autogestion/login")

        input_usuario = wait.until(
            EC.presence_of_element_located((By.ID, "username"))
        )
        input_usuario.send_keys(municipal_username)

        input_contraseña = driver.find_element(By.ID, "password")
        input_contraseña.send_keys(municipal_password)

        login_btn = driver.find_element(
            By.XPATH, '//*[@id="wrapper"]/div/div/div[1]/form/div[3]/button'
        )
        login_btn.click()
        output_messages.append("Login hecho. Esperando redirección...")

        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        driver.get("https://sistema.posadas.gov.ar/mp_sistemas/autogestion/relacionesPropias")
        output_messages.append("Entramos a relacionesPropias")

        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        driver.get("https://sistema.posadas.gov.ar/mp_sistemas/autogestion/seccion/4/show")
        output_messages.append("Entramos a sección 4 (declaración jurada mensual)")

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

        wait.until(lambda d: len(selector.find_elements(By.TAG_NAME, "option")) > 1)

        select = Select(selector)
        select.select_by_index(1)
        output_messages.append("Seleccionada opción: Declaración Jurada Mensual")

        ventana_original = driver.current_window_handle
        wait.until(lambda d: len(d.window_handles) > 1)

        ventanas = driver.window_handles
        for ventana in ventanas:
            if ventana != ventana_original:
                driver.switch_to.window(ventana)
                break
        output_messages.append("Cambiamos a la ventana nueva")

        # Paso 5: Ingresar el monto imponible
        wait.until(EC.presence_of_element_located((By.ID, "monto_imponible"))).send_keys(monto)
        output_messages.append(f"Escrito el monto: {monto}")

        # Paso 6: Hacer clic en "Agregar"
        driver.find_element(By.ID, "addRow").click()
        output_messages.append("Clic en Agregar")

        # Paso 7: Hacer clic en "Presentar declaración jurada"
        wait.until(EC.element_to_be_clickable((By.ID, "send"))).click()
        output_messages.append("Declaración presentada con éxito.")
        
        status = 'Success'

    except Exception as e:
        error_messages.append(f"Error en munibot: {e}")
    finally:
        if driver:
            driver.quit()
        return status, "\n".join(output_messages), "\n".join(error_messages)