import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

# ------------------------------
#   ARCHIVOS
# ------------------------------

PERFILES_FILE = "perfiles.json"
LIKES_FILE = "likes.json"
CHATS_FILE = "chats.json"


def cargar_perfiles():
    if os.path.exists(PERFILES_FILE):
        with open(PERFILES_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}


def guardar_perfiles(perfiles):
    with open(PERFILES_FILE, "w", encoding="utf-8") as f:
        json.dump(perfiles, f, ensure_ascii=False, indent=4)


def cargar_likes():
    if os.path.exists(LIKES_FILE):
        with open(LIKES_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}


def guardar_likes(likes):
    with open(LIKES_FILE, "w", encoding="utf-8") as f:
        json.dump(likes, f, ensure_ascii=False, indent=4)


def asegurar_usuario_en_likes(likes, user_id):
    if user_id not in likes:
        likes[user_id] = {"dados": [], "recibidos": []}


def cargar_chats():
    if os.path.exists(CHATS_FILE):
        with open(CHATS_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}


def guardar_chats(chats):
    with open(CHATS_FILE, "w", encoding="utf-8") as f:
        json.dump(chats, f, ensure_ascii=False, indent=4)


# ------------------------------
#   ESTADOS DEL PERFIL
# ------------------------------

FOTO, EDAD, CIUDAD, BUSCA, DESCRIPCION, ROL, ESTATURA = range(7)

# ------------------------------
#   /start
# ------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🌈 *Bienvenido a HolaChico* 🌈\n\n"
        "Un espacio para conocer gente cerca de ti.\n\n"
        "📌 Comandos:\n"
        "• /perfil – crear o actualizar tu perfil\n"
        "• /ver – ver otros perfiles\n"
        "• /likes – ver quién te dio me gusta\n"
        "• /matches – ver tus matches\n"
        "• /chat <id> – abrir chat con un match\n"
        "• /cerrarchat – cerrar el chat actual\n"
        "• /borrar – eliminar tu perfil e interacciones\n\n"
        "Disfruta y conecta con respeto. 💬",
        parse_mode="Markdown"
    )

# ------------------------------
#   CREACIÓN DE PERFIL
# ------------------------------

async def perfil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📸 Envíame una *foto* para tu perfil.", parse_mode="Markdown")
    return FOTO


async def recibir_foto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["foto"] = update.message.photo[-1].file_id
    await update.message.reply_text("📅 ¿Qué *edad* tienes?", parse_mode="Markdown")
    return EDAD


async def recibir_edad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["edad"] = update.message.text
    await update.message.reply_text("📍 ¿En qué *ciudad* estás?", parse_mode="Markdown")
    return CIUDAD


async def recibir_ciudad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["ciudad"] = update.message.text
    await update.message.reply_text("💘 ¿Qué *buscas*? (amigos, relación, charlar…)", parse_mode="Markdown")
    return BUSCA


async def recibir_busca(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["busca"] = update.message.text
    await update.message.reply_text("📝 Escribe una *descripción* sobre ti.", parse_mode="Markdown")
    return DESCRIPCION


async def recibir_descripcion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["descripcion"] = update.message.text
    await update.message.reply_text(
        "🎭 ¿Cuál es tu *rol*?\n"
        "- activo\n- pasivo\n- inter\n- inter activo\n- inter pasivo",
        parse_mode="Markdown"
    )
    return ROL


async def recibir_rol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["rol"] = update.message.text
    await update.message.reply_text("📏 ¿Cuál es tu *estatura*? (ej: 1.78)", parse_mode="Markdown")
    return ESTATURA


async def recibir_estatura(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["estatura"] = update.message.text

    user_id = str(update.effective_user.id)
    perfiles = cargar_perfiles()
    perfiles[user_id] = context.user_data
    guardar_perfiles(perfiles)

    p = context.user_data
    texto = (
        f"📸 *Tu perfil está listo*\n\n"
        f"Edad: {p['edad']}\n"
        f"Ciudad: {p['ciudad']}\n"
        f"Busca: {p['busca']}\n"
        f"Descripción: {p['descripcion']}\n"
        f"Rol: {p['rol']}\n"
        f"Estatura: {p['estatura']}"
    )

    await update.message.reply_photo(
        photo=p["foto"],
        caption=texto,
        parse_mode="Markdown"
    )

    return ConversationHandler.END

# ------------------------------
#   VER PERFILES
# ------------------------------

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
    perfiles = cargar_perfiles()
    ids = list(perfiles.keys())

    user_id = str(update.effective_user.id)
    if user_id in ids:
        ids.remove(user_id)

    if not ids:
        await update.message.reply_text("😕 Aún no hay otros perfiles.")
        return

    context.user_data["lista_perfiles"] = ids
    context.user_data["indice"] = 0

    await mostrar_perfil(update, context)


async def mostrar_perfil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    perfiles = cargar_perfiles()
    ids = context.user_data["lista_perfiles"]
    indice = context.user_data["indice"]
    user_id = ids[indice]
    p = perfiles[user_id]

    texto = construir_texto_perfil(p)

    botones = [
        [
            InlineKeyboardButton("❤️ Me gusta", callback_data=f"like_{user_id}"),
            InlineKeyboardButton("💬 Contactar", callback_data=f"contactar_{user_id}")
        ],
        [InlineKeyboardButton("➡️ Siguiente", callback_data="siguiente")]
    ]

    await update.message.reply_photo(
        photo=p["foto"],
        caption=texto,
        reply_markup=InlineKeyboardMarkup(botones)
    )

# ------------------------------
#   BOTONES: LIKE / CONTACTAR / SIGUIENTE
# ------------------------------

async def botones(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    from_id = str(query.from_user.id)

    perfiles = cargar_perfiles()
    likes = cargar_likes()
    asegurar_usuario_en_likes(likes, from_id)

    # SIGUIENTE
    if data == "siguiente":
        context.user_data["indice"] += 1
        if context.user_data["indice"] >= len(context.user_data["lista_perfiles"]):
            context.user_data["indice"] = 0

        ids = context.user_data["lista_perfiles"]
        indice = context.user_data["indice"]
        user_id = ids[indice]
        p = perfiles[user_id]

        texto = construir_texto_perfil(p)

        botones = [
            [
                InlineKeyboardButton("❤️ Me gusta", callback_data=f"like_{user_id}"),
                InlineKeyboardButton("💬 Contactar", callback_data=f"contactar_{user_id}")
            ],
            [InlineKeyboardButton("➡️ Siguiente", callback_data="siguiente")]
        ]

        await query.message.reply_photo(
            photo=p["foto"],
            caption=texto,
            reply_markup=InlineKeyboardMarkup(botones)
        )
        return

    # LIKE
    if data.startswith("like_"):
        target_id = data.split("_")[1]
        asegurar_usuario_en_likes(likes, target_id)

        if target_id not in likes[from_id]["dados"]:
            likes[from_id]["dados"].append(target_id)
        if from_id not in likes[target_id]["recibidos"]:
            likes[target_id]["recibidos"].append(from_id)

        guardar_likes(likes)

        # Notificar al otro usuario que alguien le dio like
        try:
            await context.application.bot.send_message(
                chat_id=int(target_id),
                text="❤️ Alguien te ha dado *me gusta*.",
                parse_mode="Markdown"
            )
        except Exception:
            pass

        # Comprobar si hay match
        if from_id in likes[target_id]["dados"]:
            nombre_from = query.from_user.first_name or "Alguien"
            try:
                await context.application.bot.send_message(
                    chat_id=int(target_id),
                    text=f"🔥 ¡Tienes un *match* con {nombre_from}! Usa /matches para verlo.",
                    parse_mode="Markdown"
                )
            except Exception:
                pass

            try:
                await context.application.bot.send_message(
                    chat_id=int(from_id),
                    text="🔥 ¡Tienes un *match* nuevo! Usa /matches para verlo.",
                    parse_mode="Markdown"
                )
            except Exception:
                pass

            await query.message.reply_text("🔥 ¡Es un match! Podéis usar /chat para hablar.")
        else:
            await query.message.reply_text("❤️ Me gusta enviado.")

        return

    # CONTACTAR (aviso directo)
    if data.startswith("contactar_"):
        target_id = data.split("_")[1]
        nombre_from = query.from_user.first_name or "Alguien"

        try:
            await context.application.bot.send_message(
                chat_id=int(target_id),
                text=(
                    f"💬 {nombre_from} quiere contactar contigo.\n"
                    f"Puedes hablar con esta persona si tenéis match usando /chat.\n"
                    f"También puedes abrir su perfil o usar:\n"
                    f"👉 tg://user?id={from_id}"
                )
            )
        except Exception:
            pass

        await query.message.reply_text(
            f"Hemos avisado a esa persona. También puedes intentar escribirle aquí:\n👉 tg://user?id={target_id}"
        )
        return

# ------------------------------
#   /likes y /matches
# ------------------------------

async def likes_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    likes = cargar_likes()
    asegurar_usuario_en_likes(likes, user_id)

    recibidos = likes[user_id]["recibidos"]
    if not recibidos:
        await update.message.reply_text("Aún no tienes me gustas recibidos.")
        return

    texto = "❤️ Te han dado *me gusta* estos usuarios:\n\n"
    for uid in recibidos:
        texto += f"• tg://user?id={uid}\n"

    await update.message.reply_text(texto, parse_mode="Markdown")


async def matches_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    likes = cargar_likes()
    asegurar_usuario_en_likes(likes, user_id)

    dados = set(likes[user_id]["dados"])
    recibidos = set(likes[user_id]["recibidos"])
    matches = list(dados & recibidos)

    if not matches:
        await update.message.reply_text("Aún no tienes matches.")
        return

    texto = "🔥 *Tus matches:*\n\n"
    for uid in matches:
        texto += f"• ID: {uid}  (puedes usar /chat {uid})\n"

    await update.message.reply_text(texto, parse_mode="Markdown")

# ------------------------------
#   CHAT PRIVADO: /chat y /cerrarchat
# ------------------------------

async def chat_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    likes = cargar_likes()
    asegurar_usuario_en_likes(likes, user_id)

    if not context.args:
        await update.message.reply_text(
            "Usa /chat <id> para abrir un chat con un match.\n"
            "Puedes ver los IDs en /matches."
        )
        return

    target_id = context.args[0]

    # Comprobar que hay match mutuo
    dados = set(likes[user_id]["dados"])
    recibidos = set(likes[user_id]["recibidos"])
    matches = dados & recibidos

    if target_id not in matches:
        await update.message.reply_text("Solo puedes abrir chat con alguien que sea tu match.")
        return

    chats = cargar_chats()
    chats[user_id] = target_id
    chats[target_id] = user_id
    guardar_chats(chats)

    await update.message.reply_text(
        "💬 Chat privado abierto.\n"
        "Todo lo que escribas ahora se enviará a esa persona.\n"
        "Usa /cerrarchat para cerrar el chat."
    )

    try:
        await context.application.bot.send_message(
            chat_id=int(target_id),
            text="💬 Alguien ha abierto un chat privado contigo. Todo lo que escribas aquí se enviará a esa persona.\nUsa /cerrarchat para cerrar el chat."
        )
    except Exception:
        pass


async def cerrarchat_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    chats = cargar_chats()

    if user_id not in chats:
        await update.message.reply_text("No tienes ningún chat activo.")
        return

    partner_id = chats[user_id]
    # borrar ambos lados
    if partner_id in chats:
        del chats[partner_id]
    del chats[user_id]
    guardar_chats(chats)

    await update.message.reply_text("🔒 Chat cerrado.")

    try:
        await context.application.bot.send_message(
            chat_id=int(partner_id),
            text="🔒 La otra persona ha cerrado el chat."
        )
    except Exception:
        pass


async def chat_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    chats = cargar_chats()

    if user_id not in chats:
        return  # mensaje normal, no está en chat activo

    partner_id = chats[user_id]
    texto = update.message.text

    try:
        await context.application.bot.send_message(
            chat_id=int(partner_id),
            text=f"📩 Mensaje: {texto}"
        )
    except Exception:
        pass

# ------------------------------
#   BORRAR PERFIL
# ------------------------------

async def borrar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    perfiles = cargar_perfiles()
    likes = cargar_likes()
    chats = cargar_chats()

    eliminado = False

    if user_id in perfiles:
        del perfiles[user_id]
        guardar_perfiles(perfiles)
        eliminado = True

    if user_id in likes:
        del likes[user_id]
        guardar_likes(likes)
        eliminado = True

    if user_id in chats:
        partner_id = chats[user_id]
        if partner_id in chats:
            del chats[partner_id]
        del chats[user_id]
        guardar_chats(chats)
        eliminado = True

    if eliminado:
        await update.message.reply_text("🗑️ Tu perfil e interacciones han sido eliminados.")
    else:
        await update.message.reply_text("No tenías perfil ni interacciones guardadas.")

# ------------------------------
#   TOKEN Y MAIN
# ------------------------------

TOKEN = "8197198334:AAHHxsA_4DfQgjF1Cy3Fz8UR4F_kiycJ5QM"  # pon aquí tu token real

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("perfil", perfil)],
        states={
            FOTO: [MessageHandler(filters.PHOTO, recibir_foto)],
            EDAD: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_edad)],
            CIUDAD: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_ciudad)],
            BUSCA: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_busca)],
            DESCRIPCION: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_descripcion)],
            ROL: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_rol)],
            ESTATURA: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_estatura)],
        },
        fallbacks=[]
    )
    app.add_handler(conv_handler)

    app.add_handler(CommandHandler("ver", ver))
    app.add_handler(CallbackQueryHandler(botones))
    app.add_handler(CommandHandler("likes", likes_cmd))
    app.add_handler(CommandHandler("matches", matches_cmd))
    app.add_handler(CommandHandler("chat", chat_cmd))
    app.add_handler(CommandHandler("cerrarchat", cerrarchat_cmd))
    app.add_handler(CommandHandler("borrar", borrar))

    # Relay de mensajes cuando hay chat activo
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat_message))

    app.run_polling()

if __name__ == "__main__":
    main()
