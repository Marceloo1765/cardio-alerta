import streamlit as st
import pandas as pd
import pydeck as pdk
import json
from pathlib import Path
from datetime import datetime

# ============================================================
# NEOLINK - PROTOTIPO MVP OFFLINE FIRST
# Reto: Cardio Alerta Perú - cuidando corazones desde el primer latido
# Prototipo para hackatón. No es una herramienta clínica validada.
# ============================================================

LOCAL_FILE = Path("neolink_local.json")
CENTRAL_FILE = Path("neolink_central.json")
FACILITY_FILE = Path("neolink_facility.json")

ALTITUDE_OPTIONS = [
    "0–2499 m s. n. m.",
    "2500–3599 m s. n. m.",
    "3600–4500 m s. n. m.",
]

# Rangos de horas de vida del recién nacido
HOURS_LIFE_OPTIONS = [
    "0–12 horas de vida",
    "12–24 horas de vida",
    "24–48 horas de vida",
    "Más de 48 horas de vida",
]

# ============================================================
# CRITERIOS CLÍNICOS LATIDOSEGURO-CHD
# Complementa la oximetría (ANDES-CHD) cuando está disponible.
# Si no hay sensor neonatal, funciona como estratificación
# clínica pero NO sustituye el tamizaje por oximetría.
#
# Cada criterio es un dict con:
#   key      -> identificador interno
#   code     -> código clínico (M1..M5 / m1..m6)
#   label    -> nombre del criterio
#   how_to   -> guía de CÓMO EVALUARLO (se muestra ANTES de
#               ingresar los datos, igual que la oximetría)
#   kind     -> tipo de "calculadora" que se renderiza para que
#               el doctor ingrese valores y la app calcule el
#               resultado del criterio automáticamente:
#                 "cianosis"     -> observación + test de hiperoxia opcional
#                 "pulsos"       -> pulsos femoral/braquial + perfusión
#                 "shock"        -> llenado capilar + signos de hipoperfusión
#                 "silverman"    -> puntaje Silverman-Andersen (0–10)
#                 "taquicardia"  -> FC (lpm) + causa evidente descartada
#                 "checklist"    -> lista de signos (positivo si ≥1 marcado)
#                 "bool"         -> observación clínica directa Sí/No
#   options  -> (solo checklist) lista de signos a marcar
#   umbral_nota -> texto opcional con el umbral usado en el cálculo
# ============================================================

MAYOR_CRITERIA = [
    {
        "key": "cianosis", "code": "M1",
        "label": "Cianosis central persistente",
        "how_to": (
            "Observe la coloración de la lengua, la mucosa oral/labios "
            "y el tronco del recién nacido.\n\n"
            "Si está disponible y clínicamente corresponde, realice el "
            "**test de hiperoxia** con O₂ al 100% durante 10 minutos. "
            "Evalúe si la **PaO₂ (presión arterial de oxígeno)** es mayor "
            "después de los 10 minutos. No se registra SpO₂ en este paso. "
            "La ausencia del test **no descarta** cardiopatía por sí sola."
        ),
        "kind": "cianosis",
    },
    {
        "key": "pulsos", "code": "M2",
        "label": "Alteración de pulsos / perfusión diferencial",
        "how_to": (
            "Palpe los pulsos y registre la **frecuencia cardíaca en "
            "latidos por minuto (lpm)**. Por ejemplo: 100 lpm.\n\n"
            "Evalúe además la perfusión, color y temperatura, y registre "
            "los hallazgos clínicos observados."
        ),
        "kind": "pulsos",
    },
    {
        "key": "shock", "code": "M3",
        "label": "Signos de shock / hipoperfusión",
        "how_to": (
            "Mida el llenado capilar (presione la piel 5 s y cuente "
            "cuánto tarda en recuperar el color) y evalúe pulsos, "
            "color y temperatura.\n\n"
            "El criterio se calcula como positivo si el llenado "
            "capilar es >3 s, o si marca algún otro signo de "
            "hipoperfusión."
        ),
        "kind": "shock",
    },
    {
        "key": "distres", "code": "M4",
        "label": "Dificultad respiratoria significativa",
        "how_to": (
            "Evalúela objetivamente con el **Test de Silverman-"
            "Andersen (0–10)**, calificando cada ítem de 0 (ausente) "
            "a 2 (intenso):\n\n"
            "- Disociación toracoabdominal\n"
            "- Tiraje intercostal\n"
            "- Retracción xifoidea\n"
            "- Aleteo nasal\n"
            "- Quejido espiratorio\n\n"
            "LatidoSeguro suma el puntaje automáticamente e "
            "interpreta el resultado."
        ),
        "kind": "silverman",
        "umbral_nota": (
            "Se considera dificultad respiratoria significativa con "
            "puntaje ≥4 (moderada o severa). Umbral de prototipo, "
            "ajustable según protocolo institucional."
        ),
    },

]

MINOR_CRITERIA = [
    {
        "key": "soplo", "code": "m1",
        "label": "Soplo cardíaco",
        "how_to": (
            "Ausculte el corazón del recién nacido en un ambiente "
            "tranquilo.\n\n"
            "Marque este criterio si identifica un soplo cardíaco. "
            "Por su limitada especificidad en el RN, **no se "
            "considera mayor aisladamente**."
        ),
        "kind": "bool",
        "question": "¿Se ausculta soplo cardíaco?",
    },
    {
        "key": "taquicardia", "code": "m2",
        "label": "Taquicardia persistente",
        "how_to": (
            "Controle la frecuencia cardíaca (FC) en reposo, "
            "**descartando primero** llanto, fiebre u otra "
            "explicación evidente.\n\n"
            "Ingrese la FC medida; LatidoSeguro calcula si "
            "corresponde a taquicardia persistente."
        ),
        "kind": "taquicardia",
        "umbral_nota": (
            "Umbral de referencia: FC > 180 lpm en reposo, sin otra "
            "causa evidente. Ajustable según protocolo institucional."
        ),
    },
    {
        "key": "lactancia", "code": "m3",
        "label": "Alteración durante la lactancia",
        "how_to": (
            "Observe al recién nacido durante una toma y marque los "
            "signos que presente. LatidoSeguro considera el criterio "
            "positivo si hay al menos uno."
        ),
        "kind": "checklist",
        "options": [
            "Fatiga durante la toma",
            "Pausas frecuentes",
            "Mala succión",
            "Diaforesis (sudoración) excesiva",
        ],
    },
    {
        "key": "familiar", "code": "m4",
        "label": "Antecedente familiar",
        "how_to": (
            "Revise la historia familiar durante la anamnesis.\n\n"
            "Marque este criterio si hay cardiopatía congénita en un "
            "familiar de primer grado."
        ),
        "kind": "bool",
        "question": (
            "¿Hay cardiopatía congénita en un familiar de primer "
            "grado?"
        ),
    },
    {
        "key": "materno", "code": "m5",
        "label": "Factores de riesgo materno/prenatal",
        "how_to": (
            "Revise la historia prenatal materna.\n\n"
            "Marque este criterio si se identifican antecedentes "
            "maternos relevantes (por ejemplo, diabetes gestacional, "
            "infecciones, exposición a teratógenos, entre otros "
            "según protocolo institucional)."
        ),
        "kind": "bool",
        "question": (
            "¿Hay antecedentes maternos/prenatales relevantes?"
        ),
    },
    {
        "key": "sindrome", "code": "m6",
        "label": (
            "Fenotipo/síndrome asociado a cardiopatía congénita"
        ),
        "how_to": (
            "Realice el examen físico general del recién nacido.\n\n"
            "Marque este criterio si hay hallazgos físicos que hagan "
            "sospechar un síndrome con asociación conocida a "
            "cardiopatías congénitas."
        ),
        "kind": "bool",
        "question": (
            "¿Hay hallazgos físicos sugestivos de un síndrome "
            "asociado a cardiopatía congénita?"
        ),
    },
]

# Lista combinada para el asistente paso a paso: cada elemento
# lleva además el tipo ("mayor" / "menor") para poder clasificar
# al final del recorrido.
ALL_CRITERIA = (
    [dict(tipo="mayor", **c) for c in MAYOR_CRITERIA]
    + [dict(tipo="menor", **c) for c in MINOR_CRITERIA]
)

# ============================================================
# DEPARTAMENTOS DEL PERÚ
# ============================================================

PERU_DEPARTMENTS = {
    "Amazonas":       {"altitude_range": "0–2499 m s. n. m.",    "lat": -6.2297,  "lon": -77.8714},
    "Áncash":         {"altitude_range": "2500–3599 m s. n. m.", "lat": -9.5277,  "lon": -77.5279},
    "Apurímac":       {"altitude_range": "2500–3599 m s. n. m.", "lat": -13.6339, "lon": -72.8814},
    "Arequipa":       {"altitude_range": "2500–3599 m s. n. m.", "lat": -16.4090, "lon": -71.5375},
    "Ayacucho":       {"altitude_range": "2500–3599 m s. n. m.", "lat": -13.1588, "lon": -74.2239},
    "Cajamarca":      {"altitude_range": "2500–3599 m s. n. m.", "lat": -7.1637,  "lon": -78.5003},
    "Callao":         {"altitude_range": "0–2499 m s. n. m.",    "lat": -12.0566, "lon": -77.1181},
    "Cusco":          {"altitude_range": "2500–3599 m s. n. m.", "lat": -13.5319, "lon": -71.9675},
    "Huancavelica":   {"altitude_range": "3600–4500 m s. n. m.", "lat": -12.7864, "lon": -74.9758},
    "Huánuco":        {"altitude_range": "0–2499 m s. n. m.",    "lat": -9.9306,  "lon": -76.2422},
    "Ica":            {"altitude_range": "0–2499 m s. n. m.",    "lat": -14.0678, "lon": -75.7286},
    "Junín":          {"altitude_range": "2500–3599 m s. n. m.", "lat": -12.0653, "lon": -75.2049},
    "La Libertad":    {"altitude_range": "0–2499 m s. n. m.",    "lat": -8.1116,  "lon": -79.0288},
    "Lambayeque":     {"altitude_range": "0–2499 m s. n. m.",    "lat": -6.7011,  "lon": -79.9061},
    "Lima":           {"altitude_range": "0–2499 m s. n. m.",    "lat": -12.0464, "lon": -77.0428},
    "Loreto":         {"altitude_range": "0–2499 m s. n. m.",    "lat": -3.7437,  "lon": -73.2516},
    "Madre de Dios":  {"altitude_range": "0–2499 m s. n. m.",    "lat": -12.5933, "lon": -69.1891},
    "Moquegua":       {"altitude_range": "2500–3599 m s. n. m.", "lat": -17.1938, "lon": -70.9347},
    "Pasco":          {"altitude_range": "3600–4500 m s. n. m.", "lat": -10.6828, "lon": -76.2569},
    "Piura":          {"altitude_range": "0–2499 m s. n. m.",    "lat": -5.1945,  "lon": -80.6328},
    "Puno":           {"altitude_range": "3600–4500 m s. n. m.", "lat": -15.8402, "lon": -70.0219},
    "San Martín":     {"altitude_range": "0–2499 m s. n. m.",    "lat": -6.4870,  "lon": -76.3654},
    "Tacna":          {"altitude_range": "0–2499 m s. n. m.",    "lat": -18.0146, "lon": -70.2536},
    "Tumbes":         {"altitude_range": "0–2499 m s. n. m.",    "lat": -3.5669,  "lon": -80.4515},
    "Ucayali":        {"altitude_range": "0–2499 m s. n. m.",    "lat": -8.3791,  "lon": -74.5539},
}


# ============================================================
# PERSISTENCIA
# ============================================================

def load_json(path, default):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default
    return default


def save_json(path, data):
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


# ============================================================
# ESTADO INICIAL
# ============================================================

if "local_cases" not in st.session_state:
    st.session_state.local_cases = load_json(LOCAL_FILE, [])

if "central_cases" not in st.session_state:
    st.session_state.central_cases = load_json(CENTRAL_FILE, [])

if "facility" not in st.session_state:
    st.session_state.facility = load_json(FACILITY_FILE, None)

if "screen" not in st.session_state:
    st.session_state.screen = (
        "Inicio"
        if st.session_state.facility
        else "Configuración"
    )

if "connection" not in st.session_state:
    st.session_state.connection = False

if "current_case" not in st.session_state:
    st.session_state.current_case = None

if "result" not in st.session_state:
    st.session_state.result = None

if "history_next_screen" not in st.session_state:
    st.session_state.history_next_screen = "Inicio"

if "history_record" not in st.session_state:
    st.session_state.history_record = None


# ============================================================
# CONFIGURACIÓN DE PÁGINA
# ============================================================

st.set_page_config(
    page_title="NeoLink",
    page_icon="❤️",
    layout="centered"
)


# ============================================================
# ESTILOS
# ============================================================

st.markdown("""
<style>

:root {
    --nl-cyan: #0DD7ED;
    --nl-blue: #0785F3;
    --nl-navy: #042048;
}

.block-container {
    max-width: 850px;
    padding-top: 2rem;
}

.big-title {
    font-size: 34px;
    font-weight: 700;
    margin-bottom: 0;
    color: var(--nl-navy);
}

.subtitle {
    font-size: 18px;
    color: var(--nl-blue);
    font-weight: 600;
    margin-bottom: 25px;
}

.brand-banner {
    background: linear-gradient(
        135deg,
        var(--nl-navy) 0%,
        var(--nl-blue) 100%
    );
    color: #ffffff;
    padding: 14px 16px;
    border-radius: 10px;
    font-weight: 700;
    font-size: 20px;
    margin-bottom: 6px;
}

.brand-banner span {
    color: var(--nl-cyan);
}

.status-online {
    padding: 8px 12px;
    border-radius: 8px;
    background: var(--nl-cyan);
    color: var(--nl-navy);
    font-weight: 700;
    border: 1px solid var(--nl-blue);
}

.status-offline {
    padding: 8px 12px;
    border-radius: 8px;
    background: #FFE9A8;
    color: #5C4200;
    font-weight: 700;
    border: 1px solid #D9A400;
}

.result-green {
    padding: 25px;
    border-radius: 12px;
    background: #E4F8EA;
    border: 2px solid #2E9E4B;
    color: #14532D;
}

.result-yellow {
    padding: 25px;
    border-radius: 12px;
    background: #FFF3CD;
    border: 2px solid #C98A00;
    color: #5C4200;
}

.result-red {
    padding: 25px;
    border-radius: 12px;
    background: #FCE4E4;
    border: 2px solid #D9534F;
    color: #7A1212;
}

.result-green h2,
.result-yellow h2,
.result-red h2 {
    margin-top: 0;
}

.card {
    padding: 20px;
    border-radius: 12px;
    border: 1px solid var(--nl-cyan);
    margin-bottom: 15px;
    background: #F5FCFE;
    color: var(--nl-navy);
}

.small {
    color: #4A5A70;
    font-size: 14px;
}

.step-box {
    background: #EAF6FC;
    border-left: 5px solid var(--nl-blue);
    color: var(--nl-navy);
    padding: 16px 18px;
    border-radius: 8px;
    font-size: 15.5px;
    line-height: 1.7;
}

.criteria-code {
    display: inline-block;
    background: var(--nl-navy);
    color: #ffffff;
    padding: 3px 10px;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 700;
    margin-right: 8px;
}

.criteria-code.minor {
    background: var(--nl-blue);
}

.history-section h4 {
    color: var(--nl-navy);
    border-bottom: 2px solid var(--nl-cyan);
    padding-bottom: 4px;
    margin-top: 18px;
}

.altitude-badge {
    display: inline-block;
    background: var(--nl-navy);
    color: #ffffff;
    padding: 8px 14px;
    border-radius: 8px;
    font-size: 15px;
}

.altitude-badge b {
    color: var(--nl-cyan);
}

.ambulance-box {
    background: #7A1212;
    color: #ffffff;
    padding: 16px;
    border-radius: 10px;
    text-align: center;
    font-weight: 700;
    margin-top: 10px;
}

button[kind="primary"],
.stButton > button[kind="primary"] {
    background-color: var(--nl-blue) !important;
    color: #ffffff !important;
    border: none !important;
}

button[kind="primary"]:hover {
    background-color: var(--nl-navy) !important;
    color: #ffffff !important;
}

section[data-testid="stSidebar"] {
    background-color: #F5FCFE;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# FUNCIONES DE NAVEGACIÓN
# ============================================================

def go(screen):
    st.session_state.screen = screen
    st.rerun()


def get_altitude_group():
    return st.session_state.facility["altitude_range"]


# ============================================================
# MOTOR DE DECISIÓN LOCAL
# ============================================================

def evaluate_screening(pre, post, altitude_group):

    diff = abs(pre - post)

    if altitude_group == "0–2499 m s. n. m.":

        positive_cutoff = 90
        negative_cutoff = 95

    elif altitude_group == "2500–3599 m s. n. m.":

        positive_cutoff = 87
        negative_cutoff = 90

    else:

        positive_cutoff = 85
        negative_cutoff = 89

    if pre < positive_cutoff or post < positive_cutoff:
        return "POSITIVO", diff

    if (
        pre >= negative_cutoff
        and post >= negative_cutoff
        and diff < 3
    ):
        return "NEGATIVO", diff

    return "REPETIR", diff


# ============================================================
# CLASIFICACIÓN CLÍNICA LATIDOSEGURO-CHD (SIN OXÍMETRO)
# ============================================================
#
# 🔴 ALTO RIESGO:      ≥1 criterio MAYOR
# 🟡 RIESGO INTERMEDIO: 0 mayores + ≥2 criterios MENORES
# 🟢 BAJO RIESGO:       0 mayores + 0–1 criterio MENOR
#
# El resultado se mapea al mismo vocabulario POSITIVO / REPETIR /
# NEGATIVO que usa el resto de la app para no duplicar lógica en
# Pendientes, Alertas y Dashboard.

def classify_clinical_only(n_mayores, n_menores):

    if n_mayores >= 1:
        return (
            "POSITIVO",
            "🔴 Alto riesgo clínico — CARDIO ALERTA ACTIVADA"
        )

    if n_menores >= 2:
        return (
            "REPETIR",
            "🟡 Sospecha de riesgo — considerar referencia y evaluación"
        )

    return (
        "NEGATIVO",
        "🟢 Bajo riesgo clínico — seguimiento habitual"
    )


# ============================================================
# COMBINACIÓN ANDES-CHD (OXIMETRÍA) + CRITERIOS CLÍNICOS
# ============================================================
#
# Cuando sí hay sensor, el resultado de oximetría (ANDES-CHD) se
# combina con los criterios clínicos LatidoSeguro. Las filas
# marcadas con * son reglas propuestas por LatidoSeguro, aún
# pendientes de validación clínica prospectiva.

def combine_andes_clinical(andes_result, n_mayores, n_menores):

    if andes_result == "POSITIVO":
        return (
            "POSITIVO",
            "🔴 Alto riesgo — SpO2 positiva (ANDES-CHD)"
        )

    if andes_result == "REPETIR":

        if n_mayores >= 1:
            return (
                "POSITIVO",
                "🔴 Alto riesgo — SpO2 intermedia + criterio clínico mayor"
            )

        if n_menores >= 2:
            return (
                "POSITIVO",
                "🔴 Alto riesgo* — SpO2 intermedia + ≥2 criterios menores"
            )

        return (
            "REPETIR",
            "🟡 Repetir SpO2 según protocolo"
        )

    # andes_result == "NEGATIVO"

    if n_mayores >= 1:
        return (
            "REPETIR",
            "🟡 Riesgo clínico / interconsulta — "
            "criterio mayor pese a SpO2 negativa"
        )

    if n_menores >= 3:
        return (
            "REPETIR",
            "🟡 Riesgo clínico / interconsulta* — ≥3 criterios menores"
        )

    return (
        "NEGATIVO",
        "🟢 Bajo riesgo"
    )


# ============================================================
# CALCULADORAS DE CRITERIOS CLÍNICOS LATIDOSEGURO-CHD
# ============================================================
#
# Cada función recibe:
#   - key: identificador interno del criterio (para las keys de
#     los widgets de Streamlit)
#   - stored: dict con los valores previamente ingresados (para
#     que "Anterior"/"Siguiente" no borre lo ya escrito)
#
# Cada función DEVUELVE (positivo, detalle, raw):
#   - positivo: bool ya calculado por la app (no lo decide el
#     doctor a ojo, se deriva de los valores ingresados)
#   - detalle:  texto corto con el cálculo, para trazabilidad
#   - raw:      dict con los valores crudos ingresados (se guarda
#               para poder editarlos después)

def render_calc_cianosis(key, stored):

    observado = st.radio(
        "¿Observa cianosis central (lengua, mucosa oral/labios o "
        "tronco)?",
        ["No", "Sí"],
        index=1 if stored.get("observado") else 0,
        key=f"{key}_obs",
        horizontal=True
    )

    st.write("")

    realizado = st.checkbox(
        "Se realizó test de hiperoxia con O₂ al 100% durante 10 minutos",
        value=stored.get("hiperoxia_realizado", False),
        key=f"{key}_hip"
    )

    pao2_mayor = stored.get("pao2_mayor")

    if realizado:
        pao2_mayor = st.radio(
            "Después de 10 minutos, ¿la PaO₂ es mayor?",
            ["No", "Sí"],
            index=1 if stored.get("pao2_mayor") is True else 0,
            key=f"{key}_pao2",
            horizontal=True
        ) == "Sí"

        st.caption(
            "PaO₂ = presión arterial de oxígeno. En este paso no se registra "
            "la saturación (SpO₂)."
        )

    positive = (observado == "Sí")

    detail = (
        "Cianosis central observada"
        if positive
        else "Sin cianosis central observada"
    )

    if realizado:
        detail += (
            " · Test de hiperoxia 10 min: PaO₂ mayor"
            if pao2_mayor
            else " · Test de hiperoxia 10 min: PaO₂ no mayor"
        )

    raw = {
        "observado": positive,
        "hiperoxia_realizado": realizado,
        "pao2_mayor": pao2_mayor,
    }

    st.caption(
        ("🔴 Cálculo del criterio: POSITIVO" if positive
         else "🟢 Cálculo del criterio: NEGATIVO")
        + f" — {detail}"
    )

    return positive, detail, raw


def render_calc_pulsos(key, stored):

    fc = st.number_input(
        "Frecuencia cardíaca (latidos por minuto)",
        min_value=0, max_value=300,
        value=int(stored.get("fc", 100)),
        step=1,
        key=f"{key}_fc"
    )

    diff_perf = st.checkbox(
        "Diferencia evidente de perfusión, color o temperatura "
        "entre extremidades superiores e inferiores",
        value=stored.get("diff_perf", False),
        key=f"{key}_diff"
    )

    pulsos_alterados = st.radio(
        "¿Se observan pulsos femorales ausentes o marcadamente disminuidos?",
        ["No", "Sí"],
        index=1 if stored.get("pulsos_alterados") else 0,
        key=f"{key}_alt",
        horizontal=True
    ) == "Sí"

    positive = pulsos_alterados or diff_perf

    detail = (
        f"FC: {fc} lpm · Pulsos femorales alterados: "
        f"{'Sí' if pulsos_alterados else 'No'} · "
        f"Diferencia de perfusión: {'Sí' if diff_perf else 'No'}"
    )

    st.caption(
        ("🔴 Cálculo del criterio: POSITIVO" if positive
         else "🟢 Cálculo del criterio: NEGATIVO")
        + f" — {detail}"
    )

    raw = {
        "fc": fc,
        "pulsos_alterados": pulsos_alterados,
        "diff_perf": diff_perf,
    }

    return positive, detail, raw


def render_calc_shock(key, stored):

    llenado = st.number_input(
        "Llenado capilar (segundos)",
        min_value=0.0, max_value=10.0,
        value=float(stored.get("llenado", 2.0)),
        step=0.5,
        key=f"{key}_llen"
    )

    pulsos_debiles = st.checkbox(
        "Pulsos débiles generalizados",
        value=stored.get("pulsos_debiles", False),
        key=f"{key}_pd"
    )

    palidez = st.checkbox(
        "Palidez / color grisáceo",
        value=stored.get("palidez", False),
        key=f"{key}_pal"
    )

    frias = st.checkbox(
        "Extremidades frías",
        value=stored.get("frias", False),
        key=f"{key}_fr"
    )

    positive = (
        llenado > 3
        or pulsos_debiles
        or palidez
        or frias
    )

    signos = []
    if llenado > 3:
        signos.append(f"llenado capilar {llenado:g}s (>3s)")
    if pulsos_debiles:
        signos.append("pulsos débiles")
    if palidez:
        signos.append("palidez/grisáceo")
    if frias:
        signos.append("extremidades frías")

    detail = (
        "Signos presentes: " + ", ".join(signos)
        if signos
        else f"Sin signos de hipoperfusión (llenado capilar {llenado:g}s)"
    )

    st.caption(
        ("🔴 Cálculo del criterio: POSITIVO" if positive
         else "🟢 Cálculo del criterio: NEGATIVO")
        + f" — {detail}"
    )

    raw = {
        "llenado": llenado,
        "pulsos_debiles": pulsos_debiles,
        "palidez": palidez,
        "frias": frias,
    }

    return positive, detail, raw


def render_calc_silverman(key, stored):

    items = [
        "Disociación toracoabdominal",
        "Tiraje intercostal",
        "Retracción xifoidea",
        "Aleteo nasal",
        "Quejido espiratorio",
    ]

    st.write(
        "Puntúe cada ítem (0 = ausente · 1 = leve · 2 = intenso):"
    )

    scores = []

    for i, item in enumerate(items):

        val = st.select_slider(
            item,
            options=[0, 1, 2],
            value=stored.get(f"item_{i}", 0),
            key=f"{key}_it{i}"
        )

        scores.append(val)

    total = sum(scores)

    st.metric("Puntaje total Silverman-Andersen", f"{total} / 10")

    if total == 0:
        interp = "Sin dificultad respiratoria"
    elif total <= 3:
        interp = "Dificultad leve"
    elif total <= 6:
        interp = "Dificultad moderada"
    else:
        interp = "Dificultad severa"

    positive = total >= 4

    detail = f"Silverman-Andersen = {total}/10 ({interp})"

    st.caption(
        ("🔴 Cálculo del criterio: POSITIVO" if positive
         else "🟢 Cálculo del criterio: NEGATIVO")
        + f" — {detail}"
    )

    raw = {f"item_{i}": scores[i] for i in range(len(items))}
    raw["total"] = total

    return positive, detail, raw


def render_calc_taquicardia(key, stored):

    fc = st.number_input(
        "Frecuencia cardíaca en reposo (lpm)",
        min_value=60, max_value=300,
        value=int(stored.get("fc", 150)),
        key=f"{key}_fc"
    )

    descartado = st.checkbox(
        "Se descartó llanto, fiebre u otra causa evidente",
        value=stored.get("descartado", False),
        key=f"{key}_desc"
    )

    umbral = 180

    positive = descartado and fc > umbral

    detail = (
        f"FC {fc} lpm · causa evidente descartada: "
        f"{'Sí' if descartado else 'No'} (umbral {umbral} lpm)"
    )

    st.caption(
        ("🔴 Cálculo del criterio: POSITIVO" if positive
         else "🟢 Cálculo del criterio: NEGATIVO")
        + f" — {detail}"
    )

    raw = {"fc": fc, "descartado": descartado}

    return positive, detail, raw


def render_calc_checklist(key, stored, options):

    selected = []

    for i, opt in enumerate(options):

        checked = st.checkbox(
            opt,
            value=stored.get(f"opt_{i}", False),
            key=f"{key}_c{i}"
        )

        if checked:
            selected.append(opt)

    positive = len(selected) >= 1

    detail = (
        "Signos presentes: " + ", ".join(selected)
        if selected
        else "Sin signos presentes"
    )

    st.caption(
        ("🔴 Cálculo del criterio: POSITIVO" if positive
         else "🟢 Cálculo del criterio: NEGATIVO")
        + f" — {detail}"
    )

    raw = {
        f"opt_{i}": (options[i] in selected)
        for i in range(len(options))
    }

    return positive, detail, raw


def render_calc_bool(key, stored, question):

    ans = st.radio(
        question,
        ["No", "Sí"],
        index=1 if stored.get("presente") else 0,
        key=f"{key}_b",
        horizontal=True
    )

    positive = (ans == "Sí")
    detalle_extra = stored.get("detalle_extra", "")

    if positive and key in {"soplo", "familiar", "sindrome"}:
        detalle_label = {
            "soplo": "¿Cuál es el soplo / hallazgo auscultatorio?",
            "familiar": "¿Cuál es el familiar de primer grado con cardiopatía congénita?",
            "sindrome": "¿Cuál es el síndrome o hallazgo sugestivo?",
        }[key]

        detalle_extra = st.text_input(
            detalle_label,
            value=detalle_extra,
            key=f"{key}_detalle"
        )

    if positive:
        detail = "Presente"
        if detalle_extra:
            detail += f" · Detalle: {detalle_extra}"
    else:
        detail = "Ausente"

    raw = {
        "presente": positive,
        "detalle_extra": detalle_extra,
    }

    return positive, detail, raw


def render_criterion_calculator(crit, stored):
    """Despacha al renderizador correcto según crit['kind'] y
    devuelve (positivo, detalle, raw)."""

    kind = crit["kind"]
    key = crit["key"]

    if kind == "cianosis":
        return render_calc_cianosis(key, stored)

    if kind == "pulsos":
        return render_calc_pulsos(key, stored)

    if kind == "shock":
        return render_calc_shock(key, stored)

    if kind == "silverman":
        return render_calc_silverman(key, stored)

    if kind == "taquicardia":
        return render_calc_taquicardia(key, stored)

    if kind == "checklist":
        return render_calc_checklist(key, stored, crit["options"])

    # kind == "bool" (por defecto)
    question = crit.get(
        "question", "¿El criterio está presente?"
    )
    return render_calc_bool(key, stored, question)


# ============================================================
# MEDICIONES
# ============================================================

def new_measurement_entry(pre, post, result, diff):

    return {
        "preductal": pre,
        "postductal": post,
        "difference": diff,
        "result": result,
        "timestamp": datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        ),
    }


# ============================================================
# CONSTRUCCIÓN DE CASO
# ============================================================

def build_case_record(case, result):

    now = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    has_sensor = case.get("has_sensor", True)

    measurements = case.get("measurements", [])

    last = (
        measurements[-1]
        if measurements
        else None
    )

    return {
        "case_id": case["case_id"],
        "rn_id": case["rn_id"],
        "gestational_age": case["gestational_age"],
        "hours_life": case["hours_life"],
        "registered_at": case.get("registered_at", now),

        "facility": st.session_state.facility["name"],
        "location": st.session_state.facility["location"],
        "altitude": st.session_state.facility["altitude_range"],

        "has_sensor": has_sensor,

        "preductal": last["preductal"] if last else None,
        "postductal": last["postductal"] if last else None,
        "difference": last["difference"] if last else None,

        "measurements": measurements,
        "repeat_count": max(len(measurements) - 1, 0),

        "andes_result": case.get("andes_result"),

        "clinical_mayores": case.get("clinical_mayores", []),
        "clinical_menores": case.get("clinical_menores", []),
        "clinical_details": case.get("clinical_details", {}),
        "risk_label": case.get("risk_label", ""),

        "result": result,
        "timestamp": now,

        "sync_status": (
            "SINCRONIZADO"
            if st.session_state.connection
            else "PENDIENTE"
        ),

        "orientation_done": case.get(
            "orientation_done",
            False
        ),

        "booklet_delivered": case.get(
            "booklet_delivered",
            False
        ),

        "teleorientacion": case.get(
            "teleorientacion"
        ),

        "referencia_iniciada": case.get(
            "referencia_iniciada",
            False
        ),

        "traslado_registrado": case.get(
            "traslado_registrado",
            False
        ),

        "atencion_especializada": case.get(
            "atencion_especializada",
            False
        ),
    }


# ============================================================
# GUARDAR / ACTUALIZAR LOCAL
# ============================================================

def upsert_local(case_record):

    ids = {
        c["case_id"]: i
        for i, c in enumerate(
            st.session_state.local_cases
        )
    }

    if case_record["case_id"] in ids:

        st.session_state.local_cases[
            ids[case_record["case_id"]]
        ] = case_record

    else:

        st.session_state.local_cases.append(
            case_record
        )

    save_json(
        LOCAL_FILE,
        st.session_state.local_cases
    )


# ============================================================
# SINCRONIZACIÓN
# ============================================================

def sync_cases():

    pending = [
        c
        for c in st.session_state.local_cases
        if c.get("sync_status") == "PENDIENTE"
    ]

    existing_ids = {
        c["case_id"]
        for c in st.session_state.central_cases
    }

    for case in pending:

        case["sync_status"] = "SINCRONIZADO"

        if case["case_id"] in existing_ids:

            idx = next(
                i
                for i, c in enumerate(
                    st.session_state.central_cases
                )
                if c["case_id"] == case["case_id"]
            )

            st.session_state.central_cases[idx] = case

        else:

            st.session_state.central_cases.append(
                case
            )

            existing_ids.add(
                case["case_id"]
            )

    save_json(
        LOCAL_FILE,
        st.session_state.local_cases
    )

    save_json(
        CENTRAL_FILE,
        st.session_state.central_cases
    )

    return len(pending)


# ============================================================
# OBTENER TODOS LOS CASOS PARA DASHBOARD
# ============================================================

def get_all_cases():

    cases_dict = {}

    # Primero los centralizados
    for case in st.session_state.central_cases:

        cases_dict[
            case["case_id"]
        ] = case

    # Luego los locales.
    # Si existe en ambos, el local tiene prioridad
    # porque puede contener información más reciente.
    for case in st.session_state.local_cases:

        cases_dict[
            case["case_id"]
        ] = case

    return list(cases_dict.values())


# ============================================================
# HISTORIA CLÍNICA (RESUMEN FINAL PARA TODOS LOS RESULTADOS)
# ============================================================

def render_historia_clinica(record, next_screen, next_label):

    st.title("🗂️ Historia clínica del tamizaje")

    st.caption(
        "Resumen final del caso. Se genera automáticamente al "
        "cerrar el tamizaje, sin importar el resultado."
    )

    result = record.get("result", "")

    badge = {
        "NEGATIVO": ("🟢 NEGATIVO", "result-green"),
        "REPETIR": ("🟡 REPETIR", "result-yellow"),
        "POSITIVO": ("🔴 POSITIVO", "result-red"),
    }.get(result, (result, "card"))

    st.markdown(
        f'<div class="{badge[1]}"><h2>{badge[0]}</h2></div>',
        unsafe_allow_html=True
    )

    st.write("")

    st.markdown('<div class="history-section">', unsafe_allow_html=True)

    st.markdown("#### 🧾 Datos generales")

    g1, g2 = st.columns(2)

    with g1:
        st.write(f"**RN:** {record.get('rn_id', '—')}")
        st.write(f"**Caso:** {record.get('case_id', '—')}")
        st.write(
            f"**Edad gestacional:** "
            f"{record.get('gestational_age', '—')} semanas"
        )
        st.write(f"**Horas de vida:** {record.get('hours_life', '—')}")

    with g2:
        st.write(f"**Establecimiento:** {record.get('facility', '—')}")
        st.write(f"**Ubicación:** {record.get('location', '—')}")
        st.write(f"**Altitud:** {record.get('altitude', '—')}")
        st.write(
            f"**Registrado:** {record.get('registered_at', '—')}"
        )

    st.markdown("#### 🩺 Tamizaje por oximetría (ANDES-CHD)")

    if record.get("has_sensor", True) and record.get("preductal") is not None:

        m1, m2, m3 = st.columns(3)
        m1.metric("Preductal", f"{record['preductal']}%")
        m2.metric("Posductal", f"{record['postductal']}%")
        m3.metric("Diferencia", f"{record['difference']:.0f}%")

        st.caption(
            f"Resultado ANDES-CHD: {record.get('andes_result', '—')} · "
            f"Repeticiones realizadas: {record.get('repeat_count', 0)}"
        )

        measurements = record.get("measurements", [])

        if len(measurements) > 1:

            with st.expander("Ver todas las mediciones"):

                for i, m in enumerate(measurements, start=1):

                    st.write(
                        f'#{i} — Preductal {m["preductal"]}% · '
                        f'Posductal {m["postductal"]}% · '
                        f'Diferencia {m["difference"]:.0f}% · '
                        f'{m["result"]} · {m["timestamp"]}'
                    )

    else:

        st.info(
            "No se realizó tamizaje por oximetría — sin sensor "
            "neonatal disponible. Se usó evaluación clínica "
            "LatidoSeguro-CHD como estratificación de riesgo."
        )

    st.markdown("#### 🫀 Evaluación clínica LatidoSeguro-CHD")

    mayor_info = {c["key"]: c for c in MAYOR_CRITERIA}
    minor_info = {c["key"]: c for c in MINOR_CRITERIA}

    mayores = record.get("clinical_mayores", [])
    menores = record.get("clinical_menores", [])
    details = record.get("clinical_details", {})

    if mayores or menores:

        if mayores:
            st.write("**Criterios mayores presentes:**")
            for k in mayores:
                info = mayor_info.get(k)
                if info:
                    det = details.get(k)
                    line = f"- `{info['code']}` {info['label']}"
                    if det:
                        line += f" — {det}"
                    st.write(line)
        else:
            st.write("**Criterios mayores presentes:** ninguno")

        if menores:
            st.write("**Criterios menores presentes:**")
            for k in menores:
                info = minor_info.get(k)
                if info:
                    det = details.get(k)
                    line = f"- `{info['code']}` {info['label']}"
                    if det:
                        line += f" — {det}"
                    st.write(line)
        else:
            st.write("**Criterios menores presentes:** ninguno")

    else:

        st.write("No se registró evaluación clínica de criterios.")

    if record.get("risk_label"):
        st.info(f"**Clasificación LatidoSeguro-CHD:** {record['risk_label']}")

    st.markdown("#### 📋 Seguimiento y educación")

    if result == "NEGATIVO":
        st.write(
            f"Orientación a padres/cuidadores realizada: "
            f"{'Sí' if record.get('orientation_done') else 'No'}"
        )
        st.write(
            f"Cartilla entregada: "
            f"{'Sí' if record.get('booklet_delivered') else 'No'}"
        )

    if record.get("teleorientacion"):
        st.write(f"Teleorientación: {record['teleorientacion']}")

    if result == "POSITIVO":
        st.write(
            f"Referencia iniciada: "
            f"{'Sí' if record.get('referencia_iniciada') else 'No'}"
        )
        st.write(
            f"Traslado registrado: "
            f"{'Sí' if record.get('traslado_registrado') else 'No'}"
        )
        st.write(
            f"Atención especializada: "
            f"{'Sí' if record.get('atencion_especializada') else 'No'}"
        )

    st.markdown("#### ☁️ Registro")

    st.write(f"Estado de sincronización: {record.get('sync_status', '—')}")
    st.write(f"Fecha/hora de cierre: {record.get('timestamp', '—')}")

    st.markdown('</div>', unsafe_allow_html=True)

    st.write("")

    if st.button(
        f"Continuar ➜ {next_label}",
        type="primary",
        use_container_width=True
    ):
        st.session_state.history_record = None
        st.session_state.current_case = None
        go(next_screen)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.markdown(
        '<div class="brand-banner">'
        '❤️ NEO<span>LINK</span>'
        '</div>',
        unsafe_allow_html=True
    )

    st.caption(
        "MVP Offline First — Cardio Alerta Perú"
    )

    st.divider()

    if st.session_state.connection:

        st.markdown(
            '<div class="status-online">'
            '● CON INTERNET'
            '</div>',
            unsafe_allow_html=True
        )

    else:

        st.markdown(
            '<div class="status-offline">'
            '● MODO OFFLINE'
            '</div>',
            unsafe_allow_html=True
        )

    st.write("")

    if st.session_state.facility:

        nav_disabled = False

    else:

        nav_disabled = True

        st.caption(
            "⚠️ Configure el establecimiento para continuar."
        )

    if st.button(
        "Inicio",
        use_container_width=True,
        disabled=nav_disabled
    ):
        go("Inicio")

    if st.button(
        "Nuevo tamizaje",
        use_container_width=True,
        disabled=nav_disabled
    ):
        go("Nuevo tamizaje")

    if st.button(
        "Tamizajes pendientes",
        use_container_width=True,
        disabled=nav_disabled
    ):
        go("Pendientes")

    if st.button(
        "NeoLink Alertas",
        use_container_width=True,
        disabled=nav_disabled
    ):
        go("Alertas")

    if st.button(
        "Dashboard",
        use_container_width=True,
        disabled=nav_disabled
    ):
        go("Dashboard")

    if st.button(
        "⚙️ Configuración del establecimiento",
        use_container_width=True
    ):
        go("Configuración")

    st.divider()

    st.markdown("### Conectividad")

    if st.button(
        "Activar internet"
        if not st.session_state.connection
        else "Simular pérdida de internet",
        use_container_width=True
    ):

        st.session_state.connection = (
            not st.session_state.connection
        )

        st.rerun()

    pending_count = len([
        c
        for c in st.session_state.local_cases
        if c.get("sync_status") == "PENDIENTE"
    ])

    st.caption(
        f"Registros locales pendientes de sincronizar: "
        f"{pending_count}"
    )

    if (
        st.session_state.connection
        and pending_count
    ):

        if st.button(
            "☁️ Sincronizar ahora",
            use_container_width=True
        ):

            n = sync_cases()

            st.success(
                f"{n} caso(s) sincronizado(s) "
                "con NeoLink Cloud."
            )

            st.rerun()


# ============================================================
# CONFIGURACIÓN
# ============================================================

if st.session_state.screen == "Configuración":

    st.markdown(
        '<div class="big-title">'
        '⚙️ Configuración del establecimiento'
        '</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="subtitle">'
        'Este paso solo se realiza una vez, en la primera configuración.'
        '</div>',
        unsafe_allow_html=True
    )

    existing = (
        st.session_state.facility
        or {}
    )

    dept_names = list(
        PERU_DEPARTMENTS.keys()
    )

    st.markdown(
        '<div class="step-box">'
        '💡 Paso 1: elija el <b>departamento</b> donde se '
        'encuentra el establecimiento. La <b>altitud se calcula '
        'automáticamente</b> y con ella la app elige las reglas '
        'correctas de tamizaje.'
        '</div>',
        unsafe_allow_html=True
    )

    st.write("")

    dept_default = (
        existing.get("location")
        if existing.get("location")
        in dept_names
        else dept_names[0]
    )

    location = st.selectbox(
        "📍 Departamento",
        dept_names,
        index=dept_names.index(
            dept_default
        )
    )

    auto_altitude = (
        PERU_DEPARTMENTS[location]
        ["altitude_range"]
    )

    st.markdown(
        f'<div class="altitude-badge">'
        f'⛰️ Altitud asignada automáticamente: '
        f'<b>{auto_altitude}</b>'
        f'</div>',
        unsafe_allow_html=True
    )

    st.write("")

    with st.form("facility_form"):

        name = st.text_input(
            "🏥 Nombre del establecimiento de salud",
            value=existing.get("name", "")
        )

        identifier = st.text_input(
            "🔑 Identificador / código del establecimiento",
            value=existing.get("identifier", "")
        )

        submitted = st.form_submit_button(
            "✅ Guardar información localmente",
            type="primary"
        )

    if submitted:

        if not name or not identifier:

            st.error(
                "Complete todos los campos antes de guardar."
            )

        else:

            st.session_state.facility = {
                "name": name,
                "location": location,
                "altitude_range": auto_altitude,
                "identifier": identifier,
            }

            save_json(
                FACILITY_FILE,
                st.session_state.facility
            )

            st.success(
                "Establecimiento guardado localmente."
            )

            go("Inicio")


# ============================================================
# INICIO
# ============================================================

elif st.session_state.screen == "Inicio":

    st.markdown(
        '<div class="big-title">❤️ NEOLINK</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="subtitle">'
        'Tamizaje neonatal · MVP Offline First'
        '</div>',
        unsafe_allow_html=True
    )

    c1, c2 = st.columns(2)

    with c1:

        st.markdown("### Establecimiento")

        st.write(
            st.session_state.facility["name"]
        )

        st.write(
            st.session_state.facility["location"]
        )

        st.write(
            st.session_state.facility[
                "altitude_range"
            ]
        )

    with c2:

        st.markdown("### Estado")

        if st.session_state.connection:

            st.success(
                "Internet disponible"
            )

        else:

            st.warning(
                "Modo offline"
            )

    st.divider()

    if st.button(
        "+ NUEVO TAMIZAJE",
        type="primary",
        use_container_width=True
    ):

        st.session_state.current_case = {}

        st.session_state.result = None

        go("Nuevo tamizaje")

    c1, c2 = st.columns(2)

    with c1:

        if st.button(
            "Tamizajes pendientes",
            use_container_width=True
        ):

            go("Pendientes")

    with c2:

        if st.button(
            "NeoLink Alertas",
            use_container_width=True
        ):

            go("Alertas")

    st.write("")

    st.info(
        "Principio del MVP: medir → interpretar → clasificar "
        "→ indicar la siguiente acción puede ejecutarse localmente, "
        "sin internet. La conectividad permite luego sincronizar, "
        "conectar y teleorientar."
    )


# ============================================================
# REGISTRO DEL RN
# ============================================================

elif st.session_state.screen == "Nuevo tamizaje":

    st.title(
        "Registro del recién nacido"
    )

    st.markdown(
        '<div class="step-box">'
        '💡 Complete estos datos básicos del recién nacido '
        'antes de iniciar la medición.'
        '</div>',
        unsafe_allow_html=True
    )

    st.write("")

    with st.form("rn_form"):

        rn_id = st.text_input(
            "🆔 Código / identificación del RN",
            value="RN-001"
        )

        gestational_age = st.number_input(
            "🗓️ Edad gestacional (semanas)",
            min_value=20,
            max_value=45,
            value=39
        )

        hours_life = st.selectbox(
            "⏱️ Horas de vida del recién nacido",
            HOURS_LIFE_OPTIONS,
            index=0
        )

        fecha_hora = st.text_input(
            "📅 Fecha/hora del registro",
            value=datetime.now().strftime(
                "%Y-%m-%d %H:%M"
            )
        )

        submitted = st.form_submit_button(
            "Continuar ➜",
            type="primary"
        )

    if submitted:

        st.session_state.current_case = {

            "case_id":
                f"NL-{datetime.now().strftime('%Y%m%d%H%M%S')}",

            "rn_id": rn_id,

            "gestational_age":
                gestational_age,

            "hours_life":
                hours_life,

            "registered_at":
                fecha_hora,

            "measurements": [],
        }

        go("Sensor")


# ============================================================
# ¿CUENTA CON SENSOR NEONATAL COMPATIBLE?
# ============================================================

elif st.session_state.screen == "Sensor":

    st.title(
        "¿Cuenta con sensor neonatal compatible?"
    )

    st.markdown(
        '<div class="step-box">'
        '💡 El oxímetro de pulso es la primera opción y la '
        'evaluación clínica LatidoSeguro-CHD complementa el '
        'resultado. Si no hay sensor disponible, la evaluación '
        'clínica se usa como estratificación de riesgo, pero '
        '<b>no reemplaza</b> el tamizaje por oximetría.'
        '</div>',
        unsafe_allow_html=True
    )

    st.write("")

    c1, c2 = st.columns(2)

    with c1:

        if st.button(
            "✅ Sí, tengo sensor",
            type="primary",
            use_container_width=True
        ):

            st.session_state.current_case[
                "has_sensor"
            ] = True

            go("Mano derecha")

    with c2:

        if st.button(
            "❌ No tengo sensor",
            use_container_width=True
        ):

            st.session_state.current_case[
                "has_sensor"
            ] = False

            go("Criterios clínicos")


# ============================================================
# MANO DERECHA
# ============================================================

elif st.session_state.screen == "Mano derecha":

    st.title(
        "Tamizaje guiado"
    )

    st.progress(0.5)

    st.subheader(
        "Paso 1 de 2 · Mano derecha (preductal)"
    )

    st.markdown(
        """
        <div class="step-box">
        <b>Siga estos pasos en orden:</b><br>
        1️⃣ Encienda el oxímetro de pulso.<br>
        2️⃣ Coloque el sensor en la <b>mano derecha</b> del recién nacido.<br>
        3️⃣ Espere unos segundos hasta que el número deje de parpadear.<br>
        4️⃣ Lea el valor de saturación de oxígeno (SpO2).<br>
        5️⃣ Escriba ese número abajo.
        </div>
        """,
        unsafe_allow_html=True
    )

    st.write("")

    if st.session_state.current_case.get(
        "measurements"
    ):

        st.caption(
            f'🔁 Repetición N.° '
            f'{len(st.session_state.current_case["measurements"])} '
            f'para {st.session_state.current_case["rn_id"]}'
        )

    pre = st.number_input(
        "Saturación preductal (%)",
        min_value=50,
        max_value=100,
        value=89
    )

    if st.button(
        "Continuar ➜",
        type="primary"
    ):

        st.session_state.current_case[
            "_pre_temp"
        ] = pre

        go("Pie")


# ============================================================
# PIE
# ============================================================

elif st.session_state.screen == "Pie":

    st.title(
        "Tamizaje guiado"
    )

    st.progress(1.0)

    st.subheader(
        "Paso 2 de 2 · Pie (posductal)"
    )

    st.markdown(
        """
        <div class="step-box">
        <b>Siga estos pasos en orden:</b><br>
        1️⃣ Retire el sensor de la mano y límpielo si es necesario.<br>
        2️⃣ Coloque el sensor en <b>uno de los pies</b> del recién nacido.<br>
        3️⃣ Espere unos segundos hasta que el número deje de parpadear.<br>
        4️⃣ Lea el valor de saturación de oxígeno (SpO2).<br>
        5️⃣ Escriba el valor y presione "Evaluar".
        </div>
        """,
        unsafe_allow_html=True
    )

    st.write("")

    post = st.number_input(
        "Saturación posductal (%)",
        min_value=50,
        max_value=100,
        value=87
    )

    if st.button(
        "Evaluar ➜",
        type="primary"
    ):

        case = (
            st.session_state.current_case
        )

        pre = case.pop(
            "_pre_temp"
        )

        result, diff = evaluate_screening(
            pre,
            post,
            get_altitude_group()
        )

        entry = new_measurement_entry(
            pre,
            post,
            result,
            diff
        )

        case["measurements"].append(
            entry
        )

        case["andes_result"] = result

        go("Criterios clínicos")


# ============================================================
# CRITERIOS CLÍNICOS — ASISTENTE PASO A PASO
# ============================================================
#
# Igual que las pantallas de oximetría (Mano derecha / Pie), cada
# criterio se presenta en dos partes dentro del mismo paso:
#   1) CÓMO EVALUARLO (guía clínica) — se lee primero
#   2) La pregunta "¿Está presente?" — se responde después
#
# El recorrido avanza un criterio a la vez (mayores primero,
# luego menores) usando el índice guardado en el caso actual.

elif st.session_state.screen == "Criterios clínicos":

    case = (
        st.session_state.current_case
    )

    has_sensor = case.get(
        "has_sensor",
        True
    )

    if "_criteria_idx" not in case:
        case["_criteria_idx"] = 0

    if "_criteria_values" not in case:
        case["_criteria_values"] = {}

    if "_criteria_computed" not in case:
        case["_criteria_computed"] = {}

    idx = case["_criteria_idx"]
    total_steps = len(ALL_CRITERIA)

    if has_sensor:
        st.title("Evaluación clínica complementaria")
        st.caption(
            "LatidoSeguro-CHD — se combina con el resultado de "
            "oximetría (ANDES-CHD) ya registrado."
        )
    else:
        st.title("2B. Evaluación clínica de riesgo")
        st.warning(
            "⚠️ No reemplaza la oximetría. Esta evaluación se usa "
            "como estratificación de riesgo porque no hay sensor "
            "neonatal disponible."
        )

    # --------------------------------------------------------
    # Recorrido criterio por criterio
    # --------------------------------------------------------

    if idx < total_steps:

        crit = ALL_CRITERIA[idx]
        tipo = crit["tipo"]
        key = crit["key"]
        code = crit["code"]
        label = crit["label"]
        how_to = crit["how_to"]

        st.progress((idx) / total_steps)

        badge_class = "criteria-code" if tipo == "mayor" else "criteria-code minor"
        icon = "🔴" if tipo == "mayor" else "🟡"

        st.subheader(
            f"Paso {idx + 1} de {total_steps} · "
            f"{icon} Criterio {'mayor' if tipo == 'mayor' else 'menor'}"
        )

        st.markdown(
            f'<span class="{badge_class}">{code}</span>'
            f'<b>{label}</b>',
            unsafe_allow_html=True
        )

        st.write("")

        st.markdown(
            "**Cómo evaluarlo:**"
        )

        st.markdown(
            f'<div class="step-box">{how_to}</div>',
            unsafe_allow_html=True
        )

        if crit.get("umbral_nota"):

            st.caption(f"ℹ️ {crit['umbral_nota']}")

        st.write("")

        st.markdown("**Ingrese los datos y LatidoSeguro calcula el resultado:**")

        stored = case["_criteria_values"].get(key, {})

        positive, detail, raw = render_criterion_calculator(crit, stored)

        st.write("")

        nav1, nav2 = st.columns(2)

        with nav1:

            if idx > 0:

                if st.button(
                    "⬅ Anterior",
                    use_container_width=True
                ):

                    case["_criteria_values"][key] = raw
                    case["_criteria_computed"][key] = {
                        "positive": positive,
                        "detail": detail,
                    }
                    case["_criteria_idx"] = idx - 1
                    st.rerun()

        with nav2:

            btn_label = (
                "Siguiente ➜"
                if idx < total_steps - 1
                else "Finalizar evaluación ➜"
            )

            if st.button(
                btn_label,
                type="primary",
                use_container_width=True
            ):

                case["_criteria_values"][key] = raw
                case["_criteria_computed"][key] = {
                    "positive": positive,
                    "detail": detail,
                }
                case["_criteria_idx"] = idx + 1
                st.rerun()

    # --------------------------------------------------------
    # Fin del recorrido: calcular y clasificar
    # --------------------------------------------------------

    else:

        computed = case["_criteria_computed"]

        mayores_selected = [
            c["key"] for c in MAYOR_CRITERIA
            if computed.get(c["key"], {}).get("positive")
        ]

        menores_selected = [
            c["key"] for c in MINOR_CRITERIA
            if computed.get(c["key"], {}).get("positive")
        ]

        clinical_details = {
            c["key"]: computed.get(c["key"], {}).get("detail", "")
            for c in MAYOR_CRITERIA + MINOR_CRITERIA
            if c["key"] in computed
        }

        st.success(
            "✅ Evaluación clínica completa. Revise el resumen "
            "calculado antes de continuar."
        )

        st.write(
            f"🔴 Criterios mayores positivos: {len(mayores_selected)} · "
            f"🟡 Criterios menores positivos: {len(menores_selected)}"
        )

        mayor_labels = {c["key"]: (c["code"], c["label"]) for c in MAYOR_CRITERIA}
        minor_labels = {c["key"]: (c["code"], c["label"]) for c in MINOR_CRITERIA}

        with st.expander("Ver el cálculo completo de cada criterio", expanded=True):

            for c in MAYOR_CRITERIA:

                res = computed.get(c["key"])

                if res:

                    icon = "🔴" if res["positive"] else "⚪"

                    st.write(
                        f'{icon} **{c["code"]} · {c["label"]}** — '
                        f'{res["detail"]}'
                    )

            for c in MINOR_CRITERIA:

                res = computed.get(c["key"])

                if res:

                    icon = "🟡" if res["positive"] else "⚪"

                    st.write(
                        f'{icon} **{c["code"]} · {c["label"]}** — '
                        f'{res["detail"]}'
                    )

        nav1, nav2 = st.columns(2)

        with nav1:

            if st.button(
                "⬅ Revisar criterios",
                use_container_width=True
            ):

                case["_criteria_idx"] = total_steps - 1
                st.rerun()

        with nav2:

            if st.button(
                "Confirmar y clasificar riesgo ➜",
                type="primary",
                use_container_width=True
            ):

                case["clinical_mayores"] = mayores_selected
                case["clinical_menores"] = menores_selected
                case["clinical_details"] = clinical_details

                if has_sensor:

                    final_result, label = combine_andes_clinical(
                        case.get("andes_result", "REPETIR"),
                        len(mayores_selected),
                        len(menores_selected)
                    )

                else:

                    final_result, label = classify_clinical_only(
                        len(mayores_selected),
                        len(menores_selected)
                    )

                case["risk_label"] = label

                case.pop("_criteria_idx", None)
                case.pop("_criteria_values", None)
                case.pop("_criteria_computed", None)

                st.session_state.result = final_result

                go("Resultado")


# ============================================================
# RESULTADO
# ============================================================

elif st.session_state.screen == "Resultado":

    st.title("Resultado")

    case = (
        st.session_state.current_case
    )

    result = (
        st.session_state.result
    )

    has_sensor = case.get(
        "has_sensor",
        True
    )

    measurements = case.get(
        "measurements",
        []
    )

    last = (
        measurements[-1]
        if measurements
        else None
    )

    if has_sensor and last:

        st.metric(
            "Saturación preductal",
            f'{last["preductal"]}%'
        )

        st.metric(
            "Saturación posductal",
            f'{last["postductal"]}%'
        )

        st.metric(
            "Diferencia",
            f'{last["difference"]:.0f}%'
        )

        st.caption(
            f'Algoritmo seleccionado: '
            f'{st.session_state.facility["altitude_range"]}'
        )

        if len(measurements) > 1:

            with st.expander(
                "Mediciones anteriores"
            ):

                for i, m in enumerate(
                    measurements[:-1],
                    start=1
                ):

                    st.write(
                        f'#{i} — Preductal '
                        f'{m["preductal"]}% · '
                        f'Posductal '
                        f'{m["postductal"]}% · '
                        f'Diferencia '
                        f'{m["difference"]:.0f}% · '
                        f'{m["result"]} · '
                        f'{m["timestamp"]}'
                    )

    else:

        st.warning(
            "📋 Tamizaje por oximetría NO realizado. Resultado "
            "basado únicamente en evaluación clínica LatidoSeguro-CHD."
        )

    mayores = case.get(
        "clinical_mayores",
        []
    )

    menores = case.get(
        "clinical_menores",
        []
    )

    if mayores or menores:

        with st.expander(
            "Criterios clínicos marcados",
            expanded=not has_sensor
        ):

            mayor_labels = {
                c["key"]: c["label"] for c in MAYOR_CRITERIA
            }

            minor_labels = {
                c["key"]: c["label"] for c in MINOR_CRITERIA
            }

            if mayores:

                st.write(
                    "**Mayores:** " + ", ".join(
                        mayor_labels.get(k, k)
                        for k in mayores
                    )
                )

            else:

                st.write("**Mayores:** ninguno")

            if menores:

                st.write(
                    "**Menores:** " + ", ".join(
                        minor_labels.get(k, k)
                        for k in menores
                    )
                )

            else:

                st.write("**Menores:** ninguno")

    risk_label = case.get(
        "risk_label",
        ""
    )

    if risk_label:

        st.info(
            f"**Clasificación LatidoSeguro-CHD:** {risk_label}"
        )


    # ========================================================
    # NEGATIVO
    # ========================================================

    if result == "NEGATIVO":

        st.markdown(
            """
            <div class="result-green">
            <h2>🟢 TAMIZAJE NEGATIVO</h2>
            <p>Continuar protocolo correspondiente.</p>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.write("")

        st.subheader(
            "Educación a padres/cuidadores antes del alta"
        )

        st.caption(
            "Explicación de señales de alarma y dónde acudir."
        )

        orientation = st.checkbox(
            "☑ Orientación realizada"
        )

        booklet = st.checkbox(
            "☑ Cartilla entregada"
        )

        # ----------------------------------------------------
        # TELEORIENTACIÓN PARA VERDE
        # ----------------------------------------------------

        st.write("")

        st.subheader(
            "📞 Teleorientación"
        )

        tele = st.radio(
            "Modalidad de teleorientación",
            [
                "No iniciada",
                "Asíncrona (revisión del caso + indicaciones)",
                "Sincrónica (tiempo real)"
            ],
            key="tele_negative"
        )

        if st.button(
            "Registrar y dar de alta",
            type="primary"
        ):

            case["orientation_done"] = (
                orientation
            )

            case["booklet_delivered"] = (
                booklet
            )

            case["teleorientacion"] = (
                tele
            )

            record = build_case_record(
                case,
                "NEGATIVO"
            )

            upsert_local(
                record
            )

            st.session_state.history_record = record
            st.session_state.history_next_screen = "Inicio"

            go("Historia clínica")


    # ========================================================
    # REPETIR
    # ========================================================

    elif result == "REPETIR":

        st.markdown(
            """
            <div class="result-yellow">
            <h2>🟡 REPETIR TAMIZAJE</h2>
            <p>Nueva medición según el protocolo correspondiente.</p>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.write("")

        st.warning(
            "⏱ Recordatorio local programado para dentro de 1 hora."
        )

        # ----------------------------------------------------
        # TELEORIENTACIÓN PARA AMARILLO
        # ----------------------------------------------------

        st.subheader(
            "📞 Teleorientación"
        )

        tele = st.radio(
            "Modalidad de teleorientación",
            [
                "No iniciada",
                "Asíncrona (revisión del caso + indicaciones)",
                "Sincrónica (tiempo real)"
            ],
            key="tele_repeat"
        )

        if st.button(
            "Guardar en tamizajes pendientes",
            type="primary"
        ):

            case["teleorientacion"] = (
                tele
            )

            record = build_case_record(
                case,
                "REPETIR"
            )

            upsert_local(
                record
            )

            st.session_state.history_record = record
            st.session_state.history_next_screen = "Pendientes"

            go("Historia clínica")


    # ========================================================
    # POSITIVO
    # ========================================================

    else:

        st.markdown(
            """
            <div class="result-red">
            <h2>🔴 TAMIZAJE POSITIVO</h2>
            <p>Requiere evaluación médica inmediata.</p>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown(
            """
            <div class="ambulance-box">
            🚑 Si el bebé está en riesgo inmediato,
            llame a la ambulancia ahora mismo
            </div>
            """,
            unsafe_allow_html=True
        )

        st.link_button(
            "🚑 LLAMAR AMBULANCIA (SAMU 106)",
            "tel:106",
            use_container_width=True
        )

        st.write("")

        if st.button(
            "❤️ ACTIVAR BOTÓN CORAZÓN",
            type="primary",
            use_container_width=True
        ):

            go("NeoLink Alerta")


# ============================================================
# NEOLINK ALERTA
# ============================================================

elif st.session_state.screen == "NeoLink Alerta":

    st.title(
        "❤️ NeoLink Alerta"
    )

    case = (
        st.session_state.current_case
    )

    measurements = case.get(
        "measurements",
        []
    )

    last = (
        measurements[-1]
        if measurements
        else None
    )

    st.error(
        "TAMIZAJE POSITIVO — Requiere evaluación médica inmediata."
    )

    risk_label = case.get(
        "risk_label",
        ""
    )

    if risk_label:

        st.caption(
            risk_label
        )

    st.markdown(
        """
        <div class="ambulance-box">
        🚑 Si el bebé está en riesgo inmediato,
        llame a la ambulancia ahora mismo
        </div>
        """,
        unsafe_allow_html=True
    )

    st.link_button(
        "🚑 LLAMAR AMBULANCIA (SAMU 106)",
        "tel:106",
        use_container_width=True
    )

    st.write("")

    st.markdown(
        "### Ficha NeoLink Alerta"
    )

    mayor_labels = {
        c["key"]: c["label"] for c in MAYOR_CRITERIA
    }

    minor_labels = {
        c["key"]: c["label"] for c in MINOR_CRITERIA
    }

    data = {

        "RN":
            case["rn_id"],

        "Establecimiento":
            st.session_state.facility["name"],

        "Ubicación":
            st.session_state.facility["location"],

        "Altitud":
            st.session_state.facility["altitude_range"],

        "Edad gestacional":
            f'{case["gestational_age"]} semanas',

        "Horas de vida":
            case["hours_life"],

        "Fecha/hora de registro":
            case.get(
                "registered_at",
                ""
            ),

        "Sensor neonatal disponible":
            "Sí" if case.get("has_sensor", True) else "No",

        "Saturación preductal":
            f'{last["preductal"]}%' if last else "No realizado",

        "Saturación posductal":
            f'{last["postductal"]}%' if last else "No realizado",

        "Diferencia":
            f'{last["difference"]:.0f}%' if last else "—",

        "Mediciones anteriores":
            max(len(measurements) - 1, 0),

        "Criterios mayores":
            [
                mayor_labels.get(k, k)
                for k in case.get("clinical_mayores", [])
            ],

        "Criterios menores":
            [
                minor_labels.get(k, k)
                for k in case.get("clinical_menores", [])
            ],

        "Clasificación LatidoSeguro-CHD":
            case.get("risk_label", ""),

        "Resultado":
            "POSITIVO",
    }

    st.json(data)

    st.write("")

    st.markdown("**Proceso formal de referencia**")

    c1, c2, c3 = st.columns(3)

    ref = c1.checkbox(
        "Referencia iniciada",
        key="alert_ref"
    )

    tras = c2.checkbox(
        "Traslado registrado",
        key="alert_tras"
    )

    aten = c3.checkbox(
        "Atención especializada",
        key="alert_aten"
    )

    if st.button(
        "Guardar caso localmente",
        type="primary"
    ):

        case["referencia_iniciada"] = ref
        case["traslado_registrado"] = tras
        case["atencion_especializada"] = aten

        record = build_case_record(
            case,
            "POSITIVO"
        )

        upsert_local(
            record
        )

        if st.session_state.connection:

            sync_cases()

        st.session_state.history_record = record
        st.session_state.history_next_screen = "Alertas"

        go("Historia clínica")


# ============================================================
# HISTORIA CLÍNICA (RESUMEN FINAL)
# ============================================================

elif st.session_state.screen == "Historia clínica":

    record = st.session_state.history_record

    if not record:

        st.warning(
            "No hay un caso recién cerrado para mostrar."
        )

        if st.button("Volver al inicio"):
            go("Inicio")

    else:

        next_screen = st.session_state.history_next_screen

        next_label = {
            "Inicio": "Inicio",
            "Pendientes": "Tamizajes pendientes",
            "Alertas": "NeoLink Alertas",
        }.get(next_screen, next_screen)

        render_historia_clinica(record, next_screen, next_label)


# ============================================================
# PENDIENTES
# ============================================================

elif st.session_state.screen == "Pendientes":

    st.title(
        "Tamizajes pendientes"
    )

    pending = [
        c
        for c in st.session_state.local_cases
        if c.get("result") == "REPETIR"
    ]

    if not pending:

        st.success(
            "No hay tamizajes pendientes."
        )

    else:

        for case in pending:

            with st.container(
                border=True
            ):

                st.subheader(
                    case["rn_id"]
                )

                st.write(
                    f'Último resultado: '
                    f'🟡 {case["result"]}'
                )

                st.write(
                    f'Repeticiones realizadas: '
                    f'{case.get("repeat_count", 0)}'
                )

                st.caption(
                    f'Última medición: '
                    f'{case["timestamp"]}'
                )

                if case.get(
                    "teleorientacion"
                ):

                    st.write(
                        f'📞 Teleorientación: '
                        f'{case["teleorientacion"]}'
                    )

                if st.button(
                    "🔔 Repetir tamizaje",
                    key=f'repeat_{case["case_id"]}'
                ):

                    has_sensor = case.get(
                        "has_sensor",
                        True
                    )

                    st.session_state.current_case = {

                        "case_id":
                            case["case_id"],

                        "rn_id":
                            case["rn_id"],

                        "gestational_age":
                            case["gestational_age"],

                        "hours_life":
                            case["hours_life"],

                        "registered_at":
                            case.get(
                                "registered_at",
                                ""
                            ),

                        "has_sensor":
                            has_sensor,

                        "measurements":
                            case.get(
                                "measurements",
                                []
                            ),

                        "clinical_mayores":
                            case.get(
                                "clinical_mayores",
                                []
                            ),

                        "clinical_menores":
                            case.get(
                                "clinical_menores",
                                []
                            ),

                        "orientation_done":
                            case.get(
                                "orientation_done",
                                False
                            ),

                        "booklet_delivered":
                            case.get(
                                "booklet_delivered",
                                False
                            ),

                        "teleorientacion":
                            case.get(
                                "teleorientacion"
                            ),
                    }

                    if has_sensor:

                        go("Mano derecha")

                    else:

                        go("Criterios clínicos")


# ============================================================
# ALERTAS ROJAS
# ============================================================

elif st.session_state.screen == "Alertas":

    st.title(
        "NeoLink Alertas"
    )

    alerts = [
        c
        for c in st.session_state.local_cases
        if c.get("result") == "POSITIVO"
    ]

    if not alerts:

        st.info(
            "No hay NeoLink Alertas registradas."
        )

    else:

        for case in alerts:

            with st.container(
                border=True
            ):

                st.subheader(
                    f'🚨 {case["rn_id"]}'
                )

                st.write(
                    f'Caso: {case["case_id"]}'
                )

                if case.get("preductal") is not None:

                    st.write(
                        f'Preductal: '
                        f'{case["preductal"]}% · '
                        f'Posductal: '
                        f'{case["postductal"]}% · '
                        f'Diferencia: '
                        f'{case["difference"]:.0f}%'
                    )

                else:

                    st.write(
                        "Sin oximetría — activada por criterios "
                        "clínicos LatidoSeguro-CHD."
                    )

                if case.get("risk_label"):

                    st.caption(
                        case["risk_label"]
                    )

                st.write(
                    f'Estado de sincronización: '
                    f'{case["sync_status"]}'
                )

                st.link_button(
                    "🚑 Llamar ambulancia (SAMU 106)",
                    "tel:106",
                    key=f"amb_{case['case_id']}"
                )

                if case["sync_status"] == "PENDIENTE":

                    st.warning(
                        "📡 Pendiente de sincronización "
                        "con NeoLink Cloud."
                    )

                else:

                    st.success(
                        "☁️ Caso disponible en NeoLink Cloud "
                        "para centro/especialista correspondiente."
                    )

                # =================================================
                # SEGUIMIENTO DEL POSITIVO
                # =================================================

                st.markdown(
                    "**Proceso formal de referencia**"
                )

                c1, c2, c3 = st.columns(3)

                ref = c1.checkbox(
                    "Referencia iniciada",
                    value=case.get(
                        "referencia_iniciada",
                        False
                    ),
                    key=f"ref_{case['case_id']}"
                )

                tras = c2.checkbox(
                    "Traslado registrado",
                    value=case.get(
                        "traslado_registrado",
                        False
                    ),
                    key=f"tras_{case['case_id']}"
                )

                aten = c3.checkbox(
                    "Atención especializada",
                    value=case.get(
                        "atencion_especializada",
                        False
                    ),
                    key=f"aten_{case['case_id']}"
                )

                if st.button(
                    "Guardar seguimiento",
                    key=f"save_track_{case['case_id']}",
                    type="primary"
                ):

                    # ---------------------------------------------
                    # LOCAL
                    # ---------------------------------------------

                    idx = next(
                        (
                            j
                            for j, c
                            in enumerate(
                                st.session_state.local_cases
                            )
                            if c["case_id"]
                            == case["case_id"]
                        ),
                        None
                    )

                    if idx is not None:

                        st.session_state.local_cases[
                            idx
                        ]["referencia_iniciada"] = ref

                        st.session_state.local_cases[
                            idx
                        ]["traslado_registrado"] = tras

                        st.session_state.local_cases[
                            idx
                        ]["atencion_especializada"] = aten

                        # Si no hay internet, permanece pendiente.
                        # Si hay internet, ya queda sincronizado.
                        st.session_state.local_cases[
                            idx
                        ]["sync_status"] = (
                            "SINCRONIZADO"
                            if st.session_state.connection
                            else "PENDIENTE"
                        )

                    # Guardar archivo local
                    save_json(
                        LOCAL_FILE,
                        st.session_state.local_cases
                    )

                    # ---------------------------------------------
                    # CENTRAL
                    # ---------------------------------------------

                    cidx = next(
                        (
                            j
                            for j, c
                            in enumerate(
                                st.session_state.central_cases
                            )
                            if c["case_id"]
                            == case["case_id"]
                        ),
                        None
                    )

                    if (
                        cidx is not None
                        and st.session_state.connection
                    ):

                        st.session_state.central_cases[
                            cidx
                        ].update({

                            "referencia_iniciada":
                                ref,

                            "traslado_registrado":
                                tras,

                            "atencion_especializada":
                                aten,

                            "sync_status":
                                "SINCRONIZADO",
                        })

                        save_json(
                            CENTRAL_FILE,
                            st.session_state.central_cases
                        )

                    st.success(
                        "✅ Seguimiento actualizado correctamente."
                    )


# ============================================================
# DASHBOARD
# ============================================================

elif st.session_state.screen == "Dashboard":

    st.title(
        "📊 Dashboard de gestión"
    )

    # ========================================================
    # IMPORTANTE:
    # El dashboard ahora utiliza CENTRAL + LOCAL.
    # Esto permite visualizar datos incluso sin internet.
    # ========================================================

    cases = get_all_cases()

    total = len(cases)

    positives = len([
        c
        for c in cases
        if c.get("result") == "POSITIVO"
    ])

    repeats = len([
        c
        for c in cases
        if c.get("result") == "REPETIR"
    ])

    negatives = len([
        c
        for c in cases
        if c.get("result") == "NEGATIVO"
    ])

    eligible = max(
        total,
        125
    )

    pct_tamizados = (
        total / eligible * 100
        if eligible
        else 0
    )

    # ========================================================
    # KPIs
    # ========================================================

    c1, c2 = st.columns(2)
    c3, c4 = st.columns(2)

    c1.metric(
        "RN elegibles",
        eligible
    )

    c2.metric(
        "Tamizados",
        total,
        f"{pct_tamizados:.0f}% antes del alta"
    )

    c3.metric(
        "Tamizajes positivos",
        positives
    )

    c4.metric(
        "Tamizajes pendientes",
        repeats
    )

    st.caption(
        f"Tamizajes negativos: {negatives}"
    )

    st.divider()

    # ========================================================
    # SEGUIMIENTO
    # ========================================================

    st.subheader(
        "🔄 Seguimiento de casos"
    )

    referencias = len([
        c
        for c in cases
        if c.get(
            "referencia_iniciada",
            False
        )
    ])

    traslados = len([
        c
        for c in cases
        if c.get(
            "traslado_registrado",
            False
        )
    ])

    atenciones = len([
        c
        for c in cases
        if c.get(
            "atencion_especializada",
            False
        )
    ])

    t1, t2, t3 = st.columns(3)

    t1.metric(
        "Referencias iniciadas",
        referencias
    )

    t2.metric(
        "Traslados registrados",
        traslados
    )

    t3.metric(
        "Atenciones especializadas",
        atenciones
    )

    st.divider()

    # ========================================================
    # MAPA DEL PERÚ
    # ========================================================

    st.subheader(
        "🗺️ Mapa del Perú — Cardio Alertas reportadas"
    )

    dept_counts = {}

    for c in cases:

        if c.get(
            "result"
        ) == "POSITIVO":

            dept = c.get(
                "location",
                ""
            )

            dept_counts[dept] = (
                dept_counts.get(
                    dept,
                    0
                ) + 1
            )

    if not dept_counts:

        st.info(
            "Aún no se han reportado cardiopatías "
            "positivas para mostrar en el mapa."
        )

    else:

        map_rows = []

        for dept, count in dept_counts.items():

            coords = (
                PERU_DEPARTMENTS.get(
                    dept
                )
            )

            if not coords:
                continue

            map_rows.append({

                "lat":
                    coords["lat"],

                "lon":
                    coords["lon"],

                "departamento":
                    dept,

                "casos":
                    count,
            })

        map_df = pd.DataFrame(
            map_rows
        )

        # Vista fija centrada en Perú (no se ajusta a los puntos),
        # para que el mapa siempre quede acotado al país.
        view_state = pdk.ViewState(
            latitude=-9.19,
            longitude=-75.0152,
            zoom=4.4,
            pitch=0,
        )

        # radius_min/max_pixels limita el tamaño del punto en
        # pantalla sin importar el zoom, para que los círculos no
        # crezcan hasta tapar el mapa cuando hay muchos casos.
        scatter_layer = pdk.Layer(
            "ScatterplotLayer",
            data=map_df,
            get_position="[lon, lat]",
            get_fill_color="[122, 18, 18, 170]",
            get_line_color="[255, 255, 255, 200]",
            line_width_min_pixels=1,
            get_radius="casos",
            radius_scale=6000,
            radius_min_pixels=8,
            radius_max_pixels=28,
            pickable=True,
        )

        deck = pdk.Deck(
            layers=[scatter_layer],
            initial_view_state=view_state,
            map_style=None,
            tooltip={
                "text": "{departamento}: {casos} caso(s)"
            },
        )

        st.pydeck_chart(deck)

        st.caption(
            "El tamaño del punto rojo indica la cantidad de "
            "Cardio Alertas positivas. El mapa queda acotado al "
            "Perú independientemente de la cantidad de casos."
        )

        for dept, count in sorted(
            dept_counts.items(),
            key=lambda x: -x[1]
        ):

            st.write(
                f"🔴 **{dept}** — "
                f"{count} caso(s)"
            )

    st.divider()

    # ========================================================
    # CASOS POR DEPARTAMENTO
    # ========================================================

    st.subheader(
        "📈 Casos por departamento"
    )

    if cases:

        dept_all = {}

        for c in cases:

            dept = c.get(
                "location",
                "—"
            )

            dept_all[dept] = (
                dept_all.get(
                    dept,
                    0
                ) + 1
            )

        st.bar_chart(
            pd.Series(
                dept_all,
                name="Casos"
            )
        )

    else:

        st.info(
            "Aún no hay datos suficientes."
        )

    # ========================================================
    # DISTRIBUCIÓN
    # ========================================================

    st.subheader(
        "📊 Distribución de resultados"
    )

    if cases:

        dist = pd.Series({

            "🟢 Negativo":
                negatives,

            "🟡 Repetir":
                repeats,

            "🔴 Positivo":
                positives,

        }, name="Casos")

        st.bar_chart(
            dist
        )

    else:

        st.info(
            "Aún no hay datos suficientes."
        )

    # ========================================================
    # LÍNEA DE TIEMPO
    # ========================================================

    st.subheader(
        "🕒 Tamizajes en el tiempo"
    )

    if cases:

        df_time = pd.DataFrame(
            cases
        )

        df_time["fecha"] = (
            pd.to_datetime(
                df_time["timestamp"]
            ).dt.date
        )

        timeline = (
            df_time
            .groupby("fecha")
            .size()
        )

        timeline.name = "Casos"

        st.line_chart(
            timeline
        )

    else:

        st.info(
            "Aún no hay datos suficientes."
        )

    st.divider()

    # ========================================================
    # TAMIZAJES NO REALIZADOS
    # ========================================================

    st.subheader(
        "Tamizajes no realizados"
    )

    not_done = 5

    st.metric(
        "No realizados",
        not_done
    )

    st.write(
        "Motivos registrados "
        "(ejemplo de prototipo):"
    )

    reason_data = {

        "Falta de equipo":
            3,

        "Falta de sensor":
            1,

        "Otras causas operativas":
            1
    }

    st.bar_chart(
        reason_data
    )

    st.divider()

    # ========================================================
    # CASOS
    # ========================================================

    st.subheader(
        "Casos registrados"
    )

    if not cases:

        st.info(
            "Aún no hay casos registrados."
        )

    else:

        icon = {

            "POSITIVO":
                "🔴",

            "REPETIR":
                "🟡",

            "NEGATIVO":
                "🟢"
        }

        for case in cases:

            sync_icon = (
                "☁️"
                if case.get(
                    "sync_status"
                ) == "SINCRONIZADO"
                else "📱"
            )

            st.write(
                f'{icon.get(case["result"], "•")} '
                f'**{case["rn_id"]}** — '
                f'{case["result"]} — '
                f'{case["timestamp"]} '
                f'{sync_icon}'
            )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "NEOLINK — Prototipo MVP Offline First para hackatón "
    "(Cardio Alerta Perú). Los resultados y reglas clínicas "
    "del prototipo deben ser validados por profesionales y "
    "por el protocolo institucional antes de cualquier uso asistencial."
)
