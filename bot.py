"""
GearShift Bot - Main Entry Point
A feature-rich Discord bot for the GearShift community server.
"""

import os
import yaml
import logging
from pathlib import Path
from dotenv import load_dotenv
import discord
from discord.ext import commands
from discord import app_commands

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class GearShiftBot(commands.Bot):
    """Main bot class with configuration management."""
    
    def __init__(self):
        # Load configuration
        self.config = self.load_config()
        
        # Set up intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True
        
        # Initialize bot
        super().__init__(
            command_prefix=self.config.get('prefix', '!'),
            intents=intents,
            help_command=None  # We're using slash commands
        )
        
        self.case_id_counter = 1
        
    def load_config(self) -> dict:
        """Load configuration from config.yaml file."""
        config_path = Path('config.yaml')
        
        if not config_path.exists():
            logger.warning("config.yaml not found. Creating template...")
            self.create_config_template()
            logger.error("Please fill in config.yaml and restart the bot.")
            raise FileNotFoundError("config.yaml not found")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # Validate required config keys
        required_keys = ['guild_id', 'roles', 'channels']
        for key in required_keys:
            if key not in config:
                logger.error(f"Missing required config key: {key}")
                raise ValueError(f"Missing required config key: {key}")
        
        return config
    
    def create_config_template(self):
        """Create a template config.yaml file."""
        template = {
            'guild_id': 0,  # Your Discord server ID
            'prefix': '!',  # Not used with slash commands, but kept for compatibility
            'roles': {
                'staff': 0,  # GearShift Staff role ID
            },
            'channels': {
                'mod_log': 0,  # Moderation log channel ID
                'web_updates': 0,  # Website updates channel ID
                'app_updates': 0,  # App updates channel ID
            }
        }
        
        with open('config.yaml', 'w', encoding='utf-8') as f:
            yaml.dump(template, f, default_flow_style=False, sort_keys=False)
    
    async def setup_hook(self):
        """Called when the bot is starting up."""
        logger.info("Setting up cogs...")
        
        # Load cogs
        cogs = ['cogs.moderation', 'cogs.gearshift', 'cogs.fun']
        for cog in cogs:
            try:
                await self.load_extension(cog)
                logger.info(f"Loaded cog: {cog}")
            except Exception as e:
                logger.error(f"Failed to load cog {cog}: {e}")
        
        # Sync slash commands
        try:
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} command(s)")
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}")
    
    async def on_ready(self):
        """Called when the bot is ready."""
        logger.info(f"{self.user} has connected to Discord!")
        logger.info(f"Bot is in {len(self.guilds)} guild(s)")
        
        # Set bot status
        activity = discord.Game(name="Connecting Car Culture")
        await self.change_presence(activity=activity)
    
    def get_next_case_id(self) -> int:
        """Get the next case ID for moderation actions."""
        case_id = self.case_id_counter
        self.case_id_counter += 1
        return case_id


# Create bot instance
bot = GearShiftBot()


@bot.event
async def on_command_error(ctx, error):
    """Global error handler."""
    if isinstance(error, commands.CommandNotFound):
        return  # Ignore command not found errors
    logger.error(f"Error in command {ctx.command}: {error}")


def main():
    """Main entry point."""
    token = os.getenv('DISCORD_BOT_TOKEN')
    
    if not token:
        logger.error("DISCORD_BOT_TOKEN not found in environment variables!")
        logger.error("Please create a .env file with DISCORD_BOT_TOKEN=your_token_here")
        return
    
    try:
        bot.run(token)
    except discord.LoginFailure:
        logger.error("Invalid bot token!")
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")


if __name__ == '__main__':
    main()

