# Premium Discord Bot — Railway Ready

## Features
- Stylish embeds with configurable theme emoji.
- Advanced multi-button tickets: BUY, REPORT, SUPPORT, PAYMENT.
- Per-ticket custom message, category and staff role.
- Giveaway system with optional image, duration, winners, join button, end, cancel and reroll.
- Verify panel with configurable verify role.
- Vouch panel/channel support.
- `/config` commands for server setup.
- `/help` contains the full command guide.
- JSON database: settings survive restarts when Railway Volume storage is used.

## Railway deploy
1. Create a GitHub repository and upload these files.
2. Create a Railway project and deploy the GitHub repository.
3. Add environment variables:
   - `DISCORD_TOKEN`
   - `CLIENT_ID`
   - `GUILD_ID`
4. Deploy. The start command is `npm start`.
5. Invite the bot with the `bot` and `applications.commands` scopes and permissions required for tickets/roles/messages.

## Important
- Never share your Discord token.
- The bot must have a role higher than the Verify Role.
- For ticket creation/management, give the bot Manage Channels, Manage Messages and View Channel as appropriate.
- For giveaways, the bot needs Send Messages, Embed Links and Add Reactions if you use reaction-based features; this bot uses buttons.
- JSON storage is fine for a small server. For reliable persistence on Railway, attach a Railway Volume and mount it so `database.json` is stored on persistent disk.

## Commands
### General
`/help` — complete command guide
`/ping` — bot latency

### Setup
`/config verify-role <role>`
`/config verify-channel <channel>`
`/config vouch-channel <channel>`
`/config ticket-category <category>`
`/config ticket-staff-role <role>`
`/config giveaway-channel <channel>`
`/config theme-emoji <emoji>`
`/config color <hex>`
`/config footer <text>`

### Panels
`/verify-panel`
`/ticket-panel`
`/vouch-panel`

### Tickets
`/ticket-add-type <id> <label> <emoji> <message> [category] [staffRole]`
`/ticket-remove-type <id>`
`/ticket-list-types`
Inside a ticket:
- Close button
- Claim button
- Transcript button

### Giveaways
`/giveaway-create <duration> <winners> <prize> [image] [channel]`
`/giveaway-reroll <messageId> [channel]`
`/giveaway-end <messageId> [channel]`
`/giveaway-cancel <messageId> [channel]`

Duration examples: `30s`, `10m`, `2h`, `1d`.

## Custom Nitro emojis
Discord custom emoji strings such as `<:name:123456789012345678>` can be used in the emoji/message configuration. If an emoji is not available to the bot/server, Discord will not render it. Replace the example emojis in `database.json` or with the config commands.
