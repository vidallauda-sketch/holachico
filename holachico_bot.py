import json
import os

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

# ------------------------------
#   CONFIGURACIÓN
# ------------------------------

from pathlib import Path
import json

BASE_DIR = Path(__file__).parent

PERFILES_FILE = BASE_DIR / "perfiles.json"
LIKES_FILE = BASE_DIR / "likes.json"
CHATS_FILE = BASE_DIR / "chats.json"
SUGERENCIAS_FILE = BASE_DIR / "sugerencias.json"

ADMIN_ID = 8400361723
TOKEN = "8197198334:AAGQMMTQSi_zplmgNQfYXvAMwjkDUq2qq3Q"
CANAL_ID = -1002459139025

# ------------------------------
#   UTILIDADES JSON
# ------------------------------

def load_data(path: Path):
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}

def save_data(path: Path, data: dict):
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# ------------------------------
#   ARCHIVOS
# ------------------------------

def cargar_perfiles():
    return cargar_json(PERFILES_FILE)

def guardar_perfil(update, context):
    user = update.effective_user
    perfiles = load_data(PERFILES_FILE)

    perfiles[str(user.id)] = {
        "fotos": context.user_data.get("fotos", []),
        "edad": context.user_data.get("edad", ""),
        "ciudad": context.user_data.get("ciudad", ""),
        "busca": context.user_data.get("busca", ""),
        "descripcion": context.user_data.get("descripcion", ""),
        "rol": context.user_data.get("rol", ""),
        "estatura": context.user_data.get("estatura", ""),
    }

    save_data(PERFILES_FILE, perfiles)
    update.message.reply_text("✅ Tu perfil se ha guardado o actualizado.")

def cargar_likes():
    return cargar_json(LIKES_FILE)

def guardar_likes(likes):
    guardar_json(LIKES_FILE, likes)

def cargar_chats():
    return cargar_json(CHATS_FILE)

def guardar_chats(chats):
    guardar_json(CHATS_FILE, chats)

def cargar_sugerencias():
    return cargar_json(SUGERENCIAS_FILE)

def guardar_sugerencias(sugerencias):
    guardar_json(SUGERENCIAS_FILE, sugerencias)

def asegurar_usuario_en_likes(likes, user_id):
    if user_id not in likes:
        likes[user_id] = {"dados": [], "recibidos": []}

def iniciar_cambio_fotos(update, context):
    update.message.reply_text("📷 Envíame ahora tus nuevas fotos. Se reemplazarán las anteriores.")
    context.user_data["cambiando_fotos"] = True
    context.user_data["nuevas_fotos"] = []


def recibir_foto(update, context):
    if context.user_data.get("cambiando_fotos"):
        foto = update.message.photo[-1].file_id
        lista = context.user_data.get("nuevas_fotos", [])
        lista.append(foto)
        context.user_data["nuevas_fotos"] = lista
        update.message.reply_text("✅ Foto guardada. Envía más o escribe /guardar_fotos cuando termines.")


def guardar_fotos(update, context):
    user = update.effective_user
    perfiles = load_data(PERFILES_FILE)
    perfil = perfiles.get(str(user.id))

    if not perfil:
        update.message.reply_text("❌ No tienes perfil. Usa /perfil primero.")
        return

    nuevas = context.user_data.get("nuevas_fotos", [])
    if not nuevas:
        update.message.reply_text("❌ No has enviado fotos nuevas.")
        return

    perfil["fotos"] = nuevas
    perfiles[str(user.id)] = perfil
    save_data(PERFILES_FILE, perfiles)

    context.user_data["cambiando_fotos"] = False
    context.user_data["nuevas_fotos"] = []
    update.message.reply_text("✅ Tus fotos han sido actualizadas.")


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
        "• /borrar – eliminar tu perfil e interacciones\n"
        "• /sugerencia <texto> – enviar sugerencia al admin\n\n"
        "Disfruta y conecta con respeto. 💬",
        parse_mode="Markdown"
    )

# ------------------------------
#   CREACIÓN DE PERFIL
# ------------------------------

async def perfil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["fotos"] = []
    await update.message.reply_text(
        "📸 Envíame *todas las fotos que quieras* para tu perfil.\n"
        "Cuando termines, escribe /listo.",
        parse_mode="Markdown"
    )
    return FOTO

async def recibir_foto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    file_id = photo.file_id

    file = await context.bot.get_file(file_id)
    real_id = file.file_id

    context.user_data.setdefault("fotos", []).append(real_id)
    await update.message.reply_text("📸 Foto añadida. Envía otra o escribe /listo.")
    return FOTO

async def fotos_listas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("fotos"):
        await update.message.reply_text("Necesitas enviar al menos una foto antes de seguir.")
        return FOTO

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

    # Compatibilidad foto/fotos
    if "fotos" in p:
        fotos = p["fotos"]
    elif "foto" in p:
        fotos = [p["foto"]]
    else:
        fotos = []

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
        photo=fotos[0],
        caption=texto,
        parse_mode="Markdown"
    )

    botones = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Sí, publicar en el canal", callback_data="publicar_si"),
            InlineKeyboardButton("No, gracias", callback_data="publicar_no"),
        ]
    ])

    await update.message.reply_text(
        "¿Quieres que tu perfil aparezca en el canal público de HolaChico?",
        reply_markup=botones
    )

    return ConversationHandler.END

# ------------------------------
#   VER PERFILES + GALERÍA
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

def obtener_fotos(p):
    """Compatibilidad con formatos viejos y nuevos."""
    if "fotos" in p:
        return p["fotos"]
    if "foto" in p:
        return [p["foto"]]
    return []

def mi_perfil(update, context):
    user = update.effective_user
    perfiles = load_data(PERFILES_FILE)
    perfil = perfiles.get(str(user.id))

    if not perfil:
        update.message.reply_text("❌ Aún no tienes perfil. Usa /perfil para crearlo.")
        return

    texto = (
        f"🧑 Tu perfil\n\n"
        f"Edad: {perfil.get('edad','')}\n"
        f"Ciudad: {perfil.get('ciudad','')}\n"
        f"Busca: {perfil.get('busca','')}\n"
        f"Rol: {perfil.get('rol','')}\n"
        f"Estatura: {perfil.get('estatura','')}\n\n"
        f"Descripción:\n{perfil.get('descripcion','')}"
    )
    update.message.reply_text(texto)


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
    context.user_data["foto_index"] = 0

    await mostrar_perfil(update, context)

async def mostrar_perfil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    perfiles = cargar_perfiles()
    ids = context.user_data["lista_perfiles"]
    indice = context.user_data["indice"]
    user_id = ids[indice]
    p = perfiles[user_id]

    texto = construir_texto_perfil(p)
    fotos = obtener_fotos(p)

    if not fotos:
        await update.message.reply_text("Este perfil no tiene fotos.")
        return

    context.user_data["foto_index"] = 0

    botones = [
        [
            InlineKeyboardButton("⬅️", callback_data="foto_prev"),
            InlineKeyboardButton("➡️", callback_data="foto_next")
        ],
        [
            InlineKeyboardButton("❤️ Me gusta", callback_data=f"like_{user_id}"),
            InlineKeyboardButton("💬 Contactar", callback_data=f"contactar_{user_id}")
        ],
        [InlineKeyboardButton("➡️ Siguiente", callback_data="siguiente")]
    ]

    await update.message.reply_photo(
        photo=fotos[0],
        caption=texto,
        reply_markup=InlineKeyboardMarkup(botones)
    )

async def galeria_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    perfiles = cargar_perfiles()
    ids = context.user_data.get("lista_perfiles", [])
    indice = context.user_data.get("indice", 0)

    if not ids:
        return

    user_id = ids[indice]
    p = perfiles[user_id]
    fotos = obtener_fotos(p)

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
        [
            InlineKeyboardButton("⬅️", callback_data="foto_prev"),
            InlineKeyboardButton("➡️", callback_data="foto_next")
        ],
        [
            InlineKeyboardButton("❤️ Me gusta", callback_data=f"like_{user_id}"),
            InlineKeyboardButton("💬 Contactar", callback_data=f"contactar_{user_id}")
        ],
        [InlineKeyboardButton("➡️ Siguiente", callback_data="siguiente")]
    ]

    await query.edit_message_media(
        media=InputMediaPhoto(fotos[foto_index], caption=texto),
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
        fotos = obtener_fotos(p)

        if not fotos:
            await query.message.reply_text("Este perfil no tiene fotos.")
            return

        context.user_data["foto_index"] = 0

        botones_kb = [
            [
                InlineKeyboardButton("⬅️", callback_data="foto_prev"),
                InlineKeyboardButton("➡️", callback_data="foto_next")
            ],
            [
                InlineKeyboardButton("❤️ Me gusta", callback_data=f"like_{user_id}"),
                InlineKeyboardButton("💬 Contactar", callback_data=f"contactar_{user_id}")
            ],
            [InlineKeyboardButton("➡️ Siguiente", callback_data="siguiente")]
        ]

        await query.message.reply_photo(
            photo=fotos[0],
            caption=texto,
            reply_markup=InlineKeyboardMarkup(botones_kb)
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

        try:
            await context.application.bot.send_message(
                chat_id=int(target_id),
                text="❤️ Alguien te ha dado *me gusta*.",
                parse_mode="Markdown"
            )
        except Exception:
            pass

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

    # CONTACTAR
    if data.startswith("contactar_"):
        target_id = data.split("_")[1]
        nombre_from = query.from_user.first_name or "Alguien"

        try:
            await context.application.bot.send_message(
                chat_id=int(target_id),
                text=(
                    f"💬 {nombre_from} quiere contactar contigo.\n"
                    f"Puedes hablar con esta persona si tenéis match usando /chat.\n"
                    f"👉 tg://user?id={from_id}"
                )
            )
        except Exception:
            pass

        await query.message.reply_text(
            f"Hemos avisado a esa persona.\n\n"
            f"👉 tg://user?id={target_id}\n\n"
            f"⚠️ Si el enlace no abre, es porque esta persona solo permite mensajes de sus contactos.\n"
            f"Cuando tengáis *match*, podréis hablar con /chat."
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
        texto += f"• ID: {uid}  (usa /chat {uid})\n"

    await update.message.reply_text(texto, parse_mode="Markdown")

# ------------------------------
#   CHAT PRIVADO
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
            text=(
                "💬 Alguien ha abierto un chat privado contigo.\n"
                "Todo lo que escribas aquí se enviará a esa persona.\n"
                "Usa /cerrarchat para cerrar el chat."
            )
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
        return

    partner_id = chats[user_id]
    texto = update.message.text

    try:
        await context.application.bot.send_message(
            chat_id=int(partner_id),
            text=f"📩 {texto}"
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
#   SUGERENCIAS Y ADMIN
# ------------------------------

async def sugerencia_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if not context.args:
        await update.message.reply_text("Usa /sugerencia <texto> para enviar una sugerencia.")
        return

    texto = " ".join(context.args)

    sugerencias = cargar_sugerencias()
    lista = sugerencias.get("sugerencias", [])
    lista.append({"user_id": user_id, "texto": texto})
    sugerencias["sugerencias"] = lista
    guardar_sugerencias(sugerencias)

    await update.message.reply_text("✅ Gracias por tu sugerencia.")

    try:
        await context.application.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"💡 Nueva sugerencia de {user_id}:\n\n{texto}"
        )
    except Exception:
        pass

async def admin_broadcast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("No tienes permiso para usar este comando.")
        return

    if not context.args:
        await update.message.reply_text("Usa /admin_broadcast <mensaje> para enviar un aviso a todos los usuarios.")
        return

    mensaje = " ".join(context.args)
    perfiles = cargar_perfiles()
    enviados = 0

    for uid in perfiles.keys():
        try:
            await context.application.bot.send_message(
                chat_id=int(uid),
                text=f"📢 Aviso del administrador:\n\n{mensaje}"
            )
            enviados += 1
        except Exception:
            continue

    await update.message.reply_text(f"Mensaje enviado a {enviados} usuarios.")

async def admin_sugerencias_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("No tienes permiso para usar este comando.")
        return

    sugerencias = cargar_sugerencias()
    lista = sugerencias.get("sugerencias", [])

    if not lista:
        await update.message.reply_text("No hay sugerencias pendientes.")
        return

    texto = "💡 *Sugerencias recibidas:*\n\n"
    for s in lista:
        texto += f"- De {s['user_id']}: {s['texto']}\n"

    await update.message.reply_text(texto, parse_mode="Markdown")

async def admin_limpiar_sugerencias_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("No tienes permiso para usar este comando.")
        return

    guardar_sugerencias({"sugerencias": []})
    await update.message.reply_text("🧹 Sugerencias limpiadas.")

# ------------------------------
#   /miid (para depuración)
# ------------------------------

async def miid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text(f"Tu ID es: {user_id}")

# ------------------------------
#   PUBLICAR PERFIL EN CANAL
# ------------------------------

async def publicar_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    perfiles = cargar_perfiles()

    if user_id not in perfiles:
        await query.edit_message_text("No he encontrado tu perfil. Crea uno con /perfil.")
        return

    p = perfiles[user_id]
    fotos = obtener_fotos(p)

    if not fotos:
        await query.edit_message_text("Tu perfil no tiene fotos, no puedo publicarlo.")
        return

    if query.data == "publicar_no":
        await query.edit_message_text("Perfecto, tu perfil no será publicado en el canal.")
        return

    texto = (
        f"📸 *Nuevo perfil en HolaChico*\n\n"
        f"Edad: {p['edad']}\n"
        f"Ciudad: {p['ciudad']}\n"
        f"Busca: {p['busca']}\n"
        f"Descripción: {p['descripcion']}\n"
        f"Rol: {p['rol']}\n"
        f"Estatura: {p['estatura']}\n\n"
        f"👉 tg://user?id={user_id}"
    )

    try:
        await context.application.bot.send_photo(
            chat_id=CANAL_ID,
            photo=fotos[0],
            caption=texto,
            parse_mode="Markdown"
        )
    except Exception as e:
        await query.edit_message_text("⚠️ No pude publicar en el canal. Revisa permisos.")
        return

    await query.edit_message_text("Tu perfil ha sido publicado en el canal 🎉")

# ------------------------------
#   MAIN
# ------------------------------

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))

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
        fallbacks=[]
    )
    app.add_handler(conv_handler)

    app.add_handler(CommandHandler("ver", ver))
    app.add_handler(CallbackQueryHandler(galeria_callback, pattern="^foto_"))
    app.add_handler(CallbackQueryHandler(publicar_callback, pattern="^publicar_"))
    app.add_handler(CallbackQueryHandler(botones, pattern="^(like_|contactar_|siguiente|foto_)"))

    app.add_handler(CommandHandler("likes", likes_cmd))
    app.add_handler(CommandHandler("matches", matches_cmd))
    app.add_handler(CommandHandler("chat", chat_cmd))
    app.add_handler(CommandHandler("cerrarchat", cerrarchat_cmd))
    app.add_handler(CommandHandler("borrar", borrar))

    app.add_handler(CommandHandler("sugerencia", sugerencia_cmd))
    app.add_handler(CommandHandler("admin_broadcast", admin_broadcast_cmd))
    app.add_handler(CommandHandler("admin_sugerencias", admin_sugerencias_cmd))
    app.add_handler(CommandHandler("admin_limpiar_sugerencias", admin_limpiar_sugerencias_cmd))

    app.add_handler(CommandHandler("miid", miid))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat_message))

    app.run_polling()

if __name__ == "__main__":
    main()
