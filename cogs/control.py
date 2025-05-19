from discord.ext import commands
import discord
from ui import GuildSelectView
import os
from pymongo import MongoClient, ReturnDocument
from pymongo.server_api import ServerApi
from dotenv import load_dotenv


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
        await interaction.response.send_message("\n**Tento Discord bot byl vytvořen pro účely CSPRO akademie. Využívá slash commands.**\n\n ℹ️ **INFORMACE** \n `about` - Informace o botovi\n\n 💬 **ZPRÁVY** \n `⛔ send` - Pošle všem uživatelům zadaného serveru zprávu\n `⛔ welcome <add|edit|remove>` - Nastavuje uvítací zprávu daného serveru\n `⛔ reaction <add|list|remove>` - Nastavuje reakce na danou zprávu. Při reakci na zprávu se uživateli zašle předem nastavená DM \n\n ⛔ - pouze pro Administrátory", ephemeral=True)

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
        
    reaction = discord.app_commands.Group(name="reaction", description="⛔ Nastavuje reakce na danou zprávu. Při reakci na zprávu se uživateli zašle předem nastavená DM")

    @reaction.command(name="add", description="⛔ Přidává reakci na danou zprávu a nastavuje zprávu co se bude posílat.")
    @discord.app_commands.checks.has_permissions(administrator=True)
    async def reaction_add(self, interaction: discord.Interaction, channel_id: str, message_id: str, emoji: str, message: str):
        channel_id = int(channel_id)
        message_id = int(message_id)
        channel = self.client.get_channel(channel_id)

        duplicate = reaction_db.find_one({"channel_id": channel_id, "message_id": message_id, "emoji": emoji})

        if channel is None:
            await interaction.response.send_message("❌ Kanál nenalezen", ephemeral=True)
        elif duplicate is not None:
            await interaction.response.send_message("❌ Tato interakce již existuje", ephemeral=True)
        else:
            try:
                reaction_message = await channel.fetch_message(message_id)
                await reaction_message.add_reaction(emoji)

                id = reaction_db.find_one_and_update({"_id": "id_counter"},{"$inc": {"seq": 1}},upsert=True,return_document=ReturnDocument.AFTER)
                reaction_db.insert_one({"id": id["seq"], "channel_id": channel_id, "message_id": message_id, "emoji": emoji, "message": message})
                
                await interaction.response.send_message(f"✅ Reakce přidána\nReakce ID: `{id["seq"]}`\nChannel ID: `{channel_id}`\nMessage ID `{message_id}`\nEmoji: `{emoji}`\nMessage: `{message}`")
            
            except Exception:
                await interaction.response.send_message("❌ Nastala chyba", ephemeral=True)



    @reaction.command(name="list", description="⛔ Vypisuje všechny zprávy na které existuje reakce se zprávou.")
    @discord.app_commands.checks.has_permissions(administrator=True)
    async def reaction_list(self, interaction: discord.Interaction):
        reactions = list(reaction_db.find({"_id":{"$ne": "id_counter"}}))
        final_message = ""

        if reactions == []:
            await interaction.response.send_message("❌ Bot nemá nastavené žádné reakce.", ephemeral=True)
        else:
            for i in range(len(reactions)):
                if i != 0:
                    final_message += "\n"
                final_message += f"**Reakce ID {reactions[i]["id"]}**\nChannel ID: `{reactions[i]["channel_id"]}`\nMessage ID `{reactions[i]["message_id"]}`\nEmoji: `{reactions[i]["emoji"]}`\nMessage: `{reactions[i]["message"]}`\n\n"
            await interaction.response.send_message(final_message)


    @reaction.command(name="remove", description="⛔ Odstraní reakci na danou zprávu.")
    @discord.app_commands.checks.has_permissions(administrator=True)
    async def reaction_remove(self, interaction: discord.Interaction, reaction_id: str):
        reaction = reaction_db.find_one({"id":int(reaction_id)})

        if reaction is None:
            await interaction.response.send_message("❌ Tato reakce neexistuje", ephemeral=True)
        else:
            reaction_db.delete_one({"id":int(reaction_id)})

            channel = self.client.get_channel(reaction["channel_id"])
            reaction_message = await channel.fetch_message(reaction["message_id"])
            await reaction_message.clear_reaction(reaction["emoji"])

            await interaction.response.send_message(f"✅ Reakce ID {reaction["id"]} úspěšně smazána")
        

async def setup(client: commands.Bot):
    await client.add_cog(Control(client))
