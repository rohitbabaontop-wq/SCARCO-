
import os, json, random, asyncio, re
from datetime import datetime, timezone
import discord
from discord import app_commands
from discord.ext import commands, tasks
from dotenv import load_dotenv

load_dotenv()
TOKEN=os.getenv("DISCORD_TOKEN")
GUILD_ID=int(os.getenv("GUILD_ID","0"))
DB_FILE="database.json"

def save_db(d):
    with open(DB_FILE+".tmp","w",encoding="utf-8") as f: json.dump(d,f,indent=2,ensure_ascii=False)
    os.replace(DB_FILE+".tmp",DB_FILE)
def load_db():
    if not os.path.exists(DB_FILE): save_db({"guilds":{}})
    try:
        with open(DB_FILE,"r",encoding="utf-8") as f:return json.load(f)
    except: return {"guilds":{}}
db=load_db()

def cfg(gid):
    gid=str(gid)
    if gid not in db["guilds"]:
        db["guilds"][gid]={
            "theme":"💎","color":0x8B5CF6,"footer":"SCARCO • Premium System",
            "verify_role":0,"verify_channel":0,"vouch_channel":0,
            "ticket_category":0,"ticket_staff_role":0,"giveaway_channel":0,
            "ticket_types":{
                "BUY":{"label":"BUY","emoji":"🛒","message":"Tell us what you want to buy."},
                "REPORT":{"label":"REPORT","emoji":"⚠️","message":"Explain your report clearly."},
                "SUPPORT":{"label":"SUPPORT","emoji":"🛠️","message":"Tell us what you need help with."},
                "PAYMENT":{"label":"PAYMENT","emoji":"💳","message":"Explain your payment issue."}
            },
            "giveaways":{}
        };save_db(db)
    return db["guilds"][gid]

def E(g): return cfg(g.id)["theme"]
def emb(g,title,desc="",color=None):
    c=cfg(g.id); e=discord.Embed(title=f"{c['theme']} {title}",description=desc,
        color=color or c["color"],timestamp=datetime.now(timezone.utc))
    e.set_footer(text=c["footer"]); return e
def admin(i): return i.user.guild_permissions.administrator

intents=discord.Intents.default()
intents.guilds=True; intents.members=True; intents.message_content=True

class Bot(commands.Bot):
    async def setup_hook(self):
        self.add_view(VerifyView()); self.add_view(TicketControl())
        if GUILD_ID:
            g=discord.Object(id=GUILD_ID); self.tree.copy_global_to(guild=g); await self.tree.sync(guild=g)
        else: await self.tree.sync()
        giveaway_loop.start()
    def __init__(self): super().__init__(command_prefix="!",intents=intents)

bot=Bot()

class VerifyView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="VERIFY",style=discord.ButtonStyle.success,emoji="✅",custom_id="sc_verify")
    async def verify(self,i,b):
        r=discord.utils.get(i.guild.roles,id=cfg(i.guild.id)["verify_role"])
        if not r:return await i.response.send_message("❌ Verify role is not configured.",ephemeral=True)
        try:
            await i.user.add_roles(r,reason="SCARCO verify")
            await i.response.send_message(f"✅ Verified — {r.mention}",ephemeral=True)
        except discord.Forbidden:
            await i.response.send_message("❌ Move my bot role above the Verify Role.",ephemeral=True)

class TicketControl(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="CLAIM",style=discord.ButtonStyle.success,emoji="🙋",custom_id="sc_claim")
    async def claim(self,i,b): await i.response.send_message(f"🙋 Ticket claimed by {i.user.mention}.")
    @discord.ui.button(label="CLOSE",style=discord.ButtonStyle.danger,emoji="🔒",custom_id="sc_close")
    async def close(self,i,b):
        if not i.user.guild_permissions.manage_channels:return await i.response.send_message("❌ Staff only.",ephemeral=True)
        await i.response.send_message("🔒 Closing...")
        await asyncio.sleep(1); await i.channel.delete(reason="SCARCO ticket closed")

class TicketButton(discord.ui.Button):
    def __init__(self,key,d):
        super().__init__(label=d.get("label",key)[:80],emoji=d.get("emoji","🎫"),style=discord.ButtonStyle.primary,custom_id=f"sc_ticket_{key}")
        self.key=key;self.d=d
    async def callback(self,i):
        c=cfg(i.guild.id); cat=i.guild.get_channel(c["ticket_category"]) if c["ticket_category"] else None
        staff=i.guild.get_role(c["ticket_staff_role"]) if c["ticket_staff_role"] else None
        for ch in i.guild.text_channels:
            if ch.topic==f"sc-owner:{i.user.id}": return await i.response.send_message(f"❌ You already have {ch.mention}",ephemeral=True)
        ow={i.guild.default_role:discord.PermissionOverwrite(view_channel=False),
            i.user:discord.PermissionOverwrite(view_channel=True,send_messages=True,read_message_history=True)}
        if staff:ow[staff]=discord.PermissionOverwrite(view_channel=True,send_messages=True,read_message_history=True)
        try:
            ch=await i.guild.create_text_channel(f"{self.key.lower()}-{i.user.name}"[:90],category=cat,overwrites=ow,topic=f"sc-owner:{i.user.id}")
            await ch.send(content=f"{staff.mention if staff else ''} {i.user.mention}",embed=emb(i.guild,f"{self.key} TICKET",self.d.get("message","Please explain your request.")),view=TicketControl())
            await i.response.send_message(f"🎫 Created {ch.mention}",ephemeral=True)
        except discord.Forbidden: await i.response.send_message("❌ I need Manage Channels.",ephemeral=True)

class GiveawayView(discord.ui.View):
    def __init__(self,gid): super().__init__(timeout=None);self.gid=str(gid)
    @discord.ui.button(label="JOIN",style=discord.ButtonStyle.success,emoji="🎉")
    async def join(self,i,b):
        g=cfg(i.guild.id)["giveaways"].get(self.gid)
        if not g or g["ended"]:return await i.response.send_message("❌ Giveaway ended.",ephemeral=True)
        if i.user.id not in g["entries"]:g["entries"].append(i.user.id);save_db(db);msg="🎉 You joined!"
        else:msg="ℹ️ Already joined."
        await i.response.send_message(msg,ephemeral=True)

def parse_duration(s):
    m=re.fullmatch(r"\s*(\d+)\s*([smhd])\s*",s.lower())
    if not m:raise ValueError
    n=int(m.group(1)); mult={"s":1,"m":60,"h":3600,"d":86400}[m.group(2)]
    if n<1 or n*mult>31*86400:raise ValueError
    return n*mult

async def finish(guild,gid,cancel=False):
    c=cfg(guild.id); g=c["giveaways"].get(str(gid))
    if not g or g["ended"]:return
    g["ended"]=True; ch=guild.get_channel(g["channel"])
    if cancel:
        if ch:await ch.send(embed=emb(guild,"GIVEAWAY CANCELLED",f"ID: `{gid}`"))
    else:
        pool=g["entries"]; winners=random.sample(pool,min(g["winners"],len(pool))) if pool else []
        g["winners"]=winners
        if ch:await ch.send(embed=emb(guild,"GIVEAWAY ENDED",f"🎁 **{g['prize']}**\n🏆 Winners: "+(" ".join(f"<@{x}>" for x in winners) if winners else "No eligible winners.")))
    save_db(db)

@tasks.loop(seconds=10)
async def giveaway_loop():
    now=datetime.now(timezone.utc).timestamp()
    for gid,c in db["guilds"].items():
        guild=bot.get_guild(int(gid))
        if guild:
            for x,g in list(c["giveaways"].items()):
                if not g["ended"] and now>=g["end"]: await finish(guild,int(x))

@bot.event
async def on_ready(): print(f"SCARCO ONLINE • {bot.user}")

@bot.tree.command(name="help",description="Show all SCARCO systems")
async def helpcmd(i):
    t="**ONE-COMMAND SYSTEMS**\n`/setup` — configure everything\n`/giveaway` — create giveaway with all options\n`/ticket-panel` — send premium ticket panel\n`/verify-panel` — send verify panel\n`/vouch-panel` — send vouch panel\n\n**Ticket:** `/ticket-add-type`, `/ticket-remove-type`\n**Giveaway:** `/giveaway-end`, `/giveaway-reroll`, `/giveaway-cancel`"
    await i.response.send_message(embed=emb(i.guild,"SCARCO COMMAND CENTER",t),ephemeral=True)

@bot.tree.command(name="setup",description="Configure SCARCO in one command")
@app_commands.describe(
    verify_role="Verify role",verify_channel="Verify channel",vouch_channel="Vouch channel",
    ticket_category="Ticket category",ticket_staff_role="Ticket staff role",giveaway_channel="Default giveaway channel",
    theme_emoji="Custom Nitro/server emoji or normal emoji",color="Hex color, e.g. #8B5CF6",footer="Embed footer")
async def setup(i,verify_role:discord.Role=None,verify_channel:discord.TextChannel=None,vouch_channel:discord.TextChannel=None,
                ticket_category:discord.CategoryChannel=None,ticket_staff_role:discord.Role=None,giveaway_channel:discord.TextChannel=None,
                theme_emoji:str=None,color:str=None,footer:str=None):
    if not admin(i):return await i.response.send_message("❌ Administrator permission required.",ephemeral=True)
    c=cfg(i.guild.id)
    if verify_role:c["verify_role"]=verify_role.id
    if verify_channel:c["verify_channel"]=verify_channel.id
    if vouch_channel:c["vouch_channel"]=vouch_channel.id
    if ticket_category:c["ticket_category"]=ticket_category.id
    if ticket_staff_role:c["ticket_staff_role"]=ticket_staff_role.id
    if giveaway_channel:c["giveaway_channel"]=giveaway_channel.id
    if theme_emoji:c["theme"]=theme_emoji[:50]
    if color:
        try:c["color"]=int(color.replace("#",""),16)
        except:pass
    if footer:c["footer"]=footer[:200]
    save_db(db)
    await i.response.send_message(embed=emb(i.guild,"SETUP SAVED","All supplied settings have been updated.\n\n💡 Custom Nitro emoji: paste it directly in `theme_emoji` or ticket emoji fields."),ephemeral=True)

@bot.tree.command(name="giveaway",description="Create a complete giveaway in one command")
@app_commands.describe(prize="Prize",duration="30s / 10m / 2h / 1d",winners="Winner count",channel="Giveaway channel",image="Image URL",join_emoji="Custom Nitro/server emoji for JOIN button",join_label="Button text")
async def giveaway(i,prize:str,duration:str,winners:app_commands.Range[int,1,50],channel:discord.TextChannel=None,image:str="",join_emoji:str="🎉",join_label:str="JOIN GIVEAWAY"):
    if not admin(i):return await i.response.send_message("❌ Administrator permission required.",ephemeral=True)
    try:seconds=parse_duration(duration)
    except:return await i.response.send_message("❌ Duration: `30s`, `10m`, `2h`, `1d` (max 31d).",ephemeral=True)
    channel=channel or i.channel; gid=str(random.randint(100000,999999)); end=datetime.now(timezone.utc).timestamp()+seconds
    c=cfg(i.guild.id);c["giveaways"][gid]={"prize":prize,"winners":winners,"channel":channel.id,"end":end,"entries":[],"ended":False,"winners":[]};save_db(db)
    e=emb(i.guild,"GIVEAWAY",f"🎁 **Prize:** {prize}\n🏆 **Winners:** {winners}\n⏰ **Ends:** <t:{int(end)}:R>\n🆔 **ID:** `{gid}`")
    if image.startswith("http"):e.set_image(url=image)
    v=GiveawayView(gid)
    try:v.children[0].emoji=join_emoji[:50];v.children[0].label=join_label[:80]
    except:pass
    await channel.send(embed=e,view=v);await i.response.send_message(f"✅ Giveaway `{gid}` created in {channel.mention}.",ephemeral=True)

@bot.tree.command(name="giveaway-end",description="End a giveaway")
async def giveaway_end(i,giveaway_id:str):
    if not admin(i):return await i.response.send_message("❌ Administrator permission required.",ephemeral=True)
    if giveaway_id not in cfg(i.guild.id)["giveaways"]:return await i.response.send_message("❌ Not found.",ephemeral=True)
    await finish(i.guild,int(giveaway_id));await i.response.send_message("✅ Ended.",ephemeral=True)

@bot.tree.command(name="giveaway-cancel",description="Cancel a giveaway")
async def giveaway_cancel(i,giveaway_id:str):
    if not admin(i):return await i.response.send_message("❌ Administrator permission required.",ephemeral=True)
    if giveaway_id not in cfg(i.guild.id)["giveaways"]:return await i.response.send_message("❌ Not found.",ephemeral=True)
    await finish(i.guild,int(giveaway_id),True);await i.response.send_message("✅ Cancelled.",ephemeral=True)

@bot.tree.command(name="giveaway-reroll",description="Reroll a finished giveaway")
async def giveaway_reroll(i,giveaway_id:str):
    if not admin(i):return await i.response.send_message("❌ Administrator permission required.",ephemeral=True)
    g=cfg(i.guild.id)["giveaways"].get(giveaway_id)
    if not g or not g["ended"]:return await i.response.send_message("❌ Giveaway must be finished first.",ephemeral=True)
    pool=[x for x in g["entries"] if x not in g["winners"]]
    if not pool:return await i.response.send_message("❌ No alternate entries.",ephemeral=True)
    w=random.choice(pool);g["winners"]=[w];save_db(db)
    await i.channel.send(embed=emb(i.guild,"GIVEAWAY REROLL",f"🏆 New winner: <@{w}>"));await i.response.send_message("✅ Rerolled.",ephemeral=True)

@bot.tree.command(name="ticket-panel",description="Send the premium ticket panel")
async def ticket_panel(i):
    if not admin(i):return await i.response.send_message("❌ Administrator permission required.",ephemeral=True)
    v=discord.ui.View(timeout=None)
    for k,d in cfg(i.guild.id)["ticket_types"].items():v.add_item(TicketButton(k,d))
    text="Select a category below.\n\n"+ "\n".join(f"{d['emoji']} **{d['label']}** — {d['message']}" for d in cfg(i.guild.id)["ticket_types"].values())
    await i.channel.send(embed=emb(i.guild,"PREMIUM SUPPORT",text),view=v)
    await i.response.send_message("✅ Panel sent.",ephemeral=True)

@bot.tree.command(name="verify-panel",description="Send verification panel")
async def verify_panel(i):
    if not admin(i):return await i.response.send_message("❌ Administrator permission required.",ephemeral=True)
    await i.channel.send(embed=emb(i.guild,"VERIFICATION","Click below to verify and unlock the server."),view=VerifyView())
    await i.response.send_message("✅ Sent.",ephemeral=True)

@bot.tree.command(name="vouch-panel",description="Send vouch panel")
async def vouch_panel(i):
    if not admin(i):return await i.response.send_message("❌ Administrator permission required.",ephemeral=True)
    c=cfg(i.guild.id);ch=i.guild.get_channel(c["vouch_channel"]) or i.channel
    await ch.send(embed=emb(i.guild,"VOUCH CENTER","Had a good experience? Leave your vouch here ⭐\nThank you for supporting SCARCO."))
    await i.response.send_message("✅ Sent.",ephemeral=True)

@bot.tree.command(name="ticket-add-type",description="Add/edit a ticket button with custom emoji")
async def ticket_add_type(i,name:str,emoji:str,message:str):
    if not admin(i):return await i.response.send_message("❌ Administrator permission required.",ephemeral=True)
    key=name.upper().replace(" ","_")[:20];cfg(i.guild.id)["ticket_types"][key]={"label":name[:80],"emoji":emoji[:50],"message":message[:1000]};save_db(db)
    await i.response.send_message(f"✅ `{key}` saved. Use `/ticket-panel` to publish the updated buttons.",ephemeral=True)

@bot.tree.command(name="ticket-remove-type",description="Remove a ticket button")
async def ticket_remove_type(i,name:str):
    if not admin(i):return await i.response.send_message("❌ Administrator permission required.",ephemeral=True)
    key=name.upper();c=cfg(i.guild.id)
    if key not in c["ticket_types"]:return await i.response.send_message("❌ Not found.",ephemeral=True)
    del c["ticket_types"][key];save_db(db);await i.response.send_message(f"✅ `{key}` removed.",ephemeral=True)

if not TOKEN: raise RuntimeError("DISCORD_TOKEN is missing. Add it in Railway Variables.")
bot.run(TOKEN)
