import discord
from discord.ext import commands
import os
import asyncio
from dotenv import load_dotenv
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

intents = discord.Intents.all()
client = commands.Bot(command_prefix="/", intents=intents)

load_dotenv()
TOKEN = os.getenv("TOKEN")
PRIVATE_GUILD_ID = int(os.getenv("PRIVATE_GUILD_ID"))
PRIVATE_CATEGORY_ID = int(os.getenv("PRIVATE_CATEGORY_ID"))
MONGO_URL = os.getenv("MONGO_URL")


# Create a new client and connect to the server
mongo_client = MongoClient(MONGO_URL, server_api=ServerApi('1'))


welcome = mongo_client["cspro-bot"]["welcome"]
reaction_db = mongo_client["cspro-bot"]["reaction"]
users_db = mongo_client["cspro-bot"]["users"]

@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    mongo_client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
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
    msg = welcome.find_one({"guild_id": member.guild.id})
    if msg is not None:
        await member.send(msg["msg"])
    

@client.event
async def on_raw_reaction_add(reaction):
    if reaction.emoji.is_custom_emoji():
        emoji = f"<:{reaction.emoji.name}:{reaction.emoji.id}>"
    else:
        emoji = reaction.emoji.name
    message = reaction_db.find_one({"channel_id": reaction.channel_id, "message_id": reaction.message_id, "emoji": emoji})
    if message is not None:
        user = reaction.member
        await user.send(message["message"])

@client.event
async def on_message(message):
    check = users_db.find_one({"channel_id":message.channel.id})
    if message.guild is None and message.author.bot is False:
        user = users_db.find_one({"user_id": message.author.id})

        guild = client.get_guild(PRIVATE_GUILD_ID)
        if user is None:
            channel = await guild.create_text_channel(message.author.name,category=guild.get_channel(PRIVATE_CATEGORY_ID))
            users_db.insert_one({"user_id": message.author.id, "channel_id": channel.id})
        else:
            channel = guild.get_channel(user["channel_id"])
            if channel is None:
                channel = await guild.create_text_channel(message.author.name,category=guild.get_channel(PRIVATE_CATEGORY_ID))
                users_db.update_one({"user_id": message.author.id}, {'$set': {"channel_id": channel.id}})
        await channel.send(message.content)
    elif check is not None and message.author.bot is False:
        user = client.get_user(check["user_id"])
        await user.send(message.content)
    
    

# Loading cogs
async def load_extensions():
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            await client.load_extension(f'cogs.{filename[:-3]}')

if __name__ == "__main__":
    asyncio.run(load_extensions())
    client.run(TOKEN)
