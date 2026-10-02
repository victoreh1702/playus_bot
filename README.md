# PlayUs Stats Bot 🤖📊

Un bot de Telegram desarrollado íntegramente en Python diseñado para gestionar sistemas de puntuación competitivos en grupos. Automatiza el registro de resultados, calcula bonificaciones dinámicas basadas en el calendario y utiliza simulaciones de Montecarlo para predecir matemáticamente las probabilidades de victoria a final de temporada.

## ☁️ Entorno de Despliegue (Oracle Cloud)

Este proyecto está diseñado para ejecutarse 24/7 en un servidor remoto con un consumo mínimo de recursos. Actualmente se encuentra desplegado en una instancia de **Oracle Cloud Infrastructure (OCI)** con sistema operativo Ubuntu. 

> **Nota de Infraestructura:** El bot corre como un proceso en segundo plano (daemon) gestionado mediante `nohup`. Su bajo impacto en CPU y memoria RAM permite que conviva en la misma máquina virtual con otros servicios de red exigentes, como un túnel VPN WireGuard, sin generar latencia ni interferencias.

---

## 🧠 Arquitectura y Programación

El núcleo del bot está construido en **Python 3**, utilizando la librería `pyTelegramBotAPI` (Telebot) para la comunicación mediante *long polling* con la API de Telegram. 

La programación resuelve tres grandes desafíos lógicos:

1. **Gestión Inteligente de Fechas (El multiplicador dinámico):** 
   El sistema calcula un bonus que aumenta un +5% por cada día transcurrido desde el inicio de la temporada. Para evitar desfases lógicos al calcular predicciones, el código inspecciona la base de datos para diferenciar entre "puntuaciones base" (puntos introducidos manualmente a mitad de temporada) y "jornadas jugadas", ajustando dinámicamente los días restantes reales sin duplicar simulaciones.
2. **Lógica de Empates:** 
   El registro de jornadas (`/jornada`) implementa un sistema de partición de cadenas de texto (ej. `Jugador1-Jugador2 Jugador3`). El algoritmo detecta los guiones, agrupa a los jugadores empatados en la misma posición y recalcula automáticamente los puntos base (10 por participar + 10 por cada rival superado estrictamente) antes de aplicar el multiplicador del día.
3. **Simulación de Montecarlo (Algoritmo Predictivo):** 
   El comando `/probabilidades` no se basa en medias simples. Toma el "colchón" de puntos actuales, calcula los días exactos que faltan hasta el cierre, y ejecuta **10.000 iteraciones** simulando clasificaciones aleatorias para las jornadas restantes. Finalmente, devuelve el porcentaje exacto de veces que cada jugador se corona campeón en esos 10.000 universos paralelos.

---

## 🗄️ Estructura de la Base de Datos

Para garantizar la persistencia y la velocidad, el bot integra **SQLite3**, una base de datos relacional ligera que no requiere un motor de servidor independiente. 

El diseño se basa en un aislamiento total mediante el `chat_id` de Telegram, lo que permite que el bot funcione en múltiples grupos a la vez sin que los datos se crucen. Se compone de dos tablas principales que se auto-generan en la primera ejecución:

*   **Tabla `temporada`**
    *   `chat_id` (INTEGER PRIMARY KEY): Identificador único del grupo de Telegram.
    *   `fecha_inicio` (TEXT): Fecha de arranque (formato YYYY-MM-DD).
    *   `fecha_fin` (TEXT): Fecha de cierre de la temporada.

*   **Tabla `resultados`**
    *   `chat_id` (INTEGER): Vinculado al grupo donde se registró la partida.
    *   `fecha` (TEXT): Día exacto de la inserción. Utiliza la etiqueta especial `'BASE'` cuando se introducen puntos iniciales para no alterar el contador de días jugados.
    *   `nombre` (TEXT): Identificador del jugador.
    *   `puntos` (INTEGER): Puntuación final calculada tras sumar base, bonus por victorias y el multiplicador porcentual del día.

---

## 📋 Comandos Disponibles

| Comando | Descripción | Ejemplo de Uso |
| :--- | :--- | :--- |
| `/start` | Muestra el panel de ayuda y la estructura de comandos. | `/start` |
| `/temporada` | Define las fechas límite del torneo para el grupo actual. | `/temporada 2026-09-12 2026-10-03` |
| `/inicializar` | Inyecta puntuaciones de una temporada en curso usando la etiqueta 'BASE'. | `/inicializar Victor 577 Cristina 548` |
| `/jornada` | Registra resultados diarios, soporta empates y aplica el multiplicador actual. | `/jornada Victor Cristina-Alvaro` |
| `/ranking` | Agrupa y suma la base de datos para mostrar la clasificación actual. | `/ranking` |
| `/probabilidades`| Lanza las 10.000 simulaciones de Montecarlo y muestra el % de victoria. | `/probabilidades` |

---

## ⚙️ Puesta en Marcha en el Servidor

Para levantar el servicio desde cero en un entorno Linux/Ubuntu mediante SSH:

1. Crear el entorno virtual e instalar las dependencias:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install pyTelegramBotAPI

2. Crear el archivo bot.py, pegar el código fuente y configurar el Token de la API de Telegram (proporcionado por BotFather) directamente en la variable TOKEN.

3. Lanzar el proceso en segundo plano para poder cerrar la terminal (sesión SSH) sin que el bot se detenga. El comando es:
    nohup python bot.py &
Con este comando, el bot queda operando de forma ininterrumpida y listo para interactuar en Telegram.
   