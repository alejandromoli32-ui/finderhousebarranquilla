# Estudio Técnico y Mecánicas de Extracción Multi-Portal: Arriendos en Barranquilla (Norte / Noroccidente)
**Agente Explorador**: `explorer_survey_1`  
**Fecha de Inspección**: 2026-09-13  
**Presupuesto Máximo**: Canon + Administración <= $2.500.000 COP  
**Zona Objetivo**: Sector Norte y Noroccidente de Barranquilla (El Golf, Alto Prado, Riomar, Villa Santos, Villa Country, Miramar, Villa Carolina, Ciudad Mallorquín, Buenavista, Altos de Riomar, Granadillo, etc.)

---

## 1. Resumen Ejecutivo y Matriz de Portales

Se realizó un sondeo y pruebas empíricas de conexión, detección anti-bot, inspección de payloads y análisis de datos en vivo sobre los principales portales inmobiliarios de Colombia.

### Matriz Comparativa de Viabilidad Técnica

| Portal | Nivel de Viabilidad | Tipo de Renderizado / Acceso | Presencia Anti-Bot / WAF | Calidad de Datos (Precios, Admin, Teléfonos) | Recomendación Arquitectónica |
| :--- | :---: | :--- | :--- | :--- | :--- |
| **Metrocuadrado** (`metrocuadrado.com`) | **CRÍTICA / ÓPTIMA (10/10)** | Next.js App Router RSC (`self.__next_f`) embebido | WAF estándar permisivo con User-Agent de navegador | **Excepcional**: Incluye canon, valor de administración desglosado, celular de contacto, WhatsApp directo y teléfonos fijos en el 100% de los anuncios. Retorna 50-65 inmuebles por request de barrio. | **Fuente Primaria Indispensable**. Extracción directa de payload RSC streaming sin necesidad de ejecutar JavaScript. |
| **Finca Raíz** (`fincaraiz.com.co`) | **CRÍTICA / ÓPTIMA (9.5/10)** | Next.js Pages Router SSR (`fetchResult.searchFast`) + Schema.org JSON-LD | Cloudflare en borde (permite GET estándar con User-Agent) | **Muy Alta**: Gran volumen histórico, galería de fotos de alta resolución, desglose técnico (habitaciones, baños, garajes, m2 construidos y privados, estrato, año de construcción). | **Fuente Primaria Indispensable**. Extracción de JSON estructurado directamente de scripts de página (`searchFast.data`). |
| **Ciencuadras** (`ciencuadras.com`) | **MEDIA (6/10)** | Angular Universal SSR + Schema.org JSON-LD (`ItemList`) | Cloudflare estándar | **Aceptable**: Títulos, fotos, coordenadas y enlaces directos, pero mezcla ofertas de arriendo/venta en ciertos endpoints y oculta teléfono directo en la tarjeta de resultados. | **Fuente Secundaria / Enriquecimiento**. |
| **MercadoLibre Inmuebles** (`inmuebles.mercadolibre.com.co`) | **BAJA / ALTA FRICCIÓN (3/10)** | Akamai BotManager PoW JS Challenge (`snoopy` / `bot_challenge`) | Bloqueo activo / redirección a verificación de cuenta (`/gz/account-verification`) sin browser automatizado | Datos fragmentados y alta fricción técnica para scrapers HTTP ligeros. | **Desaconsejado para fase inicial**. Requeriría Playwright / Puppeteer pesado con overhead innecesario. |
| **Properati** (`properati.com.co`) | **NO VIABLE (1/10)** | Jetty Server | Retorna `HTTP 401 Unauthorized` de inmediato. | Inaccesible públicamente sin sesión o token privado. | **Descartado**. |

---

## 2. Radiografía Técnica Detallada de Portales Primarios

### 2.1 Metrocuadrado (`metrocuadrado.com`)

#### Arquitectura de Entrega
Metrocuadrado utiliza **Next.js App Router**. Al realizar una petición `HTTP GET`, el servidor envía un documento HTML que contiene la hidratación de componentes de servidor React Server Components (RSC) a través de llamadas de la forma:
```javascript
self.__next_f.push([1, "chunk_data..."]);
```

#### Localización del Payload de Datos
Dentro de los chunks de RSC, se encuentra una cadena JSON serializada con la clave `"results": [...]`.
Al decodificar los chunks, se obtiene un arreglo nativo de objetos con **65 inmuebles por página**.

#### Campos Clave Obtenidos Empíricamente (Verificados en vivo)
```json
{
  "midinmueble": "21602-M6953598",
  "title": "Apartamento en Arriendo, ALTO DE RIOMAR, Barranquilla",
  "mtipoinmueble": {"id": "1", "nombre": "Apartamento"},
  "mtiponegocio": "arriendo",
  "mvalorarriendo": 3500000,
  "marea": 84,
  "mnrocuartos": "2",
  "mnrobanos": "1",
  "mnrogarajes": "2",
  "mnombrecomunbarrio": "ALTO DE RIOMAR",
  "mzona": {"id": "59", "nombre": "Noroccidente"},
  "estrato": 4,
  "data": {
    "mvaloradministracion": "1000000",
    "mnombrevisitor": "DEISY NIÑO GOMEZ",
    "murldetalle": "/inmueble/arriendo-apartamento-barranquilla-abajo-2-habitaciones-1-banos-2-garajes/21602-M6953598"
  },
  "contactPhone": "3007771690",
  "whatsapp": "573007771690",
  "imageLink": "https://multimedia.metrocuadrado.com/21602-M6953598/21602-M6953598_1_p.jpg",
  "mgaleriainmueble": ["21602-M6953598_1", "21602-M6953598_2", "..."],
  "localizacion": {"lat": 10.9924659, "lon": -74.7843322}
}
```

#### URL Patterns y Consulta por Barrio
La estructura de URLs más eficiente y precisa en Metrocuadrado no es una búsqueda global con filtros de query string (que a menudo inyectan anuncios patrocinados irrelevantes de alto valor), sino la consulta directa por **slugs canónicos de barrio en el sector Norte/Noroccidente**:
- `https://www.metrocuadrado.com/apartamento-casa/arriendo/barranquilla/villa-santos/`
- `https://www.metrocuadrado.com/apartamento-casa/arriendo/barranquilla/alto-prado/`
- `https://www.metrocuadrado.com/apartamento-casa/arriendo/barranquilla/el-golf/`
- `https://www.metrocuadrado.com/apartamento-casa/arriendo/barranquilla/miramar/`
- `https://www.metrocuadrado.com/apartamento-casa/arriendo/barranquilla/villa-carolina/`
- `https://www.metrocuadrado.com/apartamento-casa/arriendo/barranquilla/riomar/`
- `https://www.metrocuadrado.com/apartamento-casa/arriendo/barranquilla/villa-country/`

#### Resultados de Prueba en Vivo (Solo inmuebles <= $2.500.000 COP)
- **Miramar**: 30 inmuebles viables <= $2.5M
- **Villa Carolina**: 26 inmuebles viables <= $2.5M
- **Villa Country**: 11 inmuebles viables <= $2.5M
- **Alto Prado**: 6 inmuebles viables <= $2.5M
- **Villa Santos**: 5 inmuebles viables <= $2.5M
- **Riomar**: 3 inmuebles viables <= $2.5M
- **El Golf**: 2 inmuebles viables <= $2.5M
*(Total en 1 sola pasada sobre estos 7 barrios: **83 inmuebles calificados** con teléfonos y WhatsApp reales).*

---

### 2.2 Finca Raíz (`fincaraiz.com.co`)

#### Arquitectura de Entrega
Finca Raíz utiliza **Next.js Pages Router** con pre-renderizado estático / server-side. En el HTML se incluye el tag `<script>` que contiene `pageProps`.

#### Localización del Payload de Datos
Dentro de `pageProps`, el objeto `fetchResult.searchFast` contiene:
- `data`: Lista de **21 inmuebles por página**.
- `paginatorInfo`: Total de registros en base de datos (e.g. 2,726 en Barranquilla), página actual, última página.
- En paralelo, en el bloque de cabecera `<script type="application/ld+json">`, se genera un `ItemList` bajo el estándar de Schema.org con el array de `RealEstateListing`.

#### Campos Clave Obtenidos Empíricamente
```json
{
  "id": 194249769,
  "title": "Apartamento en Arriendo en La campiña, Barranquilla",
  "price": {
    "amount": 2800000,
    "admin_included": 2800000,
    "hidePrice": false,
    "currency": {"id": 4, "name": "$"}
  },
  "commonExpenses": {
    "amount": 0,
    "hidePrice": false
  },
  "include_administration": true,
  "address": "Cra. 47 #85-53, Riomar, Barranquilla, Atlántico",
  "link": "/apartamento-en-arriendo-en-la-campiña-barranquilla/194249769",
  "images": [
    {"image": "https://cdn2.infocasas.com.uy/repo/img/6aa660388465a_infocdn__gr28643120260913012303jpeg.jpeg"}
  ],
  "owner": {
    "id": 177060797,
    "name": "INMOBILIARIOS OLANO Y CIA. LTDA",
    "masked_phone": "+5730",
    "whatsapp_phone": null,
    "has_whatsapp": true
  },
  "technicalSheet": [
    {"field": "property_type_name", "value": "Apartamento"},
    {"field": "bathrooms", "value": "1"},
    {"field": "bedrooms", "value": "1"},
    {"field": "garage", "value": "1"},
    {"field": "m2Built", "value": "41 m2"},
    {"field": "stratum", "value": "5"}
  ],
  "locations": {
    "location_main": {"name": "La campiña"},
    "locality": [{"name": "Riomar"}],
    "location_point": "POINT (-74.8211055 11.0028108)"
  }
}
```

#### URL Patterns y Paginación
- General Barranquilla: `https://www.fincaraiz.com.co/arriendo/apartamentos/barranquilla/atlantico`
- Por barrio: `https://www.fincaraiz.com.co/arriendo/apartamentos/{slug-barrio}/barranquilla`
  - Ejemplos: `el-golf`, `villa-santos`, `miramar`, `villa-carolina`, `riomar`
- Paginación: `/pagina2`, `/pagina3`, `/pagina4`, etc. agregados al final de la ruta de búsqueda.

---

### 2.3 Ciencuadras (`ciencuadras.com`)

#### Características Técnicas
- Retorna HTML con Schema.org `ItemList` de 28 elementos.
- Contiene títulos, URLs canónicas como `https://www.ciencuadras.com/inmueble/...`, imágenes alojadas en AWS S3 (`www-img-cc.s3.amazonaws.com`), coordenadas (`GeoCoordinates`) y área en m2.
- **Limitación observada**: En los listados generales mezcla ventas con arriendos si no se valida estrictamente el campo `offers.price` (ofertas de $300M+ corresponden a venta). Además, el teléfono de contacto no está expuesto directamente en la tarjeta del listado, requiriendo navegación a la página de detalle individual.

---

## 3. Esquema Unificado de Datos (Data Schema)

Para garantizar la integridad y alimentar sin fricción el Dashboard Web y el Dossier de Visitas, el pipeline de normalización debe mapear los datos de cualquier portal al siguiente esquema tipado:

```typescript
interface UnifiedProperty {
  // Identificación única
  id: string;                      // Formato: "{portal}_{portal_id}" (ej. "metro_21602-M6953598", "finca_194249769")
  portal: "metrocuadrado" | "fincaraiz" | "ciencuadras";
  portal_id: string;               // ID original del anuncio
  
  // Datos descriptivos básicos
  title: string;                   // Título limpio del anuncio
  property_type: "Apartamento" | "Casa" | "Apartaestudio";
  description?: string;            // Descripción del inmueble
  
  // Finanzas y Presupuesto (Regla estricta: total_price <= 2.500.000 COP)
  canon: number;                   // Valor del canon mensual en COP
  admin_fee: number;               // Valor administración en COP (0 si está incluida o no aplica)
  admin_included: boolean;         // True si el canon ya incluye la administración
  total_price: number;             // canon + (admin_included ? 0 : admin_fee) <= 2500000
  
  // Ubicación física (Barranquilla Norte/Noroccidente)
  city: "Barranquilla";
  zone: string;                    // "Noroccidente", "Riomar", "Norte Centro Histórico"
  neighborhood: string;            // "El Golf", "Alto Prado", "Miramar", "Villa Carolina", "Villa Santos", etc.
  address_text?: string;           // Dirección legible (ej. "Cra 47 # 85-53")
  latitude?: number;               // Coordenadas WGS84
  longitude?: number;
  stratum?: number;                // Estrato socioeconómico (habitualmente 4, 5 o 6 en el norte)
  
  // Características físicas del inmueble
  area_m2: number;                 // Área construida o privada en metros cuadrados
  bedrooms: number;                // Número de habitaciones
  bathrooms: number;               // Número de baños
  parking: number;                 // Cupos de parqueadero (0 si no tiene)
  floor_number?: number;           // Número de piso
  has_elevator?: boolean;          // Presencia de ascensor
  pets_allowed?: boolean;          // Acepta mascotas
  
  // Recursos multimedia y Enlace
  images: string[];                // Arreglo de URLs completas a fotos del inmueble
  main_image: string;              // URL de la foto de portada
  url: string;                     // Enlace web directo y navegable al anuncio
  
  // Información de contacto directo
  contact_phone?: string;          // Teléfono celular o fijo (ej. "3007771690")
  whatsapp?: string;               // Número listo para enlace wa.me/{whatsapp} (ej. "573007771690")
  agency_name?: string;            // Nombre de la inmobiliaria o anunciante
  contact_person?: string;         // Nombre del asesor
  
  // Metadatos de tracking
  extracted_at: string;            // ISO 8601 UTC timestamp
  status: "por_contactar" | "favorito" | "visita_programada" | "descartado"; // Estado en CRM local
  notes?: string;                  // Notas del usuario
  duplicate_group_id?: string;     // ID de cluster si fue fusionado con otro portal
}
```

---

## 4. Estrategia y Algoritmo de Deduplicación Cross-Portal

### 4.1 La Naturaleza del Problema
En el mercado inmobiliario de Barranquilla, propietarios y agencias suelen publicar el mismo inmueble en múltiples portales (especialmente Metrocuadrado y Finca Raíz) con variaciones en:
- **Títulos**: "Hermoso apto Miramar 3 habs" vs "Apartamento en Arriendo, Miramar, Barranquilla".
- **Precios**: Diferencia de $20.000 a $80.000 COP debido a si se desglosó la cuota de administración o si una agencia cobró un redondeo.
- **Áreas**: 64 m² vs 65 m² por redondeo de área privada vs construida.

### 4.2 Evidencia Empírica Obtenida en Vivo
En nuestra prueba sobre el barrio Miramar y Villa Carolina, se detectaron **46 pares de coincidencias cruzadas directas**, por ejemplo:
- **Metrocuadrado**: $1.800.000 COP | 55 m² | 2 Hab / 2 Baños | Miramar
- **Finca Raíz**: $1.800.000 COP | 54 m² | 2 Hab / 2 Baños | Miramar
- Diferencia de precio: **$0 COP**, Diferencia de área: **1 m²**.

### 4.3 Algoritmo de Deduplicación Multinivel (Specs Fingerprint + Geo)

Se define un algoritmo determinístico en 4 etapas:

```python
def compute_property_fingerprint(prop):
    """
    Genera una clave de agrupamiento grueso basada en ubicación y especificaciones discretas.
    """
    norm_barrio = normalize_neighborhood_name(prop['neighborhood'])
    rooms = prop['bedrooms']
    baths = prop['bathrooms']
    # Discretizamos el área en bloques de 3m2 y el precio en bloques de $50.000 COP
    area_bucket = round(prop['area_m2'] / 3.0) * 3 if prop['area_m2'] > 0 else 0
    price_bucket = round(prop['total_price'] / 50000.0) * 50000
    return f"{norm_barrio}_{rooms}R_{baths}B_{area_bucket}m2_{price_bucket}cop"

def calculate_similarity_score(prop_a, prop_b):
    """
    Retorna un score de 0.0 a 1.0 indicando la probabilidad de que prop_a y prop_b sean el mismo inmueble.
    """
    score = 0.0
    
    # 1. Barrio o Zona canónica (Condición obligatoria)
    norm_a = normalize_neighborhood_name(prop_a['neighborhood'])
    norm_b = normalize_neighborhood_name(prop_b['neighborhood'])
    if norm_a != norm_b and not are_neighboring(norm_a, norm_b):
        return 0.0
    score += 0.20
    
    # 2. Habitaciones y Baños (Coincidencia exacta)
    if prop_a['bedrooms'] > 0 and prop_a['bedrooms'] == prop_b['bedrooms']:
        score += 0.25
    elif prop_a['bedrooms'] != prop_b['bedrooms']:
        return 0.0 # Habitaciones distintas -> Descartar duplicado
        
    if prop_a['bathrooms'] > 0 and prop_a['bathrooms'] == prop_b['bathrooms']:
        score += 0.15
        
    # 3. Diferencia de Precio Total (Tolerancia: <= $70.000 COP o 3%)
    price_diff = abs(prop_a['total_price'] - prop_b['total_price'])
    if price_diff == 0:
        score += 0.20
    elif price_diff <= 70000:
        score += 0.15
    elif price_diff > 150000:
        return 0.0 # Gran diferencia de precio -> Inmuebles distintos
        
    # 4. Diferencia de Área (Tolerancia: <= 3 m2)
    area_diff = abs(prop_a['area_m2'] - prop_b['area_m2'])
    if area_diff <= 1.0:
        score += 0.20
    elif area_diff <= 3.0:
        score += 0.10
    elif area_diff > 6.0:
        return 0.0
        
    # 5. Coincidencia geográfica si ambas tienen lat/lon (distancia < 60 metros)
    if prop_a.get('latitude') and prop_b.get('latitude'):
        dist_meters = haversine(prop_a['latitude'], prop_a['longitude'], prop_b['latitude'], prop_b['longitude'])
        if dist_meters < 60:
            score += 0.20
            
    return score
```

### 4.4 Regla de Fusión y Enriquecimiento (Merge Rule)
Cuando dos registros superan el umbral `score >= 0.75`:
1. **Contacto y Teléfono**: Se toma preferentemente el teléfono verificado y WhatsApp de Metrocuadrado (que viene desglosado y sin enmascarar).
2. **Galería Fotográfica**: Se unen los arreglos de imágenes de ambos portales eliminando URLs duplicadas (obteniendo un catálogo visual completo).
3. **Enlaces Fuente**: Se preservan ambos enlaces en un campo `source_urls: [{"portal": "metrocuadrado", "url": "..."}, {"portal": "fincaraiz", "url": "..."}]`.
4. **Precio Total**: Se toma el valor más conservador o el precio que explicite el desglose formal de administración.

---

## 5. Recomendación de Arquitectura para el Extractor

### 5.1 Pipeline de 4 Módulos en Python
La arquitectura recomendada consta de:
1. `fetcher.py`: Gestor de solicitudes HTTP utilizando `urllib.request` (nativo de Python standard library, sin dependencias externas complejas como Selenium o Playwright). Utiliza rotación de cabeceras de navegador estándar (`Chrome/128+`) y gestión de timeouts de 15 segundos.
2. `metro_adapter.py`: Parser especializado para Metrocuadrado. Extrae los chunks de RSC streaming (`self.__next_f`), decodifica la colección `"results"`, aplica filtro local de precio (`total <= 2.500.000 COP`) y normaliza al esquema unificado.
3. `fincaraiz_adapter.py`: Parser para Finca Raíz. Extrae el JSON de `searchFast.data` y el JSON-LD de `CollectionPage`, desempaqueta las especificaciones técnicas (`technicalSheet`), parsea el valor de administración y normaliza al esquema unificado.
4. `deduplicator.py`: Agrupa y fusiona registros coincidentes entre portales, asignando un `canonical_id` y enriqueciendo los datos de contacto y fotos.

### 5.2 Almacenamiento Estructurado
- **SQLite Local (`tracker.db`)**:
  - Tabla `properties`: Almacena el inventario unificado deduplicado.
  - Tabla `property_sources`: Mapea cada fuente original (portal, URL, id original).
  - Tabla `property_status`: Registra el estado de seguimiento del usuario (`por_contactar`, `favorito`, `visita_programada`, `descartado`, notas).
- **Exportación JSON (`properties_unified.json`)**: Archivo liviano que carga el frontend web de manera inmediata sin latencia de red.

---

## 6. Inventario de Barrios Prioritarios en Barranquilla (Norte / Noroccidente)

Para maximizar la densidad de inmuebles calificados bajo el límite de $2.500.000 COP:
1. **Miramar**: Zona de mayor oferta activa con excelente relación espacio/precio (apartamentos de 60 a 85 m², 2 a 3 habitaciones, con garaje y piscina en conjunto cerrado por $1.6M - $2.3M COP total).
2. **Villa Carolina**: Sector residencial muy seguro con parques y centros comerciales (apartamentos de 55 a 75 m² por $1.7M - $2.4M COP total).
3. **Ciudad Mallorquín / Buenavista**: Nuevos desarrollos con acabados modernos, estrato 4 y amenidades completas ($1.3M - $2.2M COP total).
4. **Alto Prado / El Prado**: Sector tradicional de alto estrato; ofrece apartaestudios de 1 a 2 habitaciones y apartamentos en edificios clásicos por $1.8M - $2.5M COP total.
5. **Villa Santos / Riomar / El Golf**: Zonas prime; aquí la búsqueda se concentra en apartaestudios ejecutivos y apartamentos de 1-2 alcobas bien ubicados ($2.0M - $2.5M COP total).
6. **Villa Country**: Excelente ubicación central en el norte, cerca a Country Plaza y Villa Country ($1.8M - $2.5M COP total).
