from discord.ext import commands
import discord
from ui import GuildSelectView

class Control(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        
    @commands.Cog.listener()
    async def on_ready(self):
        print("Loaded cog: Control")

    @discord.app_commands.command(name="help", description="Vypíše jak používat tohoto bota.")
    async def help(self, interaction: discord.Interaction):
        await interaction.response.send_message("\n**Tento Discord bot byl vytvořen pro účely CSPRO akademie. Využívá slash commands.**\n\n ℹ️ **INFORMACE** \n `about` - Informace o botovi\n\n 💬 **ZPRÁVY** \n `⛔send` - Pošle všem uživatelům zadaného serveru zprávu \n\n ⛔ - pouze pro Administrátory", ephemeral=True)

    @discord.app_commands.command(name="about", description="Informace o botovi")
    async def about(self, interaction: discord.Interaction):
        await interaction.response.send_message("Vytvořeno pro účely CSPRO akademie. \n\n Autor: @newton55", ephemeral=True)

    @discord.app_commands.command(name="send", description="⛔ Pošle všem uživatelům zadaného serveru zprávu")
    @discord.app_commands.checks.has_permissions(administrator=True)
    async def send(self, interaction: discord.Interaction, message: str):
        view = GuildSelectView(self.client.guilds, self.client)
        await interaction.response.send_message("Všem uživatelům z tohoto serveru se zašle daná zpráva.", view=view, ephemeral=True)
        await view.wait()  # Waits for choice
        guild = view.selected_guild

        count = 0
        failed = 0

        for member in guild.members:
            if member.bot:
                continue
            try:
                await member.send(message)
                count += 1
            except Exception:
                failed += 1

        await interaction.followup.send(f"✅ Odesláno {count} uživatelům\n❌ Chyba nastala u {failed} uživatelů")

    
    setup = discord.app_commands.Group(name="setup", description="⛔ Nastavuje reakce na zprávy a uvítací zprávu")

    @setup.command(name="welcome", description="⛔ Nastavuje uvítací zprávu pro členy daného serveru")
    @discord.app_commands.checks.has_permissions(administrator=True)
    async def welcome(self, interaction: discord.Interaction, message: str):
        view = GuildSelectView(self.client.guilds, self.client)
        await interaction.response.send_message("Vyberte server pro který chcete welcome zprávu změnit:", view=view, ephemeral=True)
        await view.wait()  # Waits for choice
        guild = view.selected_guild

        await interaction.followup.send(f"Zpráva pro server ID {guild.id} bude nastavena na {message}")

async def setup(client: commands.Bot):
    await client.add_cog(Control(client))
