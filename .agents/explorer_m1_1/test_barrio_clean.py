import re

def clean_barrio(raw):
    if not raw: return "Norte"
    s = raw.strip()
    # remove trailing/leading noise words
    patterns = [
        r'\bnoroccidente\b',
        r'\bnorte\b',
        r'\bbarranquilla\b',
        r'\bzona urbana\b',
        r'\bub\b\.?',
        r'\bbarrio\b',
        r'\bsector\b',
    ]
    for pat in patterns:
        s = re.sub(pat, '', s, flags=re.IGNORECASE)
    s = re.sub(r'[\(\),]', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    
    # map known variations
    s_lower = s.lower()
    if "mallorquin" in s_lower:
        return "Ciudad Mallorquín"
    if "villa carolina" in s_lower:
        return "Villa Carolina"
    if "villa santos" in s_lower:
        return "Villa Santos"
    if "villa country" in s_lower:
        return "Villa Country"
    if "alto prado" in s_lower:
        return "Alto Prado"
    if "golf" in s_lower:
        return "El Golf"
    if "altos de riomar" in s_lower:
        return "Altos de Riomar"
    if "riomar" in s_lower:
        return "Riomar"
    if "miramar" in s_lower:
        return "Miramar"
    if "campi" in s_lower:
        return "La Campiña"
    if "cumbre" in s_lower:
        return "La Cumbre"
    if "tabor" in s_lower:
        return "El Tabor"
    if "san vicente" in s_lower:
        return "San Vicente"
    if "paraiso" in s_lower:
        return "Paraíso"
    if "andalucia" in s_lower:
        return "Andalucía"
    if "alpes" in s_lower:
        return "Los Alpes"
    if "bellavista" in s_lower:
        return "Bellavista"
    if "prado" in s_lower:
        return "El Prado"
    if "limoncito" in s_lower:
        return "El Limoncito"
    if "buenavista" in s_lower:
        return "Buenavista"
        
    return s.title()

# Test on the sample names
test_names = [
    "Miramar Noroccidente", "Villa Carolina Noroccidente", "Ciudad de Mallorquin",
    "Barranquilla Villa Carolina", "Alto Prado Noroccidente", "Golf Alto Prado",
    "Altos de Riomar Noroccidente", "Barranquilla Ciudad de Mallorquin",
    "Horizontes de Miramar Noroccidente", "Ciudad Mallorquin Zona Urbana"
]
for tn in test_names:
    print(f"'{tn}' -> '{clean_barrio(tn)}'")
