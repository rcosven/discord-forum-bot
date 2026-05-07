import os
import discord
from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID"))

TZ = ZoneInfo("America/Santiago")
GUILD = discord.Object(id=GUILD_ID)

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
scheduler = AsyncIOScheduler(timezone=TZ)


async def clonar_post(post_id: int, foro_destino_id: int):
    thread = await bot.fetch_channel(post_id)
    foro_destino = await bot.fetch_channel(foro_destino_id)

    starter_message = await thread.fetch_message(thread.id)

    archivos = []
    for attachment in starter_message.attachments:
        if attachment.filename.lower().endswith((".zip", ".rar", ".7z")):
            continue
        archivos.append(await attachment.to_file())

    await foro_destino.create_thread(
        name=thread.name,
        content=starter_message.content,
        files=archivos
    )


@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")

    if not scheduler.running:
        scheduler.start()

    try:
        # limpia comandos globales viejos
        bot.tree.clear_commands(guild=None)
        await bot.tree.sync()

        # sincroniza solo comandos del servidor
        synced = await bot.tree.sync(guild=GUILD)

        print(f"Slash commands sincronizados: {len(synced)}")

    except Exception as e:
        print(e)


@bot.tree.command(name="hora", description="Muestra la hora actual del bot", guild=GUILD)
async def hora(interaction: discord.Interaction):
    await interaction.response.send_message(
        f"🕒 Hora actual del bot: `{datetime.now(TZ).strftime('%Y-%m-%d %H:%M:%S')}`",
        ephemeral=True
    )


@bot.tree.command(name="programar", description="Programa con fecha exacta", guild=GUILD)
async def programar(
    interaction: discord.Interaction,
    post_id: str,
    foro_destino: discord.ForumChannel,
    fecha: str,
    hora: int,
    minuto: int
):
    await interaction.response.defer(ephemeral=True)

    try:
        if hora < 0 or hora > 23:
            await interaction.followup.send("❌ La hora debe estar entre 0 y 23.", ephemeral=True)
            return

        if minuto < 0 or minuto > 59:
            await interaction.followup.send("❌ El minuto debe estar entre 0 y 59.", ephemeral=True)
            return

        fecha_hora = datetime.strptime(fecha, "%Y-%m-%d")
        fecha_hora = fecha_hora.replace(hour=hora, minute=minuto, tzinfo=TZ)

        if fecha_hora <= datetime.now(TZ):
            await interaction.followup.send(
                f"❌ Esa hora ya pasó.\n"
                f"Hora actual: `{datetime.now(TZ).strftime('%Y-%m-%d %H:%M:%S')}`",
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
            f"✅ Programado correctamente.\n"
            f"📌 Post ID: `{post_id}`\n"
            f"📁 Destino: {foro_destino.mention}\n"
            f"🕒 Hora: `{fecha_hora.strftime('%Y-%m-%d %H:%M:%S')}` hora Chile\n"
            f"🆔 Job ID: `{job.id}`",
            ephemeral=True
        )

    except Exception as e:
        await interaction.followup.send(f"❌ Error: `{e}`", ephemeral=True)


@bot.tree.command(name="programar_rapido", description="Programa usando días, hora y minuto", guild=GUILD)
async def programar_rapido(
    interaction: discord.Interaction,
    post_id: str,
    foro_destino: discord.ForumChannel,
    dias: int,
    hora: int,
    minuto: int
):
    await interaction.response.defer(ephemeral=True)

    try:
        if dias < 0:
            await interaction.followup.send("❌ Los días no pueden ser negativos.", ephemeral=True)
            return

        if hora < 0 or hora > 23:
            await interaction.followup.send("❌ La hora debe estar entre 0 y 23.", ephemeral=True)
            return

        if minuto < 0 or minuto > 59:
            await interaction.followup.send("❌ El minuto debe estar entre 0 y 59.", ephemeral=True)
            return

        ahora = datetime.now(TZ)
        fecha_base = ahora + timedelta(days=dias)

        fecha_hora = fecha_base.replace(
            hour=hora,
            minute=minuto,
            second=0,
            microsecond=0
        )

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
            f"✅ Programado rápido.\n"
            f"📌 Post ID: `{post_id}`\n"
            f"📁 Destino: {foro_destino.mention}\n"
            f"📆 Días desde hoy: `{dias}`\n"
            f"🕒 Hora: `{fecha_hora.strftime('%Y-%m-%d %H:%M:%S')}` hora Chile\n"
            f"🆔 Job ID: `{job.id}`",
            ephemeral=True
        )

    except Exception as e:
        await interaction.followup.send(f"❌ Error: `{e}`", ephemeral=True)


@bot.tree.command(name="programar_test", description="Programa una prueba en X minutos", guild=GUILD)
async def programar_test(
    interaction: discord.Interaction,
    post_id: str,
    foro_destino: discord.ForumChannel,
    minutos: int
):
    await interaction.response.defer(ephemeral=True)

    try:
        if minutos <= 0:
            await interaction.followup.send("❌ Los minutos deben ser mayores a 0.", ephemeral=True)
            return

        fecha_hora = datetime.now(TZ) + timedelta(minutes=minutos)

        job = scheduler.add_job(
            clonar_post,
            "date",
            run_date=fecha_hora,
            args=[int(post_id), foro_destino.id]
        )

        await interaction.followup.send(
            f"✅ Test programado.\n"
            f"📌 Post ID: `{post_id}`\n"
            f"📁 Destino: {foro_destino.mention}\n"
            f"⏱️ En: `{minutos}` minuto(s)\n"
            f"🕒 Hora exacta: `{fecha_hora.strftime('%Y-%m-%d %H:%M:%S')}` hora Chile\n"
            f"🆔 Job ID: `{job.id}`",
            ephemeral=True
        )

    except Exception as e:
        await interaction.followup.send(f"❌ Error: `{e}`", ephemeral=True)


@bot.tree.command(name="tareas", description="Muestra publicaciones programadas", guild=GUILD)
async def tareas(interaction: discord.Interaction):
    jobs = scheduler.get_jobs()

    if not jobs:
        await interaction.response.send_message(
            "📭 No hay publicaciones programadas.",
            ephemeral=True
        )
        return

    texto = "**Publicaciones programadas:**\n\n"

    for job in jobs:
        texto += f"🆔 Job ID: `{job.id}`\n"
        texto += f"🕒 Hora: `{job.next_run_time.astimezone(TZ).strftime('%Y-%m-%d %H:%M:%S')}` hora Chile\n\n"

    await interaction.response.send_message(texto, ephemeral=True)


bot.run(TOKEN)