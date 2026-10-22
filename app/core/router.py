import asyncio
import os
import logging
import re
import unicodedata
import time
import uuid
import httpx

# =====================================================================
# SCALABLE MODEL CATALOG
# =====================================================================
REGISTRO_MODELOS = {
    "llama3.2:3b": {
        "proveedor": "provider-a",
        "url": os.getenv("AI_FINOPS_PROVIDER_A_URL", "http://localhost:11434/v1/chat/completions"),
        "nivel_exigencia": 1,      # Level 1: Standard or incomplete requests
        "precio_in": 0.06,
        "precio_out": 0.06,
        "factor_eficiencia": 0.82
    },
    "mistral:7b": {
        "proveedor": "provider-b",
        "url": os.getenv("AI_FINOPS_PROVIDER_B_URL", "http://localhost:11435/v1/chat/completions"),
        "nivel_exigencia": 2,      # Nivel 2: Para peticiones estrictamente complejas y largas
        "precio_in": 0.24,
        "precio_out": 0.24,
        "factor_eficiencia": 1.00
    }
}

logger = logging.getLogger(__name__)

# =====================================================================
# SEMANTIC DICTIONARY
# =====================================================================
PALABRAS_COMPLEJAS = {
    # 1. Programming Languages and Technologies
    "python", "javascript", "java", "c++", "c#", "sql", "html", "css", "php",
    "ruby", "swift", "golang", "rust", "bash", "shell", "powershell", "typescript",
    "docker", "kubernetes", "git", "linux", "aws", "azure", "gcp", "terraform",
    "kotlin", "scala", "dart", "perl", "haskell", "lua", "matlab", "r",

    # 2. Development and Architecture Concepts
    "api", "rest", "graphql", "json", "xml", "yaml", "regex", "debug", "refactoriza",
    "compila", "despliegue", "frontend", "backend", "query", "consulta", "algoritmo",
    "bucle", "funcion", "clase", "objeto", "asincrono", "framework", "react",
    "angular", "vue", "django", "flask", "fastapi", "node", "express", "spring",
    "arquitectura", "escalabilidad", "rendimiento", "microservicios", "patrón",
    "script", "código", "programar", "variable", "repositorio", "commit", "merge",
    "pipeline", "ci/cd", "testing", "unitario", "mock", "middleware", "endpoint",

    # 3. Data, Databases, and Formats
    "csv", "excel", "pandas", "dataframe", "scraping", "parsear", "extraer",
    "transformar", "etl", "dashboard", "grafica", "visualizacion", "dataset",
    "mysql", "postgres", "mongodb", "nosql", "redis", "elasticsearch", "supabase",
    "oracle", "sqlite", "cassandra", "hadoop", "spark", "kafka", "parquet",

    # 4. Data Science, AI, and Machine Learning
    "machine", "learning", "ia", "deep", "redes", "neuronales", "nlp", "vision",
    "entrenamiento", "prediccion", "clustering", "regresion", "clasificacion",
    "tensor", "pytorch", "scikit", "llm", "prompt", "token", "embedding",

    # 5. Reasoning, Logic, and Mathematics
    "analiza", "evalua", "compara", "deduce", "justifica", "optimiza", "abstraccion",
    "inferencia", "estadistica", "probabilidad", "matematicas", "calculo", "ecuacion",
    "integral", "derivada", "matriz", "algebra", "fisica", "teoria", "teorema",
    "demuestra", "logica", "hipotesis", "complejidad", "heuristica", "trigonometria",
    "geometria", "aritmetica", "proporcion", "varianza", "distribucion",

    # 6. Professional, Legal, and Corporate Documentation
    "ensayo", "tesis", "informe", "contrato", "legal", "clausula", "patente",
    "cientifico", "paper", "metodologia", "bibliografia", "citacion", "apa",
    "normativa", "cumplimiento", "auditoria", "vulnerabilidad", "ciberseguridad",
    "gdpr", "criptografia", "encriptacion", "estrategico", "financiero", "balance"
}

def _normalizar_texto(texto: str) -> str:
    texto_normalizado = unicodedata.normalize("NFKD", texto)
    texto_sin_tildes = "".join(
        caracter for caracter in texto_normalizado if not unicodedata.combining(caracter)
    )
    return texto_sin_tildes.casefold()

def comprimir_prompt(texto: str) -> str:
    """
    Técnica FinOps: Prompt Stripping.
    Elimina espacios, tabulaciones y saltos de línea redundantes para reducir el coste de tokens de entrada.
    """
    if not texto:
        return ""
    # 1. Reemplazar múltiples saltos de línea o tabulaciones por un solo salto
    texto_limpio = re.sub(r'[\r\n\t]+', '\n', texto)
    # 2. Reemplazar múltiples espacios consecutivos por un solo espacio
    texto_limpio = re.sub(r'[ ]+', ' ', texto_limpio)
    # 3. Quitar espacios y saltos sobrantes al principio y al final
    return texto_limpio.strip()

def deshidratar_prompt(prompt: str) -> tuple[str, dict]:
    """
    Sustituye datos sensibles por tokens opacos aleatorios (UUIDs).
    Devuelve el prompt anonimizado y el mapa de rehidratación privada.
    """
    if not prompt:
        return "", {}
    
    mapa_rehidratacion = {}
    prompt_filtrado = prompt

    # 1. Regex para Correos Electrónicos
    regex_email = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    correos = re.findall(regex_email, prompt_filtrado)
    for correo in correos:
        token_falso = f"[EMAIL_{uuid.uuid4().hex[:6].upper()}]"
        mapa_rehidratacion[token_falso] = correo
        prompt_filtrado = prompt_filtrado.replace(correo, token_falso)

    # 2. Regex para IDs de Empleado (ej: c1234567)
    regex_empleado = r'\b[cmCM]\d{7}\b'
    empleados = re.findall(regex_empleado, prompt_filtrado)
    for emp in empleados:
        token_falso = f"[EMP_{uuid.uuid4().hex[:6].upper()}]"
        mapa_rehidratacion[token_falso] = emp
        prompt_filtrado = prompt_filtrado.replace(emp, token_falso)

    # 3. Regex para VINs de Mercedes-Benz (17 caracteres)
    regex_vin = r'\b[A-HJ-NPR-Z0-9]{17}\b'
    vins = re.findall(regex_vin, prompt_filtrado)
    for vin in vins:
        token_falso = f"[VIN_{uuid.uuid4().hex[:6].upper()}]"
        mapa_rehidratacion[token_falso] = vin
        prompt_filtrado = prompt_filtrado.replace(vin, token_falso)

    return prompt_filtrado, mapa_rehidratacion


def rehidratar_respuesta(texto_ia: str, mapa_rehidratacion: dict) -> str:
    """
    Restaura los datos sensibles reales en la respuesta final que lee el usuario.
    """
    if not texto_ia or not mapa_rehidratacion:
        return texto_ia
    
    texto_final = texto_ia
    # Recorremos el mapa privado y cambiamos los tokens falsos por el valor real
    for token_falso, valor_real in mapa_rehidratacion.items():
        texto_final = texto_final.replace(token_falso, valor_real)
        
    return texto_final

def evaluar_complejidad(prompt: str) -> int:
    """
    Asigna el Nivel de Exigencia:
    - Nivel 2 (Mistral): DEBE tener palabras clave Y más de 400 caracteres.
    - Nivel 1 (Llama): Cualquier otra cosa (falla en uno o ambos requisitos).
    """
    prompt_normalizado = _normalizar_texto(prompt)
    palabras_prompt_actual = set(re.findall(r'\b\w+\b', prompt_normalizado))

    tiene_palabras_complejas = bool(palabras_prompt_actual.intersection(PALABRAS_COMPLEJAS))
    es_largo = len(prompt_normalizado) > 400

    if tiene_palabras_complejas and es_largo:
        return 2  # Pasa al resto (Mistral)

    return 1  # Va a Llama

def _seleccionar_mejor_modelo(nivel_requerido: int, modelo_solicitado: str) -> tuple[str, str]:
    modelos_validos = {
        nombre: info for nombre, info in REGISTRO_MODELOS.items()
        if info["nivel_exigencia"] >= nivel_requerido
    }

    if not modelos_validos:
        modelo_ideal = max(REGISTRO_MODELOS.items(), key=lambda x: x[1]["nivel_exigencia"])[0]
    else:
        modelo_ideal = min(modelos_validos.items(), key=lambda x: x[1]["precio_in"] + x[1]["precio_out"])[0]

    if modelo_solicitado and modelo_solicitado in REGISTRO_MODELOS:
        return modelo_solicitado, "Explicit Choice Respected"

    return modelo_ideal, f"Automatic Routing (Level {nivel_requerido})"

async def enrutar_peticion(prompt: str, porcentaje_presupuesto_gastado: float, mensajes_completos: list, modelo_solicitado: str) -> tuple[dict, dict]:
    
    prompt_optimizado = comprimir_prompt(prompt)

    prompt_seguro, mapa_privado = deshidratar_prompt(prompt_optimizado)

    if mensajes_completos and mensajes_completos[-1]["role"] == "user":
        mensajes_completos[-1]["content"] = prompt_seguro
    
    nivel_requerido = evaluar_complejidad(prompt_seguro)
    modelo_elegido, regla_aplicada = _seleccionar_mejor_modelo(nivel_requerido, modelo_solicitado)

    if porcentaje_presupuesto_gastado >= 90.0:
        modelo_elegido = min(REGISTRO_MODELOS.items(), key=lambda x: x[1]["precio_in"] + x[1]["precio_out"])[0]
        regla_aplicada = "FinOps degradation (Budget >90%)"

    url_destino = REGISTRO_MODELOS[modelo_elegido]["url"]
    metadata = {"rule": regla_aplicada, "provider": REGISTRO_MODELOS[modelo_elegido]["proveedor"]}

    payload = {
        "model": modelo_elegido,
        "messages": mensajes_completos,
        "temperature": 0.7
    }

    try:
        async with httpx.AsyncClient() as client:
            t0_http = time.time()
            respuesta = await client.post(url_destino, json=payload, timeout=300.0)
            metadata["llm_latency_ms"] = (time.time() - t0_http) * 1000
            respuesta.raise_for_status()
            resp_json = respuesta.json()

            try:
                # Extraemos el texto que ha redactado la IA con los tokens ficticios
                texto_ia = resp_json["choices"][0]["message"]["content"]
                
                # Interceptamos y cambiamos los tokens efímeros por los datos reales del mapa privado
                texto_rehidratado = rehidratar_respuesta(texto_ia, mapa_privado)
                
                # Guardamos el texto real final en el JSON de respuesta para el usuario
                resp_json["choices"][0]["message"]["content"] = texto_rehidratado
            except (KeyError, IndexError):
                pass
            
            if isinstance(resp_json, dict) and "model" not in resp_json:
                resp_json["model"] = modelo_elegido
            return resp_json, metadata
        
    except httpx.HTTPStatusError as e:
        return {"error": "Internal AI provider error", "details": str(e)}, metadata
    except httpx.RequestError as e:
        return {"error": "Could not connect to the AI engine", "details": str(e)}, metadata