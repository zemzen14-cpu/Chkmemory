#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎬 NETFLIX NFToken BOT - Generador de Links de Acceso (Webhook + Polling)
"""

import os
import re
import json
import logging
import requests
import urllib.parse
from datetime import datetime
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# ================== CONFIGURACIÓN ==================
TOKEN = "8945828877:AAFNznpCroIeQblmaw7HVSqjFOlDB2e8Ugs"
WATERMARK = "✨ @oscuridad10"

# ================== CONFIGURACIÓN WEBHOOK ==================
PORT = int(os.environ.get("PORT", 8080))
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")  # Ej: https://tudominio.onrender.com

# ================== LOGGING ==================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)

# ================== CONSTANTES NETFLIX ==================
API_URL = "https://ios.prod.ftl.netflix.com/iosui/user/15.48"

QUERY_PARAMS = {
    "appVersion": "15.48.1",
    "config": '{"gamesInTrailersEnabled":"false","isTrailersEvidenceEnabled":"false","cdsMyListSortEnabled":"true","kidsBillboardEnabled":"true","addHorizontalBoxArtToVideoSummariesEnabled":"false","skOverlayTestEnabled":"false","homeFeedTestTVMovieListsEnabled":"false","baselineOnIpadEnabled":"true","trailersVideoIdLoggingFixEnabled":"true","postPlayPreviewsEnabled":"false","bypassContextualAssetsEnabled":"false","roarEnabled":"false","useSeason1AltLabelEnabled":"false","disableCDSSearchPaginationSectionKinds":["searchVideoCarousel"],"cdsSearchHorizontalPaginationEnabled":"true","searchPreQueryGamesEnabled":"true","kidsMyListEnabled":"true","billboardEnabled":"true","useCDSGalleryEnabled":"true","contentWarningEnabled":"true","videosInPopularGamesEnabled":"true","avifFormatEnabled":"false","sharksEnabled":"true"}',
    "device_type": "NFAPPL-02-",
    "esn": "NFAPPL-02-IPHONE8%3D1-PXA-02026U9VV5O8AUKEAEO8PUJETCGDD4PQRI9DEB3MDLEMD0EACM4CS78LMD334MN3MQ3NMJ8SU9O9MVGS6BJCURM1PH1MUTGDPF4S4200",
    "idiom": "phone",
    "iosVersion": "15.8.5",
    "isTablet": "false",
    "languages": "en-US",
    "locale": "en-US",
    "maxDeviceWidth": "375",
    "model": "saget",
    "modelType": "IPHONE8-1",
    "odpAware": "true",
    "path": '["account","token","default"]',
    "pathFormat": "graph",
    "pixelDensity": "2.0",
    "progressive": "false",
    "responseFormat": "json",
}

BASE_HEADERS = {
    "User-Agent": "Argo/15.48.1 (iPhone; iOS 15.8.5; Scale/2.00)",
    "x-netflix.request.attempt": "1",
    "x-netflix.request.client.user.guid": "A4CS633D7VCBPE2GPK2HL4EKOE",
    "x-netflix.context.profile-guid": "A4CS633D7VCBPE2GPK2HL4EKOE",
    "x-netflix.request.routing": '{"path":"/nq/mobile/nqios/~15.48.0/user","control_tag":"iosui_argo"}',
    "x-netflix.context.app-version": "15.48.1",
    "x-netflix.argo.translated": "true",
    "x-netflix.context.form-factor": "phone",
    "x-netflix.context.sdk-version": "2012.4",
    "x-netflix.client.appversion": "15.48.1",
    "x-netflix.context.max-device-width": "375",
    "x-netflix.context.ab-tests": "",
    "x-netflix.tracing.cl.useractionid": "4DC655F2-9C3C-4343-8229-CA1B003C3053",
    "x-netflix.client.type": "argo",
    "x-netflix.client.ftl.esn": "NFAPPL-02-IPHONE8=1-PXA-02026U9VV5O8AUKEAEO8PUJETCGDD4PQRI9DEB3MDLEMD0EACM4CS78LMD334MN3MQ3NMJ8SU9O9MVGS6BJCURM1PH1MUTGDPF4S4200",
    "x-netflix.context.locales": "en-US",
    "x-netflix.context.top-level-uuid": "90AFE39F-ADF1-4D8A-B33E-528730990FE3",
    "x-netflix.client.iosversion": "15.8.5",
    "accept-language": "en-US;q=1",
    "x-netflix.argo.abtests": "",
    "x-netflix.context.os-version": "15.8.5",
    "x-netflix.request.client.context": '{"appState":"foreground"}',
    "x-netflix.context.ui-flavor": "argo",
    "x-netflix.argo.nfnsm": "9",
    "x-netflix.context.pixel-density": "2.0",
    "x-netflix.request.toplevel.uuid": "90AFE39F-ADF1-4D8A-B33E-528730990FE3",
    "x-netflix.request.client.timezoneid": "Asia/Dhaka",
}

COOKIE_KEYS = ("NetflixId", "SecureNetflixId", "nfvdid", "OptanonConsent", "flwssn", "SessionId")
REQUIRED_COOKIE = "NetflixId"

# ================== FUNCIONES DE EXTRACCIÓN ==================

def decode_cookie_value(value):
    if isinstance(value, str):
        if "%" in value:
            try:
                return urllib.parse.unquote(value)
            except:
                pass
        try:
            return json.loads(f'"{value}"')
        except:
            pass
    return value

def parse_netscape_line(line):
    parts = line.strip().split('\t')
    if len(parts) >= 7:
        return {parts[5]: parts[6]}
    return {}

def extract_cookie_dict(text):
    cookie_dict = {}
    
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if '\t' in line:
            cookie_dict.update(parse_netscape_line(line))
            continue
        if '=' in line and not line.startswith('{'):
            for key in COOKIE_KEYS:
                if key in line:
                    pattern = rf'(?<!\w){re.escape(key)}=([^;,\s\n]+)'
                    match = re.search(pattern, line)
                    if match:
                        cookie_dict[key] = decode_cookie_value(match.group(1))
    
    try:
        data = json.loads(text)
        if isinstance(data, list):
            for cookie in data:
                name = cookie.get("name")
                value = cookie.get("value")
                if name in COOKIE_KEYS and isinstance(value, str):
                    cookie_dict[name] = decode_cookie_value(value)
        elif isinstance(data, dict):
            for key in COOKIE_KEYS:
                value = data.get(key)
                if isinstance(value, str):
                    cookie_dict[key] = decode_cookie_value(value)
    except:
        pass
    
    for key in COOKIE_KEYS:
        if key not in cookie_dict:
            for pattern in [rf'(?<!\w){re.escape(key)}=([^;,\s\n]+)', rf'"{re.escape(key)}":"([^"]+)"']:
                match = re.search(pattern, text)
                if match:
                    cookie_dict[key] = decode_cookie_value(match.group(1))
                    break
    
    return cookie_dict

def extract_nftoken_from_cookie(cookie_dict):
    for key, value in cookie_dict.items():
        if key in ("NetflixId", "SecureNetflixId"):
            decoded = decode_cookie_value(value)
            for pattern in [r'ct%3D([^%]+)', r'ct=([^&]+)', r'ct%3D([^&]+)', r'token%3D([^&]+)', r'([A-Za-z0-9+/=]{40,})']:
                match = re.search(pattern, decoded)
                if match:
                    token = match.group(1)
                    clean = re.sub(r'[^A-Za-z0-9+/=_-]', '', token)
                    if len(clean) > 40:
                        return clean
    return None

def get_cookie_string(cookie_dict):
    cookie_parts = []
    for key in ["NetflixId", "SecureNetflixId", "nfvdid"]:
        if key in cookie_dict:
            cookie_parts.append(f"{key}={cookie_dict[key]}")
    return "; ".join(cookie_parts) if cookie_parts else None

def is_token_valid(token):
    if not token:
        return False
    clean = re.sub(r'[^A-Za-z0-9+/=_-]', '', token)
    if len(clean) < 350:
        return True
    else:
        return False

def fetch_nftoken(cookie_dict):
    netflix_id = cookie_dict.get(REQUIRED_COOKIE)
    if not netflix_id:
        raise ValueError("❌ Falta NetflixId")

    cookie_string = get_cookie_string(cookie_dict)
    if not cookie_string:
        raise ValueError("❌ No hay cookies válidas")

    headers = dict(BASE_HEADERS)
    headers["Cookie"] = cookie_string

    try:
        response = requests.get(API_URL, params=QUERY_PARAMS, headers=headers, timeout=30, verify=False)

        if response.status_code == 401:
            raise ValueError("❗️ COOKIE INVALIDA - La sesión ha expirado")

        if response.status_code != 200:
            token = extract_nftoken_from_cookie(cookie_dict)
            if token:
                return token, None
            raise ValueError(f"❗️ COOKIE INVALIDA - Error {response.status_code}")

        data = response.json()
        
        if data.get("error") or data.get("errors"):
            token = extract_nftoken_from_cookie(cookie_dict)
            if token:
                return token, None
            raise ValueError("❗️ COOKIE INVALIDA - Sesión expirada")

        token_data = data.get("value", {}).get("account", {}).get("token", {}).get("default", {})
        token = token_data.get("token")
        expires = token_data.get("expires")

        if not token:
            token = extract_nftoken_from_cookie(cookie_dict)
            if token:
                return token, None
            raise ValueError("❗️ COOKIE INVALIDA - No se encontró token")

        if isinstance(expires, int) and len(str(expires)) == 13:
            expires //= 1000

        return token, expires

    except requests.Timeout:
        raise ValueError("⏱️ Tiempo de espera agotado")
    except requests.ConnectionError:
        raise ValueError("🔌 Error de conexión")
    except Exception as e:
        raise ValueError(f"❗️ COOKIE INVALIDA - {str(e)}")

def build_nftoken_link(token):
    return f"https://netflix.com/?nftoken={token}"

def format_expiry(expires):
    if not expires:
        return "Desconocida"
    try:
        return datetime.fromtimestamp(expires).strftime("%Y-%m-%d %H:%M:%S")
    except:
        return str(expires)

# ================== BOT DE TELEGRAM ==================

class NetflixBot:
    def __init__(self, token):
        self.token = token
        self.app = None
        self.user_cookies = {}

    # ---------- COMANDO /start ----------
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_chat.type != "private":
            await update.message.reply_text("❌ Este bot solo funciona en privado.")
            return

        keyboard = [
            [
                InlineKeyboardButton("📖 Cómo usar", callback_data="how_to"),
                InlineKeyboardButton("ℹ️ Info", callback_data="info")
            ],
            [
                InlineKeyboardButton("📤 Enviar TXT", callback_data="send_txt")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"╔═══════════════════════════════════╗\n"
            f"║  🎬 <b>NETFLIX NFToken BOT</b>  ║\n"
            f"╚═══════════════════════════════════╝\n\n"
            f"<i>🍪 Convierte cookies en acceso directo</i>\n\n"
            f"▫️ <b>Envía un archivo .txt</b> con tus cookies\n"
            f"▫️ El bot genera un <b>NFToken</b>\n"
            f"▫️ Recibe tu <b>link mágico</b> 🪄\n\n"
            f"📌 <b>Comandos:</b>\n"
            f"  /start  → Menú principal\n"
            f"  /howto  → Instrucciones\n\n"
            f"{WATERMARK}",
            parse_mode='HTML',
            reply_markup=reply_markup
        )

    # ---------- COMANDO /howto ----------
    async def howto_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_chat.type != "private":
            await update.message.reply_text("❌ Solo en privado.")
            return

        await update.message.reply_text(
            f"╔═══════════════════════════════════════╗\n"
            f"║  📖 <b>CÓMO USAR ESTE BOT</b>  ║\n"
            f"╚═══════════════════════════════════════╝\n\n"
            f"<b>1️⃣ OBTÉN TUS COOKIES</b>\n"
            f"   Usa EditThisCookie o Cookie-Editor\n"
            f"   Copia las cookies de Netflix 🍪\n\n"
            f"<b>2️⃣ CREA UN ARCHIVO TXT</b>\n"
            f"   Pega las cookies en un archivo\n"
            f"   Formato: <code>NetflixId=abc123; SecureNetflixId=def456</code>\n\n"
            f"<b>3️⃣ ENVÍA EL ARCHIVO</b>\n"
            f"   Arrástralo al chat o adjúntalo\n\n"
            f"<b>4️⃣ RECIBE TU LINK</b>\n"
            f"   • Si el link es <b>CORTO</b> (≤ 350 caracteres) → ✅ Cookie Válida\n"
            f"   • Si el link es <b>LARGO</b> (> 350 caracteres) → ❌ Cookie Inválida\n\n"
            f"<b>⚠️ IMPORTANTE</b>\n"
            f"   • El token tiene fecha de expiración\n"
            f"   • Las cookies se procesan en memoria\n"
            f"   • No guardamos tus datos 🔒\n\n"
            f"{WATERMARK}",
            parse_mode='HTML',
            disable_web_page_preview=True
        )

    # ---------- MANEJO DE ARCHIVOS ----------
    async def file_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_chat.type != "private":
            await update.message.reply_text("❌ Este bot solo funciona en privado.")
            return

        user_id = update.effective_user.id
        document = update.message.document

        if not document.file_name.lower().endswith('.txt'):
            await update.message.reply_text(
                f"╔═══════════════════════════════════╗\n"
                f"║  📄 <b>SOLO ARCHIVOS .TXT</b>  ║\n"
                f"╚═══════════════════════════════════╝\n\n"
                f"Guarda tus cookies en un archivo de texto y envíalo.\n\n"
                f"{WATERMARK}",
                parse_mode='HTML'
            )
            return

        if document.file_size > 10 * 1024 * 1024:
            await update.message.reply_text("📦 Archivo demasiado grande (máx 10 MB)")
            return

        processing_msg = await update.message.reply_text(
            f"⏳ <b>Procesando tu archivo...</b>\n\n"
            f"▫️ Extrayendo cookies...\n"
            f"▫️ Conectando con Netflix...",
            parse_mode='HTML'
        )

        try:
            file = await document.get_file()
            file_content = await file.download_as_bytearray()
            content = file_content.decode('utf-8', errors='ignore')

            if not content.strip():
                await processing_msg.edit_text("❌ El archivo está vacío.")
                return

            cookie_dict = extract_cookie_dict(content)

            if not cookie_dict or REQUIRED_COOKIE not in cookie_dict:
                await processing_msg.edit_text(
                    f"╔═══════════════════════════════════════╗\n"
                    f"║  ❌ <b>COOKIES INVÁLIDAS</b>  ║\n"
                    f"╚═══════════════════════════════════════╝\n\n"
                    f"📌 No se encontró <code>NetflixId</code>\n"
                    f"📌 Usa /howto para ver instrucciones\n\n"
                    f"{WATERMARK}",
                    parse_mode='HTML'
                )
                return

            self.user_cookies[user_id] = cookie_dict

            try:
                token, expires = fetch_nftoken(cookie_dict)
                
                token_valid = is_token_valid(token)
                clean_token = re.sub(r'[^A-Za-z0-9+/=_-]', '', token)
                link = build_nftoken_link(token)

                cookies_found = []
                for key in ["NetflixId", "SecureNetflixId", "nfvdid"]:
                    if key in cookie_dict:
                        value = cookie_dict[key][:25] + "..." if len(cookie_dict[key]) > 25 else cookie_dict[key]
                        cookies_found.append(f"▫️ <code>{key}</code>: {value}")

                if token_valid:
                    await processing_msg.edit_text(
                        f"╔═══════════════════════════════════════╗\n"
                        f"║  ✅ <b>COOKIE VÁLIDA</b> 🎉  ║\n"
                        f"╚═══════════════════════════════════════╝\n\n"
                        f"🔑 <b>Link de acceso:</b>\n"
                        f"<code>{link}</code>\n\n"
                        f"📏 <b>Tamaño del token:</b> <code>{len(clean_token)} caracteres</code> (CORTO ✅)\n\n"
                        f"⏰ <b>Expira:</b> <code>{format_expiry(expires)}</code>\n\n"
                        f"<b>📌 Cookies usadas:</b>\n" + "\n".join(cookies_found) + "\n\n"
                        f"<b>💡 ¿Cómo usar?</b>\n"
                        f"  🔹 Haz clic en el botón de abajo\n"
                        f"  🔹 O copia y pega en tu navegador\n"
                        f"  🔹 Acceso directo a Netflix 🎬\n\n"
                        f"{WATERMARK}",
                        parse_mode='HTML',
                        disable_web_page_preview=True
                    )

                    keyboard = [[InlineKeyboardButton("🎬 Abrir Netflix", url=link)]]
                    await update.message.reply_text(
                        "🔗 <b>Haz clic para acceder</b>",
                        parse_mode='HTML',
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                    
                else:
                    await processing_msg.edit_text(
                        f"╔═══════════════════════════════════════╗\n"
                        f"║  ❌ <b>COOKIE INVALIDA</b>  ║\n"
                        f"╚═══════════════════════════════════════╝\n\n"
                        f"🔑 <b>Link generado:</b>\n"
                        f"<code>{link}</code>\n\n"
                        f"📏 <b>Tamaño del token:</b> <code>{len(clean_token)} caracteres</code> (LARGO ❌)\n\n"
                        f"<b>📌 Posibles causas:</b>\n"
                        f"  🔸 La cookie ha expirado\n"
                        f"  🔸 La sesión no está activa\n"
                        f"  🔸 Las cookies están incompletas\n"
                        f"  🔸 La cuenta fue deslogueada\n\n"
                        f"<b>💡 Solución:</b>\n"
                        f"  1️⃣ Abre Netflix en tu navegador\n"
                        f"  2️⃣ Inicia sesión nuevamente\n"
                        f"  3️⃣ Obtén cookies frescas\n"
                        f"  4️⃣ Envía el nuevo archivo\n\n"
                        f"{WATERMARK}",
                        parse_mode='HTML'
                    )

            except ValueError as e:
                error_msg = str(e)
                await processing_msg.edit_text(
                    f"╔═══════════════════════════════════════╗\n"
                    f"║  ❌ <b>COOKIE INVALIDA</b>  ║\n"
                    f"╚═══════════════════════════════════════╝\n\n"
                    f"<code>{error_msg}</code>\n\n"
                    f"<b>📌 Posibles causas:</b>\n"
                    f"  🔸 La cookie ha expirado\n"
                    f"  🔸 La sesión no está activa\n"
                    f"  🔸 Las cookies están incompletas\n"
                    f"  🔸 La cuenta fue deslogueada\n\n"
                    f"<b>💡 Solución:</b>\n"
                    f"  1️⃣ Abre Netflix en tu navegador\n"
                    f"  2️⃣ Inicia sesión nuevamente\n"
                    f"  3️⃣ Obtén cookies frescas\n"
                    f"  4️⃣ Envía el nuevo archivo\n\n"
                    f"{WATERMARK}",
                    parse_mode='HTML'
                )

        except Exception as e:
            log.error(f"Error: {str(e)}")
            await processing_msg.edit_text(
                f"╔═══════════════════════════════════════╗\n"
                f"║  ❌ <b>ERROR INESPERADO</b>  ║\n"
                f"╚═══════════════════════════════════════╝\n\n"
                f"<code>{str(e)}</code>\n\n"
                f"📌 Verifica que las cookies sean válidas.\n"
                f"📌 Usa /howto para ver instrucciones.\n\n"
                f"{WATERMARK}",
                parse_mode='HTML'
            )

    # ---------- CALLBACKS ----------
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        if query.data == "how_to":
            await self.howto_callback(update, context)
        elif query.data == "info":
            await self.info_callback(update, context)
        elif query.data == "send_txt":
            await self.send_txt_callback(update, context)

    async def howto_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.edit_message_text(
            f"╔═══════════════════════════════════════╗\n"
            f"║  📖 <b>CÓMO USAR ESTE BOT</b>  ║\n"
            f"╚═══════════════════════════════════════╝\n\n"
            f"<b>1️⃣ OBTÉN TUS COOKIES</b>\n"
            f"   Usa EditThisCookie o Cookie-Editor\n"
            f"   Copia las cookies de Netflix 🍪\n\n"
            f"<b>2️⃣ CREA UN ARCHIVO TXT</b>\n"
            f"   Pega las cookies en un archivo\n"
            f"   Formato: <code>NetflixId=abc123; SecureNetflixId=def456</code>\n\n"
            f"<b>3️⃣ ENVÍA EL ARCHIVO</b>\n"
            f"   Arrástralo al chat o adjúntalo\n\n"
            f"<b>4️⃣ RECIBE TU LINK</b>\n"
            f"   • Si el link es <b>CORTO</b> (≤ 350 caracteres) → ✅ Cookie Válida\n"
            f"   • Si el link es <b>LARGO</b> (> 350 caracteres) → ❌ Cookie Inválida\n\n"
            f"🔙 <i>Volver al inicio</i> /start",
            parse_mode='HTML',
            disable_web_page_preview=True
        )

    async def info_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.edit_message_text(
            f"╔═══════════════════════════════════════╗\n"
            f"║  ℹ️ <b>INFORMACIÓN</b>  ║\n"
            f"╚═══════════════════════════════════════╝\n\n"
            f"🤖 <b>Bot:</b> Netflix NFToken Generator\n"
            f"📦 <b>Versión:</b> 7.1\n"
            f"👨‍💻 <b>Creador:</b> @oscuridad10\n\n"
            f"<b>📌 Funciones:</b>\n"
            f"  🔹 Extraer NFToken de cookies\n"
            f"  🔹 Validar cookies por tamaño (≤ 350 = válida)\n"
            f"  🔹 Generar links de acceso\n"
            f"  🔹 Procesamiento en memoria\n\n"
            f"<b>🔐 Seguridad:</b>\n"
            f"  🔸 No se guardan archivos en disco\n"
            f"  🔸 Cookies en memoria temporal\n"
            f"  🔸 No compartimos tus datos\n\n"
            f"🔙 <i>Volver al inicio</i> /start",
            parse_mode='HTML'
        )

    async def send_txt_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.edit_message_text(
            f"╔═══════════════════════════════════════╗\n"
            f"║  📤 <b>ENVIAR ARCHIVO TXT</b>  ║\n"
            f"╚═══════════════════════════════════════╝\n\n"
            f"Adjunta un archivo con extensión <code>.txt</code>\n"
            f"conteniendo tus cookies de Netflix.\n\n"
            f"📝 <b>Formato:</b>\n"
            f"  <code>NetflixId=abc123; SecureNetflixId=def456</code>\n\n"
            f"📌 Usa /howto para ver instrucciones completas\n\n"
            f"🔙 <i>Volver al inicio</i> /start",
            parse_mode='HTML'
        )

    async def unknown(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_chat.type != "private":
            return

        await update.message.reply_text(
            f"╔═══════════════════════════════════════╗\n"
            f"║  📄 <b>ENVÍA UN ARCHIVO .TXT</b>  ║\n"
            f"╚═══════════════════════════════════════╝\n\n"
            f"📌 Usa <code>/start</code> para ver los comandos.\n"
            f"📌 Usa <code>/howto</code> para instrucciones.\n\n"
            f"{WATERMARK}",
            parse_mode='HTML'
        )

    # ========== RUN CON POLLING (Original) ==========
    def run_polling(self):
        """Ejecuta el bot con Polling (original)"""
        print("🎬 Iniciando Netflix NFToken Bot v7.1 (Polling)...")
        print(f"📡 Token: {self.token[:10]}...")
        print("📌 Solo responde en privado.")
        print("💾 Sin archivos locales - Todo en memoria")
        print("📏 Validación por tamaño de token activada")
        print("   ✅ CORTO (≤ 350) = Cookie Válida")
        print("   ❌ LARGO (> 350) = Cookie Inválida")
        print("✅ Bot listo!\n")

        self.app = ApplicationBuilder().token(self.token).build()

        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("howto", self.howto_command))
        self.app.add_handler(MessageHandler(filters.Document.ALL & ~filters.COMMAND, self.file_handler))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.unknown))
        self.app.add_handler(CallbackQueryHandler(self.handle_callback))

        self.app.run_polling()

    # ========== RUN CON WEBHOOK ==========
    def run_webhook(self):
        """Ejecuta el bot con Webhook"""
        if not WEBHOOK_URL:
            log.error("❌ WEBHOOK_URL no configurada")
            print("❌ Configura la variable WEBHOOK_URL")
            print("Ejemplo: WEBHOOK_URL=https://tudominio.onrender.com")
            return

        print("🎬 Iniciando Netflix NFToken Bot v7.1 (Webhook)...")
        print(f"📡 Token: {self.token[:10]}...")
        print(f"🌐 Webhook URL: {WEBHOOK_URL}")
        print(f"📌 Puerto: {PORT}")
        print("✅ Bot listo!\n")

        self.app = ApplicationBuilder().token(self.token).build()

        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("howto", self.howto_command))
        self.app.add_handler(MessageHandler(filters.Document.ALL & ~filters.COMMAND, self.file_handler))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.unknown))
        self.app.add_handler(CallbackQueryHandler(self.handle_callback))

        # Configurar webhook
        webhook_path = f"/{self.token}"
        webhook_url = f"{WEBHOOK_URL}{webhook_path}"
        
        log.info(f"Configurando webhook: {webhook_url}")
        
        # Iniciar con webhook
        self.app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=webhook_path,
            webhook_url=webhook_url,
            drop_pending_updates=True
        )

# ================== MAIN ==================

def main():
    bot = NetflixBot(TOKEN)
    
    # Si WEBHOOK_URL está configurada, usar webhook
    if WEBHOOK_URL:
        bot.run_webhook()
    else:
        # Si no, usar polling
        print("⚠️ WEBHOOK_URL no configurada, usando polling...")
        bot.run_polling()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️ Bot detenido")
    except Exception as e:
        print(f"❌ Error fatal: {e}")
