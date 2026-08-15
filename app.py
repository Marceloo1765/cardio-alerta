import streamlit as st
import json
from pathlib import Path
from datetime import datetime

# ============================================================
# CARDIO ALERTA - PROTOTIPO MVP OFFLINE FIRST
# Prototipo para hackatón. No es una herramienta clínica validada.
# ============================================================

LOCAL_FILE = Path("cardio_alerta_local.json")
CENTRAL_FILE = Path("cardio_alerta_central.json")

# -----------------------------
# Persistencia local simulada
# -----------------------------
def load_json(path):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []

def save_json(path, data):
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

if "local_cases" not in st.session_state:
    st.session_state.local_cases = load_json(LOCAL_FILE)

if "central_cases" not in st.session_state:
    st.session_state.central_cases = load_json(CENTRAL_FILE)

if "screen" not in st.session_state:
    st.session_state.screen = "Inicio"

if "connection" not in st.session_state:
    st.session_state.connection = False

if "current_case" not in st.session_state:
    st.session_state.current_case = None

if "result" not in st.session_state:
    st.session_state.result = None

if "repeat_count" not in st.session_state:
    st.session_state.repeat_count = 0


# -----------------------------
# Configuración del establecimiento
# -----------------------------
if "facility" not in st.session_state:
    st.session_state.facility = {
        "name": "Centro de Salud Demo",
        "location": "Ayacucho",
        "altitude_range": "2500–3599 m s. n. m.",
        "identifier": "CS-DEMO-001"
    }


# ============================================================
# ESTILOS
# ============================================================
st.set_page_config(
    page_title="Cardio Alerta",
    page_icon="❤️",
    layout="centered"
)

st.markdown("""
<style>
.block-container {
    max-width: 850px;
    padding-top: 2rem;
}
.big-title {
    font-size: 34px;
    font-weight: 700;
    margin-bottom: 0;
}
.subtitle {
    font-size: 18px;
    color: #666;
    margin-bottom: 25px;
}
.status-online {
    padding: 8px 12px;
    border-radius: 8px;
    background: #e9f7ef;
    color: #1e7e34;
    font-weight: 600;
}
.status-offline {
    padding: 8px 12px;
    border-radius: 8px;
    background: #fff3cd;
    color: #856404;
    font-weight: 600;
}
.result-green {
    padding: 25px;
    border-radius: 12px;
    background: #eaf7ea;
    border: 2px solid #55a855;
}
.result-yellow {
    padding: 25px;
    border-radius: 12px;
    background: #fff8df;
    border: 2px solid #d9a400;
}
.result-red {
    padding: 25px;
    border-radius: 12px;
    background: #fdecec;
    border: 2px solid #d9534f;
}
.card {
    padding: 20px;
    border-radius: 12px;
    border: 1px solid #ddd;
    margin-bottom: 15px;
}
.small {
    color: #666;
    font-size: 14px;
}
</style>
""", unsafe_allow_html=True)


# ============================================================
# FUNCIONES
# ============================================================
def go(screen):
    st.session_state.screen = screen
    st.rerun()

def get_altitude_group():
    return st.session_state.facility["altitude_range"]

def evaluate_screening(pre, post, altitude_group):
    """
    Reglas del prototipo basadas en el esquema trabajado por el equipo:
      0–2499 m:
        Positivo inmediato: cualquier SpO2 < 90%
        Repetir: 90–94% o diferencia > 3%
        Negativo: ambas >=95% y diferencia <3%

      2500–3599 m:
        Positivo inmediato: cualquier SpO2 < 87%
        Repetir: 87–89% o diferencia >3%
        Negativo: ambas >=90% y diferencia <3%

      3600–4500 m:
        Positivo inmediato: cualquier SpO2 < 85%
        Repetir: 85–88% o diferencia >3%
        Negativo: ambas >=89% y diferencia <3%

    Nota: para implementación real, estas reglas deben ser validadas
    y aprobadas por el equipo clínico/institución correspondiente.
    """
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

    # Positivo inmediato
    if pre < positive_cutoff or post < positive_cutoff:
        return "POSITIVO", diff

    # Negativo
    if pre >= negative_cutoff and post >= negative_cutoff and diff < 3:
        return "NEGATIVO", diff

    # Todo lo que queda en zona intermedia
    return "REPETIR", diff


def create_case(data, result, diff):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return {
        "case_id": data["case_id"],
        "rn_id": data["rn_id"],
        "gestational_age": data["gestational_age"],
        "hours_life": data["hours_life"],
        "facility": st.session_state.facility["name"],
        "location": st.session_state.facility["location"],
        "altitude": st.session_state.facility["altitude_range"],
        "preductal": data["preductal"],
        "postductal": data["postductal"],
        "difference": diff,
        "result": result,
        "timestamp": now,
        "sync_status": "SINCRONIZADO" if st.session_state.connection else "PENDIENTE",
        "repeat_count": st.session_state.repeat_count
    }


def save_local(case):
    st.session_state.local_cases.append(case)
    save_json(LOCAL_FILE, st.session_state.local_cases)


def sync_cases():
    pending = [
        c for c in st.session_state.local_cases
        if c.get("sync_status") == "PENDIENTE"
    ]

    for case in pending:
        case["sync_status"] = "SINCRONIZADO"
        # Evita duplicados en la central
        existing_ids = {c["case_id"] for c in st.session_state.central_cases}
        if case["case_id"] not in existing_ids:
            st.session_state.central_cases.append(case)

    save_json(LOCAL_FILE, st.session_state.local_cases)
    save_json(CENTRAL_FILE, st.session_state.central_cases)

    return len(pending)


# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown("## CARDIO ALERTA")
    st.caption("MVP Offline First")

    st.divider()

    if st.session_state.connection:
        st.markdown(
            '<div class="status-online">● CON INTERNET</div>',
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            '<div class="status-offline">● MODO OFFLINE</div>',
            unsafe_allow_html=True
        )

    st.write("")

    if st.button("Inicio", use_container_width=True):
        go("Inicio")

    if st.button("Nuevo tamizaje", use_container_width=True):
        go("Nuevo tamizaje")

    if st.button("Tamizajes pendientes", use_container_width=True):
        go("Pendientes")

    if st.button("Cardio Alertas", use_container_width=True):
        go("Alertas")

    if st.button("Dashboard", use_container_width=True):
        go("Dashboard")

    st.divider()

    st.markdown("### Conectividad")

    if st.button(
        "Activar internet" if not st.session_state.connection
        else "Simular pérdida de internet",
        use_container_width=True
    ):
        st.session_state.connection = not st.session_state.connection
        st.rerun()

    pending_count = len([
        c for c in st.session_state.local_cases
        if c.get("sync_status") == "PENDIENTE"
    ])

    st.caption(f"Registros locales pendientes: {pending_count}")

    if st.session_state.connection and pending_count:
        if st.button("Sincronizar ahora", use_container_width=True):
            n = sync_cases()
            st.success(f"{n} caso(s) sincronizado(s).")
            st.rerun()


# ============================================================
# INICIO
# ============================================================
if st.session_state.screen == "Inicio":

    st.markdown('<div class="big-title">CARDIO ALERTA</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="subtitle">Tamizaje neonatal · MVP Offline First</div>',
        unsafe_allow_html=True
    )

    c1, c2 = st.columns(2)

    with c1:
        st.markdown("### Establecimiento")
        st.write(st.session_state.facility["name"])
        st.write(st.session_state.facility["location"])
        st.write(st.session_state.facility["altitude_range"])

    with c2:
        st.markdown("### Estado")
        if st.session_state.connection:
            st.success("Internet disponible")
        else:
            st.warning("Modo offline")

    st.divider()

    if st.button("+ NUEVO TAMIZAJE", type="primary", use_container_width=True):
        st.session_state.current_case = {}
        st.session_state.result = None
        st.session_state.repeat_count = 0
        go("Nuevo tamizaje")

    c1, c2 = st.columns(2)

    with c1:
        if st.button("Tamizajes pendientes", use_container_width=True):
            go("Pendientes")

    with c2:
        if st.button("Cardio Alertas", use_container_width=True):
            go("Alertas")

    st.write("")

    st.info(
        "Principio del MVP: medir → interpretar → clasificar → indicar "
        "la siguiente acción puede ejecutarse localmente. "
        "La conectividad permite posteriormente sincronizar y conectar."
    )


# ============================================================
# NUEVO TAMIZAJE
# ============================================================
elif st.session_state.screen == "Nuevo tamizaje":

    st.title("Nuevo tamizaje")

    with st.form("rn_form"):
        rn_id = st.text_input("Código / identificación del RN", value="RN-001")
        gestational_age = st.number_input(
            "Edad gestacional (semanas)",
            min_value=20,
            max_value=45,
            value=39
        )
        hours_life = st.number_input(
            "Horas de vida",
            min_value=0,
            max_value=168,
            value=18
        )

        submitted = st.form_submit_button("Continuar", type="primary")

    if submitted:
        st.session_state.current_case = {
            "case_id": f"CA-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "rn_id": rn_id,
            "gestational_age": gestational_age,
            "hours_life": hours_life
        }
        go("Mano derecha")


# ============================================================
# MANO DERECHA
# ============================================================
elif st.session_state.screen == "Mano derecha":

    st.title("Tamizaje")
    st.progress(0.5)
    st.subheader("Paso 1 de 2")

    st.info("Coloque el sensor del oxímetro en la mano derecha.")

    pre = st.number_input(
        "Saturación preductal (%)",
        min_value=50,
        max_value=100,
        value=89
    )

    if st.button("Continuar", type="primary"):
        st.session_state.current_case["preductal"] = pre
        go("Pie")


# ============================================================
# PIE
# ============================================================
elif st.session_state.screen == "Pie":

    st.title("Tamizaje")
    st.progress(1.0)
    st.subheader("Paso 2 de 2")

    st.info("Coloque el sensor del oxímetro en uno de los pies.")

    post = st.number_input(
        "Saturación posductal (%)",
        min_value=50,
        max_value=100,
        value=87
    )

    if st.button("Evaluar", type="primary"):
        st.session_state.current_case["postductal"] = post

        result, diff = evaluate_screening(
            st.session_state.current_case["preductal"],
            post,
            get_altitude_group()
        )

        st.session_state.result = result
        st.session_state.current_case["difference"] = diff

        go("Resultado")


# ============================================================
# RESULTADO
# ============================================================
elif st.session_state.screen == "Resultado":

    st.title("Resultado")

    case = st.session_state.current_case
    result = st.session_state.result

    st.metric("Saturación preductal", f'{case["preductal"]}%')
    st.metric("Saturación posductal", f'{case["postductal"]}%')
    st.metric("Diferencia", f'{case["difference"]:.0f}%')

    st.caption(
        f'Algoritmo seleccionado: {st.session_state.facility["altitude_range"]}'
    )

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
        st.subheader("Educación antes del alta")
        orientation = st.checkbox("Orientación realizada")
        booklet = st.checkbox("Cartilla entregada")

        if st.button("Registrar y dar de alta", type="primary"):
            case["orientation_done"] = orientation
            case["booklet_delivered"] = booklet
            final_case = create_case(case, "NEGATIVO", case["difference"])
            save_local(final_case)
            st.success("Resultado guardado localmente.")
            st.session_state.current_case = None
            go("Inicio")

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
        st.warning("Recordatorio local programado para 1 hora.")

        if st.button("Programar repetición", type="primary"):
            case["pending_repeat"] = True
            case["repeat_count"] = st.session_state.repeat_count + 1
            pending_case = create_case(case, "REPETIR", case["difference"])
            save_local(pending_case)
            st.session_state.current_case = case
            go("Pendientes")

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

        if st.button("❤️ ACTIVAR CARDIO ALERTA", type="primary", use_container_width=True):
            go("Cardio Alerta")


# ============================================================
# CARDIO ALERTA
# ============================================================
elif st.session_state.screen == "Cardio Alerta":

    st.title("❤️ Cardio Alerta")

    case = st.session_state.current_case

    st.error("TAMIZAJE POSITIVO — Requiere evaluación médica inmediata.")

    st.markdown("### Ficha Cardio Alerta")

    data = {
        "RN": case["rn_id"],
        "Establecimiento": st.session_state.facility["name"],
        "Ubicación": st.session_state.facility["location"],
        "Altitud": st.session_state.facility["altitude_range"],
        "Edad gestacional": f'{case["gestational_age"]} semanas',
        "Horas de vida": case["hours_life"],
        "Saturación preductal": f'{case["preductal"]}%',
        "Saturación posductal": f'{case["postductal"]}%',
        "Diferencia": f'{case["difference"]:.0f}%',
        "Resultado": "POSITIVO"
    }

    st.json(data)

    if st.button("Guardar caso localmente", type="primary"):
        final_case = create_case(
            case,
            "POSITIVO",
            case["difference"]
        )
        save_local(final_case)

        st.session_state.current_case = final_case

        if st.session_state.connection:
            sync_cases()
            st.success("Cardio Alerta sincronizada con el servidor.")
        else:
            st.warning(
                "📡 Sin conexión. Cardio Alerta guardada localmente "
                "y pendiente de sincronización."
            )

        go("Alertas")


# ============================================================
# PENDIENTES
# ============================================================
elif st.session_state.screen == "Pendientes":

    st.title("Tamizajes pendientes")

    pending = [
        c for c in st.session_state.local_cases
        if c.get("result") == "REPETIR"
    ]

    if not pending:
        st.success("No hay tamizajes pendientes.")
    else:
        for case in pending:
            with st.container(border=True):
                st.subheader(case["rn_id"])
                st.write(f'Resultado: {case["result"]}')
                st.write(f'Repeticiones: {case.get("repeat_count", 1)}')

                if st.button(
                    "Repetir tamizaje",
                    key=f'repeat_{case["case_id"]}'
                ):
                    st.session_state.current_case = {
                        "case_id": case["case_id"],
                        "rn_id": case["rn_id"],
                        "gestational_age": case["gestational_age"],
                        "hours_life": case["hours_life"],
                        "preductal": 89
                    }
                    st.session_state.repeat_count = case.get("repeat_count", 1)
                    go("Mano derecha")


# ============================================================
# ALERTAS
# ============================================================
elif st.session_state.screen == "Alertas":

    st.title("Cardio Alertas")

    alerts = [
        c for c in st.session_state.local_cases
        if c.get("result") == "POSITIVO"
    ]

    if not alerts:
        st.info("No hay Cardio Alertas registradas.")
    else:
        for case in alerts:
            with st.container(border=True):
                st.subheader(f'🚨 {case["rn_id"]}')
                st.write(f'Caso: {case["case_id"]}')
                st.write(f'Preductal: {case["preductal"]}%')
                st.write(f'Posductal: {case["postductal"]}%')
                st.write(f'Diferencia: {case["difference"]:.0f}%')
                st.write(f'Estado de sincronización: {case["sync_status"]}')

                if st.session_state.connection:
                    st.success("Caso disponible para revisión.")
                else:
                    st.warning("Pendiente de sincronización.")


# ============================================================
# DASHBOARD
# ============================================================
elif st.session_state.screen == "Dashboard":

    st.title("Dashboard de gestión")

    cases = st.session_state.central_cases

    total = len(cases)
    positives = len([c for c in cases if c.get("result") == "POSITIVO"])
    repeats = len([c for c in cases if c.get("result") == "REPETIR"])
    negatives = len([c for c in cases if c.get("result") == "NEGATIVO"])

    # Para la demo, se muestra un número de RN elegibles superior
    # para poder visualizar el indicador.
    eligible = max(total, 125)

    c1, c2 = st.columns(2)
    c3, c4 = st.columns(2)

    c1.metric("RN elegibles", eligible)
    c2.metric("Tamizados", total)
    c3.metric("Tamizajes positivos", positives)
    c4.metric("Tamizajes pendientes", repeats)

    st.divider()

    st.subheader("Tamizajes no realizados")

    not_done = 5
    st.metric("No realizados", not_done)

    st.write("Motivos registrados (ejemplo de prototipo):")

    reason_data = {
        "Falta de equipo": 3,
        "Falta de sensor": 1,
        "Otras causas operativas": 1
    }

    st.bar_chart(reason_data)

    st.divider()

    st.subheader("Casos sincronizados")

    if not cases:
        st.info("Aún no hay casos sincronizados.")
    else:
        for case in cases:
            st.write(
                f'**{case["rn_id"]}** — '
                f'{case["result"]} — '
                f'{case["timestamp"]}'
            )


# ============================================================
# FOOTER
# ============================================================
st.divider()
st.caption(
    "CARDIO ALERTA — Prototipo MVP Offline First para hackatón. "
    "Los resultados y reglas clínicas del prototipo deben ser validados "
    "por profesionales y por el protocolo institucional antes de cualquier uso asistencial."
)
