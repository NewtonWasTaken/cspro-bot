import discord

class GuildSelect(discord.ui.Select):
    def __init__(self, guilds: list[discord.Guild], client: discord.Client, view: discord.ui.View):
        self.client = client
        self._view = view
        options = [
            discord.SelectOption(label=guild.name, value=str(guild.id))
            for guild in guilds
        ]
        super().__init__(
            placeholder="Vyber server",
            options=options,
            min_values=1,
            max_values=1
        )

    async def callback(self, interaction: discord.Interaction):
        guild_id = int(self.values[0])
        guild = self.client.get_guild(guild_id)
        self.view.selected_guild = guild
        self.view.stop()  # Waiting for choice
        await interaction.response.defer() 

class GuildSelectView(discord.ui.View):
    def __init__(self, guilds: list[discord.Guild], client: discord.Client):
        super().__init__()
        self.selected_guild: discord.Guild | None = None
        self.add_item(GuildSelect(guilds, client, self))
