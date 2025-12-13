# GearShift Bot

A feature-rich Discord bot for the "GearShift, Connecting Car Culture" community server.

## Features

### 🔨 Moderation Commands
- `/ban` - Permanently ban a user
- `/unban` - Unban a user by ID
- `/kick` - Kick a user from the server
- `/timeout` - Place a user in timeout for a specified duration
- `/warn` - Issue a formal warning (stored in Supabase)
- `/warnings` - View all warnings for a user
- `/clear_warnings` - Clear all warnings for a user
- `/purge` - Delete a specified number of messages (1-100)

### 🌐 GearShift-Specific Commands (Staff Only)
- `/update-web` - Send an update log to the website updates channel
- `/update-app` - Send an update log to the app updates channel
- `/update-app-github` - Fetch and display the latest commit from a GitHub repository

### 😂 Fun & Utility Commands
- `/ping` - Check the bot's latency
- `/8ball` - Ask the magic 8-ball a question
- `/carfacts` - Get a random interesting car fact

### 🔒 Security & Anti-Raid Commands
- `/lockdown [reason]` - Immediately lock down all channels to prevent raids
- `/unlock [reason]` - Revert permissions to pre-lockdown state
- `/silence [duration] [reason]` - Temporarily mute all members except staff
- `/pause_invites [reason]` - Delete all invite links and prevent new ones
- `/set_min_age [days]` - Set minimum account age requirement
- `/view_audit_log [limit]` - View recent audit log entries
- `/view_user_info [user]` - Display detailed security profile for a user

### 🛡️ Automatic Security Features
- **Auto-Quarantine**: New members automatically receive a quarantine role
- **Auto-Age Check**: Automatically kicks accounts below minimum age threshold
- **Link Spam Filter**: Detects and removes scam/phishing links and excessive links
- **Mass Mention Filter**: Automatically handles mention spam
- **Anti-Nuke Monitoring**: Monitors staff actions and revokes permissions if suspicious activity is detected

## Installation

### Prerequisites
- Python 3.10 or higher
- A Discord bot application (get your token from [Discord Developer Portal](https://discord.com/developers/applications))
- (Optional) A Supabase account for warnings storage
- (Optional) A GitHub personal access token for the GitHub integration

### Step 1: Clone or Download
Download or clone this repository to your local machine.

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Configure the Bot

1. **Create a `.env` file** (copy from `.env.example`):
   ```bash
   cp .env.example .env
   ```
   
   Then edit `.env` and add your Discord bot token:
   ```
   DISCORD_BOT_TOKEN=your_bot_token_here
   ```

2. **Configure `config.yaml`**:
   - Open `config.yaml`
   - Replace all `0` values with your actual Discord server IDs:
     - `guild_id`: Your Discord server ID
     - `roles.staff`: Your GearShift Staff role ID
     - `channels.mod_log`: Your moderation log channel ID
     - `channels.web_updates`: Your website updates channel ID
     - `channels.app_updates`: Your app updates channel ID

   **How to get IDs:**
   - Enable Developer Mode in Discord (User Settings → Advanced → Developer Mode)
   - Right-click on your server, role, or channel → Copy ID

3. **Optional: Set up Supabase** (for warnings storage):
   - Create a Supabase project at [supabase.com](https://supabase.com)
   - Create a table named `warnings` with the following columns:
     - `id` (bigint, primary key, auto-increment)
     - `user_id` (text)
     - `moderator_id` (text)
     - `reason` (text)
     - `created_at` (timestamp)
   - Add your Supabase URL and key to `.env`

4. **Optional: Set up GitHub Token** (for `/update-app-github`):
   - Create a personal access token at [GitHub Settings](https://github.com/settings/tokens)
   - Add it to `.env` as `GITHUB_TOKEN`

5. **Optional: Configure Security Features**:
   - On first run, the bot will create `security_config.json` with default settings
   - Edit `security_config.json` to configure:
     - `quarantine_role_id`: Role ID for auto-quarantine (new members get this role)
     - `mute_role_id`: Role ID for the `/silence` command
     - `min_account_age_days`: Minimum account age (default: 7 days)
     - `link_spam_threshold`: Max links per message before action (default: 3)
     - `mention_spam_threshold`: Max mentions per message before action (default: 5)
     - Toggle features: `auto_quarantine_enabled`, `auto_age_check_enabled`, etc.

### Step 4: Invite the Bot to Your Server

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Select your bot application
3. Go to OAuth2 → URL Generator
4. Select the following scopes:
   - `bot`
   - `applications.commands`
5. Select the following bot permissions:
   - Administrator (recommended for full functionality)
   - OR select individually:
     - Manage Messages
     - Kick Members
     - Ban Members
     - Moderate Members
     - Send Messages
     - Embed Links
     - Read Message History
     - Manage Channels
     - Manage Roles
     - View Audit Log
     - Manage Server
6. Copy the generated URL and open it in your browser to invite the bot

### Step 5: Run the Bot

```bash
python bot.py
```

The bot should now be online and ready to use!

## Usage

All commands are slash commands. Simply type `/` in Discord to see available commands.

### Moderation Commands
- All moderation commands require appropriate permissions (Kick Members, Ban Members, etc.)
- All actions are logged to the configured moderation log channel
- Each action is assigned a unique case ID

### GearShift Commands
- Restricted to users with the GearShift Staff role
- Update commands send formatted embeds to designated channels

### Fun Commands
- Available to all users
- `/ping` shows bot latency
- `/8ball` provides randomized responses
- `/carfacts` displays random car-related facts

### Security Commands
- All security commands require Administrator permissions
- `/lockdown` saves current permissions and locks all channels
- `/unlock` restores permissions from before lockdown
- `/silence` applies mute role to all non-staff members
- `/view_user_info` shows account age, join date, warnings, and suspicious indicators
- Auto-filters run automatically on message send and member join

## Troubleshooting

### Bot doesn't respond to commands
- Make sure the bot is online and running
- Check that you've synced slash commands (they should sync automatically on startup)
- Verify the bot has the `applications.commands` scope

### Moderation commands don't work
- Ensure the bot has the required permissions in your server
- Check that the bot's role is above the target user's role
- Verify channel IDs in `config.yaml` are correct

### Warnings not saving
- Check your Supabase configuration in `.env`
- Verify the `warnings` table exists with the correct schema
- Check the bot logs for Supabase errors

### GitHub command fails
- Verify the repository owner, name, and branch are correct
- Check if you've hit GitHub's rate limit (set `GITHUB_TOKEN` to avoid this)
- Ensure the repository is public or your token has access

## Support

For issues or questions, please check the bot logs in `bot.log` or contact the GearShift staff.

## License

This bot is created for the GearShift community server.

