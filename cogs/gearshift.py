"""
GearShift Cog
Handles GearShift-specific commands for website and app updates.
Restricted to GearShift Staff role.
"""

import discord
from discord import app_commands
from discord.ext import commands
import logging
from datetime import datetime
import requests
import os

logger = logging.getLogger(__name__)


class GearShift(commands.Cog):
    """GearShift-specific commands for staff members."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    def _check_staff_role(self, interaction: discord.Interaction) -> bool:
        """Check if user has the GearShift Staff role."""
        config = self.bot.config
        staff_role_id = config['roles'].get('staff')
        
        if not staff_role_id:
            logger.warning("Staff role not configured")
            return False
        
        staff_role = interaction.guild.get_role(staff_role_id)
        if not staff_role:
            logger.warning(f"Staff role not found: {staff_role_id}")
            return False
        
        return staff_role in interaction.user.roles or interaction.user.guild_permissions.administrator
    
    async def _send_update_log(
        self,
        channel_id: int,
        title: str,
        log_message: str,
        color: discord.Color
    ) -> bool:
        """Send a formatted update log to a channel."""
        channel = self.bot.get_channel(channel_id)
        if not channel:
            logger.warning(f"Could not find channel: {channel_id}")
            return False
        
        embed = discord.Embed(
            title=title,
            description=log_message,
            color=color,
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text="GearShift Update Log")
        
        try:
            await channel.send(embed=embed)
            return True
        except Exception as e:
            logger.error(f"Failed to send update log: {e}")
            return False
    
    @app_commands.command(name="update-web", description="Send an update log to the website updates channel")
    @app_commands.describe(log_message="The update message to send")
    async def update_web(
        self,
        interaction: discord.Interaction,
        log_message: str
    ):
        """Send an update log to the website updates channel."""
        if not self._check_staff_role(interaction):
            await interaction.response.send_message(
                "❌ You don't have permission to use this command! This command is restricted to GearShift Staff.",
                ephemeral=True
            )
            return
        
        config = self.bot.config
        channel_id = config['channels'].get('web_updates')
        
        if not channel_id:
            await interaction.response.send_message(
                "❌ Website updates channel not configured!",
                ephemeral=True
            )
            return
        
        success = await self._send_update_log(
            channel_id,
            "🌐 Website Update",
            log_message,
            discord.Color.blue()
        )
        
        if success:
            embed = discord.Embed(
                title="✅ Update Log Sent",
                description=f"Update log has been sent to <#{channel_id}>",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(
                "❌ Failed to send update log. Please check the channel configuration.",
                ephemeral=True
            )
    
    @app_commands.command(name="update-app", description="Send an update log to the app updates channel")
    @app_commands.describe(log_message="The update message to send")
    async def update_app(
        self,
        interaction: discord.Interaction,
        log_message: str
    ):
        """Send an update log to the app updates channel."""
        if not self._check_staff_role(interaction):
            await interaction.response.send_message(
                "❌ You don't have permission to use this command! This command is restricted to GearShift Staff.",
                ephemeral=True
            )
            return
        
        config = self.bot.config
        channel_id = config['channels'].get('app_updates')
        
        if not channel_id:
            await interaction.response.send_message(
                "❌ App updates channel not configured!",
                ephemeral=True
            )
            return
        
        success = await self._send_update_log(
            channel_id,
            "📱 App Update",
            log_message,
            discord.Color.green()
        )
        
        if success:
            embed = discord.Embed(
                title="✅ Update Log Sent",
                description=f"Update log has been sent to <#{channel_id}>",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(
                "❌ Failed to send update log. Please check the channel configuration.",
                ephemeral=True
            )
    
    @app_commands.command(
        name="update-app-github",
        description="Fetch and display the latest commit from a GitHub repository as an app update"
    )
    @app_commands.describe(
        repo_owner="The repository owner (username or organization)",
        repo_name="The repository name",
        branch="The branch to check (default: main)"
    )
    async def update_app_github(
        self,
        interaction: discord.Interaction,
        repo_owner: str,
        repo_name: str,
        branch: str = "main"
    ):
        """Fetch the latest commit from GitHub and send it as an app update."""
        if not self._check_staff_role(interaction):
            await interaction.response.send_message(
                "❌ You don't have permission to use this command! This command is restricted to GearShift Staff.",
                ephemeral=True
            )
            return
        
        config = self.bot.config
        channel_id = config['channels'].get('app_updates')
        
        if not channel_id:
            await interaction.response.send_message(
                "❌ App updates channel not configured!",
                ephemeral=True
            )
            return
        
        # Check for GitHub token (optional, but recommended for rate limits)
        github_token = os.getenv('GITHUB_TOKEN')
        headers = {}
        if github_token:
            headers['Authorization'] = f'token {github_token}'
        
        # Fetch latest commit
        api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/commits/{branch}"
        
        try:
            await interaction.response.defer(ephemeral=True)
            
            response = requests.get(api_url, headers=headers, timeout=10)
            
            if response.status_code == 404:
                await interaction.followup.send(
                    "❌ Repository or branch not found! Please check the repository owner, name, and branch.",
                    ephemeral=True
                )
                return
            
            if response.status_code == 403:
                await interaction.followup.send(
                    "❌ Rate limit exceeded. Consider setting a GITHUB_TOKEN in your environment variables.",
                    ephemeral=True
                )
                return
            
            response.raise_for_status()
            commit_data = response.json()
            
            # Extract commit information
            commit_message = commit_data['commit']['message']
            commit_author = commit_data['commit']['author']['name']
            commit_date = commit_data['commit']['author']['date']
            commit_sha = commit_data['sha'][:7]  # Short SHA
            commit_url = commit_data['html_url']
            
            # Format the update message
            update_message = f"**Latest Commit:** {commit_message}\n\n"
            update_message += f"**Author:** {commit_author}\n"
            update_message += f"**Commit:** [{commit_sha}]({commit_url})\n"
            update_message += f"**Date:** {commit_date[:10]}"
            
            # Send to app updates channel
            channel = self.bot.get_channel(channel_id)
            if not channel:
                await interaction.followup.send(
                    "❌ Could not find app updates channel!",
                    ephemeral=True
                )
                return
            
            embed = discord.Embed(
                title="📱 App Update",
                description=update_message,
                color=discord.Color.green(),
                timestamp=datetime.utcnow(),
                url=commit_url
            )
            embed.set_footer(text="GearShift Update Log | From GitHub")
            
            await channel.send(embed=embed)
            
            success_embed = discord.Embed(
                title="✅ Update Log Sent",
                description=f"Latest commit from `{repo_owner}/{repo_name}` ({branch}) has been sent to <#{channel_id}>",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            await interaction.followup.send(embed=success_embed, ephemeral=True)
            
        except requests.exceptions.Timeout:
            await interaction.followup.send(
                "❌ Request timed out. Please try again later.",
                ephemeral=True
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching GitHub commit: {e}")
            await interaction.followup.send(
                f"❌ An error occurred while fetching the commit: {e}",
                ephemeral=True
            )
        except KeyError as e:
            logger.error(f"Unexpected API response format: {e}")
            await interaction.followup.send(
                "❌ Unexpected response from GitHub API. Please try again later.",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Unexpected error in update-app-github: {e}")
            await interaction.followup.send(
                f"❌ An unexpected error occurred: {e}",
                ephemeral=True
            )


async def setup(bot: commands.Bot):
    """Setup function for the cog."""
    await bot.add_cog(GearShift(bot))

