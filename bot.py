import os
import discord
from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
scheduler = AsyncIOScheduler()


async def clonar_post(post_id: int, foro_destino_id: int):
    thread = await bot.fetch_channel(post_id)

    foro_destino = bot.get_channel(foro_destino_id)
    if foro_destino is None:
        foro_destino = await bot.fetch_channel(foro_destino_id)

    starter_message = await thread.fetch_message(thread.id)
    contenido = starter_message.content

    archivos = []
    for attachment in starter_message.attachments:
        if attachment.filename.lower().endswith((".zip", ".rar", ".7z")):
            continue
        archivos.append(await attachment.to_file())

    await foro_destino.create_thread(
        name=thread.name,
        content=contenido,
        files=archivos
    )


@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")
    if not scheduler.running:
        scheduler.start()


@bot.command()
async def clonar(ctx, post_id: int, foro_destino_id: int):
    await ctx.send("Clonando publicación...")
    try:
        await clonar_post(post_id, foro_destino_id)
        await ctx.send("✅ Publicación clonada correctamente.")
    except Exception as e:
        await ctx.send(f"❌ Error: `{e}`")


@bot.command()
async def programar(ctx, post_id: int, foro_destino_id: int, fecha: str, hora: str):
    try:
        fecha_hora = datetime.strptime(f"{fecha} {hora}", "%Y-%m-%d %H:%M")

        scheduler.add_job(
            clonar_post,
            "date",
            run_date=fecha_hora,
            args=[post_id, foro_destino_id]
        )

        await ctx.send(f"✅ Programado para `{fecha} {hora}`.")
    except Exception as e:
        await ctx.send(f"❌ Error: `{e}`")


@bot.command()
async def ayuda(ctx):
    await ctx.send("""
**Comandos**

`!clonar ID_POST ID_FORO_DESTINO`
Clona inmediatamente en el foro que elijas.

`!programar ID_POST ID_FORO_DESTINO YYYY-MM-DD HH:MM`
Programa una clonación en el foro que elijas.

Ejemplo:
`!clonar 123456789123456789 987654321987654321`

Ejemplo programado:
`!programar 123456789123456789 987654321987654321 2026-05-08 20:00`
""")


bot.run(TOKEN)