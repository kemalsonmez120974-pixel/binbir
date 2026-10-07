import discord
from discord.ext import commands, tasks
import requests
import logging
import sys
import asyncio
import os
import threading
from flask import Flask, render_template_string, request, redirect, url_for

# ----------------------------------------------------
# LOGLAMA AYARLARI
# ----------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)]
)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ----------------------------------------------------
# AYARLAR (Kanal ID'leri ve Token)
# ----------------------------------------------------
BOT_TOKEN = "MTU1NjI3NzgyMjUzMDc4MTI1Ng.GwXI35.42_dZX3JaA2_oL9brcOPBODpI9liuQ7xg6uNIU"

DUYURU_KANALLARI = [1443995440038019153]
GIRIS_CIKIS_KANAL_ID = 1443995380910919731  
OYUN_DUYURU_KANAL_ID = 1556345368596455485

YAYINCILAR = ["elcnybir", "berkobir", "burobir", "yagobir"]
yayin_durumlari = {yayinci: False for yayinci in YAYINCILAR}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

SON_LOGLAR = []

class WebLogHandler(logging.Handler):
    def emit(self, record):
        log_entry = self.format(record)
        SON_LOGLAR.append(log_entry)
        if len(SON_LOGLAR) > 50:
            SON_LOGLAR.pop(0)

web_handler = WebLogHandler()
web_handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s", "%H:%M:%S"))
logging.getLogger().addHandler(web_handler)

def kick_yayin_kontrol(kullanici_adi):
    try:
        url = f"https://kick.com/api/v2/channels/{kullanici_adi}"
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            data = response.json()
            livestream = data.get("livestream")
            if livestream is not None and livestream.get("is_live") is True:
                kategoriler = livestream.get("categories") or []
                kategori_adi = kategoriler[0].get("name", "Genel") if kategoriler else "Genel"
                thumbnail_data = livestream.get("thumbnail") or {}
                return {
                    "canli": True,
                    "baslik": livestream.get("session_title", "Canlı Yayın!"),
                    "kategori": kategori_adi,
                    "izleyici": livestream.get("viewer_count", 0),
                    "resim": thumbnail_data.get("url", "")
                }
    except Exception as e:
        logging.error(f"Kick API bağlantı hatası ({kullanici_adi}): {e}")
    return {"canli": False}

# ----------------------------------------------------
# 1. KICK YAYIN KONTROL DÖNGÜSÜ
# ----------------------------------------------------
@tasks.loop(seconds=60)
async def yayin_kontrol_dongusu():
    logging.info("🔍 Kick yayıncılık durumları taranıyor...")
    for yayinci in YAYINCILAR:
        bilgi = kick_yayin_kontrol(yayinci)
        if bilgi["canli"] and not yayin_durumlari[yayinci]:
            yayin_durumlari[yayinci] = True
            logging.info(f"🟢 YAYIN BAŞLADI: {yayinci} canlı yayında!")
            
            embed = discord.Embed(
                title=f"🟢 {yayinci.upper()} CANLI YAYINDA!",
                description=f"**{bilgi['baslik']}**\n\n👉 [Yayına Katılmak İçin Tıkla](https://kick.com/{yayinci})",
                color=0x53FC18
            )
            embed.add_field(name="🎮 Kategori", value=bilgi["kategori"], inline=True)
            if bilgi["resim"]:
                embed.set_image(url=bilgi["resim"])
            embed.set_