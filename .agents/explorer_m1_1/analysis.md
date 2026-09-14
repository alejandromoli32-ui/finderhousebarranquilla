# Análisis Técnico y Estrategia de Implementación: Extractor Metrocuadrado
**Módulo Objetivo**: `data_pipeline/extractors/metrocuadrado.py`  
**Agente**: `explorer_m1_1` (Milestone 1 - Extracción y Normalización)  
**Fecha**: 2026-09-13  
**Target**: Inmuebles en Arriendo en Barranquilla Norte (Canon + Administración <= $2.500.000 COP)

---

## 1. Resumen Ejecutivo y Factibilidad Técnica

Metrocuadrado (`metrocuadrado.com`) representa la **fuente primaria de mayor calidad y densidad** para arriendos en Barranquilla. A diferencia de portales que enmascaran u ocultan datos de contacto, Metrocuadrado expone de forma directa y abierta:
- **Canon mensual** y **cuota de administración** desglosados en valores numéricos limpios.
- **Teléfonos celulares directos y números de WhatsApp** (con prefijo internacional `57`) en el 100% de los anuncios validados.
- **Nombres de agencias o asesores comerciales directos**.
- **Galerías fotográficas completas** en alta resolución (`multimedia.metrocuadrado.com`).
- **Especificaciones físicas completas**: Área construida/privada, habitaciones, baños, parqueaderos y estrato socioeconómico.

### Resultados de la Prueba Empírica en Vivo
- **Ruta de acceso probada**: Peticiones directas al endpoint de React Server Components (RSC) Next.js App Router (`RSC: 1`).
- **Barrios explorados**: 20 slugs canónicos del sector Norte y Noroccidente de Barranquilla (Miramar, Villa Carolina, Villa Country, Alto Prado, Villa Santos, Riomar, El Golf, Ciudad Mallorquín, Altos de Riomar, Buenavista, Paraíso, Bellavista, El Prado, El Limoncito, El Tabor, Los Alpes, Andalucía, San Vicente, La Campiña, La Cumbre).
- **Inmuebles brutos recuperados**: **873 inmuebles**.
- **Inmuebles calificados únicos (Canon + Administración <= $2.500.000 COP)**: **224 propiedades**.
- **Disponibilidad de WhatsApp verificado**: **100% (224/224)**.
- **Disponibilidad de teléfono directo**: **100% (224/224)**.
- **Disponibilidad de galería de fotos**: **100% (224/224)**.
- **Tasa de error HTTP**: **0%** (100% respuestas HTTP 200 OK bajo timeout de 12s).

---

## 2. Arquitectura de Conexión y Protocolo de Extracción

### 2.1 Petición Directa Next.js RSC Stream (Header `RSC: 1`)
Metrocuadrado utiliza **Next.js App Router**. Al enviar las cabeceras de cliente RSC nativas, el servidor Next.js no genera el envoltorio HTML tradicional, sino que transmite directamente el flujo RSC en formato `text/x-component`:

```python
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept": "text/x-component",
    "RSC": "1",
}
```

#### Ventajas frente al scraping tradicional de HTML:
1. **Reducción masiva de payload**: El flujo RSC pesa ~240 KB frente a páginas HTML completas con scripts innecesarios.
2. **Sin parsers pesados**: No requiere Beautiful Soup, Selenium, Playwright ni Chromium headless.
3. **Estructura JSON directa**: Contiene un bloque serializado `initialResults` con hasta 65 objetos estructurados por respuesta.

### 2.2 Estrategia de URLs: Barrido Multi-Slug vs Búsqueda Global
La búsqueda global `/apartamento-casa/arriendo/barranquilla/` retorna únicamente los primeros 50 inmuebles generales de toda la ciudad, mezclando el sur, centro y anuncios patrocinados irrelevantes.

La estrategia óptima validada consiste en un **barrido sistemático por slugs canónicos de barrios del Norte/Noroccidente**:
`URL = f"https://www.metrocuadrado.com/apartamento-casa/arriendo/barranquilla/{slug}/"`

#### Catálogo de 20 Slugs Prioritarios:
| Slug de Consulta | Barrio Canónico | Zona Asignada | Rendimiento Típico (<= $2.5M) |
| :--- | :--- | :--- | :--- |
| `ciudad-mallorquin` | Ciudad Mallorquín | Noroccidente | ~44 inmuebles |
| `miramar` | Miramar | Noroccidente | ~30 inmuebles |
| `villa-carolina` | Villa Carolina | Norte | ~26 inmuebles |
| `paraiso` | Paraíso | Norte | ~20 inmuebles |
| `la-cumbre` | La Cumbre | Noroccidente | ~16 inmuebles |
| `san-vicente` | San Vicente | Norte | ~14 inmuebles |
| `tabor` | El Tabor | Noroccidente | ~14 inmuebles |
| `andalucia` | Andalucía | Noroccidente | ~12 inmuebles |
| `villa-country` | Villa Country | Norte | ~11 inmuebles |
| `altos-de-riomar` | Altos de Riomar | Noroccidente | ~9 inmuebles |
| `los-alpes` | Los Alpes | Noroccidente | ~9 inmuebles |
| `alto-prado` | Alto Prado | Norte | ~6 inmuebles |
| `villa-santos` | Villa Santos | Noroccidente | ~5 inmuebles |
| `la-campina` | La Campiña | Noroccidente | ~5 inmuebles |
| `el-prado` | El Prado | Norte | ~4 inmuebles |
| `riomar` | Riomar | Noroccidente | ~3 inmuebles |
| `bellavista` | Bellavista | Norte | ~3 inmuebles |
| `el-golf` | El Golf | Norte | ~2 inmuebles |
| `el-limoncito` | El Limoncito | Norte | ~1 inmueble |
| `buenavista` | Buenavista | Noroccidente | Oferta alta (> $2.5M) |

---

## 3. Mecánica de Decodificación y Extracción del Payload RSC

### 3.1 Localización de `initialResults`
Dentro de la respuesta de texto RSC (`text/x-component`), el objeto de resultados comienza con la subcadena `"initialResults":{`.

```python
def extract_results_from_rsc(rsc_text: str) -> list[dict]:
    """
    Localiza y deserializa la lista de inmuebles del bloque initialResults en el flujo RSC.
    Maneja balanceo de llaves JSON determinístico.
    """
    start_pos = rsc_text.find('"initialResults":{')
    if start_pos == -1:
        # Fallback alternativo: búsqueda de direct array "results":[
        res_pos = rsc_text.find('"results":[')
        if res_pos == -1:
            return []
        arr_start = res_pos + len('"results":')
        cnt = 0
        for i in range(arr_start, len(rsc_text)):
            if rsc_text[i] == '[': cnt += 1
            elif rsc_text[i] == ']':
                cnt -= 1
                if cnt == 0:
                    try:
                        return json.loads(rsc_text[arr_start:i+1])
                    except Exception:
                        return []
        return []

    obj_start = start_pos + len('"initialResults":')
    cnt = 0
    for i in range(obj_start, len(rsc_text)):
        if rsc_text[i] == '{': cnt += 1
        elif rsc_text[i] == '}':
            cnt -= 1
            if cnt == 0:
                try:
                    data = json.loads(rsc_text[obj_start:i+1])
                    return data.get("results", [])
                except Exception:
                    return []
    return []
```

### 3.2 Doble Capa de Resiliencia: Fallback HTML
Si un intermediario de red o CDN elimina las cabeceras `RSC: 1` y retorna un documento HTML estándar, el extractor implementa el fallback comprobado en `survey_portals.md`:
```python
def extract_results_from_html(html: str) -> list[dict]:
    """Fallback si el servidor retorna HTML en vez de text/x-component."""
    matches = re.findall(r'self\.__next_f\.push\(\[1,\s*"(.*?)"\]\)', html)
    combined = ""
    for m in matches:
        try:
            combined += json.loads(f'"{m}"')
        except Exception:
            combined += m
    return extract_results_from_rsc(combined)
```

---

## 4. Matriz de Mapeo de Campos al Esquema Canónico (`PROJECT.md`)

Cada registro generado debe satisfacer rigurosamente el esquema unificado de `PROJECT.md`:

| Campo Esquema | Tipo | Origen Metrocuadrado (`itm`) | Regla de Transformación / Normalización |
| :--- | :--- | :--- | :--- |
| `id` | `string` | `itm["midinmueble"]` | Prefijo `"MQ-" + str(midinmueble)` (ej. `"MQ-10557-M6998101"`). Unicidad garantizada. |
| `portal` | `string` | Constante | `"Metrocuadrado"` |
| `title` | `string` | `itm.get("title")` | Si viene vacío: `f"{property_type} en Arriendo en {neighborhood}, Barranquilla"`. |
| `property_type`| `string` | `itm.get("mtipoinmueble", {}).get("nombre")` | Si contiene `"casa"` -> `"Casa"`; de lo contrario `"Apartamento"`. |
| `canon` | `number (int)` | `itm.get("mvalorarriendo")` | Entero en COP. `int(round(float(val)))`. |
| `admin_fee` | `number (int)` | `itm.get("data", {}).get("mvaloradministracion")` | Si existe y es numérico: `int(round(float(val)))`; si es `None` o `"0"` -> `0`. |
| `total_price` | `number (int)` | Calculado | `canon + admin_fee`. **Filtro estricto**: Si `total_price <= 0` o `total_price > 2500000`, el inmueble es descartado. |
| `neighborhood`| `string` | `itm.get("mnombrecomunbarrio")` o `itm.get("mbarrio")` | Normalizado con limpiador de ruidos (remueve "Noroccidente", "Zona Urbana", "Barranquilla"). |
| `zone` | `string` | `itm.get("mzona", {}).get("nombre")` | `"Noroccidente"` o `"Norte"` según correspondencia geográfica del barrio. |
| `address` | `string` | `itm.get("mnombreproyecto")` | Si no existe nombre de edificio/conjunto, formatear: `f"{neighborhood}, Barranquilla"`. |
| `area_m2` | `number (float)`| `itm.get("marea")` o `itm.get("mareac")` | Float en m². Default `0.0`. |
| `bedrooms` | `number (int)` | `itm.get("mnrocuartos")` | Parseo entero. Default `1` (ej. apartaestudios). |
| `bathrooms` | `number (int)` | `itm.get("mnrobanos")` | Parseo entero. Default `1`. |
| `parking` | `number (int)` | `itm.get("mnrogarajes")` | Parseo entero. Si ausente o no numérico -> `0`. |
| `stratum` | `number (int)` | `itm.get("estrato")` | Entero entre 1 y 6. Default `4` en caso de null. |
| `images` | `array[string]`| `imageLink` + `mgaleriainmueble` | URL principal reemplazando `_p.jpg` por `.jpg` (alta resolución) + hasta 10 fotos de galería en `https://multimedia.metrocuadrado.com/{mid}/{photo_id}.jpg`. |
| `url` | `string` | `itm.get("link")` o `data.murldetalle` | URL completa: `f"https://www.metrocuadrado.com{link}"`. |
| `contact.phone`| `string` | `itm.get("contactPhone")` | Teléfono sin caracteres especiales. |
| `contact.whatsapp`| `string` | `itm.get("whatsapp")` o `contactPhone` | Formato internacional: Si inicia con `3` y tiene 10 dígitos, anteponer `57` -> `"573007771690"`. |
| `contact.agency`| `string` | `data.mnombrevisitor` o `OwnerType` | Nombre de inmobiliaria o tipo de oferente. |
| `contact.agent_name`| `string`| `data.mnombrevisitor` | Nombre del asesor si está disponible; default `"Asesor Comercial"`. |
| `description` | `string` | `itm.get("comment")` | Texto descriptivo completo del inmueble. |
| `verified` | `boolean` | Empírico | `True` (datos verificados por contacto activo). |

---

## 5. Resiliencia a Errores, Concurrencia y Fallback Caching

### 5.1 Gestión de Timeouts y Reintentos
- **Timeout HTTP**: 15 segundos por petición.
- **Política de Reintentos**: Hasta 3 intentos por barrio con retroceso exponencial (`1s`, `2s`, `4s`) ante errores `HTTP 5xx`, `429 Too Many Requests` o `URLError/Timeout`.
- **Cortesía de Petición**: Pausa de `0.25s` a `0.4s` entre slugs de barrios para evitar saturar el WAF o provocar rate-limiting.

### 5.2 Estrategia de Caché Local Offline (Fallback Caching)
Para cumplir con el criterio de integridad de `PROJECT.md` y permitir que el sistema funcione en entornos sin conexión o cuando el portal presente caídas temporales:
1. **Archivo de Caché**: `data_pipeline/cache/metrocuadrado_cache.json` (y `data/fallback/metrocuadrado_fallback.json`).
2. **Actualización Atómica**: Cada extracción exitosa escribe una copia temporal y la renombra atómicamente (`os.replace`) con timestamp ISO 8601.
3. **Mecanismo de Rescate**: Si el barrido HTTP falla totalmente (por ejemplo, desconexión de red o bloqueo de IP) o retorna 0 inmuebles, el extractor:
   - Emite un log de advertencia claro (`logger.warning("Fallo de red en Metrocuadrado. Activando fallback dataset...")`).
   - Carga el archivo de respaldo validado (que contiene los 224 inmuebles reales extraídos).
   - Retorna los datos con el indicador `is_fallback=True`.

---

## 6. Especificación de Diseño del Módulo `metrocuadrado.py`

El worker de implementación deberá estructurar `data_pipeline/extractors/metrocuadrado.py` con las siguientes clases y funciones:

```python
"""
data_pipeline/extractors/metrocuadrado.py
Extractor especializado de arriendos en Barranquilla Norte desde Metrocuadrado.
"""

class MetrocuadradoExtractor:
    def __init__(self, cache_path: str = None, timeout: int = 15, max_retries: int = 3):
        self.cache_path = cache_path or "data/fallback/metrocuadrado_fallback.json"
        self.timeout = timeout
        self.max_retries = max_retries
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Accept": "text/x-component",
            "RSC": "1",
        }

    def fetch_neighborhood_stream(self, slug: str) -> str:
        """Realiza petición HTTP con cabecera RSC: 1 y reintentos exponenciales."""
        ...

    def parse_rsc_stream(self, raw_stream: str) -> list[dict]:
        """Decodifica el flujo RSC y extrae el arreglo initialResults.results."""
        ...

    def normalize_property(self, raw_item: dict, default_barrio: str, default_zone: str) -> dict | None:
        """Mapea un inmueble crudo al esquema canónico verificando total_price <= 2.500.000 COP."""
        ...

    def extract_all(self, use_cache_on_failure: bool = True) -> list[dict]:
        """
        Ejecuta el barrido por los 20 slugs de Barranquilla Norte,
        deduplica internamente por ID 'MQ-...', guarda en caché y retorna los inmuebles.
        """
        ...
```

---

## 7. Plan de Verificación y Criterios de Aceptación del Módulo

Para dar por aprobada la implementación en M1:
1. **Prueba Unitaria de Mapeo (`tests/test_metrocuadrado.py`)**:
   - `test_map_valid_item`: Verifica que un item crudo se transforme fielmente en el diccionario canónico.
   - `test_strict_price_filter`: Verifica que un inmueble con Canon $2.400.000 + Admin $200.000 ($2.600.000) sea rechazado (`None`).
   - `test_exact_price_boundary`: Verifica que un inmueble con Total exacto $2.500.000 sea aceptado.
   - `test_whatsapp_normalization`: Verifica que `"3007771690"` se convierta en `"573007771690"`.
   - `test_rsc_parser_resilience`: Verifica que el decodificador de chunks RSC extraiga arrays válidos sin lanzar excepciones.
2. **Prueba de Extracción en Vivo**:
   - Ejecución del barrido produciendo >= 100 inmuebles calificados reales en Barranquilla Norte.
3. **Prueba de Fallback**:
   - Desconectar o simular fallo HTTP (URL inválida o mock de excepción) y comprobar que retorna exitosamente el dataset del caché local.
