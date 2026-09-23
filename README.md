# SCARCO Python Discord Bot

Railway-ready Python Discord bot.

## Railway Variables
Add:
- DISCORD_TOKEN
- CLIENT_ID
- GUILD_ID

Do NOT put your token in GitHub or chat.

## Deploy
Upload these files to GitHub and connect the repo to Railway:
- bot.py
- requirements.txt
- runtime.txt
- railway.json
- nixpacks.toml
- database.json

Railway will run:
python bot.py

## Required Discord permissions
Administrator is easiest for setup. The bot also needs permissions for:
Manage Channels, Manage Roles, Send Messages, Embed Links, Read Message History, View Channels.

Move the bot's role above the Verify Role.

## Commands
/help
/ping
/verify-panel
/ticket-panel
/vouch-panel
/config verify-role
/config verify-channel
/config vouch-channel
/config ticket-category
/config ticket-staff-role
/config giveaway-channel
/config theme-emoji
/config color
/config footer
/ticket-add-type
/ticket-remove-type
/ticket-list-types
/giveaway-create
/giveaway-end
/giveaway-cancel
/giveaway-reroll

## Database
This version uses database.json so no MongoDB is required to start. Railway's normal filesystem can be reset during redeploys; for long-term persistent data, later move the database to MongoDB or attach a Railway volume.
