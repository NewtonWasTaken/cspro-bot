import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import asyncio

intents = discord.Intents.all()
client = commands.Bot(command_prefix="/", intents=intents)

load_dotenv()
TOKEN = os.getenv("TOKEN")


@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    GUILD_IDS = [guild.id for guild in client.guilds]


    # Copy global commands to guilds
    for guild_id in GUILD_IDS:
        guild = discord.Object(id=guild_id)
        try:
            client.tree.copy_global_to(guild=guild)
            await client.tree.sync(guild=guild)
            print(f"Slash commands synced for guild ID {guild_id}")
        except Exception as e:
            print(f"Error while syncing guild ID {guild_id}: {e}")



@client.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    if isinstance(error, discord.app_commands.MissingPermissions):
        await interaction.response.send_message("❌ Nemáš dostatečná oprávnění pro tento příkaz.", ephemeral=True)
    elif isinstance(error, discord.app_commands.CommandOnCooldown):
        await interaction.response.send_message(f"⏳ Příkaz je na cooldownu, zkus to za {round(error.retry_after, 1)} sekund.", ephemeral=True)
    else:
        # Using reponse if possible, else followup
        try:
            if interaction.response.is_done():
                await interaction.followup.send("❌ Došlo k neočekávané chybě.", ephemeral=True)
            else:
                await interaction.response.send_message("❌ Došlo k neočekávané chybě.", ephemeral=True)
        except Exception:
            pass
        # 
        print(f"[ERROR] {error} while executing command {interaction.command}")

@client.event
async def on_member_join(member):
    await member.send("Vítej na serveru CSPRO!")
        
# Loading cogs
async def load_extensions():
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            await client.load_extension(f'cogs.{filename[:-3]}')

if __name__ == "__main__":
    asyncio.run(load_extensions())
    client.run(TOKEN)
