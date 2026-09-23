require("dotenv").config();

const fs = require("fs");
const path = require("path");
const {
  Client,
  GatewayIntentBits,
  Partials,
  PermissionsBitField,
  ChannelType,
  EmbedBuilder,
  ActionRowBuilder,
  ButtonBuilder,
  ButtonStyle,
  SlashCommandBuilder,
  REST,
  Routes,
  Events
} = require("discord.js");

const DB = path.join(__dirname, "database.json");

function loadDB() {
  try { return JSON.parse(fs.readFileSync(DB, "utf8")); }
  catch { return { config: {}, ticketTypes: [], giveaways: {} }; }
}
let db = loadDB();

function saveDB() {
  fs.writeFileSync(DB, JSON.stringify(db, null, 2));
}

const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.MessageContent
  ],
  partials: [Partials.Channel, Partials.Message]
});

const E = () => db.config.themeEmoji || "💎";
const color = () => db.config.accentColor || "#5865F2";
const footer = () => db.config.footer || "Premium Bot";

function embed(title, description) {
  return new EmbedBuilder()
    .setColor(color())
    .setTitle(`${E()} ${title}`)
    .setDescription(description)
    .setFooter({ text: footer() })
    .setTimestamp();
}

function isAdmin(i) {
  return i.memberPermissions?.has(PermissionsBitField.Flags.Administrator);
}

function replaceVars(text, user) {
  return String(text || "").replaceAll("{user}", `<@${user.id}>`).replaceAll("{username}", user.username);
}

function parseDuration(s) {
  const m = String(s).trim().match(/^(\d+)\s*(s|m|h|d|w)$/i);
  if (!m) return null;
  const n = Number(m[1]);
  const mult = {s:1000,m:60000,h:3600000,d:86400000,w:604800000}[m[2].toLowerCase()];
  const ms = n * mult;
  if (ms < 5000 || ms > 31 * 86400000) return null;
  return ms;
}

function ticketTypeButtons() {
  const rows = [];
  let row = new ActionRowBuilder();
  for (const t of db.ticketTypes.slice(0, 5)) {
    const b = new ButtonBuilder()
      .setCustomId(`ticket_create:${t.id}`)
      .setLabel(t.label.slice(0, 80))
      .setStyle(ButtonStyle.Primary);
    if (t.emoji) b.setEmoji(t.emoji);
    if (row.components.length >= 5) {
      rows.push(row); row = new ActionRowBuilder();
    }
    row.addComponents(b);
  }
  if (row.components.length) rows.push(row);
  return rows.slice(0, 5);
}

function ticketControlRow() {
  return new ActionRowBuilder().addComponents(
    new ButtonBuilder().setCustomId("ticket_claim").setLabel("CLAIM").setStyle(ButtonStyle.Success).setEmoji("👑"),
    new ButtonBuilder().setCustomId("ticket_transcript").setLabel("TRANSCRIPT").setStyle(ButtonStyle.Secondary).setEmoji("📜"),
    new ButtonBuilder().setCustomId("ticket_close").setLabel("CLOSE").setStyle(ButtonStyle.Danger).setEmoji("🔒")
  );
}

async function registerCommands() {
  const commands = [
    new SlashCommandBuilder().setName("help").setDescription("Show the complete bot guide"),
    new SlashCommandBuilder().setName("ping").setDescription("Show bot latency"),

    new SlashCommandBuilder().setName("verify-panel").setDescription("Send the verify panel"),
    new SlashCommandBuilder().setName("ticket-panel").setDescription("Send the multi-button ticket panel"),
    new SlashCommandBuilder().setName("vouch-panel").setDescription("Send the vouch panel"),

    new SlashCommandBuilder().setName("config").setDescription("Configure the bot")
      .addSubcommand(s => s.setName("verify-role").setDescription("Set verify role").addRoleOption(o => o.setName("role").setDescription("Role").setRequired(true)))
      .addSubcommand(s => s.setName("verify-channel").setDescription("Set verify channel").addChannelOption(o => o.setName("channel").setDescription("Channel").addChannelTypes(ChannelType.GuildText).setRequired(true)))
      .addSubcommand(s => s.setName("vouch-channel").setDescription("Set vouch channel").addChannelOption(o => o.setName("channel").setDescription("Channel").addChannelTypes(ChannelType.GuildText).setRequired(true)))
      .addSubcommand(s => s.setName("ticket-category").setDescription("Set default ticket category").addChannelOption(o => o.setName("category").setDescription("Category").addChannelTypes(ChannelType.GuildCategory).setRequired(true)))
      .addSubcommand(s => s.setName("ticket-staff-role").setDescription("Set default ticket staff role").addRoleOption(o => o.setName("role").setDescription("Role").setRequired(true)))
      .addSubcommand(s => s.setName("giveaway-channel").setDescription("Set default giveaway channel").addChannelOption(o => o.setName("channel").setDescription("Channel").addChannelTypes(ChannelType.GuildText).setRequired(true)))
      .addSubcommand(s => s.setName("theme-emoji").setDescription("Set the main theme emoji").addStringOption(o => o.setName("emoji").setDescription("Emoji or custom emoji").setRequired(true)))
      .addSubcommand(s => s.setName("color").setDescription("Set embed color").addStringOption(o => o.setName("hex").setDescription("#5865F2").setRequired(true)))
      .addSubcommand(s => s.setName("footer").setDescription("Set embed footer").addStringOption(o => o.setName("text").setDescription("Footer").setRequired(true))),

    new SlashCommandBuilder().setName("ticket-add-type").setDescription("Add or update a ticket button")
      .addStringOption(o => o.setName("id").setDescription("Unique id e.g. buy").setRequired(true))
      .addStringOption(o => o.setName("label").setDescription("Button label").setRequired(true))
      .addStringOption(o => o.setName("emoji").setDescription("Emoji").setRequired(true))
      .addStringOption(o => o.setName("message").setDescription("Ticket welcome message").setRequired(true))
      .addChannelOption(o => o.setName("category").setDescription("Optional category").addChannelTypes(ChannelType.GuildCategory))
      .addRoleOption(o => o.setName("staff-role").setDescription("Optional staff role")),

    new SlashCommandBuilder().setName("ticket-remove-type").setDescription("Remove a ticket button")
      .addStringOption(o => o.setName("id").setDescription("Ticket type id").setRequired(true)),
    new SlashCommandBuilder().setName("ticket-list-types").setDescription("List ticket button types"),

    new SlashCommandBuilder().setName("giveaway-create").setDescription("Create a giveaway")
      .addStringOption(o => o.setName("duration").setDescription("30s, 10m, 2h, 1d").setRequired(true))
      .addIntegerOption(o => o.setName("winners").setDescription("Number of winners").setMinValue(1).setMaxValue(20).setRequired(true))
      .addStringOption(o => o.setName("prize").setDescription("Prize").setRequired(true))
      .addStringOption(o => o.setName("image").setDescription("Optional image URL"))
      .addChannelOption(o => o.setName("channel").setDescription("Optional channel").addChannelTypes(ChannelType.GuildText)),
    new SlashCommandBuilder().setName("giveaway-reroll").setDescription("Reroll a finished giveaway")
      .addStringOption(o => o.setName("message_id").setDescription("Giveaway message ID").setRequired(true))
      .addChannelOption(o => o.setName("channel").setDescription("Channel").addChannelTypes(ChannelType.GuildText)),
    new SlashCommandBuilder().setName("giveaway-end").setDescription("End a giveaway now")
      .addStringOption(o => o.setName("message_id").setDescription("Giveaway message ID").setRequired(true))
      .addChannelOption(o => o.setName("channel").setDescription("Channel").addChannelTypes(ChannelType.GuildText)),
    new SlashCommandBuilder().setName("giveaway-cancel").setDescription("Cancel a giveaway")
      .addStringOption(o => o.setName("message_id").setDescription("Giveaway message ID").setRequired(true))
      .addChannelOption(o => o.setName("channel").setDescription("Channel").addChannelTypes(ChannelType.GuildText))
  ].map(x => x.toJSON());

  const rest = new REST({ version: "10" }).setToken(process.env.DISCORD_TOKEN);
  await rest.put(Routes.applicationGuildCommands(process.env.CLIENT_ID, process.env.GUILD_ID), { body: commands });
}

async function finishGiveaway(messageId, cancelled = false) {
  const g = db.giveaways[messageId];
  if (!g || g.ended) return;
  const channel = await client.channels.fetch(g.channelId).catch(() => null);
  const msg = channel ? await channel.messages.fetch(messageId).catch(() => null) : null;
  g.ended = true;
  g.cancelled = cancelled;
  saveDB();

  if (!msg) return;
  const users = [...new Set(g.entries || [])];
  const winners = [];
  while (!cancelled && winners.length < g.winners && users.length) {
    winners.push(users.splice(Math.floor(Math.random() * users.length), 1)[0]);
  }

  const result = cancelled
    ? `${E()} **Giveaway cancelled.**`
    : winners.length
      ? `${E()} **Winner${winners.length > 1 ? "s" : ""}:** ${winners.map(x => `<@${x}>`).join(", ")}\n\n${E()} Prize: **${g.prize}**`
      : `${E()} **No eligible participants.**`;

  await msg.edit({
    embeds: [embed(cancelled ? "GIVEAWAY CANCELLED" : "GIVEAWAY ENDED", result).setImage(g.image || null)],
    components: []
  }).catch(() => {});

  if (winners.length && channel) {
    await channel.send(`${E()} Congratulations ${winners.map(x => `<@${x}>`).join(", ")}! You won **${g.prize}**.`).catch(() => {});
  }
}

client.once(Events.ClientReady, async c => {
  console.log(`Logged in as ${c.user.tag}`);
  await registerCommands();
  for (const [id, g] of Object.entries(db.giveaways || {})) {
    if (!g.ended && g.endAt <= Date.now()) finishGiveaway(id);
  }
  setInterval(() => {
    for (const [id, g] of Object.entries(db.giveaways || {})) {
      if (!g.ended && g.endAt <= Date.now()) finishGiveaway(id);
    }
  }, 5000);
});

client.on(Events.InteractionCreate, async i => {
  try {
    if (i.isChatInputCommand()) {
      if (i.commandName !== "help" && !i.guild) return i.reply({ content: `${E()} This bot works inside a server.`, ephemeral: true });

      if (i.commandName === "ping") return i.reply({ content: `${E()} Pong! \`${client.ws.ping}ms\``, ephemeral: true });

      if (i.commandName === "help") {
        return i.reply({ embeds: [embed("BOT HELP", [
          `${E()} **GENERAL**`,
          "`/help` — complete guide",
          "`/ping` — latency",
          "",
          `${E()} **PANELS**`,
          "`/verify-panel` — verify button",
          "`/ticket-panel` — ticket buttons",
          "`/vouch-panel` — vouch panel",
          "",
          `${E()} **SETUP**`,
          "`/config ...` — configure roles/channels/theme",
          "`/ticket-add-type` — add custom ticket button",
          "`/ticket-remove-type` — remove ticket button",
          "`/ticket-list-types` — list ticket buttons",
          "",
          `${E()} **GIVEAWAY**`,
          "`/giveaway-create` — create",
          "`/giveaway-end` — end",
          "`/giveaway-reroll` — reroll",
          "`/giveaway-cancel` — cancel",
          "",
          `${E()} **TICKET BUTTONS**`,
          "CLAIM • TRANSCRIPT • CLOSE",
          "",
          `${E()} Replace the default emojis with your server/Nitro custom emoji strings in the configuration."
        ].join("\n"))], ephemeral: true });
      }

      if (!isAdmin(i)) return i.reply({ content: `${E()} Administrator permission required.`, ephemeral: true });

      if (i.commandName === "config") {
        const s = i.options.getSubcommand();
        const map = {
          "verify-role": ["verifyRoleId", i.options.getRole("role").id],
          "verify-channel": ["verifyChannelId", i.options.getChannel("channel").id],
          "vouch-channel": ["vouchChannelId", i.options.getChannel("channel").id],
          "ticket-category": ["ticketCategoryId", i.options.getChannel("category").id],
          "ticket-staff-role": ["ticketStaffRoleId", i.options.getRole("role").id],
          "giveaway-channel": ["giveawayChannelId", i.options.getChannel("channel").id],
          "theme-emoji": ["themeEmoji", i.options.getString("emoji")],
          "color": ["accentColor", i.options.getString("hex")],
          "footer": ["footer", i.options.getString("text")]
        };
        const [k, v] = map[s];
        if (s === "color" && !/^#[0-9a-f]{6}$/i.test(v)) return i.reply({ content: `${E()} Use a valid hex color like \`#5865F2\`.`, ephemeral: true });
        db.config[k] = v; saveDB();
        return i.reply({ content: `${E()} **${k}** updated successfully.`, ephemeral: true });
      }

      if (i.commandName === "ticket-add-type") {
        const id = i.options.getString("id").toLowerCase().replace(/[^a-z0-9_-]/g, "").slice(0, 30);
        const item = {
          id,
          label: i.options.getString("label").slice(0, 80),
          emoji: i.options.getString("emoji"),
          message: i.options.getString("message"),
          categoryId: i.options.getChannel("category")?.id || db.config.ticketCategoryId || "",
          staffRoleId: i.options.getRole("staff-role")?.id || db.config.ticketStaffRoleId || ""
        };
        db.ticketTypes = db.ticketTypes.filter(x => x.id !== id);
        db.ticketTypes.push(item); saveDB();
        return i.reply({ content: `${E()} Ticket type **${id}** saved.`, ephemeral: true });
      }

      if (i.commandName === "ticket-remove-type") {
        const id = i.options.getString("id");
        db.ticketTypes = db.ticketTypes.filter(x => x.id !== id); saveDB();
        return i.reply({ content: `${E()} Ticket type **${id}** removed.`, ephemeral: true });
      }

      if (i.commandName === "ticket-list-types") {
        return i.reply({ embeds: [embed("TICKET TYPES", db.ticketTypes.map(t => `${t.emoji} **${t.label}** — \`${t.id}\``).join("\n") || "No ticket types configured.")], ephemeral: true });
      }

      if (i.commandName === "verify-panel") {
        const row = new ActionRowBuilder().addComponents(new ButtonBuilder().setCustomId("verify_user").setLabel("VERIFY").setStyle(ButtonStyle.Success).setEmoji(E()));
        return i.reply({ embeds: [embed("VERIFY", "Press the button below to verify yourself and receive the configured verification role.")], components: [row] });
      }

      if (i.commandName === "ticket-panel") {
        return i.reply({ embeds: [embed("TICKET SUPPORT", "Choose the option that matches your request. Each button can use its own category, staff role and welcome message.")], components: ticketTypeButtons() });
      }

      if (i.commandName === "vouch-panel") {
        return i.reply({ embeds: [embed("VOUCH", "After receiving help/service, leave your vouch in the configured vouch channel. Thank you for supporting the server!") ] });
      }

      if (i.commandName === "giveaway-create") {
        const ms = parseDuration(i.options.getString("duration"));
        if (!ms) return i.reply({ content: `${E()} Invalid duration. Examples: \`30s\`, \`10m\`, \`2h\`, \`1d\`. Max 31d.`, ephemeral: true });
        const winners = i.options.getInteger("winners");
        const prize = i.options.getString("prize");
        const image = i.options.getString("image");
        const channel = i.options.getChannel("channel") || (db.config.giveawayChannelId ? await i.guild.channels.fetch(db.config.giveawayChannelId).catch(() => null) : i.channel);
        if (!channel || channel.type !== ChannelType.GuildText) return i.reply({ content: `${E()} Giveaway channel is invalid.`, ephemeral: true });

        const endAt = Date.now() + ms;
        const join = new ActionRowBuilder().addComponents(new ButtonBuilder().setCustomId("giveaway_join:pending").setLabel("JOIN GIVEAWAY").setStyle(ButtonStyle.Primary).setEmoji(E()));
        const gEmbed = embed("GIVEAWAY", `${E()} **Prize:** ${prize}\n${E()} **Winners:** ${winners}\n${E()} **Ends:** <t:${Math.floor(endAt/1000)}:R>\n\n${E()} Click **JOIN GIVEAWAY** to enter.`);
        if (image) gEmbed.setImage(image);

        const msg = await channel.send({ embeds: [gEmbed], components: [join] });
        db.giveaways[msg.id] = { channelId: channel.id, prize, winners, image: image || "", endAt, ended: false, entries: [], hostId: i.user.id };
        saveDB();
        const realRow = new ActionRowBuilder().addComponents(new ButtonBuilder().setCustomId(`giveaway_join:${msg.id}`).setLabel("JOIN GIVEAWAY").setStyle(ButtonStyle.Primary).setEmoji(E()));
        await msg.edit({ components: [realRow] });
        return i.reply({ content: `${E()} Giveaway created in ${channel}.`, ephemeral: true });
      }

      const giveawayAction = ["giveaway-reroll","giveaway-end","giveaway-cancel"].includes(i.commandName);
      if (giveawayAction) {
        const id = i.options.getString("message_id");
        if (i.commandName === "giveaway-reroll") {
          const g = db.giveaways[id];
          if (!g || !g.ended || g.cancelled) return i.reply({ content: `${E()} Finished giveaway not found.`, ephemeral: true });
          const users = [...new Set(g.entries || [])];
          if (!users.length) return i.reply({ content: `${E()} No participants.`, ephemeral: true });
          const winner = users[Math.floor(Math.random()*users.length)];
          return i.reply({ content: `${E()} New winner: <@${winner}> — **${g.prize}**` });
        }
        await finishGiveaway(id, i.commandName === "giveaway-cancel");
        return i.reply({ content: `${E()} Giveaway action completed.`, ephemeral: true });
      }
    }

    if (!i.isButton()) return;

    if (i.customId === "verify_user") {
      const roleId = db.config.verifyRoleId;
      if (!roleId) return i.reply({ content: `${E()} Verify role is not configured yet.`, ephemeral: true });
      const role = i.guild.roles.cache.get(roleId);
      if (!role) return i.reply({ content: `${E()} Verify role no longer exists.`, ephemeral: true });
      await i.member.roles.add(role);
      return i.reply({ content: `${E()} You are now verified!`, ephemeral: true });
    }

    if (i.customId.startsWith("giveaway_join:")) {
      const id = i.customId.split(":")[1];
      const g = db.giveaways[id];
      if (!g || g.ended) return i.reply({ content: `${E()} This giveaway has ended.`, ephemeral: true });
      if (g.entries.includes(i.user.id)) return i.reply({ content: `${E()} You are already entered.`, ephemeral: true });
      g.entries.push(i.user.id); saveDB();
      return i.reply({ content: `${E()} You are entered in the giveaway!`, ephemeral: true });
    }

    if (i.customId.startsWith("ticket_create:")) {
      const id = i.customId.split(":")[1];
      const t = db.ticketTypes.find(x => x.id === id);
      if (!t) return i.reply({ content: `${E()} Ticket type not found.`, ephemeral: true });

      const existing = i.guild.channels.cache.find(c => c.topic === `ticket-owner:${i.user.id}`);
      if (existing) return i.reply({ content: `${E()} You already have an open ticket: ${existing}`, ephemeral: true });

      const parent = t.categoryId ? i.guild.channels.cache.get(t.categoryId) : null;
      const staffRole = t.staffRoleId ? i.guild.roles.cache.get(t.staffRoleId) : null;
      const channel = await i.guild.channels.create({
        name: `${t.id}-${i.user.username}`.toLowerCase().replace(/[^a-z0-9-]/g, "").slice(0, 90),
        type: ChannelType.GuildText,
        parent: parent?.type === ChannelType.GuildCategory ? parent.id : undefined,
        topic: `ticket-owner:${i.user.id}`,
        permissionOverwrites: [
          { id: i.guild.roles.everyone.id, deny: [PermissionsBitField.Flags.ViewChannel] },
          { id: i.user.id, allow: [PermissionsBitField.Flags.ViewChannel, PermissionsBitField.Flags.SendMessages, PermissionsBitField.Flags.ReadMessageHistory] },
          ...(staffRole ? [{ id: staffRole.id, allow: [PermissionsBitField.Flags.ViewChannel, PermissionsBitField.Flags.SendMessages, PermissionsBitField.Flags.ReadMessageHistory] }] : [])
        ]
      });

      await channel.send({
        content: `${i.user}${staffRole ? ` ${staffRole}` : ""}`,
        embeds: [embed(`${t.label} TICKET`, replaceVars(t.message, i.user))],
        components: [ticketControlRow()]
      });
      return i.reply({ content: `${E()} Ticket created: ${channel}`, ephemeral: true });
    }

    if (!i.channel?.topic?.startsWith("ticket-owner:")) return;

    if (i.customId === "ticket_claim") {
      return i.reply({ content: `${E()} Ticket claimed by ${i.user}.` });
    }

    if (i.customId === "ticket_transcript") {
      const messages = await i.channel.messages.fetch({ limit: 100 });
      const lines = [...messages.values()].reverse().map(m => `[${m.createdAt.toISOString()}] ${m.author.tag}: ${m.content}`);
      const text = lines.join("\n").slice(0, 1800);
      return i.reply({ embeds: [embed("TICKET TRANSCRIPT", `\`\`\`\n${text || "No text messages."}\n\`\`\``)], ephemeral: true });
    }

    if (i.customId === "ticket_close") {
      await i.reply({ content: `${E()} Closing ticket...`, ephemeral: true });
      setTimeout(() => i.channel.delete().catch(() => {}), 1500);
    }
  } catch (err) {
    console.error(err);
    if (!i.replied && !i.deferred) i.reply({ content: `${E()} Something went wrong. Check Railway logs.`, ephemeral: true }).catch(() => {});
  }
});

if (!process.env.DISCORD_TOKEN || !process.env.CLIENT_ID || !process.env.GUILD_ID) {
  console.error("Missing DISCORD_TOKEN, CLIENT_ID or GUILD_ID in environment variables.");
  process.exit(1);
}

client.login(process.env.DISCORD_TOKEN);
