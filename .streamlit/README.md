# Cardio Alerta Perú

## Hackatón en Salud — INSNSB

**“Año de la Esperanza y el Fortalecimiento de la Democracia”**

Cardio Alerta Perú es una solución desarrollada en el marco de la **Hackatón en Salud**, impulsada por el **Instituto Nacional de Salud del Niño San Borja (INSNSB)**, en articulación con la Secretaría de Gobierno y Transformación Digital de la PCM, la PUCP, ESAN y aliados del ecosistema de innovación.

La propuesta responde al desafío:

> **Cardio Alerta Perú: cuidando Corazones desde el primer latido**

### Desafío

¿Cómo podríamos mejorar el tamizaje y la identificación temprana de pacientes pediátricos con sospecha de cardiopatías críticas, para que sean orientados y derivados de manera oportuna y segura, logrando reducir retrasos en la evaluación y atención especializada?

## Solución

**Cardio Alerta Perú** busca contribuir a la identificación temprana de señales asociadas a posibles cardiopatías críticas en pacientes pediátricos, mediante una solución tecnológica que facilite el análisis de información y apoye la toma de decisiones durante el proceso de tamizaje.

La propuesta está orientada a fortalecer la detección oportuna y contribuir a una derivación más segura y eficiente hacia los servicios especializados.

## Principales características

* Análisis de información relacionada con factores cardiovasculares pediátricos.
* Visualización interactiva de información.
* Indicadores para facilitar la identificación de patrones y señales de alerta.
* Filtros para explorar diferentes características de los datos.
* Interfaz web desarrollada con Streamlit.
* Arquitectura preparada para futuras mejoras y ampliaciones.
* Componentes desarrollados disponibles para consulta y reutilización.

## Tecnologías

* Python
* Streamlit
* Pandas
* Plotly
* Git
* GitHub

## Estructura del proyecto

```text
cardio-alerta/
│
├── .streamlit/
│   └── config.toml
│
├── app.py
├── requirements.txt
└── README.md
```

## Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/Marceloo1765/cardio-alerta.git
cd cardio-alerta
```

### 2. Crear un entorno virtual

```bash
python -m venv venv
```

En Windows:

```bash
venv\Scripts\activate
```

En macOS o Linux:

```bash
source venv/bin/activate
```

### 3. Instalar las dependencias

```bash
pip install -r requirements.txt
```

## Ejecución

Para iniciar la aplicación:

```bash
streamlit run src/app.py
```

La aplicación se abrirá en el navegador mediante la dirección local proporcionada por Streamlit.

## Configuración

La configuración visual de la aplicación se encuentra en:

```text
.streamlit/config.toml
```

Este archivo permite establecer parámetros relacionados con la apariencia y configuración de Streamlit.

## Hackatón en Salud

La propuesta fue desarrollada bajo el enfoque de innovación abierta y trabajo multidisciplinario promovido por la **Hackatón en Salud del INSNSB**.

El proyecto considera los principales criterios de evaluación establecidos para la Hackatón:

* **Innovación:** propuesta de un enfoque tecnológico para abordar el problema identificado.
* **Impacto en salud:** potencial contribución a la identificación temprana de cardiopatías pediátricas.
* **Viabilidad técnica y económica:** posibilidad de desarrollo e implementación progresiva de la solución.
* **Enfoque en el usuario:** consideración de las necesidades de los actores involucrados en el proceso de tamizaje y atención.
* **Calidad de la presentación:** comunicación clara de la problemática, solución e impacto esperado.

## Consideraciones sobre datos

La solución debe utilizar información de manera ética y responsable, respetando los principios de privacidad, confidencialidad y anonimización.

No se deberán incorporar al repositorio datos personales, información clínica identificable, credenciales ni información institucional restringida.

Las fuentes externas utilizadas deberán ser debidamente identificadas y referenciadas.

## Licencia

Los componentes desarrollados en el marco de la Hackatón se ponen a disposición bajo un enfoque de innovación abierta, de acuerdo con las condiciones establecidas en las bases de participación del evento.

## Autor

**Neo Link**

## Repositorio

[GitHub — Cardio Alerta Perú](https://github.com/Marceloo1765/cardio-alerta)
