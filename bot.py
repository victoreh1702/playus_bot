import telebot
import sqlite3
import random
from datetime import date, datetime

TOKEN = 'TOCKEN CORRESPONDIENTE'
bot = telebot.TeleBot(TOKEN)

def init_db():
    conn = sqlite3.connect('playus.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS temporada
                 (chat_id INTEGER PRIMARY KEY, fecha_inicio TEXT, fecha_fin TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS resultados
                 (chat_id INTEGER, fecha TEXT, nombre TEXT, puntos INTEGER)''')
    conn.commit()
    conn.close()

def get_temporada(chat_id):
    conn = sqlite3.connect('playus.db')
    c = conn.cursor()
    c.execute("SELECT fecha_inicio, fecha_fin FROM temporada WHERE chat_id = ?", (chat_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return datetime.strptime(row[0], '%Y-%m-%d').date(), datetime.strptime(row[1], '%Y-%m-%d').date()
    return None, None

@bot.message_handler(commands=['start'])
def send_welcome(message):
    texto = ("¡Hola! Soy PlayUs Stats.\n\n"
             "1️⃣ Usa /temporada [Inicio] [Fin] (ej: /temporada 2026-09-12 2026-10-03)\n"
             "2️⃣ Usa /inicializar [Nombre] [Puntos] para cargar el estado actual.\n"
             "3️⃣ Usa /jornada [1º] [2º] [3º] para guardar resultados.\n"
             "4️⃣ Usa /ranking o /probabilidades.")
    bot.reply_to(message, texto)

@bot.message_handler(commands=['temporada'])
def configurar_temporada(message):
    try:
        partes = message.text.split()
        if len(partes) != 3:
            bot.reply_to(message, "❌ Uso: /temporada YYYY-MM-DD YYYY-MM-DD")
            return
        
        inicio = datetime.strptime(partes[1], '%Y-%m-%d').date()
        fin = datetime.strptime(partes[2], '%Y-%m-%d').date()
        
        conn = sqlite3.connect('playus.db')
        c = conn.cursor()
        c.execute("REPLACE INTO temporada (chat_id, fecha_inicio, fecha_fin) VALUES (?, ?, ?)", 
                  (message.chat.id, str(inicio), str(fin)))
        conn.commit()
        conn.close()
        
        bot.reply_to(message, f"✅ Temporada configurada:\nInicio: {inicio}\nFin: {fin}")
    except ValueError:
        bot.reply_to(message, "❌ Error de formato. Usa Año-Mes-Día.")

@bot.message_handler(commands=['inicializar'])
def inicializar_puntuacion(message):
    try:
        partes = message.text.split()[1:]
        if len(partes) % 2 != 0 or not partes:
            bot.reply_to(message, "❌ Formato incorrecto.")
            return

        conn = sqlite3.connect('playus.db')
        c = conn.cursor()
        
        c.execute("DELETE FROM resultados WHERE chat_id = ?", (message.chat.id,))
        
        respuesta = "✅ **Estado actual cargado:**\n\n"

        for i in range(0, len(partes), 2):
            nombre = partes[i]
            puntos = int(partes[i+1])
            c.execute("INSERT INTO resultados VALUES (?, ?, ?, ?)", (message.chat.id, 'BASE', nombre, puntos))
            respuesta += f"- {nombre}: {puntos} pts\n"

        conn.commit()
        conn.close()
        bot.reply_to(message, respuesta)
    except Exception as e:
        bot.reply_to(message, "❌ Hubo un error.")

@bot.message_handler(commands=['jornada'])
def registrar_jornada(message):
    inicio, fin = get_temporada(message.chat.id)
    if not inicio:
        bot.reply_to(message, "⚠️ Primero configura las fechas con /temporada")
        return

    try:
        grupos = message.text.split()[1:]
        if not grupos:
            bot.reply_to(message, "❌ Error de formato.")
            return

        hoy = date.today()
        dias_pasados = max(0, (hoy - inicio).days)
        bonus_porcentaje = dias_pasados * 5
        multiplicador = 1 + (bonus_porcentaje / 100.0)

        conn = sqlite3.connect('playus.db')
        c = conn.cursor()

        respuesta = f"📅 **Jornada registrada ({hoy})**\nBonus de hoy: +{bonus_porcentaje}%\n\n"
        lista_posiciones = [grupo.split('-') for grupo in grupos]

        for i, jugadores_en_grupo in enumerate(lista_posiciones):
            superados = sum(len(g) for g in lista_posiciones[i+1:])
            puntos_base = 10 + (10 * superados)
            puntos_finales = round(puntos_base * multiplicador)
            
            for nombre in jugadores_en_grupo:
                c.execute("INSERT INTO resultados VALUES (?, ?, ?, ?)", (message.chat.id, str(hoy), nombre, puntos_finales))
                respuesta += f"{i+1}º {nombre}: {puntos_finales} pts\n"

        conn.commit()
        conn.close()
        bot.reply_to(message, respuesta)
    except Exception as e:
        bot.reply_to(message, "❌ Hubo un error. Usa guiones para empates.")

@bot.message_handler(commands=['ranking'])
def mostrar_ranking(message):
    conn = sqlite3.connect('playus.db')
    c = conn.cursor()
    c.execute("SELECT nombre, SUM(puntos) FROM resultados WHERE chat_id = ? GROUP BY nombre ORDER BY SUM(puntos) DESC", (message.chat.id,))
    datos = c.fetchall()
    conn.close()

    if not datos:
        bot.reply_to(message, "Aún no hay datos registrados.")
        return

    respuesta = "🏆 **RANKING PLAYUS** 🏆\n\n"
    for i, (nombre, puntos) in enumerate(datos, start=1):
        respuesta += f"{i}. {nombre}: {puntos} pts\n"
    
    bot.reply_to(message, respuesta)

@bot.message_handler(commands=['probabilidades'])
def calcular_probabilidades(message):
    inicio, fin = get_temporada(message.chat.id)
    if not inicio:
        bot.reply_to(message, "⚠️ Primero configura las fechas con /temporada")
        return

    hoy = date.today()
    
    conn = sqlite3.connect('playus.db')
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM resultados WHERE chat_id = ? AND fecha = ?", (message.chat.id, str(hoy)))
    jugado_hoy = c.fetchone()[0] > 0

    dias_restantes = (fin - hoy).days if jugado_hoy else (fin - hoy).days + 1
    
    if dias_restantes <= 0:
        bot.reply_to(message, "🏁 La temporada ya ha terminado.")
        conn.close()
        return
        
    c.execute("SELECT nombre, SUM(puntos) FROM resultados WHERE chat_id = ? GROUP BY nombre", (message.chat.id,))
    datos_actuales = c.fetchall()
    conn.close()

    if len(datos_actuales) < 2:
        bot.reply_to(message, "Faltan datos en el ranking.")
        return

    jugadores = [fila[0] for fila in datos_actuales]
    puntos_base_dict = {fila[0]: fila[1] for fila in datos_actuales}
    
    simulaciones = 10000
    victorias = {jugador: 0 for jugador in jugadores}
    
    for _ in range(simulaciones):
        puntos_sim = puntos_base_dict.copy()
        
        for i in range(dias_restantes):
            offset = i + 1 if jugado_hoy else i
            dias_desde_inicio = (hoy - inicio).days + offset
            multiplicador = 1 + (dias_desde_inicio * 5 / 100.0)
            
            orden_aleatorio = jugadores.copy()
            random.shuffle(orden_aleatorio)
            
            total_jugadores = len(orden_aleatorio)
            for pos, nombre in enumerate(orden_aleatorio):
                puntos_ganados = 10 + 10 * (total_jugadores - (pos + 1))
                puntos_sim[nombre] += round(puntos_ganados * multiplicador)
        
        ganador = max(puntos_sim, key=puntos_sim.get)
        victorias[ganador] += 1
        
    respuesta = f"🔮 **PREDICCIÓN DE VICTORIA** 🔮\nBasado en {simulaciones} simulaciones (quedan {dias_restantes} jornadas):\n\n"
    resultados_ordenados = sorted(victorias.items(), key=lambda x: x[1], reverse=True)
    
    for nombre, ganadas in resultados_ordenados:
        porcentaje = (ganadas / simulaciones) * 100
        respuesta += f"- {nombre}: {porcentaje:.1f}%\n"
        
    bot.reply_to(message, respuesta)

init_db()
bot.infinity_polling()