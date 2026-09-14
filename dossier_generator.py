#!/usr/bin/env python3
"""
dossier_generator.py
Curated Immediate Visit Dossier & Contact Sheets Generator for Barranquilla Norte.

Implements the 100-point Multi-Factor Value Index (MFVI):
  1. Price per m² efficiency (25 pts)
  2. Location prestige & security in Barranquilla Norte (25 pts)
  3. Space & layout (rooms, baths, parking, area) (20 pts)
  4. Stratum & amenities (15 pts)
  5. Immediate contact readiness (direct WhatsApp & phone) (15 pts)

Evaluates the verified inventory from data/inmuebles_barranquilla.json,
selects the top 12 to 15 standout properties, and outputs:
  - DOSSIER_VISITAS.md (Comprehensive, polished Spanish Markdown guide)
  - data/dossier_curado.json (Structured curated dataset for dashboard consumption)
"""

import json
import os
import re
import urllib.parse
from datetime import datetime
from pathlib import Path


def clean_phone(phone_str):
    """Normalizes phone numbers to standard format or Colombian international prefix 57..."""
    if not phone_str:
        return ""
    digits = re.sub(r"\D", "", str(phone_str))
    if len(digits) == 10 and digits.startswith("3"):
        return "57" + digits
    if len(digits) == 12 and digits.startswith("573"):
        return digits
    return digits


def format_cop(amount):
    """Formats numeric values into standard Colombian peso strings, e.g. $1.850.000"""
    if amount is None or amount == "":
        return "$0"
    try:
        val = int(round(float(amount)))
        # Format with dot as thousand separator
        return "$" + f"{val:,}".replace(",", ".")
    except (ValueError, TypeError):
        return "$0"


def generate_whatsapp_url(prop):
    """Generates click-to-chat WhatsApp link with prefilled polite appointment inquiry."""
    contact = prop.get("contact", {})
    wa = clean_phone(contact.get("whatsapp"))
    phone = clean_phone(contact.get("phone"))
    target = wa if (wa and wa.startswith("573")) else (phone if (phone and phone.startswith("573")) else "")
    if not target:
        target = "573000000000"

    prop_id = prop.get("id", "")
    ptype = prop.get("property_type", "Apartamento").lower()
    barrio = prop.get("neighborhood", "Barranquilla")
    total_str = format_cop(prop.get("total_price", 0))

    message = (
        f"Hola, cordial saludo. Vi la publicación del {ptype} en {barrio} (Ref: {prop_id}) "
        f"por {total_str} COP mensual con administración incluida. "
        f"Tengo interés serio en agendar una visita física esta semana. "
        f"¿Qué días y horarios tienen disponibles para coordinar? Muchas gracias."
    )
    encoded = urllib.parse.quote(message)
    return f"https://wa.me/{target}?text={encoded}"


class MultiFactorValueIndex:
    """Calculates the 100-point Multi-Factor Value Index (MFVI)."""

    @staticmethod
    def score_price_per_m2(total_price, area_m2):
        """1. Price per m² efficiency (Max 25 pts)"""
        if not area_m2 or area_m2 <= 0:
            return 12.0, 0.0

        cost_m2 = total_price / area_m2
        if cost_m2 < 28000:
            pts = 25.0
        elif cost_m2 <= 33000:
            pts = 21.0
        elif cost_m2 <= 38000:
            pts = 17.0
        elif cost_m2 <= 44000:
            pts = 13.0
        else:
            pts = 8.0
        return pts, round(cost_m2, 0)

    @staticmethod
    def score_location(neighborhood):
        """2. Location prestige / security in Barranquilla Norte (Max 25 pts)"""
        b = (neighborhood or "").lower()
        # Tier A+ (25 pts): Core North Premium / Classic
        if any(k in b for k in ["golf", "alto prado", "altos del prado", "riomar", "altos de riomar", "villa country"]):
            return 25.0, "Tier A+ (Alta Exclusividad / Central Norte)"
        # Tier A (22 pts): Modern Residential / Expansion
        elif any(k in b for k in ["villa santos", "buenavista", "altos del limon", "el poblado", "la castellana", "san vicente"]):
            return 22.0, "Tier A (Moderno Residencial / Buenavista)"
        # Tier B+ (18 pts): High-Amenity Family & Emerging Norte
        elif any(k in b for k in ["miramar", "villa carolina", "paraiso", "paríso", "andalucia", "andalucía", "el limoncito", "el tabor", "los alpes", "la cumbre", "ciudad jardin", "ciudad jardín"]):
            return 18.0, "Tier B+ (Residencial Familiar Consolidado)"
        # Tier B (14 pts): Other authorized Norte / Noroccidente
        else:
            return 14.0, "Tier B (Noroccidente / Corredor Norte)"

    @staticmethod
    def score_space_and_layout(bedrooms, bathrooms, parking, area_m2):
        """3. Space & Layout (Max 20 pts: Bedrooms 6, Bathrooms 5, Parking 5, Area 4)"""
        # Bedrooms (6 max)
        beds = bedrooms or 0
        if beds >= 3:
            s_beds = 6.0
        elif beds == 2:
            s_beds = 5.0
        elif beds == 1:
            s_beds = 3.0
        else:
            s_beds = 2.0

        # Bathrooms (5 max)
        baths = bathrooms or 0
        if baths >= 2:
            s_baths = 5.0
        elif baths == 1:
            s_baths = 3.0
        else:
            s_baths = 1.0

        # Parking (5 max)
        park = parking or 0
        s_park = 5.0 if park >= 1 else 0.0

        # Area bonus (4 max)
        area = area_m2 or 0
        if area >= 85:
            s_area = 4.0
        elif area >= 65:
            s_area = 3.0
        elif area >= 45:
            s_area = 2.0
        else:
            s_area = 1.0

        total_space = s_beds + s_baths + s_park + s_area
        return round(total_space, 1)

    @staticmethod
    def score_stratum_and_amenities(stratum, title, description):
        """4. Stratum & amenities (Max 15 pts: Stratum 6, Amenities 9)"""
        strat = stratum or 0
        if strat == 6:
            s_strat = 6.0
        elif strat == 5:
            s_strat = 5.0
        elif strat == 4:
            s_strat = 4.0
        else:
            s_strat = 2.0

        text = f"{title or ''} {description or ''}".lower()
        amenity_keywords = [
            "piscina", "gimnasio", "ascensor", "vigilancia",
            "porteria", "portería", "planta", "balcon", "balcón",
            "bbq", "salon social", "salón social", "parque infantil", "cocina integral"
        ]
        matched = set()
        for kw in amenity_keywords:
            clean_kw = kw.replace("í", "i").replace("ó", "o")
            norm_text = text.replace("í", "i").replace("ó", "o")
            if clean_kw in norm_text:
                matched.add(clean_kw)

        s_amen = min(9.0, len(matched) * 1.5)
        return round(s_strat + s_amen, 1), list(matched)

    @staticmethod
    def score_contact_readiness(contact):
        """5. Immediate contact readiness (Max 15 pts: WhatsApp 8, Phone 4, Agency 3)"""
        wa = clean_phone(contact.get("whatsapp"))
        phone = clean_phone(contact.get("phone"))
        agency = contact.get("agency") or contact.get("agent_name") or ""

        s_wa = 8.0 if (wa and len(wa) == 12 and wa.startswith("573")) else (4.0 if wa else 0.0)
        s_ph = 4.0 if (phone and len(phone) >= 10) else 0.0
        s_ag = 3.0 if agency.strip() else 0.0

        total_contact = s_wa + s_ph + s_ag
        return round(total_contact, 1)

    @classmethod
    def evaluate(cls, prop):
        """Evaluates a single property and returns total MFVI score (0-100) and breakdown."""
        total_price = prop.get("total_price", 0)
        area_m2 = prop.get("area_m2", 0)
        neighborhood = prop.get("neighborhood", "")
        bedrooms = prop.get("bedrooms", 0)
        bathrooms = prop.get("bathrooms", 0)
        parking = prop.get("parking", 0)
        stratum = prop.get("stratum", 0)
        title = prop.get("title", "")
        description = prop.get("description", "")
        contact = prop.get("contact", {})

        s_pm2, cost_m2 = cls.score_price_per_m2(total_price, area_m2)
        s_loc, loc_tier = cls.score_location(neighborhood)
        s_space = cls.score_space_and_layout(bedrooms, bathrooms, parking, area_m2)
        s_amen, matched_amenities = cls.score_stratum_and_amenities(stratum, title, description)
        s_contact = cls.score_contact_readiness(contact)

        total_score = round(s_pm2 + s_loc + s_space + s_amen + s_contact, 1)

        # Quality tier badge
        if total_score >= 90.0:
            badge = "🏆 Selección Diamante (Prioridad #1)"
            tier = "Diamante"
        elif total_score >= 82.0:
            badge = "🌟 Selección Oro (Excelente Relación Valor)"
            tier = "Oro"
        elif total_score >= 75.0:
            badge = "✨ Selección Plata (Opción Sólida Aprobada)"
            tier = "Plata"
        else:
            badge = "Catálogo General"
            tier = "General"

        return {
            "mfvi_score": total_score,
            "tier": tier,
            "badge": badge,
            "cost_per_m2": cost_m2,
            "location_tier": loc_tier,
            "matched_amenities": matched_amenities,
            "breakdown": {
                "price_efficiency": s_pm2,
                "location_prestige": s_loc,
                "space_layout": s_space,
                "stratum_amenities": s_amen,
                "contact_readiness": s_contact
            }
        }


def select_curated_properties(all_properties, target_count=15):
    """
    Funnel selection algorithm:
      Stage 1: Binary validation filters (<= $2.5M, images >= 3, active contact & URL, Barranquilla Norte).
      Stage 2: MFVI evaluation.
      Stage 3: Typology and neighborhood diversity quotas to avoid monotypic clusters.
      Stage 4: Top target_count ranking.
    """
    candidates = []
    for p in all_properties:
        # Binary Stage 1
        if p.get("total_price", 0) > 2500000:
            continue
        if len(p.get("images", [])) < 3:
            continue
        if not p.get("url"):
            continue
        contact = p.get("contact", {})
        if not contact.get("phone") and not contact.get("whatsapp"):
            continue

        eval_res = MultiFactorValueIndex.evaluate(p)
        if eval_res["mfvi_score"] < 75.0:
            continue

        item = dict(p)
        item["eval"] = eval_res
        candidates.append(item)

    # Sort primarily by MFVI score descending
    candidates.sort(key=lambda x: -x["eval"]["mfvi_score"])

    # Stage 3: Neighborhood and typology balanced selection
    selected = []
    neighborhood_counts = {}
    
    # Priority pass: guarantee diversity while keeping highest scores
    for cand in candidates:
        if len(selected) >= target_count:
            break
        b = cand.get("neighborhood", "Otro")
        current_in_b = neighborhood_counts.get(b, 0)
        # Cap any single neighborhood to max 4 to ensure broad geographic representation
        if current_in_b >= 4 and len(selected) < target_count - 2:
            continue
        
        selected.append(cand)
        neighborhood_counts[b] = current_in_b + 1

    # If still below target_count, fill with next best remaining candidates
    if len(selected) < target_count:
        for cand in candidates:
            if len(selected) >= target_count:
                break
            if cand["id"] not in [x["id"] for x in selected]:
                selected.append(cand)

    return selected


def build_curator_thesis(p):
    """Generates an insightful, objective curator thesis for why the property was chosen."""
    ev = p["eval"]
    score = ev["mfvi_score"]
    cost_m2 = ev["cost_per_m2"]
    barrio = p.get("neighborhood", "")
    area = p.get("area_m2", 0)
    beds = p.get("bedrooms", 0)
    parking = p.get("parking", 0)
    canon = p.get("canon", 0)
    admin = p.get("admin_fee", 0)
    total = p.get("total_price", 0)

    reasons = []
    if cost_m2 and cost_m2 < 30000:
        reasons.append(f"extraordinaria eficiencia de costo por metro cuadrado ({format_cop(cost_m2)}/m²)")
    elif cost_m2 and cost_m2 < 36000:
        reasons.append(f"muy competitivo valor por metro cuadrado ({format_cop(cost_m2)}/m²)")

    if any(k in barrio.lower() for k in ["golf", "alto prado", "riomar", "country"]):
        reasons.append(f"inmejorable ubicación premium en {barrio}")
    elif any(k in barrio.lower() for k in ["villa santos", "buenavista"]):
        reasons.append(f"excelente entorno residencial moderno en {barrio}")
    else:
        reasons.append(f"gran sector residencial consolidado en {barrio}")

    if beds >= 3 and area >= 80:
        reasons.append(f"amplia distribución familiar ({area}m² con {beds} alcobas)")
    elif beds >= 2 and parking >= 1:
        reasons.append(f"distribución funcional con {beds} alcobas y parqueadero privado")

    if admin == 0:
        reasons.append("administración incluida en el canon mensual")
    elif admin < 350000:
        reasons.append(f"cuota de administración moderada ({format_cop(admin)})")

    joined = ", ".join(reasons)
    return (
        f"Inmueble con índice MFVI de **{score}/100** ({ev['tier']}). "
        f"Sobresale en el mercado de Barranquilla Norte por su {joined}. "
        f"Representa una oportunidad de alto valor para agendamiento prioritario dentro del presupuesto de {format_cop(total)} COP."
    )


def build_inspection_checklist(p):
    """Generates practical, on-site visit inspection checklist items tailored to the property."""
    barrio = p.get("neighborhood", "")
    area = p.get("area_m2", 0)
    park = p.get("parking", 0)

    checks = [
        "**Presión hidráulica y suministro**: Abrir duchas y lavamanos simultáneamente para verificar caudal y corroborar funcionamiento de motobombas o tanques de reserva del edificio.",
        "**Orientación solar y ventilación cruzada**: Validar si el apartamento queda del lado sombra en las tardes caribeñas (minimiza sustancialmente el consumo de aire acondicionado).",
        "**Suplencia eléctrica**: Consultar en portería/administración si la planta eléctrica del edificio cubre únicamente áreas comunes o tiene transferencia a puntos esenciales del apartamento (luces/nevera)."
    ]

    if park >= 1:
        checks.append("**Parqueadero privado**: Probar maniobra de estacionamiento en el slot asignado y confirmar si es cubierto o descubierto.")
    else:
        checks.append("**Estacionamiento y accesos**: Confirmar disponibilidad de bahía para visitantes o costo de celaduría nocturna para vehículo en la cuadra.")

    if area >= 80:
        checks.append("**Estado de carpintería y closets**: Revisar bisagras, humedad en clósets y estado general de muebles de cocina integral.")

    return checks


def generate_dossier_markdown(curated_list, total_db_count=172):
    """Generates the full standalone DOSSIER_VISITAS.md file content."""
    now_str = datetime.now().strftime("%Y-%m-%d")
    
    # Financial aggregate statistics
    prices = [p["total_price"] for p in curated_list]
    canons = [p["canon"] for p in curated_list]
    admins = [p["admin_fee"] for p in curated_list]
    areas = [p["area_m2"] for p in curated_list if p.get("area_m2", 0) > 0]
    costs_m2 = [p["eval"]["cost_per_m2"] for p in curated_list if p["eval"]["cost_per_m2"] > 0]

    min_total = min(prices)
    max_total = max(prices)
    avg_total = sum(prices) / len(prices)
    avg_canon = sum(canons) / len(canons)
    avg_admin = sum(admins) / len(admins)
    avg_cost_m2 = sum(costs_m2) / len(costs_m2) if costs_m2 else 0

    # Top Highlights
    top_exec = None
    for p in curated_list:
        if p.get("bedrooms", 0) in [1, 2] and any(k in p.get("neighborhood", "").lower() for k in ["golf", "alto prado", "riomar", "country"]):
            top_exec = p
            break
    if not top_exec:
        top_exec = curated_list[0]

    top_family = None
    for p in curated_list:
        if p.get("bedrooms", 0) >= 3 and p.get("area_m2", 0) >= 80:
            top_family = p
            break
    if not top_family:
        top_family = curated_list[1]

    top_value = min(curated_list, key=lambda x: x["eval"]["cost_per_m2"] if x["eval"]["cost_per_m2"] > 0 else 999999)

    md = []
    md.append("# Dossier de Visitas Inmediatas — Apartamentos y Casas en Arriendo")
    md.append("## Selección Curada de Inmuebles en Barranquilla Norte (Presupuesto ≤ $2.500.000 COP)")
    md.append(f"**Fecha de Emisión**: `{now_str}` · **Inventario Evaluado**: `{total_db_count} propiedades` · **Opciones Destacadas**: `{len(curated_list)} inmuebles`")
    md.append("")
    md.append("> 📌 **Propósito de este Dossier**: Proveer al arrendatario un catálogo ejecutivo de toma de decisiones rápidas, con las mejores oportunidades habitacionales del sector Norte de Barranquilla verificadas para agendar visitas físicas esta misma semana. Cada opción incluye desglose financiero riguroso (Canon + Administración), puntuación objetiva **MFVI (0-100)**, fotos y enlace directo de WhatsApp con mensaje estructurado para respuesta inmediata.")
    md.append("")
    md.append("---")
    md.append("")

    # SECTION I: Executive Summary
    md.append("## 1. Resumen Ejecutivo del Mercado y Métricas Clave")
    md.append("")
    md.append("El segmento de arriendos residenciales en **Barranquilla Norte** por debajo del tope de **$2.500.000 COP mensual total** concentra una alta demanda. A partir del análisis cuantitativo de los inmuebles activos en portales inmobiliarios líderes, se identifican las siguientes métricas del grupo seleccionado:")
    md.append("")
    md.append(f"- **Rango de Precios Totales**: Desde **{format_cop(min_total)}** hasta **{format_cop(max_total)} COP**.")
    md.append(f"- **Promedio Total Mensual**: **{format_cop(avg_total)} COP** (Canon promedio: {format_cop(avg_canon)} | Administración promedio: {format_cop(avg_admin)}).")
    md.append(f"- **Costo Promedio por Metro Cuadrado**: **{format_cop(avg_cost_m2)} COP/m²**.")
    md.append(f"- **Cobertura Geográfica**: Riomar, Altos de Riomar, Alto Prado, El Golf, Villa Santos, Villa Country, Miramar, Paraíso, Andalucía, San Vicente.")
    md.append(f"- **Inmuebles con Parqueadero Privado**: **{sum(1 for p in curated_list if p.get('parking', 0) >= 1)} de {len(curated_list)} ({round(sum(1 for p in curated_list if p.get('parking', 0) >= 1) / len(curated_list) * 100)}%)**.")
    md.append("")
    md.append("### 🌟 Recomendaciones de Vía Rápida (Fast-Track Picks)")
    md.append("")
    md.append(f"1. **🏆 Mejor Opción Ejecutiva (1-2 Alcobas en Zona Premium)**: ")
    md.append(f"   - **{top_exec['title']}** (Ref: `{top_exec['id']}` en **{top_exec['neighborhood']}**). Total: **{format_cop(top_exec['total_price'])} COP** | Score MFVI: **{top_exec['eval']['mfvi_score']}/100**. Ideal para profesionales o parejas que priorizan caminabilidad y estrato alto.")
    md.append(f"2. **👨‍👩‍👧 Mejor Opción Familiar (3 Alcobas con Amplio Espacio)**: ")
    md.append(f"   - **{top_family['title']}** (Ref: `{top_family['id']}` en **{top_family['neighborhood']}**). Total: **{format_cop(top_family['total_price'])} COP** ({top_family['area_m2']} m², {top_family['bedrooms']} alcobas, {top_family['bathrooms']} baños).")
    md.append(f"3. **💎 Mayor Eficiencia de Espacio por Peso ($/m²)**: ")
    md.append(f"   - **{top_value['title']}** (Ref: `{top_value['id']}` en **{top_value['neighborhood']}**). A solo **{format_cop(top_value['eval']['cost_per_m2'])}/m²** ({top_value['area_m2']} m² por {format_cop(top_value['total_price'])} COP).")
    md.append("")
    md.append("---")
    md.append("")

    # SECTION II: Comparative Master Decision Table
    md.append("## 2. Tabla Maestra Comparativa de Selección (Top 15)")
    md.append("")
    md.append("Matriz comparativa ordenada por el **Índice de Valor Multifactorial (MFVI)**. Permite evaluar simultáneamente barrio, metraje, cánon, administración y contacto.")
    md.append("")
    md.append("| # | Ref ID | Barrio | Tipo | Área | Hab | Baños | Parq | Canon | Admin | Total Mes | $/m² | Score MFVI | Contacto Rápido |")
    md.append("|:---:|:---:|:---|:---:|---:|:---:|:---:|:---:|---:|---:|---:|---:|:---:|:---:|")

    for rank, p in enumerate(curated_list, 1):
        pid = p["id"]
        barrio = p.get("neighborhood", "")
        ptype = "Apto" if p.get("property_type") == "Apartamento" else "Casa"
        area = f"{p.get('area_m2', '-')} m²"
        hab = p.get("bedrooms", 0)
        ban = p.get("bathrooms", 1)
        pq = f"{p.get('parking', 0)}" if p.get('parking', 0) > 0 else "0"
        canon_str = format_cop(p.get("canon", 0))
        admin_str = format_cop(p.get("admin_fee", 0)) if p.get("admin_fee", 0) > 0 else "Incluida"
        total_str = format_cop(p.get("total_price", 0))
        cost_m2 = format_cop(p["eval"]["cost_per_m2"])
        score = f"**{p['eval']['mfvi_score']}**"
        wa_url = generate_whatsapp_url(p)
        md.append(f"| #{rank} | `{pid}` | {barrio} | {ptype} | {area} | {hab} | {ban} | {pq} | {canon_str} | {admin_str} | **{total_str}** | {cost_m2} | {score} | [📲 WhatsApp]({wa_url}) |")

    md.append("")
    md.append("---")
    md.append("")

    # SECTION III: Detailed Property Factsheets
    md.append("## 3. Fichas Técnicas Detalladas de Cada Inmueble")
    md.append("")
    md.append("A continuación se desglosa la información integral de cada una de las propiedades finalistas:")
    md.append("")

    for rank, p in enumerate(curated_list, 1):
        pid = p["id"]
        title = p.get("title", "")
        barrio = p.get("neighborhood", "")
        zone = p.get("zone", "Norte")
        ptype = p.get("property_type", "Apartamento")
        address = p.get("address", "Sector Norte, Barranquilla")
        area = p.get("area_m2", 0)
        beds = p.get("bedrooms", 0)
        baths = p.get("bathrooms", 1)
        parking = p.get("parking", 0)
        stratum = p.get("stratum", 4)
        canon = format_cop(p.get("canon", 0))
        admin = format_cop(p.get("admin_fee", 0)) if p.get("admin_fee", 0) > 0 else "Incluida ($0)"
        total = format_cop(p.get("total_price", 0))
        cost_m2 = format_cop(p["eval"]["cost_per_m2"])
        score = p["eval"]["mfvi_score"]
        tier_badge = p["eval"]["badge"]
        matched_am = p["eval"]["matched_amenities"]
        contact = p.get("contact", {})
        phone = contact.get("phone", "Consultar")
        agency = contact.get("agency") or contact.get("agent_name") or "Inmobiliaria Contacto"
        wa_link = generate_whatsapp_url(p)
        original_url = p.get("url", "#")
        images = p.get("images", [])
        primary_img = images[0] if images else ""

        thesis = build_curator_thesis(p)
        checks = build_inspection_checklist(p)

        md.append(f"### Inmueble #{rank} — {title}")
        md.append(f"**Referencia**: `{pid}` · **Portal**: `{p.get('portal', 'Web')}` · **Calificación**: {tier_badge}")
        md.append("")
        if primary_img:
            md.append(f"![Foto Principal {pid}]({primary_img})")
            md.append("")

        md.append("#### 💰 Desglose Financiero")
        md.append(f"- **Canon de Arrendamiento**: {canon} COP")
        md.append(f"- **Valor de Administración**: {admin} COP")
        md.append(f"- **COSTO TOTAL MENSUAL**: **{total} COP** *(Presupuesto verificado ≤ $2.500.000)*")
        md.append(f"- **Eficiencia por Área**: **{cost_m2} / m²**")
        md.append("")
        md.append("#### 📐 Especificaciones Físicas y Distribución")
        md.append(f"- **Ubicación**: {barrio} (Zona {zone}), {address}")
        md.append(f"- **Tipo de Inmueble**: {ptype}")
        md.append(f"- **Área Privada**: {area} m²")
        md.append(f"- **Distribución**: {beds} Habitaciones | {baths} Baños | {parking} Parqueadero(s)")
        md.append(f"- **Estrato Socioeconómico**: Estrato {stratum}")
        if matched_am:
            amen_list = ", ".join([a.title() for a in matched_am])
            md.append(f"- **Amenidades Detectadas**: {amen_list}")
        md.append("")
        md.append("#### 💡 Tesis del Curador")
        md.append(f"> {thesis}")
        md.append("")
        md.append("#### 🔍 Puntos Críticos a Verificar en la Visita Física")
        for ck in checks:
            md.append(f"- {ck}")
        md.append("")
        md.append("#### 📲 Contacto Directo y Agendamiento")
        md.append(f"- **Inmobiliaria / Asesor**: {agency}")
        md.append(f"- **Teléfono de Contacto**: `{phone}`")
        md.append(f"- **Iniciar Chat de WhatsApp Inmediato**: [👉 Clic aquí para coordinar visita en WhatsApp]({wa_link})")
        md.append(f"- **Publicación Oficial**: [Ver anuncio original en {p.get('portal', 'Portal')} ↗]({original_url})")
        md.append("")
        md.append("---")
        md.append("")

    # SECTION IV: Visit Itinerary Logistics
    md.append("## 4. Itinerario y Ruta Logística Sugerida de Visitas")
    md.append("")
    md.append("Para maximizar la eficiencia y reducir tiempos muertos en desplazamientos por las vías principales (Cra 51B, Cra 53, Calle 84 y Vía 40), se propone el siguiente plan logístico agrupado por cercanía geográfica entre **Miércoles y Sábado**:")
    md.append("")
    md.append("### 🗓️ Día 1 — Miércoles Tarde: Circuito Alto Prado & Villa Country (3:00 PM – 6:00 PM)")
    md.append("- **Sectores**: Alto Prado, El Golf, Villa Country (Carrera 51B a Carrera 54, Calles 76 a 84).")
    md.append("- **Inmuebles en Ruta**: Propiedades ubicadas en el corazón financiero y gastronómico tradicional.")
    md.append("- **Recomendación Logística**: Iniciar a las 3:00 PM antes de la hora pico en la Cra 51B. Parqueo disponible en centros comerciales aledaños (CC Viva Barranquilla, CC Country Plaza).")
    md.append("")
    md.append("### 🗓️ Día 2 — Jueves Tarde: Circuito Riomar & Altos de Riomar (3:30 PM – 6:30 PM)")
    md.append("- **Sectores**: Riomar, Altos de Riomar (Carreras 57 a 59B, Calles 88 a 98).")
    md.append("- **Inmuebles en Ruta**: Apartamentos en torres residenciales con buena brisa caribeña y parques cercanos.")
    md.append("- **Recomendación Logística**: Las cuadras residenciales de Riomar son amplias y de fácil parqueo para visitantes. Confirmar con anticipación anuncio en portería.")
    md.append("")
    md.append("### 🗓️ Día 3 — Viernes Tarde: Circuito Villa Santos & Buenavista (2:30 PM – 5:30 PM)")
    md.append("- **Sectores**: Villa Santos, Altos del Limón, perímetro CC Buenavista y Mall Plaza (Calles 99 a 106).")
    md.append("- **Inmuebles en Ruta**: Conjuntos cerrados modernos con piscinas y clubes sociales.")
    md.append("- **Recomendación Logística**: Excelente conexión por la Cra 51B hacia el norte. Tomar fotos de las zonas sociales y preguntar por los horarios de uso de zonas húmedas.")
    md.append("")
    md.append("### 🗓️ Día 4 — Sábado Mañana: Circuito Miramar, Paraíso & Villa Carolina (9:00 AM – 1:00 PM)")
    md.append("- **Sectores**: Miramar, Andalucía, Paraíso, Villa Carolina.")
    md.append("- **Inmuebles en Ruta**: Amplias opciones familiares con parques infantiles y excelente ventilación natural.")
    md.append("- **Recomendación Logística**: Aprovechar la luz de la mañana para constatar la entrada de sol y luminosidad natural. Tráfico despejado en la Circunvalar y Vía 40.")
    md.append("")
    md.append("---")
    md.append("")

    # SECTION V: Rental Application Protocol
    md.append("## 5. Protocolo de Arrendamiento y Documentación en Barranquilla")
    md.append("")
    md.append("Las inmobiliarias en Barranquilla tramitan las solicitudes de arrendamiento principalmente a través de aseguradoras como **Seguros Bolívar**, **Aseguradora El Libertador**, **Seguros Sura** o firmas afianzadoras (**FianzaCrédito / Unifianza**).")
    md.append("")
    md.append("### 📋 Requisitos Habituales:")
    md.append("1. **Solvencia Económica**: Arrendatario principal y codeudor deben demostrar ingresos mensuales netos equivalentes a **2.5 o 3 veces el valor total del canon + administración**.")
    md.append("2. **Documentación Arrendatario Empleado**:")
    md.append("   - Fotocopia de la cédula de ciudadanía al 150%.")
    md.append("   - Certificado laboral vigente (antigüedad, cargo, sueldo y tipo de contrato; vigencia no mayor a 30 días).")
    md.append("   - Tres (3) últimos desprendibles de nómina.")
    md.append("   - Tres (3) últimos extractos bancarios completos.")
    md.append("3. **Documentación Arrendatario Independiente / Prestador de Servicios**:")
    md.append("   - Fotocopia de cédula y RUT actualizado.")
    md.append("   - Tres (3) últimos extractos bancarios.")
    md.append("   - Declaración de renta del último año gravable y estados financieros con firma de contador público y tarjeta profesional.")
    md.append("4. **Codeudor o Fiador**:")
    md.append("   - Si se requiere finca raíz: Certificado de Tradición y Libertad reciente (no mayor a 30 días) de un inmueble libre de gravámenes o embargos (preferiblemente en el departamento del Atlántico o ciudades principales).")
    md.append("   - Si es codeudor con ingresos: Mismos documentos laborales y bancarios del arrendatario principal.")
    md.append("")
    md.append("---")
    md.append("*Dossier generado automáticamente por el motor de inteligencia inmobiliaria de Tracker Barranquilla.*")

    return "\n".join(md)


def main():
    root_dir = Path(__file__).resolve().parent
    data_file = root_dir / "data" / "inmuebles_barranquilla.json"
    output_md_file = root_dir / "DOSSIER_VISITAS.md"
    output_json_file = root_dir / "data" / "dossier_curado.json"

    print(f"[MFVI] Loading inventory from {data_file}...")
    if not data_file.exists():
        raise FileNotFoundError(f"Database file not found at {data_file}")

    with open(data_file, "r", encoding="utf-8") as f:
        all_properties = json.load(f)

    print(f"[MFVI] Total inventory loaded: {len(all_properties)} listings.")
    curated = select_curated_properties(all_properties, target_count=15)
    print(f"[MFVI] Curated top standout properties: {len(curated)}")

    for i, p in enumerate(curated, 1):
        ev = p["eval"]
        print(f"  #{i:2d}: [{ev['mfvi_score']:4.1f} pts] {p['id']:18s} | {p['neighborhood']:16s} | Total: {format_cop(p['total_price']):12s} | {p['bedrooms']}H/{p['bathrooms']}B | {ev['tier']}")

    # Generate Markdown
    md_content = generate_dossier_markdown(curated, total_db_count=len(all_properties))
    with open(output_md_file, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"[MFVI] Successfully generated dossier markdown at {output_md_file} ({len(md_content)} bytes)")

    # Export Curated JSON for Dashboard consumption
    export_data = {
        "generated_at": datetime.now().isoformat(),
        "total_curated": len(curated),
        "property_ids": [p["id"] for p in curated],
        "properties": [
            {
                "id": p["id"],
                "title": p.get("title"),
                "neighborhood": p.get("neighborhood"),
                "property_type": p.get("property_type"),
                "canon": p.get("canon"),
                "admin_fee": p.get("admin_fee"),
                "total_price": p.get("total_price"),
                "area_m2": p.get("area_m2"),
                "bedrooms": p.get("bedrooms"),
                "bathrooms": p.get("bathrooms"),
                "parking": p.get("parking"),
                "stratum": p.get("stratum"),
                "url": p.get("url"),
                "whatsapp_url": generate_whatsapp_url(p),
                "mfvi_score": p["eval"]["mfvi_score"],
                "tier": p["eval"]["tier"],
                "cost_per_m2": p["eval"]["cost_per_m2"]
            }
            for p in curated
        ]
    }
    with open(output_json_file, "w", encoding="utf-8") as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2)
    print(f"[MFVI] Successfully exported curated JSON at {output_json_file}")


if __name__ == "__main__":
    main()
