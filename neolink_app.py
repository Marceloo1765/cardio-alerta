import streamlit as st
import pandas as pd
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

    last = case["measurements"][-1]

    return {
        "case_id": case["case_id"],
        "rn_id": case["rn_id"],
        "gestational_age": case["gestational_age"],
        "hours_life": case["hours_life"],
        "registered_at": case.get("registered_at", now),

        "facility": st.session_state.facility["name"],
        "location": st.session_state.facility["location"],
        "altitude": st.session_state.facility["altitude_range"],

        "preductal": last["preductal"],
        "postductal": last["postductal"],
        "difference": last["difference"],

        "measurements": case["measurements"],
        "repeat_count": len(case["measurements"]) - 1,

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

        go("Mano derecha")


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

        st.session_state.result = result

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

    last = (
        case["measurements"][-1]
    )

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

    if len(case["measurements"]) > 1:

        with st.expander(
            "Mediciones anteriores"
        ):

            for i, m in enumerate(
                case["measurements"][:-1],
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

            st.success(
                "Resultado guardado localmente. "
                "RN dado de alta."
            )

            st.session_state.current_case = None

            go("Inicio")


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

            st.session_state.current_case = None

            go("Pendientes")


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

    last = (
        case["measurements"][-1]
    )

    st.error(
        "TAMIZAJE POSITIVO — Requiere evaluación médica inmediata."
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

        "Saturación preductal":
            f'{last["preductal"]}%',

        "Saturación posductal":
            f'{last["postductal"]}%',

        "Diferencia":
            f'{last["difference"]:.0f}%',

        "Mediciones anteriores":
            len(case["measurements"]) - 1,

        "Resultado":
            "POSITIVO",
    }

    st.json(data)

    if st.button(
        "Guardar caso localmente",
        type="primary"
    ):

        record = build_case_record(
            case,
            "POSITIVO"
        )

        upsert_local(
            record
        )

        st.session_state.current_case = None

        if st.session_state.connection:

            sync_cases()

            st.success(
                "☁️ NeoLink Alerta sincronizada "
                "con NeoLink Cloud."
            )

        else:

            st.warning(
                "📡 Sin conexión. NeoLink Alerta "
                "guardada localmente en ALERTAS "
                "PENDIENTES DE SINCRONIZACIÓN."
            )

        go("Alertas")


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

                        "measurements":
                            case.get(
                                "measurements",
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

                    go("Mano derecha")


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

                st.write(
                    f'Preductal: '
                    f'{case["preductal"]}% · '
                    f'Posductal: '
                    f'{case["postductal"]}% · '
                    f'Diferencia: '
                    f'{case["difference"]:.0f}%'
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
                # SIN TELEORIENTACIÓN
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

                "size":
                    8000 + count * 6000,
            })

        map_df = pd.DataFrame(
            map_rows
        )

        st.map(
            map_df,
            latitude="lat",
            longitude="lon",
            size="size",
            color="#7A1212"
        )

        st.caption(
            "El tamaño del punto rojo indica "
            "la cantidad de Cardio Alertas positivas."
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
