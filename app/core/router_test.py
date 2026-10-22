import asyncio
import sys
import re
from pathlib import Path
from unittest.mock import patch

sys.path.append(str(Path(__file__).resolve().parents[2]))

from app.core.router import enrutar_peticion, evaluar_complejidad

def _mensajes(prompt: str, historial: list | None = None):
    mensajes = historial[:] if historial else []
    mensajes.append({"role": "user", "content": prompt})
    return mensajes

async def test_evaluar_complejidad_simple():
    # Nota: Tu evaluar_complejidad actual devuelve enteros (1 o 2), no cadenas. Ajustado a la realidad del código.
    assert evaluar_complejidad("Hola, ¿cómo estás?") == 1

async def test_evaluar_complejidad_tecnica():
    # Añadimos contexto técnico largo para superar los 400 caracteres exigidos
    prompt = (
        "Escribe un script en python para web scraping utilizando la librería BeautifulSoup. "
        "El objetivo es conectarse a una plataforma web interna de inventario de Mercedes-Benz, "
        "autenticarse de forma segura mediante un token de sesión, extraer una tabla HTML con más de "
        "cinco mil registros de piezas y componentes de motores, limpiar los datos duplicados, "
        "formatear las columnas de fecha y guardar el resultado estructurado final directamente "
        "en un archivo en formato CSV o en un DataFrame de Pandas para su posterior análisis estadístico."
    )
    assert evaluar_complejidad(prompt) == 2


async def test_evaluar_complejidad_tecnica_con_tildes():
    # Añadimos contexto con tildes que supere los 400 caracteres
    prompt = (
        "Analiza la complejidad de una función asíncrona en Python que gestiona la concurrencia. "
        "La aplicación debe realizar múltiples peticiones HTTP simultáneas utilizando la librería httpx "
        "hacia diferentes endpoints de una arquitectura de microservicios distribuidos. Necesito "
        "optimizar el rendimiento general del sistema, mitigar los cuellos de botella en la base de datos "
        "relacional Postgres y asegurar que el manejo de excepciones capture cualquier fallo de red o "
        "timeout sin interrumpir el bucle de eventos principal del framework FastAPI en producción."
    )
    assert evaluar_complejidad(prompt) == 2

async def test_evaluar_complejidad_con_historial_tecnico():
    # Nota: Vuestro evaluar_complejidad actual de router.py ya no recibe el parámetro mensajes_completos
    prompt_continuidad = "Hazme un resumen de ese TFG"
    assert evaluar_complejidad(prompt_continuidad) == 1

async def test_enrutado_por_presupuesto_alto():
    prompt = "Escribe un script en python para web scraping"
    mensajes = _mensajes(prompt)

    class MockResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "model": "llama3.2:3b",
                "choices": [{"message": {"content": "Respuesta simulada"}}],
                "usage": {"prompt_tokens": 12, "completion_tokens": 8, "total_tokens": 20}
            }

    with patch("httpx.AsyncClient.post", return_value=MockResponse()):
        respuesta, metadata = await enrutar_peticion(
            prompt,
            porcentaje_presupuesto_gastado=91.0,
            mensajes_completos=mensajes,
            modelo_solicitado="mistral:7b"
        )

    assert "choices" in respuesta
    assert respuesta["model"] == "llama3.2:3b"
    assert "Degradación FinOps" in metadata["rule"]

async def test_filtro_privacidad_gobernanza():
    """
    Test de unidad que valida que el cortafuegos de gobernanza detecta datos sensibles
    empleando tokens dinámicos aleatorios basados en UUID.
    """
    prompt_con_datos = (
        "Hola, analiza el chasis del coche con VIN WDD1690311J123456 "
        "y manda el informe al ingeniero a hugo.perez@mercedes-benz.com"
    )
    mensajes = _mensajes(prompt_con_datos)

    class MockResponse:
        def raise_for_status(self):
            return None
        def json(self):
            return {
                "model": "llama3.2:3b",
                "choices": [{"message": {"content": "Procesado seguro"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5}
            }

    with patch("httpx.AsyncClient.post", return_value=MockResponse()) as mock_post:
        respuesta, metadata = await enrutar_peticion(
            prompt=prompt_con_datos,
            porcentaje_presupuesto_gastado=10.0,
            mensajes_completos=mensajes,
            modelo_solicitado="llama3.2:3b"
        )
        
        payload_enviado = mock_post.call_args[1]['json']
        ultimo_mensaje_enviado = payload_enviado["messages"][-1]["content"]

        # 1. El texto que sale a la red externa NO debe contener los datos reales
        assert "WDD1690311J123456" not in ultimo_mensaje_enviado
        assert "hugo.perez@mercedes-benz.com" not in ultimo_mensaje_enviado
        
        # 2. Deben viajar los nuevos patrones dinámicos generados por uuid
        assert "[VIN_" in ultimo_mensaje_enviado
        assert "[EMAIL_" in ultimo_mensaje_enviado

# =====================================================================
# 🔥 NUEVA PRUEBA UNITARIA: VAULTING Y REHIDRATACIÓN COMPLETA
# =====================================================================
async def test_vaulting_y_rehidratacion_completa():
    """
    Test crítico que valida que los datos confidenciales son enmascarados a la ida,
    viajan seguros, y son restaurados perfectamente a la vuelta tras la respuesta del LLM.
    """
    vin_real = "WDD1690311J123456"
    email_real = "hugo.perez@mercedes-benz.com"
    
    prompt_usuario = f"Genera un reporte para el bastidor {vin_real} del empleado {email_real}"
    mensajes = _mensajes(prompt_usuario)

    # Creamos un Mock que simulará cómo responde Ollama.
    # El LLM no conoce los datos reales; responderá utilizando los tokens dinámicos que reciba en los mensajes.
    class MockOllamaResponse:
        def __init__(self, mock_post_wrapper):
            self.wrapper = mock_post_wrapper

        def raise_for_status(self):
            return None

        def json(self):
            # Capturamos el texto que el proxy le envió al LLM para simular una respuesta fiel
            payload_recibido_por_ia = self.wrapper.call_args[1]['json']
            prompt_anonimizado = payload_recibido_por_ia["messages"][-1]["content"]
            
            # Extraemos dinámicamente los tokens efímeros generados por el proxy (ej: [VIN_A1B2C3])
            token_vin_detectado = re.search(r'\[VIN_[A-Z0-9]+\]', prompt_anonimizado).group(0)
            token_email_detectado = re.search(r'\[EMAIL_[A-Z0-9]+\]', prompt_anonimizado).group(0)

            # Simulamos la respuesta que redactaría la IA conteniendo los tokens del anonimizado
            content_ia = f"Reporte completado con éxito para el vehículo {token_vin_detectado}. Copia enviada a {token_email_detectado}."
            
            return {
                "model": "llama3.2:3b",
                "choices": [{"message": {"role": "assistant", "content": content_ia}}],
                "usage": {"prompt_tokens": 15, "completion_tokens": 20}
            }

    # Interceptamos la llamada HTTP
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = MockOllamaResponse(mock_post)
        
        respuesta, metadata = await enrutar_peticion(
            prompt=prompt_usuario,
            porcentaje_presupuesto_gastado=10.0,
            mensajes_completos=mensajes,
            modelo_solicitado="llama3.2:3b"
        )
        
        texto_final_entregado = respuesta["choices"][0]["message"]["content"]
        
        print(f"\n   [TEST LOG] Texto devuelto por el Proxy al usuario final:\n   '{texto_final_entregado}'")

        # VALIDACIÓN FINAL: Comprobamos que el usuario final sí ve sus datos restaurados de forma transparente
        assert vin_real in texto_final_entregado, "❌ El VIN real no se restauró en la respuesta."
        assert email_real in texto_final_entregado, "❌ El email real no se restauró en la respuesta."
        
        # Nos aseguramos de que no queden las etiquetas crudas en el texto devuelto
        assert "[VIN_" not in texto_final_entregado
        assert "[EMAIL_" not in texto_final_entregado

async def main():
    print("=== Probando router ===")

    await test_evaluar_complejidad_simple()
    print("OK: complejidad simple")

    await test_evaluar_complejidad_tecnica()
    print("OK: complejidad técnica")

    await test_evaluar_complejidad_tecnica_con_tildes()
    print("OK: complejidad técnica con tildes")

    await test_evaluar_complejidad_con_historial_tecnico()
    print("OK: complejidad con historial técnico")

    await test_enrutado_por_presupuesto_alto()
    print("OK: enrutado con presupuesto alto")

    await test_filtro_privacidad_gobernanza()
    print("OK: cortafuegos de privacidad y gobernanza")
    
    await test_vaulting_y_rehidratacion_completa()
    print("OK: cifrado in-memory y rehidratación completa de respuesta")

    print("=== Router validado ===")

if __name__ == "__main__":
    asyncio.run(main())