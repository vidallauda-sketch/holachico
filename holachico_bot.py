import json
import os
import logging
import asyncio
from aiohttp import web
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

# ==============================
#   CONFIGURACIÓN
# ==============================

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
PORT = int(os.getenv("PORT", "8080"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # Ej: https://tu-app.railway.app

if not TOKEN:
    raise ValueError("❌ BOT_TOKEN no está configurado")

# ==============================
#   ARCHIVOS JSON
# ==============================

PERFILES_FILE = "perfiles.json"
LIKES_FILE = "likes.json"
CHATS_FILE = "chats.json"
SUGERENCIAS_FILE = "sugerencias.json"

_file_lock = asyncio.Lock()

async def cargar_json(ruta):
    async with _file_lock:
        if not os.path.exists(ruta):
            return {}
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}

async def guardar_json(ruta, datos):
    async with _file_lock:
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)

async def cargar_perfiles(): return await cargar_json(PERFILES_FILE)
async def guardar_perfiles(d): await guardar_json(PERFILES_FILE, d)
async def cargar_likes(): return await cargar_json(LIKES_FILE)
async def guardar_likes(d): await guardar_json(LIKES_FILE, d)
async def cargar_chats(): return await cargar_json(CHATS_FILE)
async def guardar_chats(d): await guardar_json(CHATS_FILE, d)
async def cargar_sugerencias(): return await cargar_json(SUGERENCIAS_FILE)
async def guardar_sugerencias(d): await guardar_json(SUGERENCIAS_FILE, d)

def asegurar_usuario_en_likes(likes, user_id):
    if user_id not in likes:
        likes[user_id] = {"dados": [], "recibidos": []}

# ==============================
#   ESTADOS
# ==============================

FOTO, EDAD, CIUDAD, BUSCA, DESCRIPCION, ROL, ESTATURA = range(7)

# ==============================
#   COMANDOS
# ==============================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🌈 *Bienvenido a HolaChico* 🌈\n\n"
        "📌 Comandos:\n"
        "• /perfil – crear o actualizar tu perfil\n"
        "• /ver – ver otros perfiles\n"
        "• /likes – ver quién te dio me gusta\n"
        "• /matches – ver tus matches\n"
        "• /chat <id> – abrir chat con un match\n"
        "• /cerrarchat – cerrar el chat actual\n"
        "• /borrar – eliminar tu perfil\n"
        "• /sugerencia <texto> – enviar sugerencia\n\n"
        "Disfruta y conecta con respeto. 💬",
        parse_mode="Markdown"
    )

# ==============================
#   CREACIÓN DE PERFIL
# ==============================

async def perfil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data["fotos"] = []
    await update.message.reply_text(
        "📸 Envíame *todas las fotos que quieras* para tu perfil.\n"
        "Cuando termines, escribe /listo.",
        parse_mode="Markdown"
    )
    return FOTO

async def recibir_foto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file_id = update.message.photo[-1].file_id
    context.user_data.setdefault("fotos", []).append(file_id)
    await update.message.reply_text("📸 Foto añadida. Envía otra o escribe /listo.")
    return FOTO

async def fotos_listas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("fotos"):
        await update.message.reply_text("Necesitas enviar al menos una foto.")
        return FOTO
    await update.message.reply_text("📅 ¿Qué *edad* tienes?", parse_mode="Markdown")
    return EDAD

async def recibir_edad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()
    if not texto.isdigit() or not (18 <= int(texto) <= 99):
        await update.message.reply_text("❌ Edad válida (18-99):")
        return EDAD
    context.user_data["edad"] = texto
    await update.message.reply_text("📍 ¿En qué *ciudad* estás?", parse_mode="Markdown")
    return CIUDAD

async def recibir_ciudad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["ciudad"] = update.message.text.strip()
    await update.message.reply_text("💘 ¿Qué *buscas*? (amigos, relación, charlar…)", parse_mode="Markdown")
    return BUSCA

async def recibir_busca(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["busca"] = update.message.text.strip()
    await update.message.reply_text("📝 Escribe una *descripción* sobre ti.", parse_mode="Markdown")
    return DESCRIPCION

async def recibir_descripcion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["descripcion"] = update.message.text.strip()
    await update.message.reply_text(
        "🎭 ¿Cuál es tu *rol*?\n- activo\n- pasivo\n- inter\n- inter activo\n- inter pasivo",
        parse_mode="Markdown"
    )
    return ROL

async def recibir_rol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    validos = ["activo", "pasivo", "inter", "inter activo", "inter pasivo"]
    rol = update.message.text.strip().lower()
    if rol not in validos:
        await update.message.reply_text("❌ Rol no válido. Elige uno de la lista:")
        return ROL
    context.user_data["rol"] = rol
    await update.message.reply_text("📏 ¿Cuál es tu *estatura*? (ej: 1.78)", parse_mode="Markdown")
    return ESTATURA

async def recibir_estatura(update: Update, context: ContextTypes.DEFAULT_TYPE):
    estatura = update.message.text.strip().replace(",", ".")
    try:
        val = float(estatura)
        if not (1.0 <= val <= 2.5):
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Estatura no válida (ej: 1.78):")
        return ESTATURA

    context.user_data["estatura"] = estatura
    user_id = str(update.effective_user.id)
    
    perfiles = await cargar_perfiles()
    perfiles[user_id] = {
        "fotos": context.user_data["fotos"],
        "edad": context.user_data["edad"],
        "ciudad": context.user_data["ciudad"],
        "busca": context.user_data["busca"],
        "descripcion": context.user_data["descripcion"],
        "rol": context.user_data["rol"],
        "estatura": estatura,
    }
    await guardar_perfiles(perfiles)

    p = perfiles[user_id]
    texto = (
        f"📸 *Perfil listo*\n\n"
        f"Edad: {p['edad']}\n"
        f"Ciudad: {p['ciudad']}\n"
        f"Busca: {p['busca']}\n"
        f"Descripción: {p['descripcion']}\n"
        f"Rol: {p['rol']}\n"
        f"Estatura: {p['estatura']}"
    )
    await update.message.reply_photo(photo=p["fotos"][0], caption=texto, parse_mode="Markdown")
    return ConversationHandler.END

# ==============================
#   VER PERFILES
# ==============================

def construir_texto_perfil(p):
    return (
        f"Edad: {p['edad']}\n"
        f"Ciudad: {p['ciudad']}\n"
        f"Busca: {p['busca']}\n"
        f"Descripción: {p['descripcion']}\n"
        f"Rol: {p['rol']}\n"
        f"Estatura: {p['estatura']}"
    )

async def ver(update: Update, context: ContextTypes.DEFAULT_TYPE):
    perfiles = await cargar_perfiles()
    user_id = str(update.effective_user.id)
    
    ids = [uid for uid in perfiles.keys() if uid != user_id]
    
    if not ids:
        await update.message.reply_text("😕 Aún no hay otros perfiles.")
        return

    context.user_data["lista_perfiles"] = ids
    context.user_data["indice"] = 0
    context.user_data["foto_index"] = 0

    await mostrar_perfil(update, context)

async def mostrar_perfil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    perfiles = await cargar_perfiles()
    ids = context.user_data.get("lista_perfiles", [])
    indice = context.user_data.get("indice", 0)
    
    if not ids or indice >= len(ids):
        await update.message.reply_text("No hay más perfiles.")
        return

    user_id = ids[indice]
    p = perfiles.get(user_id)
    if not p:
        await update.message.reply_text("Perfil no encontrado.")
        return

    texto = construir_texto_perfil(p)
    fotos = p.get("fotos", [])
    
    if not fotos:
        await update.message.reply_text("Este perfil no tiene fotos.")
        return

    context.user_data["foto_index"] = 0

    botones = [
        [InlineKeyboardButton("⬅️", callback_data="foto_prev"),
         InlineKeyboardButton("➡️", callback_data="foto_next")],
        [InlineKeyboardButton("❤️ Me gusta", callback_data=f"like_{user_id}"),
         InlineKeyboardButton("➡️ Siguiente", callback_data="siguiente")]
    ]

    await update.message.reply_photo(
        photo=fotos[0],
        caption=texto,
        reply_markup=InlineKeyboardMarkup(botones)
    )

async def galeria_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    perfiles = await cargar_perfiles()
    ids = context.user_data.get("lista_perfiles", [])
    indice = context.user_data.get("indice", 0)

    if not ids or indice >= len(ids):
        return

    user_id = ids[indice]
    p = perfiles.get(user_id)
    if not p:
        return

    fotos = p.get("fotos", [])
    if not fotos:
        return

    foto_index = context.user_data.get("foto_index", 0)

    if query.data == "foto_next":
        foto_index = (foto_index + 1) % len(fotos)
    elif query.data == "foto_prev":
        foto_index = (foto_index - 1) % len(fotos)

    context.user_data["foto_index"] = foto_index
    texto = construir_texto_perfil(p)

    botones = [
        [InlineKeyboardButton("⬅️", callback_data="foto_prev"),
         InlineKeyboardButton("➡️", callback_data="foto_next")],
        [InlineKeyboardButton("❤️ Me gusta", callback_data=f"like_{user_id}"),
         InlineKeyboardButton("➡️ Siguiente", callback_data="siguiente")]
    ]

    await query.edit_message_media(
        media=InputMediaPhoto(fotos[foto_index], caption=texto),
        reply_markup=InlineKeyboardMarkup(botones)
    )

# ==============================
#   BOTONES: LIKE / SIGUIENTE
# ==============================

async def botones(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    from_id = str(query.from_user.id)

    perfiles = await cargar_perfiles()
    likes = await cargar_likes()
    asegurar_usuario_en_likes(likes, from_id)

    if data == "siguiente":
        context.user_data["indice"] = context.user_data.get("indice", 0) + 1
        ids = context.user_data.get("lista_perfiles", [])
        
        if context.user_data["indice"] >= len(ids):
            context.user_data["indice"] = 0

        indice = context.user_data["indice"]
        if not ids or indice >= len(ids):
            await query.message.reply_text("No hay más perfiles.")
            return

        user_id = ids[indice]
        p = perfiles.get(user_id)
        if not p:
            await query.message.reply_text("Perfil no disponible.")
            return

        texto = construir_texto_perfil(p)
        fotos = p.get("fotos", [])
        
        if not fotos:
            await query.message.reply_text("Sin fotos.")
            return

        context.user_data["foto_index"] = 0

        botones_kb = [
            [InlineKeyboardButton("⬅️", callback_data="foto_prev"),
             InlineKeyboardButton("➡️", callback_data="foto_next")],
            [InlineKeyboardButton("❤️ Me gusta", callback_data=f"like_{user_id}"),
             InlineKeyboardButton("➡️ Siguiente", callback_data="siguiente")]
        ]

        await query.message.reply_photo(
            photo=fotos[0],
            caption=texto,
            reply_markup=InlineKeyboardMarkup(botones_kb)
        )
        return

    if data.startswith("like_"):
        target_id = data.split("_")[1]
        asegurar_usuario_en_likes(likes, target_id)

        if target_id not in likes[from_id]["dados"]:
            likes[from_id]["dados"].append(target_id)
        if from_id not in likes[target_id]["recibidos"]:
            likes[target_id]["recibidos"].append(from_id)

        await guardar_likes(likes)

        try:
            await context.application.bot.send_message(
                chat_id=int(target_id),
                text="❤️ Alguien te ha dado *me gusta*.",
                parse_mode="Markdown"
            )
        except Exception:
            pass

        if from_id in likes.get(target_id, {}).get("dados", []):
            nombre_from = query.from_user.first_name or "Alguien"
            try:
                await context.application.bot.send_message(
                    chat_id=int(target_id),
                    text=f"🔥 ¡Match con {nombre_from}! Usa /matches.",
                    parse_mode="Markdown"
                )
            except Exception:
                pass

            try:
                await context.application.bot.send_message(
                    chat_id=int(from_id),
                    text="🔥 ¡Match nuevo! Usa /matches.",
                    parse_mode="Markdown"
                )
            except Exception:
                pass

            await query.message.reply_text("🔥 ¡Es un match!")
        else:
            await query.message.reply_text("❤️ Me gusta enviado.")
        return

# ==============================
#   LIKES Y MATCHES
# ==============================

async def likes_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    likes = await cargar_likes()
    asegurar_usuario_en_likes(likes, user_id)

    recibidos = likes[user_id]["recibidos"]
    if not recibidos:
        await update.message.reply_text("Aún no tienes me gustas.")
        return

    texto = "❤️ *Te han dado me gusta:*\n\n"
    for uid in recibidos:
        texto += f"• tg://user?id={uid}\n"

    await update.message.reply_text(texto, parse_mode="Markdown")

async def matches_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    likes = await cargar_likes()
    asegurar_usuario_en_likes(likes, user_id)

    dados = set(likes[user_id]["dados"])
    recibidos = set(likes[user_id]["recibidos"])
    matches = list(dados & recibidos)

    if not matches:
        await update.message.reply_text("Aún no tienes matches.")
        return

    texto = "🔥 *Tus matches:*\n\n"
    for uid in matches:
        texto += f"• ID: `{uid}`\n"

    await update.message.reply_text(texto, parse_mode="Markdown")

# ==============================
#   CHAT
# ==============================

async def chat_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    likes = await cargar_likes()
    asegurar_usuario_en_likes(likes, user_id)

    if not context.args:
        await update.message.reply_text("Usa /chat <id>")
        return

    target_id = context.args[0]
    dados = set(likes[user_id]["dados"])
    recibidos = set(likes[user_id]["recibidos"])
    matches = dados & recibidos

    if target_id not in matches:
        await update.message.reply_text("Solo con matches.")
        return

    chats = await cargar_chats()
    chats[user_id] = target_id
    chats[target_id] = user_id
    await guardar_chats(chats)

    await update.message.reply_text("💬 Chat abierto. Usa /cerrarchat para cerrar.")

    try:
        await context.application.bot.send_message(
            chat_id=int(target_id),
            text="💬 Alguien abrió chat contigo. Usa /cerrarchat para cerrar."
        )
    except Exception:
        pass

async def cerrarchat_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    chats = await cargar_chats()

    if user_id not in chats:
        await update.message.reply_text("No tienes chat activo.")
        return

    partner_id = chats[user_id]
    if partner_id in chats:
        del chats[partner_id]
    del chats[user_id]
    await guardar_chats(chats)

    await update.message.reply_text("🔒 Chat cerrado.")

    try:
        await context.application.bot.send_message(
            chat_id=int(partner_id),
            text="🔒 La otra persona cerró el chat."
        )
    except Exception:
        pass

async def chat_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    chats = await cargar_chats()

    if user_id not in chats:
        return

    partner_id = chats[user_id]
    texto = update.message.text

    try:
        await context.application.bot.send_message(
            chat_id=int(partner_id),
            text=f"📩 {texto}"
        )
    except Exception as e:
        logger.error(f"Error enviando mensaje: {e}")

# ==============================
#   BORRAR
# ==============================

async def borrar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    perfiles = await cargar_perfiles()
    likes = await cargar_likes()
    chats = await cargar_chats()

    eliminado = False

    if user_id in perfiles:
        del perfiles[user_id]
        await guardar_perfiles(perfiles)
        eliminado = True

    if user_id in likes:
        for uid, data in likes.items():
            if user_id in data.get("dados", []):
                data["dados"].remove(user_id)
            if user_id in data.get("recibidos", []):
                data["recibidos"].remove(user_id)
        del likes[user_id]
        await guardar_likes(likes)
        eliminado = True

    if user_id in chats:
        partner_id = chats[user_id]
        if partner_id in chats:
            del chats[partner_id]
        del chats[user_id]
        await guardar_chats(chats)
        eliminado = True

    if eliminado:
        await update.message.reply_text("🗑️ Perfil eliminado.")
    else:
        await update.message.reply_text("No tenías perfil.")

# ==============================
#   SUGERENCIAS Y ADMIN
# ==============================

async def sugerencia_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if not context.args:
        await update.message.reply_text("Usa /sugerencia <texto>")
        return

    texto = " ".join(context.args)
    sugerencias = await cargar_sugerencias()
    lista = sugerencias.get("sugerencias", [])
    lista.append({"user_id": user_id, "texto": texto})
    sugerencias["sugerencias"] = lista
    await guardar_sugerencias(sugerencias)

    await update.message.reply_text("✅ Sugerencia enviada.")

    if ADMIN_ID:
        try:
            await context.application.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"💡 Sugerencia de {user_id}:\n\n{texto}"
            )
        except Exception:
            pass

async def admin_broadcast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("No tienes permiso.")
        return

    if not context.args:
        await update.message.reply_text("Usa /admin_broadcast <mensaje>")
        return

    mensaje = " ".join(context.args)
    perfiles = await cargar_perfiles()
    enviados = 0

    for uid in perfiles.keys():
        try:
            await context.application.bot.send_message(
                chat_id=int(uid),
                text=f"📢 Aviso:\n\n{mensaje}"
            )
            enviados += 1
        except Exception:
            continue

    await update.message.reply_text(f"Enviado a {enviados} usuarios.")

async def admin_sugerencias_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("No tienes permiso.")
        return

    sugerencias = await cargar_sugerencias()
    lista = sugerencias.get("sugerencias", [])

    if not lista:
        await update.message.reply_text("No hay sugerencias.")
        return

    texto = "💡 *Sugerencias:*\n\n"
    for s in lista:
        texto += f"- De `{s['user_id']}`: {s['texto']}\n"

    await update.message.reply_text(texto, parse_mode="Markdown")

async def admin_limpiar_sugerencias_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("No tienes permiso.")
        return

    await guardar_sugerencias({"sugerencias": []})
    await update.message.reply_text("🧹 Sugerencias limpiadas.")

async def miid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Tu ID: `{update.effective_user.id}`", parse_mode="Markdown")

# ==============================
#   SERVIDOR WEB + MAIN
# ==============================

async def health_check(request):
    return web.Response(text="OK", status=200)

async def webhook_handler(request):
    """Recibe actualizaciones de Telegram"""
    try:
        bot_app = request.app["bot_app"]
        data = await request.json()
        update = Update.de_json(data, bot_app.bot)
        await bot_app.process_update(update)
        return web.Response(text="OK", status=200)
    except Exception as e:
        logger.error(f"Error en webhook: {e}")
        return web.Response(text="Error", status=500)

async def main():
    # Crear aplicación Telegram
    application = ApplicationBuilder().token(TOKEN).build()

    # Handlers
    application.add_handler(CommandHandler("start", start))

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("perfil", perfil)],
        states={
            FOTO: [
                MessageHandler(filters.PHOTO, recibir_foto),
                CommandHandler("listo", fotos_listas),
            ],
            EDAD: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_edad)],
            CIUDAD: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_ciudad)],
            BUSCA: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_busca)],
            DESCRIPCION: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_descripcion)],
            ROL: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_rol)],
            ESTATURA: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_estatura)],
        },
        fallbacks=[CommandHandler("cancelar", start)]
    )
    application.add_handler(conv_handler)

    application.add_handler(CommandHandler("ver", ver))
    application.add_handler(CallbackQueryHandler(galeria_callback, pattern="^foto_"))
    application.add_handler(CallbackQueryHandler(botones))

    application.add_handler(CommandHandler("likes", likes_cmd))
    application.add_handler(CommandHandler("matches", matches_cmd))
    application.add_handler(CommandHandler("chat", chat_cmd))
    application.add_handler(CommandHandler("cerrarchat", cerrarchat_cmd))
    application.add_handler(CommandHandler("borrar", borrar))

    application.add_handler(CommandHandler("sugerencia", sugerencia_cmd))
    application.add_handler(CommandHandler("admin_broadcast", admin_broadcast_cmd))
    application.add_handler(CommandHandler("admin_sugerencias", admin_sugerencias_cmd))
    application.add_handler(CommandHandler("admin_limpiar_sugerencias", admin_limpiar_sugerencias_cmd))

    application.add_handler(CommandHandler("miid", miid))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat_message))

    # Inicializar bot
    await application.initialize()
    await application.start()

    # Configurar webhook
    if WEBHOOK_URL:
        webhook_path = f"/{TOKEN}"
        full_url = f"{WEBHOOK_URL}{webhook_path}"
        await application.bot.set_webhook(url=full_url)
        logger.info(f"Webhook configurado: {full_url}")

    # Crear servidor web
    web_app = web.Application()
    web_app["bot_app"] = application
    web_app.router.add_get("/", health_check)
    web_app.router.add_post(f"/{TOKEN}", webhook_handler)

    runner = web.AppRunner(web_app)
    await runner.setup()
    
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info(f"Servidor escuchando en puerto {PORT}")

    # Mantener vivo
    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        pass
    finally:
        await application.stop()
        await runner.cleanup()

if __name__ == "__main__":
    asyncio.run(main())