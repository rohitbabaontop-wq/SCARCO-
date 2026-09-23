import os
import json
import random
import asyncio
from datetime import datetime, timedelta, timezone

import discord
from discord import app_commands
from discord.ext import commands, tasks
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", "0"))

DB_FILE = "database.json"

DEFAULT_DB = {
    "guilds": {}
}

def load_db():
    if not os.path.exists(DB_FILE):
        save_db(DEFAULT_DB)
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        save_db(DEFAULT_DB)
        return json.loads(json.dumps(DEFAULT_DB))

def save_db(data):
    tmp = DB_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, DB_FILE)

db = load_db()

def guild_cfg(guild_id):
    gid = str(guild_id)
    if gid not in db["guilds"]:
        db["guilds"][gid] = {
            "verify_role": 0,
            "verify_channel": 0,
            "vouch_channel": 0,
            "ticket_category": 0,
            "ticket_staff_role": 0,
            "giveaway_channel": 0,
            "theme": "💎",
            "color": 0x8B5CF6,
            "footer": "SCARCO • Premium System",
            "ticket_types": {
                "BUY": {"emoji": "🛒", "label": "BUY", "message": "Thanks for opening a purchase ticket."},
                "REPORT": {"emoji": "⚠️", "label": "REPORT", "message": "Please explain your report."},
                "SUPPORT": {"emoji": "🛠️", "label": "SUPPORT", "message": "Tell us what you need help with."},
                "PAYMENT": {"emoji": "💳", "label": "PAYMENT", "message": "Please provide your payment issue/details."}
            },
            "giveaways": {}
        }
        save_db(db)
    return db["guilds"][gid]

def embed(guild, title, description="", color=None):
    c = guild_cfg(guild.id)
    e = discord.Embed(title=f"{c['theme']} {title}", description=description,
                      color=color or c["color"], timestamp=datetime.now(timezone.utc))
    e.set_footer(text=c["footer"])
    return e

def is_admin(interaction):
    return interaction.user.guild_permissions.administrator

def admin_check(interaction):
    if not is_admin(interaction):
        return False
    return True

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = True

class ScarcoBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        if GUILD_ID:
            guild = discord.Object(id=GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()
        giveaway_loop.start()

bot = ScarcoBot()

class VerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="VERIFY", style=discord.ButtonStyle.success, emoji="✅", custom_id="scarco_verify")
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        cfg = guild_cfg(interaction.guild.id)
        role_id = cfg["verify_role"]
        if not role_id:
            return await interaction.response.send_message("❌ Verify role is not configured.", ephemeral=True)
        role = interaction.guild.get_role(role_id)
        if not role:
            return await interaction.response.send_message("❌ Verify role no longer exists.", ephemeral=True)
        try:
            await interaction.user.add_roles(role, reason="SCARCO verification")
            await interaction.response.send_message(f"✅ Verified! You received {role.mention}.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ I cannot give that role. Move my bot role above the Verify Role.", ephemeral=True)

class TicketView(discord.ui.View):
    def __init__(self, guild_id):
        super().__init__(timeout=None)
        cfg = guild_cfg(guild_id)
        for key, data in cfg["ticket_types"].items():
            self.add_item(TicketButton(key, data))

class TicketButton(discord.ui.Button):
    def __init__(self, key, data):
        super().__init__(
            label=data.get("label", key)[:80],
            emoji=data.get("emoji", "🎫"),
            style=discord.ButtonStyle.primary,
            custom_id=f"scarco_ticket_{key}"
        )
        self.key = key
        self.data = data

    async def callback(self, interaction: discord.Interaction):
        cfg = guild_cfg(interaction.guild.id)
        category = interaction.guild.get_channel(cfg["ticket_category"]) if cfg["ticket_category"] else None
        staff = interaction.guild.get_role(cfg["ticket_staff_role"]) if cfg["ticket_staff_role"] else None

        for ch in interaction.guild.text_channels:
            if ch.topic == f"ticket-owner:{interaction.user.id}":
                return await interaction.response.send_message(f"❌ You already have a ticket: {ch.mention}", ephemeral=True)

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
        }
        if staff:
            overwrites[staff] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

        name = f"{self.key.lower()}-{interaction.user.name}".replace(" ", "-")[:90]
        try:
            channel = await interaction.guild.create_text_channel(
                name=name, category=category, overwrites=overwrites,
                topic=f"ticket-owner:{interaction.user.id}"
            )
            await channel.send(
                content=f"{staff.mention if staff else ''} {interaction.user.mention}",
                embed=embed(interaction.guild, f"{self.key} TICKET", self.data.get("message", "Please explain your request.")),
                view=TicketControlView()
            )
            await interaction.response.send_message(f"🎫 Ticket created: {channel.mention}", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ I need Manage Channels and Manage Roles permissions.", ephemeral=True)

class TicketControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="CLAIM", style=discord.ButtonStyle.success, emoji="🙋", custom_id="scarco_claim")
    async def claim(self, interaction, button):
        await interaction.response.send_message(f"🙋 Claimed by {interaction.user.mention}.")

    @discord.ui.button(label="CLOSE", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="scarco_close")
    async def close(self, interaction, button):
        if not interaction.user.guild_permissions.manage_channels:
            return await interaction.response.send_message("❌ Staff only.", ephemeral=True)
        await interaction.response.send_message("🔒 Closing ticket...")
        await asyncio.sleep(2)
        await interaction.channel.delete(reason="SCARCO ticket closed")

class GiveawayJoin(discord.ui.View):
    def __init__(self, giveaway_id):
        super().__init__(timeout=None)
        self.giveaway_id = giveaway_id

    @discord.ui.button(label="JOIN GIVEAWAY", style=discord.ButtonStyle.success, emoji="🎉")
    async def join(self, interaction, button):
        cfg = guild_cfg(interaction.guild.id)
        g = cfg["giveaways"].get(str(self.giveaway_id))
        if not g or g["ended"]:
            return await interaction.response.send_message("❌ This giveaway has ended.", ephemeral=True)
        uid = interaction.user.id
        if uid not in g["entries"]:
            g["entries"].append(uid)
            save_db(db)
            await interaction.response.send_message("🎉 You joined the giveaway!", ephemeral=True)
        else:
            await interaction.response.send_message("ℹ️ You are already entered.", ephemeral=True)

async def finish_giveaway(guild, gid, cancelled=False):
    cfg = guild_cfg(guild.id)
    g = cfg["giveaways"].get(str(gid))
    if not g or g["ended"]:
        return
    g["ended"] = True
    channel = guild.get_channel(g["channel_id"])
    if cancelled:
        if channel:
            await channel.send(embed=embed(guild, "GIVEAWAY CANCELLED", f"Giveaway `{gid}` was cancelled."))
        save_db(db)
        return
    entries = list(g["entries"])
    winners_n = min(g["winners"], len(entries))
    winners = random.sample(entries, winners_n) if winners_n else []
    mentions = " ".join(f"<@{x}>" for x in winners) if winners else "No eligible winners."
    if channel:
        await channel.send(embed=embed(guild, "GIVEAWAY ENDED", f"Prize: **{g['prize']}**\nWinners: {mentions}"))
    g["winners_ids"] = winners
    save_db(db)

@tasks.loop(seconds=10)
async def giveaway_loop():
    now = datetime.now(timezone.utc).timestamp()
    for gid, cfg in db["guilds"].items():
        guild = bot.get_guild(int(gid))
        if not guild:
            continue
        for key, g in list(cfg["giveaways"].items()):
            if not g["ended"] and now >= g["end_at"]:
                await finish_giveaway(guild, int(key))

@bot.event
async def on_ready():
    print(f"SCARCO online as {bot.user} | Python {os.sys.version.split()[0]}")

@bot.tree.command(name="help", description="Show SCARCO commands")
async def help_cmd(interaction):
    text = (
        "**Premium Systems**\n"
        "`/verify-panel` • verification panel\n"
        "`/ticket-panel` • multi-button tickets\n"
        "`/vouch-panel` • vouch panel\n"
        "`/giveaway-create` • create giveaway\n"
        "`/giveaway-end` • end giveaway\n"
        "`/giveaway-reroll` • reroll winners\n"
        "`/giveaway-cancel` • cancel giveaway\n\n"
        "**Configuration**\n"
        "`/config` • configure channels, roles, colors and footer\n"
        "`/ticket-add-type` • add/edit ticket button\n"
        "`/ticket-remove-type` • remove ticket button\n"
        "`/ticket-list-types` • list ticket buttons"
    )
    await interaction.response.send_message(embed=embed(interaction.guild, "SCARCO HELP", text), ephemeral=True)

@bot.tree.command(name="ping", description="Check bot latency")
async def ping(interaction):
    await interaction.response.send_message(f"🏓 Pong! `{round(bot.latency*1000)}ms`")

config_group = app_commands.Group(name="config", description="SCARCO configuration")

@config_group.command(name="verify-role", description="Set verify role")
@app_commands.describe(role="Role members receive after verification")
async def verify_role(interaction, role: discord.Role):
    if not admin_check(interaction): return await interaction.response.send_message("❌ Administrator permission required.", ephemeral=True)
    guild_cfg(interaction.guild.id)["verify_role"] = role.id; save_db(db)
    await interaction.response.send_message(f"✅ Verify role set to {role.mention}")

@config_group.command(name="verify-channel", description="Set verify channel")
@app_commands.describe(channel="Verify panel channel")
async def verify_channel(interaction, channel: discord.TextChannel):
    if not admin_check(interaction): return await interaction.response.send_message("❌ Administrator permission required.", ephemeral=True)
    guild_cfg(interaction.guild.id)["verify_channel"] = channel.id; save_db(db)
    await interaction.response.send_message(f"✅ Verify channel set to {channel.mention}")

@config_group.command(name="vouch-channel", description="Set vouch channel")
async def vouch_channel(interaction, channel: discord.TextChannel):
    if not admin_check(interaction): return await interaction.response.send_message("❌ Administrator permission required.", ephemeral=True)
    guild_cfg(interaction.guild.id)["vouch_channel"] = channel.id; save_db(db)
    await interaction.response.send_message(f"✅ Vouch channel set to {channel.mention}")

@config_group.command(name="ticket-category", description="Set ticket category")
async def ticket_category(interaction, category: discord.CategoryChannel):
    if not admin_check(interaction): return await interaction.response.send_message("❌ Administrator permission required.", ephemeral=True)
    guild_cfg(interaction.guild.id)["ticket_category"] = category.id; save_db(db)
    await interaction.response.send_message(f"✅ Ticket category set to `{category.name}`")

@config_group.command(name="ticket-staff-role", description="Set ticket staff role")
async def ticket_staff_role(interaction, role: discord.Role):
    if not admin_check(interaction): return await interaction.response.send_message("❌ Administrator permission required.", ephemeral=True)
    guild_cfg(interaction.guild.id)["ticket_staff_role"] = role.id; save_db(db)
    await interaction.response.send_message(f"✅ Ticket staff role set to {role.mention}")

@config_group.command(name="giveaway-channel", description="Set giveaway channel")
async def giveaway_channel(interaction, channel: discord.TextChannel):
    if not admin_check(interaction): return await interaction.response.send_message("❌ Administrator permission required.", ephemeral=True)
    guild_cfg(interaction.guild.id)["giveaway_channel"] = channel.id; save_db(db)
    await interaction.response.send_message(f"✅ Giveaway channel set to {channel.mention}")

@config_group.command(name="theme-emoji", description="Set main theme emoji")
async def theme_emoji(interaction, emoji: str):
    if not admin_check(interaction): return await interaction.response.send_message("❌ Administrator permission required.", ephemeral=True)
    guild_cfg(interaction.guild.id)["theme"] = emoji[:50]; save_db(db)
    await interaction.response.send_message("✅ Theme emoji updated.")

@config_group.command(name="color", description="Set embed color as hex")
async def color(interaction, hex_color: str):
    if not admin_check(interaction): return await interaction.response.send_message("❌ Administrator permission required.", ephemeral=True)
    try:
        value = int(hex_color.replace("#", ""), 16)
        if not 0 <= value <= 0xFFFFFF: raise ValueError
    except ValueError:
        return await interaction.response.send_message("❌ Example: `#8B5CF6`", ephemeral=True)
    guild_cfg(interaction.guild.id)["color"] = value; save_db(db)
    await interaction.response.send_message("✅ Color updated.")

@config_group.command(name="footer", description="Set embed footer")
async def footer(interaction, text: str):
    if not admin_check(interaction): return await interaction.response.send_message("❌ Administrator permission required.", ephemeral=True)
    guild_cfg(interaction.guild.id)["footer"] = text[:200]; save_db(db)
    await interaction.response.send_message("✅ Footer updated.")

bot.tree.add_command(config_group)

@bot.tree.command(name="verify-panel", description="Send verification panel")
async def verify_panel(interaction):
    if not admin_check(interaction): return await interaction.response.send_message("❌ Administrator permission required.", ephemeral=True)
    await interaction.channel.send(embed=embed(interaction.guild, "VERIFICATION", "Click the button below to verify yourself."), view=VerifyView())
    await interaction.response.send_message("✅ Verification panel sent.", ephemeral=True)

@bot.tree.command(name="ticket-panel", description="Send ticket panel")
async def ticket_panel(interaction):
    if not admin_check(interaction): return await interaction.response.send_message("❌ Administrator permission required.", ephemeral=True)
    await interaction.channel.send(embed=embed(interaction.guild, "SUPPORT CENTER", "Select the type of ticket you need below."), view=TicketView(interaction.guild.id))
    await interaction.response.send_message("✅ Ticket panel sent.", ephemeral=True)

@bot.tree.command(name="vouch-panel", description="Send vouch panel")
async def vouch_panel(interaction):
    if not admin_check(interaction): return await interaction.response.send_message("❌ Administrator permission required.", ephemeral=True)
    await interaction.channel.send(embed=embed(interaction.guild, "VOUCH SYSTEM", "Use this channel for your vouches. Thank you for supporting SCARCO!"))
    await interaction.response.send_message("✅ Vouch panel sent.", ephemeral=True)

@bot.tree.command(name="ticket-add-type", description="Add or edit a ticket button")
@app_commands.describe(name="Button name", emoji="Emoji", message="Welcome message")
async def ticket_add_type(interaction, name: str, emoji: str, message: str):
    if not admin_check(interaction): return await interaction.response.send_message("❌ Administrator permission required.", ephemeral=True)
    key = name.upper().replace(" ", "_")[:20]
    guild_cfg(interaction.guild.id)["ticket_types"][key] = {"emoji": emoji[:50], "label": name[:80], "message": message[:1000]}
    save_db(db)
    await interaction.response.send_message(f"✅ Ticket type `{key}` saved.")

@bot.tree.command(name="ticket-remove-type", description="Remove a ticket button")
async def ticket_remove_type(interaction, name: str):
    if not admin_check(interaction): return await interaction.response.send_message("❌ Administrator permission required.", ephemeral=True)
    key = name.upper()
    cfg = guild_cfg(interaction.guild.id)
    if key not in cfg["ticket_types"]:
        return await interaction.response.send_message("❌ Ticket type not found.", ephemeral=True)
    del cfg["ticket_types"][key]; save_db(db)
    await interaction.response.send_message(f"✅ Removed `{key}`.")

@bot.tree.command(name="ticket-list-types", description="List ticket buttons")
async def ticket_list_types(interaction):
    cfg = guild_cfg(interaction.guild.id)
    lines = [f"{d.get('emoji','🎫')} **{k}** — {d.get('label',k)}" for k,d in cfg["ticket_types"].items()]
    await interaction.response.send_message(embed=embed(interaction.guild, "TICKET TYPES", "\n".join(lines) or "None"), ephemeral=True)

def parse_duration(s):
    s = s.strip().lower()
    units = {"s":1, "m":60, "h":3600, "d":86400}
    if not s or s[-1] not in units:
        raise ValueError
    n = int(s[:-1])
    if n <= 0 or n > 31 * 86400 / units[s[-1]]:
        raise ValueError
    return n * units[s[-1]]

@bot.tree.command(name="giveaway-create", description="Create a giveaway")
@app_commands.describe(prize="Prize", duration="Example: 30m, 2h, 1d", winners="Number of winners", image="Optional image URL")
async def giveaway_create(interaction, prize: str, duration: str, winners: app_commands.Range[int,1,50], image: str = ""):
    if not admin_check(interaction): return await interaction.response.send_message("❌ Administrator permission required.", ephemeral=True)
    try: seconds = parse_duration(duration)
    except: return await interaction.response.send_message("❌ Invalid duration. Use `30s`, `10m`, `2h`, or `1d`.", ephemeral=True)
    cfg = guild_cfg(interaction.guild.id)
    gid = str(random.randint(100000, 999999))
    end_at = datetime.now(timezone.utc).timestamp() + seconds
    g = {"prize": prize, "winners": winners, "channel_id": interaction.channel.id, "end_at": end_at, "entries": [], "ended": False, "winners_ids": [], "image": image}
    cfg["giveaways"][gid] = g; save_db(db)
    e = embed(interaction.guild, "🎉 GIVEAWAY", f"**Prize:** {prize}\n**Winners:** {winners}\n**Ends:** <t:{int(end_at)}:R>\n**ID:** `{gid}`")
    if image.startswith("http"): e.set_image(url=image)
    await interaction.channel.send(embed=e, view=GiveawayJoin(int(gid)))
    await interaction.response.send_message(f"✅ Giveaway `{gid}` created.", ephemeral=True)

@bot.tree.command(name="giveaway-end", description="End a giveaway")
async def giveaway_end(interaction, giveaway_id: str):
    if not admin_check(interaction): return await interaction.response.send_message("❌ Administrator permission required.", ephemeral=True)
    try: gid = int(giveaway_id)
    except: return await interaction.response.send_message("❌ Invalid ID.", ephemeral=True)
    if str(gid) not in guild_cfg(interaction.guild.id)["giveaways"]:
        return await interaction.response.send_message("❌ Giveaway not found.", ephemeral=True)
    await finish_giveaway(interaction.guild, gid)
    await interaction.response.send_message("✅ Giveaway ended.", ephemeral=True)

@bot.tree.command(name="giveaway-cancel", description="Cancel a giveaway")
async def giveaway_cancel(interaction, giveaway_id: str):
    if not admin_check(interaction): return await interaction.response.send_message("❌ Administrator permission required.", ephemeral=True)
    try: gid = int(giveaway_id)
    except: return await interaction.response.send_message("❌ Invalid ID.", ephemeral=True)
    if str(gid) not in guild_cfg(interaction.guild.id)["giveaways"]:
        return await interaction.response.send_message("❌ Giveaway not found.", ephemeral=True)
    await finish_giveaway(interaction.guild, gid, True)
    await interaction.response.send_message("✅ Giveaway cancelled.", ephemeral=True)

@bot.tree.command(name="giveaway-reroll", description="Reroll a giveaway")
async def giveaway_reroll(interaction, giveaway_id: str):
    if not admin_check(interaction): return await interaction.response.send_message("❌ Administrator permission required.", ephemeral=True)
    cfg = guild_cfg(interaction.guild.id)
    g = cfg["giveaways"].get(str(giveaway_id))
    if not g or not g["ended"]:
        return await interaction.response.send_message("❌ Giveaway must be ended first.", ephemeral=True)
    pool = [x for x in g["entries"] if x not in g["winners_ids"]]
    if not pool:
        return await interaction.response.send_message("❌ No alternate entries.", ephemeral=True)
    winner = random.choice(pool)
    g["winners_ids"] = [winner]
    save_db(db)
    await interaction.channel.send(embed=embed(interaction.guild, "GIVEAWAY REROLL", f"New winner: <@{winner}>"))
    await interaction.response.send_message("✅ Rerolled.", ephemeral=True)

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN is missing. Add it in Railway Variables.")

bot.run(TOKEN)
