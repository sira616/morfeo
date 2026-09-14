"""Corpus de consejos sobre sueño.

Cada consejo lleva su **nivel de evidencia**, y se enseña. Es una decisión de
producto, no un adorno: la American Academy of Sleep Medicine recomienda no usar la
higiene del sueño como terapia única para el insomnio crónico, porque los consejos
sueltos no son un tratamiento. Una app que presenta "ventila la habitación" y "la
cama es solo para dormir" con el mismo peso está mintiendo por omisión.

Lo que sí tiene respaldo fuerte es la parte conductual — control de estímulos y
restricción de sueño — que es la que ya aplica `app/domain/bedtime.py`. Estos consejos
acompañan; no sustituyen.

`applies_when` conecta cada consejo con una señal de los datos del usuario, para
priorizar lo que hoy le viene a cuento antes de rellenar con el resto.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Evidence = Literal["alta", "media", "baja"]


@dataclass(frozen=True)
class Tip:
    id: str
    title: str
    body: str
    category: str
    evidence: Evidence
    source: str
    # Señal que lo hace relevante hoy. None = siempre elegible.
    applies_when: str | None = None


# --- Señales que pueden activar un consejo ------------------------------------
# Las calcula `app/services/tips_service.py` a partir de la recomendación del día.
SIGNAL_CAFFEINE_LATE = "cafeina_tarde"
SIGNAL_ALCOHOL = "alcohol"
SIGNAL_LATE_EXERCISE = "ejercicio_tarde"
SIGNAL_LOW_EFFICIENCY = "eficiencia_baja"
SIGNAL_HIGH_LATENCY = "latencia_alta"
SIGNAL_IRREGULAR = "irregularidad"
SIGNAL_LONG_NAP = "siesta_larga"
SIGNAL_HIGH_DEBT = "deuda_alta"
SIGNAL_LOW_MOOD = "animo_bajo"
# El cronotipo declarado. No sale de los datos como el resto: lo elige la persona
# en el perfil. Prioriza consejos pertinentes a su ritmo sin tocar el cálculo.
SIGNAL_CHRONOTYPE_OWL = "cronotipo_buho"
SIGNAL_CHRONOTYPE_LARK = "cronotipo_alondra"


TIPS: tuple[Tip, ...] = (
    # --- Ritmo -----------------------------------------------------------------
    Tip(
        id="ritmo-ancla",
        title="La hora de levantarte es el ancla, no la de acostarte",
        body=(
            "Mantenerla dentro de media hora, también el fin de semana, es lo que más "
            "estabiliza el sueño. En 61.000 adultos del UK Biobank, el grupo con horarios "
            "más regulares tuvo un 30% menos de mortalidad por cualquier causa, y la "
            "regularidad predijo mejor que las horas dormidas."
        ),
        category="ritmo",
        evidence="alta",
        source="Windred et al., SLEEP 2024 (UK Biobank, n≈61.000)",
    ),
    Tip(
        id="ritmo-finde",
        title="Dormir de más el sábado no paga la deuda",
        body=(
            "Desplaza tu reloj interno hacia la noche y hace que el domingo te cueste más "
            "dormirte. Si arrastras sueño, es mejor una siesta corta que dos horas de más "
            "por la mañana."
        ),
        category="ritmo",
        evidence="media",
        source="Literatura sobre jet lag social",
        applies_when=SIGNAL_IRREGULAR,
    ),
    Tip(
        id="ritmo-deuda",
        title="La deuda se paga a plazos",
        body=(
            "Recuperar sueño funciona repartido en varias noches, no de golpe. Una noche "
            "de diez horas tras una semana corta desordena el ritmo y suele traer una "
            "mala noche detrás."
        ),
        category="ritmo",
        evidence="media",
        source="Consenso en cronobiología del sueño",
        applies_when=SIGNAL_HIGH_DEBT,
    ),
    # --- La cama ---------------------------------------------------------------
    Tip(
        id="cama-veinte-minutos",
        title="Si llevas un rato despierta, levántate",
        body=(
            "Unos veinte minutos sin dormirte: sal de la cama y haz algo tranquilo con poca "
            "luz hasta que vuelva el sueño. Y no los cronometres, adivínalos: mirar el reloj "
            "activa la cabeza y hace justo lo contrario de lo que buscas."
        ),
        category="cama",
        evidence="alta",
        source="Control de estímulos (Bootzin); protocolos TCC-I de Stanford y UPenn",
        applies_when=SIGNAL_HIGH_LATENCY,
    ),
    Tip(
        id="cama-solo-dormir",
        title="La cama, para dormir",
        body=(
            "Trabajar, ver series o dar vueltas a las cosas en la cama enseña al cerebro que "
            "ese sitio es para estar despierta. Deshacer esa asociación es la mitad del "
            "trabajo en el insomnio de inicio."
        ),
        category="cama",
        evidence="alta",
        source="Control de estímulos, componente central de la TCC-I",
        applies_when=SIGNAL_LOW_EFFICIENCY,
    ),
    Tip(
        id="cama-no-adelantar",
        title="Acostarte antes para compensar suele salir mal",
        body=(
            "Si no tienes sueño, adelantar la hora solo alarga el rato despierta en la cama. "
            "Es exactamente lo que Morfeo evita cuando te acorta la ventana."
        ),
        category="cama",
        evidence="alta",
        source="Restricción de sueño (TCC-I)",
        applies_when=SIGNAL_LOW_EFFICIENCY,
    ),
    Tip(
        id="cama-sueno-no-hora",
        title="Métete en la cama con sueño, no con la hora",
        body=(
            "La ventana que te doy es una oportunidad, no una orden. Si a esa hora estás "
            "completamente despejada, espera veinte minutos más haciendo algo tranquilo."
        ),
        category="cama",
        evidence="alta",
        source="Control de estímulos (TCC-I)",
    ),
    Tip(
        id="cama-tapa-reloj",
        title="Gira el despertador",
        body=(
            "Calcular cuánto te queda por dormir es una de las cosas que más activan a las "
            "tres de la mañana. Si no ves la hora, no puedes hacer la cuenta."
        ),
        category="cama",
        evidence="media",
        source="Protocolos de control de estímulos",
        applies_when=SIGNAL_HIGH_LATENCY,
    ),
    # --- Sustancias ------------------------------------------------------------
    Tip(
        id="cafeina-vida-media",
        title="La cafeína dura más de lo que parece",
        body=(
            "Su vida media son 3 a 6 horas, pero varía muchísimo: hay quien la elimina en 2 "
            "y quien tarda 10. En un ensayo de 2024, 400 mg (unos cuatro cafés) alteraron la "
            "arquitectura del sueño incluso tomados 12 horas antes; 100 mg hasta 4 horas "
            "antes no hicieron nada."
        ),
        category="sustancias",
        evidence="alta",
        source="Gardiner et al., SLEEP 2024 (ensayo cruzado aleatorizado)",
        applies_when=SIGNAL_CAFFEINE_LATE,
    ),
    Tip(
        id="cafeina-dosis",
        title="Importa la dosis, no solo la hora",
        body=(
            "Un cortado a media tarde no es lo mismo que tres cafés. Si no quieres mover la "
            "hora, prueba a bajar la cantidad: el efecto sobre el sueño depende de las dos "
            "cosas."
        ),
        category="sustancias",
        evidence="alta",
        source="Gardiner et al., SLEEP 2024",
        applies_when=SIGNAL_CAFFEINE_LATE,
    ),
    Tip(
        id="alcohol-segunda-mitad",
        title="El alcohol te duerme y luego te despierta",
        body=(
            "Acorta lo que tardas en dormirte y aumenta el sueño profundo al principio, pero "
            "suprime el REM y lo devuelve de golpe cuando se metaboliza, unas 4 o 5 horas "
            "después. De ahí los despertares y los sueños raros de madrugada."
        ),
        category="sustancias",
        evidence="alta",
        source="Metaanálisis en Sleep Medicine Reviews, 2024",
        applies_when=SIGNAL_ALCOHOL,
    ),
    Tip(
        id="alcohol-no-compensa",
        title="Una noche con alcohol no se compensa acostándote antes",
        body=(
            "El problema no es la cantidad de sueño, es cómo se rompe la segunda mitad. Más "
            "tiempo en la cama no lo arregla."
        ),
        category="sustancias",
        evidence="media",
        source="Metaanálisis en Sleep Medicine Reviews, 2024",
        applies_when=SIGNAL_ALCOHOL,
    ),
    # --- Luz -------------------------------------------------------------------
    Tip(
        id="luz-manana",
        title="Diez minutos de calle nada más levantarte",
        body=(
            "La luz de la mañana adelanta tu reloj interno, y adelantarlo una hora se traduce "
            "en unos 36 minutos menos para dormirte por la noche. Un día nublado en la calle "
            "sigue teniendo mucha más luz que tu salón."
        ),
        category="luz",
        evidence="alta",
        source="Estudios de adelanto de fase con luz brillante matutina",
    ),
    Tip(
        id="luz-noche",
        title="Baja las luces una hora antes, no solo la pantalla",
        body=(
            "La luz de tarde y noche retrasa la melatonina: en un estudio, casi una hora. "
            "Apagar el techo y dejar lámparas bajas hace más que cualquier filtro."
        ),
        category="luz",
        evidence="alta",
        source="Estudios de supresión de melatonina por luz vespertina",
    ),
    Tip(
        id="luz-gafas-azules",
        title="Las gafas de luz azul están sobrevaloradas",
        body=(
            "La revisión Cochrane de 2023 no encontró evidencia convincente de que mejoren el "
            "sueño. Un lector electrónico a brillo máximo necesitó cuatro horas para retrasar "
            "el sueño diez minutos. Baja el brillo y la luz de la habitación: eso sí pesa."
        ),
        category="luz",
        evidence="alta",
        source="Revisión Cochrane 2023 sobre lentes que filtran luz azul",
    ),
    Tip(
        id="luz-contenido",
        title="Con el móvil, el problema suele ser el contenido",
        body=(
            "Lo que te desvela rara vez es la luz de la pantalla: es discutir por mensaje, "
            "mirar el correo del trabajo o encadenar vídeos. Cambia qué haces antes de "
            "obsesionarte con los nits."
        ),
        category="luz",
        evidence="media",
        source="Interpretación de la literatura sobre pantallas y sueño",
    ),
    # --- Entorno ---------------------------------------------------------------
    Tip(
        id="entorno-temperatura",
        title="Mejor fresco que templado",
        body=(
            "Para dormir, el cuerpo necesita bajar su temperatura central un grado o dos. "
            "Entre 18 y 21 °C es el rango que suele recomendarse; por encima, la eficiencia "
            "del sueño cae de forma medible."
        ),
        category="entorno",
        evidence="media",
        source="Estudios de temperatura ambiente y eficiencia del sueño",
    ),
    Tip(
        id="entorno-ruido",
        title="El ruido es de lo peor documentado",
        body=(
            "De todas las recomendaciones clásicas de higiene del sueño, el efecto de un "
            "entorno ruidoso es de los mejor respaldados. Unos tapones baratos rinden más que "
            "casi cualquier gadget."
        ),
        category="entorno",
        evidence="alta",
        source="Revisiones sobre higiene del sueño",
    ),
    Tip(
        id="entorno-oscuridad",
        title="Oscuridad de verdad",
        body=(
            "Cualquier luz, incluida la del pasillo o el piloto del router, llega a la retina "
            "con los ojos cerrados. Un antifaz resuelve lo que una persiana no."
        ),
        category="entorno",
        evidence="media",
        source="Revisiones sobre higiene del sueño",
    ),
    # --- Actividad -------------------------------------------------------------
    Tip(
        id="actividad-ejercicio-tarde",
        title="Entrenar por la tarde no te va a estropear la noche",
        body=(
            "Un metaanálisis de 23 estudios no encontró diferencias en latencia, eficiencia "
            "ni duración del sueño. La única excepción es el ejercicio vigoroso que termina "
            "menos de una hora antes de acostarte, y aun así retrasa el inicio unos catorce "
            "minutos."
        ),
        category="actividad",
        evidence="alta",
        source="Metaanálisis sobre ejercicio vespertino y sueño",
        applies_when=SIGNAL_LATE_EXERCISE,
    ),
    Tip(
        id="actividad-ducha",
        title="Ducha caliente una o dos horas antes",
        body=(
            "De todo lo que puedes hacer, es lo que más rinde por el esfuerzo que cuesta: "
            "diez minutos bastan y acortan lo que tardas en dormirte alrededor de un 36%. "
            "Funciona por el rebote: el calor dilata los vasos y el cuerpo pierde temperatura "
            "más rápido después."
        ),
        category="actividad",
        evidence="alta",
        source="Haghayegh et al., Sleep Medicine Reviews 2019 (metaanálisis, 13 ensayos)",
    ),
    Tip(
        id="actividad-mover",
        title="Moverte durante el día pesa más que cualquier ritual nocturno",
        body=(
            "La actividad física regular mejora el sueño de forma consistente. No hace falta "
            "que sea a una hora concreta; hace falta que sea a menudo."
        ),
        category="actividad",
        evidence="alta",
        source="Revisiones sobre actividad física y calidad del sueño",
    ),
    # --- Siestas ---------------------------------------------------------------
    Tip(
        id="siesta-corta",
        title="Siesta de veinte minutos y antes de las tres",
        body=(
            "Por debajo de veinte minutos te quedas en sueño ligero y despiertas despejada. "
            "Una oportunidad de 25 minutos no afectó a la noche siguiente en estudios "
            "controlados; pasar de una hora sí la estropea."
        ),
        category="siestas",
        evidence="media",
        source="Estudios sobre duración de siesta e inercia del sueño",
        applies_when=SIGNAL_LONG_NAP,
    ),
    # --- Mente -----------------------------------------------------------------
    Tip(
        id="mente-preocupacion-constructiva",
        title="Preocúpate a propósito, pero antes",
        body=(
            "Quince minutos un par de horas antes de acostarte: escribe en una columna lo que "
            "te ronda y en otra el siguiente paso de cada cosa. Dobla el papel y déjalo. No "
            "es dejar de pensar, es terminar de pensar."
        ),
        category="mente",
        evidence="media",
        source="Ensayos sobre preocupación constructiva añadida a terapia conductual",
        applies_when=SIGNAL_LOW_MOOD,
    ),
    Tip(
        id="mente-esfuerzo",
        title="Intentar dormirte es lo que no te deja",
        body=(
            "Esforzarse en conciliar el sueño es de las conductas peor valoradas por la "
            "evidencia. Si te descubres intentándolo, el objetivo cambia: descansar tumbada "
            "sin dormir ya vale."
        ),
        category="mente",
        evidence="alta",
        source="Revisiones sobre higiene del sueño e intención paradójica",
        applies_when=SIGNAL_HIGH_LATENCY,
    ),
    Tip(
        id="mente-tarea-dificil",
        title="Nada de tareas mentalmente exigentes justo antes",
        body=(
            "Cerrar la declaración, discutir por WhatsApp o resolver un bug complicado deja "
            "la cabeza encendida. Es otro de los puntos con evidencia sólida dentro de la "
            "higiene del sueño."
        ),
        category="mente",
        evidence="alta",
        source="Revisiones sobre higiene del sueño",
    ),
    Tip(
        id="mente-rutina",
        title="Una rutina corta y siempre igual",
        body=(
            "Veinte minutos de las mismas tres cosas, en el mismo orden. El valor no está en "
            "cuáles sean, sino en que se repitan: acaban funcionando como señal."
        ),
        category="mente",
        evidence="media",
        source="Consenso clínico sobre rutinas presueño",
    ),
    # --- Expectativas ----------------------------------------------------------
    Tip(
        id="expectativa-ocho-horas",
        title="Las ocho horas son una media, no una cuota",
        body=(
            "El rango sano es amplio y personal. Perseguir una cifra concreta añade presión, "
            "y la presión es de lo que peor sienta al sueño."
        ),
        category="expectativas",
        evidence="media",
        source="Consenso sobre necesidad de sueño en adultos",
    ),
    Tip(
        id="expectativa-noche-mala",
        title="Una noche mala no significa nada",
        body=(
            "La variabilidad entre noches es normal, también en quien duerme bien. Lo que "
            "cuenta es la tendencia de dos semanas, no la de ayer."
        ),
        category="expectativas",
        evidence="media",
        source="Consenso clínico",
    ),
    Tip(
        id="expectativa-higiene-no-cura",
        title="Estos consejos no curan el insomnio, y conviene saberlo",
        body=(
            "La Academia Americana de Medicina del Sueño recomienda no usar la higiene del "
            "sueño como tratamiento único del insomnio crónico. Lo que funciona es la parte "
            "conductual: acortar la ventana y reservar la cama para dormir, que es lo que "
            "Morfeo calcula."
        ),
        category="expectativas",
        evidence="alta",
        source="Guía de práctica clínica de la AASM, 2021",
    ),
    # --- Señales de alarma -----------------------------------------------------
    Tip(
        id="alarma-apnea",
        title="Ronquido fuerte con pausas: consúltalo",
        body=(
            "Si roncas fuerte, alguien nota que dejas de respirar o te despiertas con "
            "sensación de ahogo, y además estás somnolienta de día, merece una valoración "
            "médica. La apnea no se arregla con hábitos."
        ),
        category="alarma",
        evidence="alta",
        source="Criterios de la AASM para sospecha de apnea obstructiva",
    ),
    Tip(
        id="alarma-insomnio-cronico",
        title="Tres noches por semana, tres meses: eso tiene nombre",
        body=(
            "Es la definición de insomnio crónico, y tiene tratamiento de primera línea: la "
            "terapia cognitivo-conductual para el insomnio, que funciona mejor y más tiempo "
            "que la medicación. Merece la pena buscarla."
        ),
        category="alarma",
        evidence="alta",
        source="Guía de práctica clínica de la AASM, 2021",
        applies_when=SIGNAL_LOW_EFFICIENCY,
    ),
    Tip(
        id="cronotipo-buho-luz-manana",
        title="Si eres de noche, la luz de la mañana es tu mejor palanca",
        body=(
            "El cronotipo tardío no se corrige a voluntad, pero la luz brillante nada más "
            "levantarte adelanta el reloj interno. Diez o quince minutos de luz de día al "
            "despertar, mejor fuera, empujan tu ritmo hacia adelante más que cualquier "
            "esfuerzo por acostarte antes."
        ),
        category="ritmo",
        evidence="media",
        source="Revisiones sobre fototerapia y fase circadiana",
        applies_when=SIGNAL_CHRONOTYPE_OWL,
    ),
    Tip(
        id="cronotipo-alondra-luz-tarde",
        title="Si madrugas de forma natural, cuida la luz de la tarde",
        body=(
            "El cronotipo temprano tiende a despertarse de madrugada sin querer. Recibir "
            "algo de luz al final de la tarde retrasa un poco el reloj y ayuda a no "
            "abrir los ojos a las cinco. Evita, eso sí, la pantalla brillante ya en la cama."
        ),
        category="ritmo",
        evidence="media",
        source="Revisiones sobre fototerapia y fase circadiana",
        applies_when=SIGNAL_CHRONOTYPE_LARK,
    ),
)

TIPS_BY_ID = {tip.id: tip for tip in TIPS}
