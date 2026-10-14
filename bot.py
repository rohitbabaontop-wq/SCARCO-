import os
import asyncio
import random
import re
from datetime import timedelta

import discord
from discord import app_commands
from discord.ext import commands

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = os.getenv("GUILD_ID")  # Optional: faster slash-command sync for one server

# Custom emojis supplied by the user. Custom emoji display depends on the bot having
# access to the emoji's server and permission to use external emojis where applicable.
EMOJI = {
    "announce": "<a:Annoncement:1559450692391796756>",
    "ticket": "<a:ticket:1559451417981362278>",
    "money": "<a:MoneySoaring:1559452586246017054>",
    "giveaway": "<a:Giveaway:1555517336096608357>",
    "giveaway_enter": "<a:Giveawaya:1559457485079969832>",
    "dot": "<a:dot:1559457562745643141>",
    "staff": "<a:cw_z_staff:1559457642533883944>",
    "pin": "<a:rnx_s_pin:1559450114597199962>",
    "blaze": "<a:stolen_emoji_blaze:1554565809286938664>",
    "verified": "<a:blackverify:1559450744392785922>",
    "boost": "<a:BOOST:1554561802392838305>",
    "crown": "<:Unq_crown:1554560108661313626>",
    "gift": "<:Gift:1559450387118035034>",
    "star": "<a:star_shining:1554563019235917824>",
    "arrow": "<a:Arrowrcolor:1554688856606117973>",
    "tick": "<a:tick:1554560660396970134>",
    "shop": "<:shop:1559450293706559599>",
    "cash": "<a:cash:1555505611490205726>",
}

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = True
intents.reactions = True

class PurgatoryBot(commands.Bot):
    async def setup_hook(self):
        if GUILD_ID and GUILD_ID.isdigit():
            guild = discord.Object(id=int(GUILD_ID))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            print(f"Synced commands to test guild {GUILD_ID}")
        else:
            await self.tree.sync()
            print("Synced global application commands")

bot = PurgatoryBot(command_prefix="!", intents=intents)

def styled_embed(title: str, description: str = "", color: int = 0x8B5CF6):
    # Repeated custom emojis are intentionally used throughout the bot's visual style.
    e = discord.Embed(
        title=f"{EMOJI['blaze']} {title} {EMOJI['blaze']}",
        description=f"{EMOJI['star']} {description} {EMOJI['star']}" if description else None,
        color=color
    )
    e.set_footer(text="PURGATORY • COMMUNITY SYSTEM")
    return e

def parse_duration(raw: str) -> int:
    """Accept values such as 30s, 10m, 2h, 1d; return seconds."""
    match = re.fullmatch(r"\s*(\d+)\s*([smhd])\s*", raw.lower())
    if not match:
        raise ValueError("Use a duration like `30s`, `10m`, `2h`, or `1d`.")
    amount = int(match.group(1))
    unit = {"s": 1, "m": 60, "h": 3600, "d": 86400}[match.group(2)]
    seconds = amount * unit
    if seconds < 10 or seconds > 30 * 86400:
        raise ValueError("Duration must be between 10 seconds and 30 days.")
    return seconds

class TicketCategoryView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def open_ticket(self, interaction: discord.Interaction, category: str, emoji: str):
        guild = interaction.guild
        if guild is None:
            return await interaction.response.send_message("This button only works in a server.", ephemeral=True)
        existing = discord.utils.get(guild.text_channels, topic=f"ticket-owner:{interaction.user.id}")
        if existing:
            return await interaction.response.send_message(
                f"{EMOJI['ticket']} You already have an open ticket: {existing.mention}",
                ephemeral=True
            )
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True, read_message_history=True),
        }
        # Staff can be granted access by moving the ticket under a staff-visible category
        # or by adding a role ID in the server's own configuration in a future iteration.
        safe_name = re.sub(r"[^a-z0-9-]", "", interaction.user.name.lower().replace(" ", "-"))[:18] or "member"
        channel = await guild.create_text_channel(
            name=f"ticket-{safe_name}",
            topic=f"ticket-owner:{interaction.user.id} | type:{category}",
            overwrites=overwrites,
            reason=f"Ticket opened by {interaction.user}"
        )
        embed = styled_embed(
            f"{emoji} {category} TICKET",
            f"{EMOJI['pin']} Opened by {interaction.user.mention}\n"
            f"{EMOJI['dot']} Category: **{category}**\n\n"
            f"{EMOJI['staff']} Please explain what you need help with.\n"
            f"{EMOJI['arrow']} Staff will respond when available.",
            0x2ECC71 if category == "BUY | PURCHASE" else
            0xE74C3C if category == "CLAIM | GWY REW" else
            0x9B59B6 if category == "HELP | TEAM SUPPORT" else 0xF1C40F
        )
        await channel.send(content=f"{interaction.user.mention} {EMOJI['ticket']} {EMOJI['blaze']}", embed=embed, view=CloseTicketView())
        await interaction.response.send_message(
            f"{EMOJI['tick']} Ticket created: {channel.mention} {EMOJI['ticket']}",
            ephemeral=True
        )

    @discord.ui.button(label="BUY | PURCHASE", style=discord.ButtonStyle.success, emoji=discord.PartialEmoji(name="MoneySoaring", id=1559452586246017054, animated=True), custom_id="ticket:buy")
    async def buy(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.open_ticket(interaction, "BUY | PURCHASE", EMOJI["money"])

    @discord.ui.button(label="CLAIM | GWY REW", style=discord.ButtonStyle.danger, emoji=discord.PartialEmoji(name="Giveaway", id=1555517336096608357, animated=True), custom_id="ticket:claim")
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.open_ticket(interaction, "CLAIM | GWY REW", EMOJI["giveaway"])

    @discord.ui.button(label="HELP | TEAM SUPPORT", style=discord.ButtonStyle.primary, emoji=discord.PartialEmoji(name="cw_z_staff", id=1496407206940377169, animated=True), custom_id="ticket:help")
    async def help_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.open_ticket(interaction, "HELP | TEAM SUPPORT", EMOJI["staff"])

    @discord.ui.button(label="STAFF | TEAM APPLY", style=discord.ButtonStyle.secondary, emoji=discord.PartialEmoji(name="4280reglas", id=1488923714815787079), custom_id="ticket:staff")
    async def staff_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.open_ticket(interaction, "STAFF | TEAM APPLY", EMOJI["verified"])

class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="ticket:close")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel) or not (channel.topic or "").startswith("ticket-owner:"):
            return await interaction.response.send_message("This isn't a ticket channel.", ephemeral=True)
        owner_match = re.search(r"ticket-owner:(\d+)", channel.topic or "")
        is_owner = owner_match and int(owner_match.group(1)) == interaction.user.id
        perms = interaction.user.guild_permissions
        if not is_owner and not (perms.manage_channels or perms.administrator):
            return await interaction.response.send_message("Only the ticket owner or staff can close this ticket.", ephemeral=True)
        await interaction.response.send_message(f"{EMOJI['blaze']} Ticket closing in 5 seconds...")
        await asyncio.sleep(5)
        await channel.delete(reason=f"Ticket closed by {interaction.user}")

@bot.event
async def on_ready():
    bot.add_view(TicketCategoryView())
    bot.add_view(CloseTicketView())
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")

@bot.tree.command(name="ticketpanel", description="Post the Purgatory ticket panel")
@app_commands.checks.has_permissions(manage_guild=True)
async def ticketpanel(interaction: discord.Interaction):
    embed = discord.Embed(
        title=f"{EMOJI['announce']} TICKET SYSTEM {EMOJI['ticket']}",
        description=(
            f"**__CLICK BELOW TO CREATE A TICKET__** {EMOJI['ticket']}\n\n"
            f"{EMOJI['money']} **BUY | PURCHASE**\n"
            f"{EMOJI['giveaway']} **CLAIM | GWY REW**\n"
            f"{EMOJI['staff']} **HELP | TEAM SUPPORT**\n"
            f"{EMOJI['verified']} **STAFF | TEAM APPLY**\n\n"
            f"{EMOJI['arrow']} Choose the category that matches your request.\n"
            f"{EMOJI['star']} {EMOJI['blaze']} {EMOJI['star']} {EMOJI['blaze']} {EMOJI['star']}"
        ),
        color=0x8B5CF6
    )
    embed.set_footer(text="PURGATORY • TICKET SUPPORT")
    await interaction.channel.send(embed=embed, view=TicketCategoryView())
    await interaction.response.send_message(f"{EMOJI['tick']} Ticket panel posted! {EMOJI['ticket']}", ephemeral=True)

@bot.tree.command(name="giveaway", description="Start a reaction-entry giveaway")
@app_commands.describe(prize="Giveaway prize", winners="Number of winners", duration="Duration like 30s, 10m, 2h, 1d")
@app_commands.checks.has_permissions(manage_guild=True)
async def giveaway(interaction: discord.Interaction, prize: str, winners: app_commands.Range[int, 1, 20], duration: str):
    try:
        seconds = parse_duration(duration)
    except ValueError as exc:
        return await interaction.response.send_message(str(exc), ephemeral=True)
    ends_at = discord.utils.utcnow() + timedelta(seconds=seconds)
    embed = discord.Embed(
        title=f"{EMOJI['giveaway']} {prize} {EMOJI['giveaway']}",
        description=(
            f"{EMOJI['dot']} **WINNERS** - `{winners}`\n\n"
            f"{EMOJI['dot']} **HOSTED BY** - {interaction.user.mention}\n\n"
            f"{EMOJI['dot']} **ENDS IN** - <t:{int(ends_at.timestamp())}:R>\n\n"
            f"**REACT WITH {EMOJI['giveaway_enter']} TO ENTER GIVEAWAY**\n"
            f"{EMOJI['star']} {EMOJI['blaze']} {EMOJI['star']} {EMOJI['blaze']} {EMOJI['star']}"
        ),
        color=0xE74C3C
    )
    embed.set_footer(text="PURGATORY • GIVEAWAY SYSTEM")
    await interaction.response.send_message(f"{EMOJI['gift']} Giveaway started! {EMOJI['giveaway']}", ephemeral=True)
    message = await interaction.channel.send(embed=embed)
    emoji_obj = discord.PartialEmoji(name="Giveawaya", id=1559457485079969832, animated=True)
    try:
        await message.add_reaction(emoji_obj)
    except discord.HTTPException:
        await message.add_reaction("🎉")
    await asyncio.sleep(seconds)
    try:
        refreshed = await interaction.channel.fetch_message(message.id)
        reaction = discord.utils.find(
            lambda r: str(r.emoji) in (str(emoji_obj), "🎉"),
            refreshed.reactions
        )
        entrants = []
        if reaction:
            async for user in reaction.users():
                if not user.bot:
                    entrants.append(user)
        random.shuffle(entrants)
        selected = entrants[:winners]
        if selected:
            mentions = ", ".join(u.mention for u in selected)
            await interaction.channel.send(
                f"{EMOJI['crown']} **GIVEAWAY ENDED** {EMOJI['giveaway']}\n"
                f"{EMOJI['gift']} Prize: **{prize}**\n"
                f"{EMOJI['star']} Winner(s): {mentions}\n{EMOJI['blaze']} Congratulations!"
            )
        else:
            await interaction.channel.send(f"{EMOJI['giveaway']} Giveaway ended for **{prize}**, but there were no valid entries.")
    except (discord.NotFound, discord.Forbidden, discord.HTTPException) as exc:
        print(f"Giveaway finalization issue: {exc}")

@bot.tree.command(name="announce", description="Send a Purgatory-style announcement")
@app_commands.describe(tag="Optional member to tag", announcement="Announcement text")
@app_commands.checks.has_permissions(manage_guild=True)
async def announce(interaction: discord.Interaction, announcement: str, tag: discord.Member | None = None):
    tag_text = tag.mention if tag else "@everyone"
    # Prevent accidental everyone pings unless caller intentionally chooses a member.
    if tag is None:
        tag_text = "Community"
    embed = discord.Embed(
        title=f"{EMOJI['blaze']} PURGATORY ANNOUNCE's. {EMOJI['blaze']}",
        description=(
            "· · ────── ꒰ঌ·✦·໒꒱ ────── · ·\n\n"
            f"{EMOJI['pin']} **TAG** • {tag_text}\n\n"
            "· · ────── ꒰ঌ·✦·໒꒱ ────── · ·\n\n"
            f"{announcement}\n\n"
            "· · ────── ꒰ঌ·✦·໒꒱ ────── · ·\n\n"
            f"**BY •** {interaction.user.mention} {EMOJI['staff']}\n"
            f"{EMOJI['star']} {EMOJI['blaze']} {EMOJI['star']} {EMOJI['blaze']} {EMOJI['star']}"
        ),
        color=0x8B5CF6
    )
    embed.set_footer(text="PURGATORY • OFFICIAL ANNOUNCEMENT")
    await interaction.channel.send(content=tag.mention if tag else None, embed=embed, allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False))
    await interaction.response.send_message(f"{EMOJI['tick']} Announcement posted! {EMOJI['announce']}", ephemeral=True)

@bot.tree.command(name="purge", description="Delete recent messages")
@app_commands.describe(amount="Number of messages to delete (1-100)")
@app_commands.checks.has_permissions(manage_messages=True)
async def purge(interaction: discord.Interaction, amount: app_commands.Range[int, 1, 100]):
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=amount)
    await interaction.followup.send(f"{EMOJI['tick']} Deleted {len(deleted)} messages. {EMOJI['blaze']}", ephemeral=True)

@bot.tree.command(name="bothelp", description="Show Purgatory bot commands")
async def bothelp(interaction: discord.Interaction):
    embed = styled_embed(
        "PURGATORY BOT COMMANDS",
        f"{EMOJI['ticket']} `/ticketpanel` — Post ticket panel (Manage Server)\n"
        f"{EMOJI['giveaway']} `/giveaway prize winners duration` — Start giveaway\n"
        f"{EMOJI['announce']} `/announce announcement [tag]` — Send announcement\n"
        f"{EMOJI['blaze']} `/purge amount` — Delete messages (Manage Messages)\n"
        f"{EMOJI['star']} `/bothelp` — Show this help",
        0x5865F2
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        message = "You don't have permission to use this command."
    else:
        message = "Something went wrong. Check Railway logs for details."
        print(f"Command error: {error!r}")
    if interaction.response.is_done():
        await interaction.followup.send(f"{EMOJI['blaze']} {message}", ephemeral=True)
    else:
        await interaction.response.send_message(f"{EMOJI['blaze']} {message}", ephemeral=True)

if not TOKEN:
    raise RuntimeError("Missing DISCORD_TOKEN environment variable. Add it in Railway Variables.")

bot.run(TOKEN)
