import os
import discord
from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
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
        print(f"Slash commands sincronizados: {len(synced)}")
    except Exception as e:
        print(e)


@bot.tree.command(name="hora", description="Muestra la hora actual del bot", guild=discord.Object(id=GUILD_ID))
async def hora(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)

    ahora = datetime.now(TZ)

    await interaction.followup.send(
        f"🕒 Hora actual del bot: `{ahora.strftime('%Y-%m-%d %H:%M:%S')}`",
        ephemeral=True
    )


@bot.tree.command(name="tareas", description="Muestra publicaciones programadas", guild=discord.Object(id=GUILD_ID))
async def tareas(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)

    jobs = scheduler.get_jobs()

    if not jobs:
        await interaction.followup.send("📭 No hay publicaciones programadas.", ephemeral=True)
        return

    texto = "**Publicaciones programadas:**\n\n"

    for job in jobs:
        texto += f"📌 Publicación: `{job.name}`\n"
        texto += f"🕒 Hora: `{job.next_run_time.astimezone(TZ).strftime('%Y-%m-%d %H:%M:%S')}` hora Chile\n"
        texto += f"🆔 Job ID: `{job.id}`\n\n"

    await interaction.followup.send(texto, ephemeral=True)


@bot.tree.command(name="clonar_aqui", description="Clona este post al foro destino", guild=discord.Object(id=GUILD_ID))
async def clonar_aqui(
    interaction: discord.Interaction,
    foro_destino: discord.ForumChannel
):
    await interaction.response.defer(ephemeral=True)

    try:
        post_id = interaction.channel.id

        await clonar_post(post_id, foro_destino.id)

        await interaction.followup.send(
            f"✅ Publicación clonada.\n"
            f"📁 Destino: {foro_destino.mention}",
            ephemeral=True
        )

    except Exception as e:
        await interaction.followup.send(f"❌ Error: `{e}`", ephemeral=True)


@bot.tree.command(name="programar_aqui", description="Programa este post para publicarse después", guild=discord.Object(id=GUILD_ID))
async def programar_aqui(
    interaction: discord.Interaction,
    foro_destino: discord.ForumChannel,
    dias: int = 0,
    horas: int = 0,
    minutos: int = 0
):
    await interaction.response.defer(ephemeral=True)

    try:
        if dias < 0 or horas < 0 or minutos < 0:
            await interaction.followup.send("❌ No uses números negativos.", ephemeral=True)
            return

        if dias == 0 and horas == 0 and minutos == 0:
            await interaction.followup.send(
                "❌ Debes poner al menos minutos, horas o días.",
                ephemeral=True
            )
            return

        post_id = interaction.channel.id
        ahora = datetime.now(TZ)

        fecha_hora = ahora + timedelta(
            days=dias,
            hours=horas,
            minutes=minutos
        )

thread = interaction.channel
nombre_post = getattr(thread, "name", "Post sin nombre")

        job = scheduler.add_job(
    clonar_post,
    "date",
    run_date=fecha_hora,
    args=[post_id, foro_destino.id],
    id=f"{post_id}-{foro_destino.id}-{int(fecha_hora.timestamp())}",
    name=f"{nombre_post} → {foro_destino.name}"
)

        await interaction.followup.send(
            f"✅ Publicación programada.\n"
            f"📁 Destino: {foro_destino.mention}\n"
            f"🕒 Publicará: `{fecha_hora.strftime('%Y-%m-%d %H:%M:%S')}` hora Chile\n"
            f"🆔 Job ID: `{job.id}`",
            ephemeral=True
        )

    except Exception as e:
        await interaction.followup.send(f"❌ Error: `{e}`", ephemeral=True)

@bot.tree.command(
    name="cancelar_tarea",
    description="Cancela una publicación programada",
    guild=discord.Object(id=GUILD_ID)
)
async def cancelar_tarea(
    interaction: discord.Interaction,
    job_id: str
):
    await interaction.response.defer(ephemeral=True)

    try:
        job = scheduler.get_job(job_id)

        if not job:
            await interaction.followup.send(
                "❌ No se encontró esa tarea.",
                ephemeral=True
            )
            return

        scheduler.remove_job(job_id)

        await interaction.followup.send(
            f"🗑️ Tarea cancelada.\n🆔 Job ID: `{job_id}`",
            ephemeral=True
        )

    except Exception as e:
        await interaction.followup.send(
            f"❌ Error: `{e}`",
            ephemeral=True
        )
bot.run(TOKEN)