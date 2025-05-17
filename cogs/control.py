from discord.ext import commands
import discord
from ui import GuildSelectView
from dotenv import load_dotenv
import os
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi


load_dotenv()
MONGO_URL = os.getenv("MONGO_URL")
# Create a new client and connect to the server
mongo_client = MongoClient(MONGO_URL, server_api=ServerApi('1'))

welcome = mongo_client["cspro-bot"]["welcome"]
reaction_db = mongo_client["cspro-bot"]["reaction"]

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

    
    welcome = discord.app_commands.Group(name="welcome", description="⛔ Nastavuje uvítací zprávu daného serveru")

    @welcome.command(name="add", description="⛔ Přidává uvítací zprávu pro členy daného serveru")
    @discord.app_commands.checks.has_permissions(administrator=True)
    async def welcome_add(self, interaction: discord.Interaction, message: str):
        view = GuildSelectView(self.client.guilds, self.client)
        await interaction.response.send_message("Vyberte server pro který chcete welcome zprávu přidat:", view=view, ephemeral=True)
        await view.wait()  # Waits for choice
        guild = view.selected_guild
        if welcome.find_one({"guild_id": guild.id}) is not None:
            await interaction.followup.send(f"❌ Zpráva pro server ID `{guild.id}` už existuje: \n `{welcome.find_one({"guild_id": guild.id})["msg"]}`")
        else:
            welcome.insert_one({"guild_id": guild.id, "msg": message})
            await interaction.followup.send(f"✅ Zpráva pro server ID `{guild.id}` bude nastavena na: `{message}`")

    @welcome.command(name="edit", description="⛔ Upravuje uvítací zprávu pro členy daného serveru")
    @discord.app_commands.checks.has_permissions(administrator=True)
    async def welcome_edit(self, interaction: discord.Interaction, new_message: str):
        view = GuildSelectView(self.client.guilds, self.client)
        await interaction.response.send_message("Vyberte server pro který chcete welcome zprávu změnit:", view=view, ephemeral=True)
        await view.wait()  # Waits for choice
        guild = view.selected_guild

        past_msg = welcome.find_one({"guild_id": guild.id})
        if past_msg is None:
            await interaction.followup.send(f"❌ Zpráva pro server ID `{guild.id}` neexistuje")
        else:
            welcome.update_one({"guild_id": guild.id}, {'$set': {"msg": new_message}})
            await interaction.followup.send(f"✅ Změněna zpráva pro server ID `{guild.id}`: \n Původní: `{past_msg["msg"]}`\n Nová: `{new_message}`")

    @welcome.command(name="remove", description="⛔ Odebírá uvítací zprávu pro členy daného serveru")
    @discord.app_commands.checks.has_permissions(administrator=True)
    async def welcome_remove(self, interaction: discord.Interaction):
        view = GuildSelectView(self.client.guilds, self.client)
        await interaction.response.send_message("Vyberte server pro který chcete welcome zprávu smazat:", view=view, ephemeral=True)
        await view.wait()  # Waits for choice
        guild = view.selected_guild

        past_msg = welcome.find_one({"guild_id": guild.id})
        if past_msg is None:
            await interaction.followup.send(f"❌ Zpráva pro server ID `{guild.id}` neexistuje")
        else:
            welcome.delete_one({"guild_id": guild.id})
            await interaction.followup.send(f"✅ Zpráva `{past_msg["msg"]}` pro server ID `{guild.id}` byla smazána.")
        
    reaction = discord.app_commands.Group(name="reaction", description="⛔ Nastavuje reakce na danou zprávu")

    @reaction.command(name="add", description="⛔ Přidává reakci na danou zprávu. Při reakci na zprávu se uživateli zašle DM se zadanou zprávou.")
    @discord.app_commands.checks.has_permissions(administrator=True)
    async def reaction_add(self, interaction: discord.Interaction, channel_id: str, message_id: str, emoji: str, message: str):
        channel_id = int(channel_id)
        message_id = int(message_id)
        channel = self.client.get_channel(channel_id)

        if channel is None:
            await interaction.response.send_message("❌ Kanál nenalezen", ephemeral=True)
        else:
            try:
            
                reaction_message = await channel.fetch_message(message_id)
                print(emoji)
                await reaction_message.add_reaction(emoji)
                reaction_db.insert_one({"channel_id": channel_id, "message_id": message_id, "emoji": emoji, "message": message})
                await interaction.response.send_message(f"✅ Reakce přidána\nChannel ID: `{channel_id}`\nMessage ID `{message_id}`\nEmoji: `{emoji}`\nMessage: `{message}`")
            except Exception:
                await interaction.response.send_message("❌ Nastala chyba", ephemeral=True)
async def setup(client: commands.Bot):
    await client.add_cog(Control(client))
