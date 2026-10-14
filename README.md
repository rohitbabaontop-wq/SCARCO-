# Purgatory Discord Bot (Python)

Features included:
- `/ticketpanel`: persistent ticket panel with four category buttons
- Ticket channels are private to the opener and bot; `/Close Ticket` button can be used by the opener or a member with Manage Channels
- `/giveaway prize winners duration`: reaction-entry giveaway; duration examples: `30s`, `10m`, `2h`, `1d`
- `/announce announcement [tag]`: Purgatory-style announcement
- `/purge amount`: delete up to 100 messages
- `/bothelp`: command list
- Railway deployment files included

## 1. Create the Discord application
1. Open the Discord Developer Portal and create an application.
2. Add a Bot user and copy its token. Never share the token in chat or commit it to files.
3. In OAuth2 URL Generator, select `bot` and `applications.commands`. Give it the permissions it needs: View Channels, Send Messages, Embed Links, Read Message History, Add Reactions, Manage Channels, Manage Messages, and Use External Emojis where needed.
4. In the Bot settings, enable **Server Members Intent** and **Message Content Intent** if you need them. Invite the bot to your server.

## 2. Deploy on Railway
1. Upload/push these files to a GitHub repository.
2. In Railway, create a new project and deploy the repository.
3. Add Railway Variables:
   - `DISCORD_TOKEN` = your bot token
   - `GUILD_ID` = optional test server ID (slash commands sync faster to that server)
4. Start command: `python bot.py` (the included Procfile/railway.json also set this).
5. Check deployment logs. When it says `Logged in as ...`, the bot is online.

## 3. Use commands
- `/ticketpanel` — run in the channel where you want the panel. Requires Manage Server.
- `/giveaway prize:<text> winners:<number> duration:<10s/10m/2h/1d>` — requires Manage Server.
- `/announce announcement:<text> tag:<optional member>` — requires Manage Server.
- `/purge amount:<1-100>` — requires Manage Messages.
- `/bothelp`

## Important notes
- Custom emojis render only when the bot can access the emoji. The bot must be in the emoji's source server or otherwise have permission to use that emoji. Some emojis in the supplied list may be from another server or may no longer be available.
- Discord button colors are limited to Blurple, Grey, Green, and Red. The requested purple/yellow category colors are represented by embed colors, not exact button colors.
- This starter version keeps ticket/giveaway state in memory while commands run. A Railway restart will stop active giveaway timers; use a database for durable giveaways and transcripts in a production version.
- The bot's private ticket channels currently grant access to the ticket opener and the bot. Add your staff role to the channel permission overwrites if your server has a dedicated support role.
