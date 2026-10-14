import asyncio
import json
import os
import random
import discord
from discord.ext import commands
from discord.ui import Button, View
from dotenv import load_dotenv
import requests
import yt_dlp
from threading import Thread
from flask import Flask

# --- Веб-сервер для Render и UptimeRobot ---
app = Flask('')


@app.route('/')
def home():
    return "Bot is alive!"


def run():
    app.run(host='0.0.0.0', port=10000)


def keep_alive():
    t = Thread(target=run)
    t.start()


# Запускаем веб-сервер в фоновом режиме
keep_alive()
# -------------------------------------------

# 1. Завантажуємо токен з файлу .env
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# ID владельца бота (для админ-команд, например !shutdown)
OWNER_ID = 796083179005149204

# 2. Налаштовуємо доступи (Intents)
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

# 3. Ініціалізуємо бота
bot = commands.Bot(command_prefix='!', intents=intents)
bot.remove_command('help')

# Глобальная переменная для хранения текущей громкости (по умолчанию 50%)
CURRENT_VOLUME = 0.5

# Файл бази даних для збереження прив'язок Discord ID -> Steam ID
DB_FILE = 'database.json'


def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_db(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


# --- БАЗА ДАНИХ СВЯЗОК ТА СТРАТЕГІЙ ---
STRATS_DB = {
    2: [
        {"heroes": "Tiny + Centaur Warrunner",
         "desc": "💣 **Тактика «Авіабомба»**: Тіні кидає Кентавра прямо в обличчя ворогам, Кентавр дає стан з ноги!"},
        {"heroes": "Sven + Crystal Maiden",
         "desc": "❄️ **Класичний стан-лайн**: ЦМка дає нескінченний манареген та контролить, Свен все розбиває."},
        {"heroes": "Ursa + Shadow Shaman",
         "desc": "🐻 **Мертвий контроль**: Раста тримає в сітці та гексі, Урса розбирає за пару секунд."},
        {"heroes": "Viper + Venomancer",
         "desc": "🧪 **Отруйне пекло**: Заповільнення та урон отрутою такі, що вороги тильтують вже на 2-й хвилині."},
        {"heroes": "Grimstroke + Lich",
         "desc": "🔮 **Подвійний ульт**: Грімстрок зв'язує ворогів Soulbind'ом, а Ліч пускає чайник, який відскакує з подвійною силою!"}
    ],
    3: [
        {"heroes": "Magnus + Faceless Void + Witch Doctor",
         "desc": "🌀 **Комбо з ультів**: Магнус стягує в RP, Войд ставить купол зверху, а ВД поливає катушкою смерті!"},
        {"heroes": "Centaur + Tusk + Lina",
         "desc": "🛷 **Ганг-сквад**: Таск закидає в кучугуру, Кентавр тупає, Ліна випаровує з Laguna Blade."},
        {"heroes": "Slardar + Dazzle + Ursa",
         "desc": "🛡️ **Мінус армор**: Слардар і Даззл знімають броню в нуль, Урса розриває Рошана та ворогів за 2 удари."}
    ],
    4: [
        {"heroes": "Underlord + Nature's Prophet + Spirit Breaker + Io",
         "desc": "🌍 **Глобал-ганг**: Раптовий поява всієї команди на будь-якій ділянці карти за секунду."},
        {"heroes": "Dark Seer + Enigma + Tidehunter + Disruptor",
         "desc": "🌀 **Стяжка**: Вакуум + Black Hole + Ravage + Static Storm. Вороги навіть не зрозуміють, що сталося."}
    ],
    5: [
        {"heroes": "Ogre Magi + Omniknight + Abaddon + Dazzle + Wraith King",
         "desc": "✨ **Безсмертна паті (Save-страт)**: Вбити неможливо, у кожного по 3 життя та щити."},
        {"heroes": "Nature's Prophet + Zeus + Spectre + Ancient Apparition + Invoker",
         "desc": "📡 **Глобал-спам**: Вороги вмирають на фонтані від прокастів з всієї карти."},
        {"heroes": "Axe + Crystal Maiden + Lion + Lina + Earthshaker",
         "desc": "⚡ **Пурпурний каст**: Тонна магічного урону та станів у перші 15 хвилин гри."}
    ]
}

# --- БАЗА ДАНИХ ЖАРТІВ ПРО ДОТУ ---
DOTA_JOKES = [
    "— Який у тебе улюблений предмет у Доті?\n— БКБ. Шкода, що мої кєррі про нього ніколи не чули! 🛡️",
    "Сапорт — це професія, де ти купуєш варди на останні гроші, а кєррі все одно вмирає під ворожою вежею та звинувачує тебе. 👁️",
    "Справжня містична загадка Dota 2: чому у ворожого Інвокера 10 рук, а у твого — 2 ліві? 🐙",
    "— Дорогий, ти де?\n— У ЛП, люба... Застряг з 4 міпорями на тиждень. ⛓️",
    "Фраза «Ще одну і спати» офіційно визнана головною причиною зливу 500 MMR за ніч. 📉",
    "Ніщо так не об'єднує 5 незнайомих людей, як ненависть до ворожого Тінкера. 🤖",
    "— Чому ти не купив БКБ?\n— Воно дає занадто мало урону, чувак! (c) Кєррі 0-12-1 🤡"
]

KEYWORD_RESPONSES = {
    'тильт': ["Не тильтуй, випий чайку та тисни «Шукати гру» знову! ☕",
              "Тильт — це просто знак, що час зіграти на Паджі через хук наосліп! 🎣"],
    'мид': ["Двоє людей на міді — це вже не лінія, це сімейні розбірки! ⚔️"],
    'мід': ["Двоє людей на міді — це вже не лінія, це сімейні розбірки! ⚔️"],
    'лп': ["Ласкаво просимо до ЛП! Тут зібралися найкращі уми кіберспорту 🎩"],
    'саппорт': ["Повага сапортам! Без вас цей кєррі помер би ще на 30-й секунді 🤝"],
    'сапорт': ["Повага сапортам! Без вас цей кєррі помер би ще на 30-й секунді 🤝"],
    'бкб': ["БКБ — кнопка для слабких! Справжні козаки ловлять усі стани обличчям! 🗿"],
    'раки': ["Раки живуть не тільки в річці на міді, а й у нашій паті! 🦞"]
}

WEATHER_TRANSLATIONS = {
    'patchy rain nearby': 'Місцями невеликий дощ',
    'light rain shower': 'Невеликий дощ',
    'moderate rain': 'Помірний дощ',
    'heavy rain': 'Сильний дощ',
    'partly cloudy': 'Мінлива хмарність',
    'sunny': 'Сонячно',
    'clear': 'Ясно',
    'overcast': 'Похмуро',
    'light drizzle': 'Мряка',
    'fog': 'Туман',
}


def translate_weather(text):
    if not text:
        return ""
    text_lower = text.lower().strip()
    return WEATHER_TRANSLATIONS.get(text_lower, text)


RADIO_STATIONS = {
    'roks': ('Radio ROKS 🎸', 'https://online.radioroks.ua/RadioROKS_HD'),
    'рок': ('Radio ROKS 🎸', 'https://online.radioroks.ua/RadioROKS_HD'),
    'hit': ('Хіт FM 📻', 'https://online.hitfm.ua/HitFM_HD'),
    'хит': ('Хіт FM 📻', 'https://online.hitfm.ua/HitFM_HD'),
    'kiss': ('Kiss FM 🎧', 'https://online.kissfm.ua/KissFM_HD'),
    'кисс': ('Kiss FM 🎧', 'https://online.kissfm.ua/KissFM_HD'),
    'lux': ('Люкс FM ✨', 'https://online.luxfm.ua/LuxFM_HD'),
    'люкс': ('Люкс FM ✨', 'https://online.luxfm.ua/LuxFM_HD'),
    'nashe': ('Наше Радіо 🇺🇦', 'https://online.nasheradio.ua/NasheRadio_HD'),
    'наше': ('Наше Радіо 🇺🇦', 'https://online.nasheradio.ua/NasheRadio_HD'),
    'bayraktar': ('Радіо Байрактар 🎶', 'https://online.radiobayraktar.ua/RadioBayraktar_HD'),
    'байрактар': ('Радіо Байрактар 🎶', 'https://online.radiobayraktar.ua/RadioBayraktar_HD')
}

yt_dlp.utils.bug_reports_message = lambda *args, **kwargs: ''
ytdl_format_options = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
}

FFMPEG_EXECUTABLE = './ffmpeg.exe' if os.path.exists('./ffmpeg.exe') else 'ffmpeg'
ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}
ytdl = yt_dlp.YoutubeDL(ytdl_format_options)


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=True, volume=0.5):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        if 'entries' in data:
            data = data['entries'][0]
        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, executable=FFMPEG_EXECUTABLE, **ffmpeg_options), data=data,
                   volume=volume)


class BotHelpView(View):
    @discord.ui.button(label="🏓 Пінґ", style=discord.ButtonStyle.blurple)
    async def ping_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("Понґ! Бот на зв'язку та готовий до каток 🏓", ephemeral=True)

    @discord.ui.button(label="📊 Як дізнатися свій ID?", style=discord.ButtonStyle.green)
    async def info_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message(
            "1. Відкрийте профіль на **OpenDota.com**.\n"
            "2. Скопіюйте цифри з адресної строки (`.../players/ВАШ_ID`).\n"
            "3. Напишіть у чат: `!reg ВАШ_ID`.\n"
            "Після цього команда `!last` (`!катка`) буде автоматично перевіряти ваші ігри!",
            ephemeral=True
        )


@bot.event
async def on_ready():
    print(f'Бот {bot.user} успішно запущений і готовий до роботи!')


@bot.event
async def on_member_join(member):
    for channel in member.guild.text_channels:
        if channel.permissions_for(member.guild.me).send_messages:
            await channel.send(
                f"👋 Здоров, {member.mention}! Ласкаво просимо на сервер нашої тусовки. Введи команду `!reg [Steam ID]`, щоб бот запам'ятав твій профіль!")
            break


@bot.event
async def on_voice_state_update(member, before, after):
    if member.bot:
        return
    if before.channel is None and after.channel is not None:
        for channel in member.guild.text_channels:
            if channel.permissions_for(member.guild.me).send_messages:
                await channel.send(
                    f"🎮 **{member.display_name}** залетів у голосовий канал **«{after.channel.name}»**. Готуємось до катки! 🔥")
                break


@bot.event
async def on_message(message):
    if message.author.bot:
        return
    content_lower = message.content.lower()
    for word, responses in KEYWORD_RESPONSES.items():
        if word in content_lower:
            reply = random.choice(responses)
            await message.channel.send(f"{message.author.mention}, {reply}")
            break
    await bot.process_commands(message)


@bot.command(name='ping', aliases=['пінг', 'пинг'])
async def ping(ctx):
    await ctx.send('Понґ! Dotka_bot на зв\'язку та готовий до каток 🏓')


@bot.command(name='wake', aliases=['разбуди', 'розбуди', 'будильник'])
async def wake_user(ctx, *, target_str: str = None):
    if not target_str:
        await ctx.send("❌ Вкажіть, кого потрібно розбудити! Приклад: `!wake @друг` або `!wake MostWanted`")
        return
    target = None
    if ctx.message.mentions:
        target = ctx.message.mentions[0]
    if not target:
        search_query = target_str.lower().strip()
        for member in ctx.guild.members:
            if search_query in member.name.lower() or (
                    member.nick and search_query in member.nick.lower()) or search_query in member.display_name.lower():
                target = member
                break
    if not target:
        await ctx.send(f"❌ Користувача `{target_str}` не знайдено на цьому сервері!")
        return
    await ctx.send(f"🔔 **{target.mention}, ПІДЙОМ!** Тебе кличуть у катку! 🎮🔥")
    try:
        await target.send(f"⏰ **{target.display_name}**, тебе кличуть на сервері **{ctx.guild.name}**! Вмикай звук!")
    except Exception:
        pass
    if target.voice and target.voice.channel:
        current_channel = target.voice.channel
        other_channels = [ch for ch in ctx.guild.voice_channels if ch != current_channel]
        if other_channels and ctx.guild.me.guild_permissions.move_members:
            temp_channel = other_channels[0]
            try:
                await target.move_to(temp_channel)
                await asyncio.sleep(0.5)
                await target.move_to(current_channel)
            except Exception as e:
                print(f"Помилка переміщення: {e}")


@bot.command(name='shutdown', aliases=['выключить', 'вимкнути'])
async def shutdown_bot(ctx):
    if ctx.author.id != OWNER_ID:
        await ctx.send("❌ У вас немає прав на вимкнення бота!")
        return
    await ctx.send("🛑 Вимикаю систему... Бувай! 👋")
    await bot.close()


@bot.command(name='weather', aliases=['погода'])
async def get_weather(ctx, *, city: str):
    async with ctx.typing():
        try:
            url = f"https://wttr.in/{city}?format=j1&lang=uk"
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                current_condition = data['current_condition'][0]
                nearest_area = data['nearest_area'][0]
                today_weather = data['weather'][0]
                city_name = nearest_area['areaName'][0]['value']
                country_name = nearest_area['country'][0]['value']
                temp_c = current_condition['temp_C']
                feels_like_c = current_condition['FeelsLikeC']
                humidity = current_condition['humidity']
                wind_speed = current_condition['windspeedKmph']
                raw_desc = current_condition.get('lang_uk', [{}])[0].get('value') or \
                           current_condition['weatherDesc'][0]['value']
                weather_desc = translate_weather(raw_desc)
                embed = discord.Embed(
                    title=f"🌤️ Погода у місті {city_name} ({country_name})",
                    description=f"**Зараз:** {weather_desc} | 🌡️ **{temp_c}°C** (відчувається як `{feels_like_c}°C`)\n"
                                f"💧 Вологість: `{humidity}%` | 💨 Вітер: `{wind_speed} км/год`",
                    color=discord.Color.teal()
                )
                hourly_list = today_weather.get('hourly', [])
                forecast_lines = []
                for h in hourly_list:
                    time_val = int(h.get('time', 0))
                    hour_str = f"{time_val // 100:02d}:00"
                    h_temp = h.get('tempC', '')
                    h_feels = h.get('FeelsLikeC', '')
                    raw_h_desc = h.get('lang_uk', [{}])[0].get('value') or h.get('weatherDesc', [{}])[0].get('value',
                                                                                                             '')
                    h_desc = translate_weather(raw_h_desc)
                    forecast_lines.append(f"`{hour_str}` — **{h_temp}°C** (відч. `{h_feels}°C`), {h_desc}")
                if forecast_lines:
                    embed.add_field(name="⏰ Прогноз на сьогодні (по інтервалах)", value="\n".join(forecast_lines),
                                    inline=False)
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"❌ Не вдалося знайти місто `{city}`. Перевірте назву.")
        except Exception as e:
            await ctx.send(f"❌ Сталася помилка при запиті погоди: `{e}`")


@bot.command(name='joke', aliases=['жарт', 'анекдот', 'шутка'])
async def joke(ctx):
    random_joke = random.choice(DOTA_JOKES)
    embed = discord.Embed(title="🎭 Дотерський гумор", description=random_joke, color=discord.Color.gold())
    await ctx.send(embed=embed)


@bot.command(name='strat', aliases=['страт', 'связка', "зв'язка"])
async def strat(ctx, count: int = 2):
    if count not in STRATS_DB:
        await ctx.send("❌ Доступні зв'язки тільки для **2, 3, 4 або 5** гравців! Приклад: `!strat 2` або `!страт 5`")
        return
    selected_strat = random.choice(STRATS_DB[count])
    embed = discord.Embed(
        title=f"⚔️ Стратегія / Зв'язка для {count} гравців",
        description=f"**Герої:** `{selected_strat['heroes']}`\n\n{selected_strat['desc']}",
        color=discord.Color.purple()
    )
    await ctx.send(embed=embed)


@bot.command(name='news', aliases=['новости', 'оновлення', 'обновления'])
async def dota_news(ctx):
    async with ctx.typing():
        try:
            url = "https://api.steampowered.com/ISteamNews/GetNewsForApp/v2/?appid=570&count=3&maxlength=200&format=json"
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                news_items = data.get('appnews', {}).get('newsitems', [])
                if not news_items:
                    await ctx.send("📭 Свіжих новин Dota 2 не знайдено.")
                    return
                embed = discord.Embed(title="📰 Останні новини та оновлення Dota 2",
                                      description="Офіційні патчі та анонси від Valve:", color=discord.Color.red())
                for item in news_items[:3]:
                    title = item.get('title', 'Без назви')
                    url_link = item.get('url', '')
                    content = item.get('contents', '')[:150].replace('&quot;', '"').replace('&amp;', '&') + "..."
                    embed.add_field(name=title, value=f"[Читати повністю на Steam]({url_link})\n{content}",
                                    inline=False)
                await ctx.send(embed=embed)
            else:
                await ctx.send("❌ Не вдалося зв'язатися з сервером Steam API.")
        except Exception as e:
            await ctx.send(f"❌ Сталася помилка при отриманні новин: `{e}`")


@bot.command(name='hero', aliases=['герой'])
async def hero_info(ctx, *, hero_name: str):
    async with ctx.typing():
        try:
            heroes_url = "https://api.opendota.com/api/constants/heroes"
            abilities_url = "https://api.opendota.com/api/constants/abilities"
            heroes_res = requests.get(heroes_url)
            abilities_res = requests.get(abilities_url)
            if heroes_res.status_code == 200 and abilities_res.status_code == 200:
                heroes_data = heroes_res.json()
                abilities_data = abilities_res.json()
                found_hero = None
                search_query = hero_name.lower().replace(" ", "").replace("'", "")
                for hero_id, data in heroes_data.items():
                    localized_name = data.get('localized_name', '').lower().replace(" ", "").replace("'", "")
                    name_key = data.get('name', '').replace('npc_dota_hero_', '').lower()
                    if search_query in localized_name or search_query in name_key:
                        found_hero = data
                        break
                if not found_hero:
                    await ctx.send(
                        f"❌ Герой `{hero_name}` не знайдений. Спробуйте ввести англійською (наприклад, `!hero Pudge` або `!герой Axe`).")
                    return
                name = found_hero.get('localized_name')
                primary_attr = found_hero.get('primary_attr', '').upper()
                attr_map = {'STR': 'Сила 💪', 'AGI': 'Спритність 🗡️', 'INT': 'Інтелект 🧠', 'ALL': 'Універсальний 🌟'}
                attr_text = attr_map.get(primary_attr, primary_attr)
                base_str = found_hero.get('base_str', 0)
                str_gain = found_hero.get('str_gain', 0)
                base_agi = found_hero.get('base_agi', 0)
                agi_gain = found_hero.get('agi_gain', 0)
                base_int = found_hero.get('base_int', 0)
                int_gain = found_hero.get('int_gain', 0)
                move_speed = found_hero.get('move_speed', 0)
                base_armor = round(found_hero.get('base_armor', 0), 1)
                roles = ", ".join(found_hero.get('roles', []))
                hero_system_name = found_hero.get('name', '')
                prefix = hero_system_name.replace('npc_dota_hero_', '')
                hero_abilities = []
                for ab_name, ab_data in abilities_data.items():
                    if ab_data.get('dname') and ab_name.startswith(prefix):
                        hero_abilities.append(ab_data.get('dname'))

                # ИСПРАВЛЕННАЯ СТРОКА:
                abilities_text = "\n".join(hero_abilities[:5]) if hero_abilities else "Завантажуються через OpenDota"

                img_path = found_hero.get('img', '')
                img_url = f"https://api.opendota.com{img_path}" if img_path else None
                embed = discord.Embed(title=f"🧙‍♂️ Герой: {name}",
                                      description=f"**Основний атрибут:** {attr_text}\n**Ролі:** {roles}",
                                      color=discord.Color.dark_gold())
                embed.add_field(name="📊 Характеристики",
                                value=f"• Сила: `{base_str}` (+{str_gain}/рів)\n• Спритність: `{base_agi}` (+{agi_gain}/рів)\n• Інтелект: `{base_int}` (+{int_gain}/рів)",
                                inline=True)
                embed.add_field(name="⚔️ Параметри",
                                value=f"• Броня: `{base_armor}`\n• Швидкість: `{move_speed}`\n• Атака: `{found_hero.get('attack_type')}`",
                                inline=True)
                embed.add_field(name="✨ Основні здібності (Скили)", value=f"• {abilities_text}", inline=False)
                if img_url:
                    embed.set_thumbnail(url=img_url)
                await ctx.send(embed=embed)
            else:
                await ctx.send("❌ Не вдалося завантажити дані про героїв.")
        except Exception as e:
            await ctx.send(f"❌ Сталася помилка: `{e}`")


@bot.command(name='reg', aliases=['рег', 'реєстрація', 'регистрация'])
async def register_id(ctx, account_id: int):
    db = load_db()
    db[str(ctx.author.id)] = account_id
    save_db(db)
    await ctx.send(f"✅ Готово, {ctx.author.mention}! Ваш Steam ID (`{account_id}`) успішно збережено.")


@bot.command(name='players', aliases=['гравці', 'игроки'])
async def show_players(ctx):
    db = load_db()
    if not db:
        await ctx.send("📭 Бот поки нікого не запам'ятав! Введіть `!reg [ваш_id]` або `!рег [ваш_id]`.")
        return
    embed = discord.Embed(title="📋 Збережені гравці нашої компанії", color=discord.Color.green())
    for discord_id_str, steam_id in db.items():
        member = ctx.guild.get_member(int(discord_id_str))
        name = member.display_name if member else f"Користувач ({discord_id_str})"
        embed.add_field(name=name, value=f"Steam ID: `{steam_id}`\n`!last <@{discord_id_str}>`", inline=False)
    await ctx.send(embed=embed)


@bot.command(name='help', aliases=['хелп', 'допомога', 'помощь'])
async def help_command(ctx):
    embed = discord.Embed(title="🤖 Панель керування Dotka_bot", description="Доступні команди (працюють UA / RU / EN):",
                          color=discord.Color.blue())
    embed.add_field(name="`!reg` / `!рег [ID]`", value="Прив'язати ваш Steam ID до Discord.", inline=False)
    embed.add_field(name="`!last` / `!катка` / `!игра`", value="Подивитися останню гру (свою або друга).", inline=False)
    embed.add_field(name="`!wake` / `!разбуди` [@друг]", value="Привернути увагу та «розбудити» друга.", inline=False)
    embed.add_field(name="`!hero` / `!герой [Ім'я]`", value="Інфо та скіли героя (`!герой Pudge`).", inline=False)
    embed.add_field(name="`!weather` / `!погода [Місто]`", value="Детальна погода на день (`!погода Харків`).",
                    inline=False)
    embed.add_field(name="`!news` / `!новости` / `!оновлення`", value="Останні патчі та новини Dota 2 від Valve.",
                    inline=False)
    embed.add_field(name="`!players` / `!гравці`", value="Список усіх зареєстрованих гравців.", inline=False)
    embed.add_field(name="`!strat` / `!страт [2-5]`", value="Випадкова зв'язка героїв для паті (`!страт 2`).",
                    inline=False)
    embed.add_field(name="`!joke` / `!жарт` / `!анекдот`", value="Випадковий жарт про Доту.", inline=False)
    embed.add_field(name="`!play` / `!грати` [назва]", value="Увімкнути музику з YouTube у голосовому каналі.",
                    inline=False)
    radio_list_text = (
        "Увімкнути українське радіо:\n"
        "• `roks` / `рок` — Radio ROKS 🎸\n"
        "• `hit` / `хит` — Хіт FM 📻\n"
        "• `kiss` / `кисс` — Kiss FM 🎧\n"
        "• `lux` / `люкс` — Люкс FM ✨\n"
        "• `nashe` / `наше` — Наше Радіо 🇺🇦\n"
        "• `bayraktar` / `байрактар` — Радіо Байрактар 🎶\n"
        "*(Приклад: `!радіо roks` або `!радіо хит`)*"
    )
    embed.add_field(name="`!radio` / `!радіо` [станція]", value=radio_list_text, inline=False)
    embed.add_field(name="`!volume` / `!гучність` / `!громкость` [0-100]",
                    value="Змінити гучність відтворення (`!гучність 20`).", inline=False)
    embed.add_field(name="`!stop` / `!стоп`", value="Зупинити програвання музики чи радіо.", inline=False)
    embed.add_field(name="`!leave` / `!вийти` / `!выйти`", value="Вигнати бота з голосового каналу.", inline=False)
    embed.add_field(name="`!shutdown` / `!выключить`", value="Вимкнути бота (тільки для власника).", inline=False)
    embed.set_footer(text="Використовуйте кнопки нижче 👇")
    await ctx.send(embed=embed, view=BotHelpView())


@bot.command(name='last', aliases=['катка', 'гра', 'игра', 'матч'])
async def last_match(ctx, target: str = None):
    db = load_db()
    account_id = None
    if target is None:
        user_id_str = str(ctx.author.id)
        if user_id_str in db:
            account_id = db[user_id_str]
        else:
            await ctx.send("⚠️ Ви не прив'язали Steam ID! Напишіть `!reg [ID]` або `!last [ID]`")
            return
    elif target.startswith('<@') and target.endswith('>'):
        clean_id = target.replace('<@', '').replace('!', '').replace('>', '')
        if clean_id in db:
            account_id = db[clean_id]
        else:
            await ctx.send("⚠️ У цього учасника не прив'язаний Steam ID.")
            return
    else:
        try:
            account_id = int(target)
        except ValueError:
            await ctx.send("❌ Невірний формат! Використовуйте: `!last`, `!катка @друг` або `!last [ID]`")
            return
    url = f"https://api.opendota.com/api/players/{account_id}/recentMatches"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            matches = response.json()
            if not matches:
                await ctx.send(f"⚠️ У гравця з ID `{account_id}` немає останніх матчів.")
                return
            match = matches[0]
            match_id = match.get('match_id')
            hero_id = match.get('hero_id')
            kills = match.get('kills', 0)
            deaths = match.get('deaths', 0)
            assists = match.get('assists', 0)
            player_slot = match.get('player_slot', 0)
            is_radiant = player_slot < 128
            radiant_win = match.get('radiant_win', False)
            won = (is_radiant and radiant_win) or (not is_radiant and not radiant_win)
            result_text = "🏆 Перемога!" if won else "💀 Поразка"
            await ctx.send(
                f"📊 **Статистика останнього матчу (ID: `{account_id}`):**\n"
                f"• Результат: **{result_text}**\n"
                f"• Герой (ID): `{hero_id}`\n"
                f"• KDA: `{kills} / {deaths} / {assists}`\n"
                f"• ID матча: `{match_id}`"
            )
        else:
            await ctx.send("❌ Помилка зв'язку з OpenDota API.")
    except Exception as e:
        await ctx.send(f"❌ Сталася помилка: `{e}`")


@bot.command(name='volume', aliases=['громкость', 'гучність', 'vol'])
async def change_volume(ctx, volume: int = None):
    global CURRENT_VOLUME
    if volume is None:
        await ctx.send(f"🔊 Поточна гучність бота: `{int(CURRENT_VOLUME * 100)}%`")
        return
    if volume < 0 or volume > 100:
        await ctx.send("❌ Гучність має бути в діапазоні від **0 до 100**!")
        return
    CURRENT_VOLUME = volume / 100.0
    if ctx.voice_client and ctx.voice_client.source:
        ctx.voice_client.source.volume = CURRENT_VOLUME
    await ctx.send(f"🔊 Гучність встановлено на **{volume}%**!")


@bot.command(name='radio', aliases=['радио', 'радіо'])
async def play_radio(ctx, station_name: str = None):
    if not ctx.author.voice:
        await ctx.send("❌ Ви повинні перебувати в голосовому каналі!")
        return
    if not station_name:
        embed = discord.Embed(
            title="📻 Доступні радіостанції",
            description="Використання: `!радіо [назва]` (наприклад: `!радіо roks` або `!радіо хит`)\n\n"
                        "• **roks / рок** — Radio ROKS 🎸\n"
                        "• **hit / хит** — Хіт FM 📻\n"
                        "• **kiss / кисс** — Kiss FM 🎧\n"
                        "• **lux / люкс** — Люкс FM ✨\n"
                        "• **nashe / наше** — Наше Радіо 🇺🇦\n"
                        "• **bayraktar / байрактар** — Радіо Байрактар 🎶",
            color=discord.Color.gold()
        )
        await ctx.send(embed=embed)
        return
    station_key = station_name.lower().strip()
    if station_key not in RADIO_STATIONS:
        await ctx.send(f"❌ Радіостанцію `{station_name}` не знайдено! Напишіть `!радіо`, щоб побачити список.")
        return
    title, stream_url = RADIO_STATIONS[station_key]
    channel = ctx.author.voice.channel
    if ctx.voice_client is None:
        await channel.connect()
    elif ctx.voice_client.channel != channel:
        await ctx.voice_client.move_to(channel)
    async with ctx.typing():
        try:
            if ctx.voice_client.is_playing():
                ctx.voice_client.stop()
            raw_source = discord.FFmpegPCMAudio(stream_url, **ffmpeg_options)
            source = discord.PCMVolumeTransformer(raw_source, volume=CURRENT_VOLUME)
            ctx.voice_client.play(source, after=lambda e: print(f'Помилка радіо: {e}') if e else None)
            await ctx.send(f"📻 Зараз грає радіостанція: **{title}** (гучність `{int(CURRENT_VOLUME * 100)}%`) ")
        except Exception as e:
            await ctx.send(f"❌ Не вдалося підключитися до радіопотоку: `{e}`")


@bot.command(name='play', aliases=['грати', 'играть', 'музика', 'музыка'])
async def play(ctx, *, query: str):
    if not ctx.author.voice:
        await ctx.send("❌ Ви повинні перебувати в голосовому каналі, щоб увімкнути музику!")
        return
    channel = ctx.author.voice.channel
    if ctx.voice_client is None:
        await channel.connect()
    elif ctx.voice_client.channel != channel:
        await ctx.voice_client.move_to(channel)
    async with ctx.typing():
        try:
            player = await YTDLSource.from_url(query, loop=bot.loop, stream=True, volume=CURRENT_VOLUME)
            if ctx.voice_client.is_playing():
                ctx.voice_client.stop()
            ctx.voice_client.play(player, after=lambda e: print(f'Помилка програвання: {e}') if e else None)
            await ctx.send(f"🎶 Зараз грає: **{player.title}** (гучність `{int(CURRENT_VOLUME * 100)}%`) ")
        except Exception as e:
            await ctx.send(f"❌ Не вдалося відтворити трек: `{e}`")


@bot.command(name='stop', aliases=['стоп'])
async def stop(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏹ Потік зупинено.")
    else:
        await ctx.send("⚠️ Зараз нічого не грає.")


# Запуск бота
bot.run(TOKEN)