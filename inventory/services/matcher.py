"""
Maps a row from the daily consumption ticket export onto a Material in our
master list. The export gives us three-ish columns to work with:

    Materials  -> broad group: 'Dropwire', 'Router', 'IPTV'
    Category   -> for Dropwire, the length e.g. '100 Meter'
    Type       -> for Dropwire the connector 'APC/APC'/'APC/UPC';
                  for Router the band 'Dual Band'/'Single Band'/'Wifi 6';
                  for IPTV always 'Setup Box'
    ONTModel   -> the field that actually reveals refurbished/repaired
                  condition, e.g. 'Single Band Router-REF', 'Dual Band Router- REF',
                  '...-Repaired'. Contains 'REF' or 'Repaired' -> refurbished.

We match against Material.match_material_group / match_length_or_band /
match_connector / match_condition, which the admin sets up once against the
material master list (see management command seed_materials).
"""
import re


def normalize(text):
    return (text or "").strip().upper()


def extract_length(category_text):
    """'100 Meter' -> '100'   '2 Meter' -> '2' """
    if not category_text:
        return ""
    m = re.match(r"\s*(\d+)", category_text)
    return m.group(1) if m else ""


def is_refurbished(ont_model_text):
    t = normalize(ont_model_text)
    return "REF" in t or "REPAIR" in t


def classify_row(materials_text, category_text, type_text, ont_model_text):
    """Returns a dict describing the row's group/length/connector/condition,
    used both to build the Material.match_* hints and to match incoming rows.
    """
    group = normalize(materials_text)
    band_or_length = ""
    connector = ""
    condition = ""

    if group == "DROPWIRE":
        band_or_length = extract_length(category_text)
        connector = normalize(type_text)  # APC/APC or APC/UPC
    elif group == "ROUTER":
        band_or_length = normalize(type_text)  # DUAL BAND / SINGLE BAND / WIFI 6
        condition = "REFURBISHED" if is_refurbished(ont_model_text) else "NEW"
    elif group == "IPTV":
        band_or_length = normalize(type_text)  # SETUP BOX or REMOTE
        # ONTModel is unreliable for IPTV rows - it sometimes reflects a
        # router installed on the same ticket, not the IPTV box's own
        # condition, so we don't use it to guess refurbished status here.
        condition = ""

    return {
        "group": group,
        "band_or_length": band_or_length,
        "connector": connector,
        "condition": condition,
    }


def match_material(row, material_qs):
    """row: dict with keys materials, category, type, ont_model.
    material_qs: queryset/list of Material (should have match_* fields populated).
    Returns the matching Material instance, or None if nothing matches.
    """
    cls = classify_row(row.get("materials"), row.get("category"), row.get("type"), row.get("ont_model"))

    for m in material_qs:
        if normalize(m.match_material_group) != cls["group"]:
            continue
        if cls["group"] == "DROPWIRE":
            m_length = extract_length(m.match_length_or_band) or normalize(m.match_length_or_band)
            if m_length != cls["band_or_length"]:
                continue
            if m.match_connector and normalize(m.match_connector) != cls["connector"]:
                continue
            return m
        else:
            if normalize(m.match_length_or_band) != cls["band_or_length"]:
                continue
            if m.match_condition and m.match_condition != cls["condition"]:
                continue
            if not m.match_condition and cls["condition"] == "REFURBISHED":
                # material has no condition hint set - only match it to NEW rows
                continue
            return m
    return None
