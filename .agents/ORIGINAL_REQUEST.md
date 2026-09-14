# Original User Request

## Initial Request — 2026-09-13T16:50:35-05:00

Construir un buscador y rastreador inteligente de apartamentos y casas en arriendo en Barranquilla con presupuesto máximo de $2.500.000 COP (incluyendo canon + administración), con base de datos unificada de portales inmobiliarios y un dashboard web interactivo local, además de una selección curada e inmediata de opciones viables para agendar visitas esta semana.

Working directory: c:/Users/Admin/Downloads/TRACKER DE APARTAMENTOS Y CASA BARRANQUILLA PARA ARRENDAR
Integrity mode: development

## Requirements

### R1. Base de Datos y Extracción Multi-Portal (Barranquilla Norte)
Consolidar una base de datos estructurada de inmuebles en arriendo (apartamentos y casas) en Barranquilla a partir de portales líderes (como Finca Raíz, Metrocuadrado, Ciencuadras, etc.), priorizando el sector Norte / Noroccidente (El Golf, Alto Prado, Riomar, Villa Santos, Villa Country, Miramar, Villa Carolina y aledaños).
- Condición de precio estricta: Canon + Administración <= $2.500.000 COP mensual.
- Campos requeridos por registro: título, tipo de inmueble, precio de canon, valor de administración, precio total, barrio/zona, área (m²), número de habitaciones, baños, parqueaderos, fotos/enlace a imágenes, enlace directo a la publicación original y datos de contacto (teléfono/inmobiliaria/WhatsApp si está disponible).

### R2. Buscador y Dashboard Web Interactivo Local
Implementar una aplicación web interactiva local de uso inmediato que cargue la base de datos y permita:
- Búsqueda en tiempo real por texto y filtros dinámicos (barrio, rango de precio total, número de habitaciones, baños, con/sin parqueadero).
- Vista en cuadrícula de tarjetas atractivas con fotos, etiquetas de precio total (canon + admin desglosados), y enlaces directos al anuncio original.
- Sistema de seguimiento o estado de interés para cada propiedad (ej. Por contactar, Visita programada, Descartado, Favorito) persistido localmente.

### R3. Dossier Curado de Opciones Inmediatas para Visitar Esta Semana
Generar un informe o catálogo destacado con las mejores opciones activas verificadas en el norte de Barranquilla por debajo de $2.500.000 COP total, listas con su información de contacto y enlaces directos para iniciar agendamiento inmediato de visitas.

## Acceptance Criteria

### Integridad y Calidad de Datos
- [ ] La base de datos contiene propiedades reales en Barranquilla dentro del sector objetivo (Norte/Noroccidente).
- [ ] Para cada inmueble registrado, el valor total (canon + administración) no excede $2.500.000 COP.
- [ ] No existen registros duplicados de un mismo inmueble provenientes de diferentes portales.
- [ ] Todos los enlaces a las publicaciones originales son válidos y directos.

### Funcionalidad del Dashboard
- [ ] El dashboard web arranca y se puede abrir localmente en el navegador sin errores.
- [ ] Los filtros por barrio, precio, habitaciones y búsqueda de texto responden de manera fluida en tiempo real.
- [ ] Se puede marcar y guardar el estado de seguimiento de los inmuebles (favoritos, visitas, descartados).

### Verificación del Catálogo
- [ ] El dossier de visitas para esta semana presenta al menos 10 a 15 opciones destacadas con mejor relación calidad/precio/ubicación, con datos de contacto listos para llamar o escribir.
