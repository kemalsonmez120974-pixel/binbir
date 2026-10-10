import discord
from discord.ext import commands, tasks
import aiohttp
import asyncio

# Bot yetkileri (Intents) ayarlama
intents = discord.Intents.default()
intents.members = True          # Gelen/Giden üye takibi için şart!
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ==========================================
# ⚙️ AYARLAR VE KANAL ID'LERİ (Doldurunuz)
# ==========================================
WELCOME_CHANNEL_ID = 1443995380910919731   # Gelen/Giden duyuru kanalı ID
FREE_GAMES_CHANNEL_ID = 1556345368596455485 # Ücretsiz oyun duyuru kanalı ID
STREAM_CHANNEL_ID = 1443995440038019153	     # Kick yayın duyuru kanalı ID

# Kick Yayıncı Listesi
KICK_CHANNELS = ["yagobir", "berkobir", "burobir", "elcnybir"]
stream_status = {channel: False for channel in KICK_CHANNELS}

# Hafızadaki Ücretsiz Oyunlar (Tekrar tekrar duyuru atmaması için)
announced_games = set()

# ==========================================
# 🚀 BOT BAŞLATMA EVENTİ
# ==========================================
@bot.event
async def on_ready():
    print(f'✅ {bot.user.name} (BİRLİK) aktif ve göreve hazır!')
    check_free_games.start()
    check_kick_streams.start()

# ==========================================
# 👋 GELEN / GİDEN ÜYE DUYURULARI
# ==========================================
@bot.event
async def on_member_join(member):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if channel:
        embed = discord.Embed(
            title="🎉 Aramıza Katıldı!",
            description=f"Hoş geldin {member.mention}! **{member.guild.name}** ailesine katıldığın için çok mutluyuz.",
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"Toplam Üye Sayımız: {member.guild.member_count}")
        await channel.send(embed=embed)

@bot.event
async def on_member_remove(member):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if channel:
        embed = discord.Embed(
            title="👋 Bir Üye Ayrıldı",
            description=f"**{member.name}** aramızdan ayrıldı. Görüşmek üzere!",
            color=discord.Color.red()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"Kalan Üye Sayısı: {member.guild.member_count}")
        await channel.send(embed=embed)

# ==========================================
# 🎮 EPİC GAMES ÜCRETSİZ OYUN KONTROLÜ
# ==========================================
@tasks.loop(minutes=30)
async def check_free_games():
    channel = bot.get_channel(FREE_GAMES_CHANNEL_ID)
    if not channel:
        return

    async with aiohttp.ClientSession() as session:
        epic_url = "https://store-site-backend-static.akamaized.net/freeGamesPromotions?locale=tr-TR&country=TR&allowCountries=TR"
        try:
            async with session.get(epic_url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    elements = data['data']['Catalog']['searchStore']['elements']
                    for game in elements:
                        promotions = game.get('promotions')
                        if promotions and promotions.get('promotionalOffers'):
                            title = game.get('title')
                            game_id = game.get('id')
                            
                            if game_id not in announced_games:
                                announced_games.add(game_id)
                                page_slug = game.get('productSlug') or (game.get('offerMappings')[0]['pageSlug'] if game.get('offerMappings') else None)
                                game_url = f"https://store.epicgames.com/tr/p/{page_slug}" if page_slug else "https://store.epicgames.com/tr/"
                                
                                embed = discord.Embed(
                                    title=f"🎁 Epic Games Ücretsiz Oyun: {title}",
                                    description=f"**{title}** Epic Games'te geçici olarak tamamen ücretsiz!",
                                    url=game_url,
                                    color=discord.Color.purple()
                                )
                                embed.add_field(name="Platform", value="Epic Games Store", inline=True)
                                embed.add_field(name="Hemen Al", value=f"[Oyuna Git]({game_url})", inline=True)
                                if game.get('keyImages'):
                                    embed.set_image(url=game['keyImages'][0]['url'])
                                
                                await channel.send(embed=embed)
        except Exception as e:
            print(f"Epic Games kontrol hatası: {e}")

# ==========================================
# 🔴 KİCK CANLI YAYIN DUYURUSU (OTOMATİK)
# ==========================================
@tasks.loop(minutes=2)  # Her 2 dakikada bir yayın kontrolü yapar
async def check_kick_streams():
    channel = bot.get_channel(STREAM_CHANNEL_ID)
    if not channel:
        return

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        for kick_name in KICK_CHANNELS:
            api_url = f"https://kick.com/api/v2/channels/{kick_name}"
            try:
                async with session.get(api_url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        livestream = data.get('livestream')

                        # Yayıncı canlı yayındaysa
                        if livestream is not None and livestream.get('is_live'):
                            if not stream_status[kick_name]: # Daha önce duyuru atılmadıysa
                                stream_status[kick_name] = True
                                title = livestream.get('session_title', 'Canlı Yayın Başladı!')
                                category = livestream.get('categories', [{}])[0].get('name', 'Genel')
                                viewer_count = livestream.get('viewer_count', 0)
                                stream_url = f"https://kick.com/{kick_name}"

                                # Yayın duyurusu şık bir Embed tasarımı ile
                                embed = discord.Embed(
                                    title=f"🔴 {kick_name.upper()} KICK'TE YAYINDA!",
                                    description=f"**Yayın Başlığı:** {title}\n\n🎮 **Kategori:** `{category}`\n👥 **İzleyici:** `{viewer_count}`",
                                    url=stream_url,
                                    color=discord.Color.from_rgb(83, 252, 24) # Kick yeşili rengi
                                )
                                
                                # Yayından küçük kapak resmi (thumbnail) ekleme
                                if livestream.get('thumbnail'):
                                    embed.set_image(url=livestream['thumbnail']['url'])
                                
                                embed.set_footer(text="BİRLİK Bot • Canlı Yayın Duyuru Sistemi", icon_url=bot.user.display_avatar.url)

                                # Bildirim metni (@everyone veya @here ekleyebilirsin)
                                await channel.send(
                                    content=f"📢 @everyone **{kick_name}** yayına girdi! Kaçırma:", 
                                    embed=embed
                                )
                        else:
                            # Yayın kapandıysa durumu sıfırla ki bir sonraki yayında tekrar duyuru atsın
                            stream_status[kick_name] = False
            except Exception as e:
                print(f"Kick duyuru kontrol hatası ({kick_name}): {e}")

# ==========================================
# 🔑 BOTU BAŞLATMA
# ==========================================
bot.run("MTU1ODQxNzMwMDEwNzk2MDQ3Mg.GTl2ZD.6lYmEWsAvvs98iulyVotOS5o5otOCYHQy1Nyrw")
