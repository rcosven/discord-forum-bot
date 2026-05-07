from discord import app_commands

import os
import discord
from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
from zoneinfo import ZoneInfo

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID"))
TZ = ZoneInfo("America/Santiago")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
scheduler = AsyncIOScheduler(timezone=TZ)


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

    try:
        guild = discord.Object(id=GUILD_ID)
        synced = await bot.tree.sync(guild=guild)
        print(f"Slash commands sincronizados en servidor: {len(synced)}")
    except Exception as e:
        print(e)


@bot.tree.command(name="hora", description="Muestra la hora actual del bot", guild=discord.Object(id=GUILD_ID))
async def hora_slash(interaction: discord.Interaction):
    ahora = datetime.now(TZ)
    await interaction.response.send_message(
        f"🕒 Hora actual del bot: `{ahora.strftime('%Y-%m-%d %H:%M:%S')}`",
        ephemeral=True
    )


@bot.tree.command(name="programar", description="Programa una publicación", guild=discord.Object(id=GUILD_ID))
async def programar_slash(
    interaction: discord.Interaction,
    post_id: str,
    foro_destino: discord.ForumChannel,
    fecha: str,
    hora: str
):
    await interaction.response.defer(ephemeral=True)

    try:
        fecha_hora = datetime.strptime(f"{fecha} {hora}", "%Y-%m-%d %H:%M")
        fecha_hora = fecha_hora.replace(tzinfo=TZ)

        ahora = datetime.now(TZ)

        if fecha_hora <= ahora:
            await interaction.followup.send(
                f"❌ Esa hora ya pasó.\n"
                f"Hora actual: `{ahora.strftime('%Y-%m-%d %H:%M:%S')}`",
                ephemeral=True
            )
            return

        job = scheduler.add_job(
            clonar_post,
            "date",
            run_date=fecha_hora,
            args=[int(post_id), foro_destino.id]
        )

        await interaction.followup.send(
            f"✅ Programado.\n"
            f"📁 Destino: {foro_destino.mention}\n"
            f"🕒 Hora: `{fecha_hora.strftime('%Y-%m-%d %H:%M:%S')}` hora Chile\n"
            f"🆔 Job ID: `{job.id}`",
            ephemeral=True
        )

    except Exception as e:
        await interaction.followup.send(f"❌ Error: `{e}`", ephemeral=True)


@bot.tree.command(name="tareas", description="Muestra publicaciones programadas", guild=discord.Object(id=GUILD_ID))
async def tareas_slash(interaction: discord.Interaction):
    jobs = scheduler.get_jobs()

    if not jobs:
        await interaction.response.send_message("📭 No hay publicaciones programadas.", ephemeral=True)
        return

    texto = "**Publicaciones programadas:**\n\n"

    for job in jobs:
        texto += f"Job ID: `{job.id}`\n"
        texto += f"Hora: `{job.next_run_time.astimezone(TZ).strftime('%Y-%m-%d %H:%M:%S')}` hora Chile\n\n"

    await interaction.response.send_message(texto, ephemeral=True)


bot.run(TOKEN)