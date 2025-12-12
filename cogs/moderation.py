"""
Moderation Cog
Handles all moderation-related commands including ban, kick, timeout, warnings, and message purging.
"""

import discord
from discord import app_commands
from discord.ext import commands
import logging
from datetime import datetime, timedelta
from supabase import create_client, Client
import os

logger = logging.getLogger(__name__)


class Moderation(commands.Cog):
    """Moderation commands for server management."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.supabase = self._init_supabase()
        self._ensure_warnings_table()
    
    def _init_supabase(self) -> Client:
        """Initialize Supabase client."""
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_KEY')
        
        if not supabase_url or not supabase_key:
            logger.warning("Supabase credentials not found. Warnings will not be persisted.")
            return None
        
        try:
            return create_client(supabase_url, supabase_key)
        except Exception as e:
            logger.error(f"Failed to initialize Supabase: {e}")
            return None
    
    def _ensure_warnings_table(self):
        """Ensure the warnings table exists in Supabase."""
        if not self.supabase:
            return
        
        # Note: This assumes the table already exists in Supabase
        # You'll need to create it manually with columns: id, user_id, moderator_id, reason, created_at
        logger.info("Supabase warnings table should exist with columns: id, user_id, moderator_id, reason, created_at")
    
    async def _log_moderation_action(
        self,
        action: str,
        moderator: discord.Member,
        target: discord.Member | discord.User,
        reason: str,
        case_id: int,
        duration: str = None
    ):
        """Log moderation action to the moderation log channel."""
        config = self.bot.config
        channel_id = config['channels'].get('mod_log')
        
        if not channel_id:
            logger.warning("Moderation log channel not configured")
            return
        
        channel = self.bot.get_channel(channel_id)
        if not channel:
            logger.warning(f"Could not find moderation log channel: {channel_id}")
            return
        
        # Create embed
        embed = discord.Embed(
            title=f"Moderation Action: {action}",
            color=discord.Color.red() if action in ['Ban', 'Kick'] else discord.Color.orange(),
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(name="Case ID", value=f"#{case_id}", inline=True)
        embed.add_field(name="Moderator", value=f"{moderator.mention} ({moderator.id})", inline=True)
        embed.add_field(name="Target", value=f"{target.mention if hasattr(target, 'mention') else str(target)} ({target.id})", inline=True)
        embed.add_field(name="Reason", value=reason or "No reason provided", inline=False)
        
        if duration:
            embed.add_field(name="Duration", value=duration, inline=True)
        
        embed.set_footer(text=f"User ID: {target.id}")
        
        try:
            await channel.send(embed=embed)
        except Exception as e:
            logger.error(f"Failed to send moderation log: {e}")
    
    @app_commands.command(name="ban", description="Permanently ban a user from the server")
    @app_commands.describe(user="The user to ban", reason="Reason for the ban")
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        reason: str = "No reason provided"
    ):
        """Ban a user from the server."""
        if user.top_role >= interaction.user.top_role and interaction.user.id != interaction.guild.owner_id:
            await interaction.response.send_message(
                "You cannot ban someone with equal or higher roles!",
                ephemeral=True
            )
            return
        
        if user.id == interaction.user.id:
            await interaction.response.send_message(
                "You cannot ban yourself!",
                ephemeral=True
            )
            return
        
        case_id = self.bot.get_next_case_id()
        
        try:
            await user.ban(reason=f"{interaction.user} ({interaction.user.id}): {reason}")
            
            await self._log_moderation_action(
                "Ban",
                interaction.user,
                user,
                reason,
                case_id
            )
            
            embed = discord.Embed(
                title="✅ User Banned",
                description=f"{user.mention} has been banned from the server.",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.add_field(name="Case ID", value=f"#{case_id}", inline=True)
            
            await interaction.response.send_message(embed=embed)
        except discord.Forbidden:
            await interaction.response.send_message(
                "I don't have permission to ban this user!",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error banning user: {e}")
            await interaction.response.send_message(
                f"An error occurred while banning the user: {e}",
                ephemeral=True
            )
    
    @app_commands.command(name="unban", description="Unban a user from the server")
    @app_commands.describe(user_id="The ID of the user to unban")
    @app_commands.checks.has_permissions(ban_members=True)
    async def unban(
        self,
        interaction: discord.Interaction,
        user_id: str
    ):
        """Unban a user from the server."""
        try:
            user_id_int = int(user_id)
        except ValueError:
            await interaction.response.send_message(
                "Invalid user ID format!",
                ephemeral=True
            )
            return
        
        try:
            user = await self.bot.fetch_user(user_id_int)
            await interaction.guild.unban(user, reason=f"Unbanned by {interaction.user}")
            
            case_id = self.bot.get_next_case_id()
            
            await self._log_moderation_action(
                "Unban",
                interaction.user,
                user,
                "User unbanned",
                case_id
            )
            
            embed = discord.Embed(
                title="✅ User Unbanned",
                description=f"{user.mention} ({user.id}) has been unbanned from the server.",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Case ID", value=f"#{case_id}", inline=True)
            
            await interaction.response.send_message(embed=embed)
        except discord.NotFound:
            await interaction.response.send_message(
                "User not found or not banned!",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error unbanning user: {e}")
            await interaction.response.send_message(
                f"An error occurred while unbanning the user: {e}",
                ephemeral=True
            )
    
    @app_commands.command(name="kick", description="Kick a user from the server")
    @app_commands.describe(user="The user to kick", reason="Reason for the kick")
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        reason: str = "No reason provided"
    ):
        """Kick a user from the server."""
        if user.top_role >= interaction.user.top_role and interaction.user.id != interaction.guild.owner_id:
            await interaction.response.send_message(
                "You cannot kick someone with equal or higher roles!",
                ephemeral=True
            )
            return
        
        if user.id == interaction.user.id:
            await interaction.response.send_message(
                "You cannot kick yourself!",
                ephemeral=True
            )
            return
        
        case_id = self.bot.get_next_case_id()
        
        try:
            await user.kick(reason=f"{interaction.user} ({interaction.user.id}): {reason}")
            
            await self._log_moderation_action(
                "Kick",
                interaction.user,
                user,
                reason,
                case_id
            )
            
            embed = discord.Embed(
                title="✅ User Kicked",
                description=f"{user.mention} has been kicked from the server.",
                color=discord.Color.orange(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.add_field(name="Case ID", value=f"#{case_id}", inline=True)
            
            await interaction.response.send_message(embed=embed)
        except discord.Forbidden:
            await interaction.response.send_message(
                "I don't have permission to kick this user!",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error kicking user: {e}")
            await interaction.response.send_message(
                f"An error occurred while kicking the user: {e}",
                ephemeral=True
            )
    
    @app_commands.command(name="timeout", description="Place a user in timeout")
    @app_commands.describe(
        user="The user to timeout",
        duration="Duration (e.g., 1h, 30m, 1d)",
        reason="Reason for the timeout"
    )
    @app_commands.checks.has_permissions(moderate_members=True)
    async def timeout(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        duration: str,
        reason: str = "No reason provided"
    ):
        """Place a user in timeout."""
        if user.top_role >= interaction.user.top_role and interaction.user.id != interaction.guild.owner_id:
            await interaction.response.send_message(
                "You cannot timeout someone with equal or higher roles!",
                ephemeral=True
            )
            return
        
        if user.id == interaction.user.id:
            await interaction.response.send_message(
                "You cannot timeout yourself!",
                ephemeral=True
            )
            return
        
        # Parse duration
        duration_seconds = self._parse_duration(duration)
        if duration_seconds is None:
            await interaction.response.send_message(
                "Invalid duration format! Use format like: 1h, 30m, 1d, etc.",
                ephemeral=True
            )
            return
        
        if duration_seconds > 2419200:  # 28 days max
            await interaction.response.send_message(
                "Maximum timeout duration is 28 days!",
                ephemeral=True
            )
            return
        
        timeout_until = datetime.utcnow() + timedelta(seconds=duration_seconds)
        case_id = self.bot.get_next_case_id()
        
        try:
            await user.timeout(timeout_until, reason=f"{interaction.user} ({interaction.user.id}): {reason}")
            
            await self._log_moderation_action(
                "Timeout",
                interaction.user,
                user,
                reason,
                case_id,
                duration
            )
            
            embed = discord.Embed(
                title="✅ User Timed Out",
                description=f"{user.mention} has been placed in timeout.",
                color=discord.Color.orange(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Duration", value=duration, inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.add_field(name="Case ID", value=f"#{case_id}", inline=True)
            
            await interaction.response.send_message(embed=embed)
        except discord.Forbidden:
            await interaction.response.send_message(
                "I don't have permission to timeout this user!",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error timing out user: {e}")
            await interaction.response.send_message(
                f"An error occurred while timing out the user: {e}",
                ephemeral=True
            )
    
    def _parse_duration(self, duration: str) -> int | None:
        """Parse duration string (e.g., '1h', '30m', '1d') to seconds."""
        duration = duration.lower().strip()
        
        multipliers = {
            's': 1,
            'm': 60,
            'h': 3600,
            'd': 86400,
            'w': 604800
        }
        
        try:
            if duration[-1] in multipliers:
                value = int(duration[:-1])
                return value * multipliers[duration[-1]]
            else:
                # Try to parse as just a number (default to minutes)
                return int(duration) * 60
        except ValueError:
            return None
    
    @app_commands.command(name="warn", description="Issue a formal warning to a user")
    @app_commands.describe(user="The user to warn", reason="Reason for the warning")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def warn(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        reason: str = "No reason provided"
    ):
        """Issue a formal warning to a user."""
        if user.id == interaction.user.id:
            await interaction.response.send_message(
                "You cannot warn yourself!",
                ephemeral=True
            )
            return
        
        case_id = self.bot.get_next_case_id()
        
        # Store warning in Supabase
        warning_id = None
        if self.supabase:
            try:
                result = self.supabase.table('warnings').insert({
                    'user_id': str(user.id),
                    'moderator_id': str(interaction.user.id),
                    'reason': reason,
                    'created_at': datetime.utcnow().isoformat()
                }).execute()
                
                if result.data:
                    warning_id = result.data[0].get('id')
            except Exception as e:
                logger.error(f"Failed to store warning in Supabase: {e}")
        
        await self._log_moderation_action(
            "Warn",
            interaction.user,
            user,
            reason,
            case_id
        )
        
        embed = discord.Embed(
            title="⚠️ Warning Issued",
            description=f"{user.mention} has been warned.",
            color=discord.Color.yellow(),
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Case ID", value=f"#{case_id}", inline=True)
        if warning_id:
            embed.add_field(name="Warning ID", value=str(warning_id), inline=True)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="warnings", description="View all warnings for a user")
    @app_commands.describe(user="The user to check warnings for")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def warnings(
        self,
        interaction: discord.Interaction,
        user: discord.Member
    ):
        """View all warnings for a user."""
        if not self.supabase:
            await interaction.response.send_message(
                "Warning system is not available (Supabase not configured).",
                ephemeral=True
            )
            return
        
        try:
            result = self.supabase.table('warnings').select('*').eq('user_id', str(user.id)).execute()
            
            warnings_list = result.data if result.data else []
            
            if not warnings_list:
                embed = discord.Embed(
                    title="📋 User Warnings",
                    description=f"{user.mention} has no warnings.",
                    color=discord.Color.green()
                )
                await interaction.response.send_message(embed=embed)
                return
            
            embed = discord.Embed(
                title=f"📋 Warnings for {user.display_name}",
                description=f"Total warnings: {len(warnings_list)}",
                color=discord.Color.yellow(),
                timestamp=datetime.utcnow()
            )
            
            for i, warning in enumerate(warnings_list[:10], 1):  # Limit to 10 warnings
                moderator_id = warning.get('moderator_id', 'Unknown')
                try:
                    moderator = await self.bot.fetch_user(int(moderator_id))
                    moderator_name = moderator.display_name
                except:
                    moderator_name = f"User ID: {moderator_id}"
                
                created_at = warning.get('created_at', 'Unknown')
                reason = warning.get('reason', 'No reason provided')
                
                embed.add_field(
                    name=f"Warning #{i}",
                    value=f"**Reason:** {reason}\n**Moderator:** {moderator_name}\n**Date:** {created_at[:10] if len(created_at) > 10 else created_at}",
                    inline=False
                )
            
            if len(warnings_list) > 10:
                embed.set_footer(text=f"Showing 10 of {len(warnings_list)} warnings")
            
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            logger.error(f"Error fetching warnings: {e}")
            await interaction.response.send_message(
                f"An error occurred while fetching warnings: {e}",
                ephemeral=True
            )
    
    @app_commands.command(name="clear_warnings", description="Clear all warnings for a user")
    @app_commands.describe(user="The user to clear warnings for")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def clear_warnings(
        self,
        interaction: discord.Interaction,
        user: discord.Member
    ):
        """Clear all warnings for a user."""
        if not self.supabase:
            await interaction.response.send_message(
                "Warning system is not available (Supabase not configured).",
                ephemeral=True
            )
            return
        
        try:
            result = self.supabase.table('warnings').delete().eq('user_id', str(user.id)).execute()
            
            case_id = self.bot.get_next_case_id()
            
            await self._log_moderation_action(
                "Clear Warnings",
                interaction.user,
                user,
                "All warnings cleared",
                case_id
            )
            
            embed = discord.Embed(
                title="✅ Warnings Cleared",
                description=f"All warnings for {user.mention} have been cleared.",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Case ID", value=f"#{case_id}", inline=True)
            
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            logger.error(f"Error clearing warnings: {e}")
            await interaction.response.send_message(
                f"An error occurred while clearing warnings: {e}",
                ephemeral=True
            )
    
    @app_commands.command(name="purge", description="Delete a specified number of messages")
    @app_commands.describe(amount="Number of messages to delete (1-100)")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def purge(
        self,
        interaction: discord.Interaction,
        amount: int
    ):
        """Delete a specified number of messages."""
        if amount < 1 or amount > 100:
            await interaction.response.send_message(
                "Amount must be between 1 and 100!",
                ephemeral=True
            )
            return
        
        try:
            deleted = await interaction.channel.purge(limit=amount)
            
            case_id = self.bot.get_next_case_id()
            
            await self._log_moderation_action(
                "Purge",
                interaction.user,
                interaction.channel,
                f"Deleted {len(deleted)} message(s)",
                case_id
            )
            
            embed = discord.Embed(
                title="✅ Messages Purged",
                description=f"Deleted {len(deleted)} message(s) from {interaction.channel.mention}",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Case ID", value=f"#{case_id}", inline=True)
            
            await interaction.response.send_message(embed=embed, delete_after=5)
        except discord.Forbidden:
            await interaction.response.send_message(
                "I don't have permission to delete messages!",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error purging messages: {e}")
            await interaction.response.send_message(
                f"An error occurred while purging messages: {e}",
                ephemeral=True
            )
    
    @ban.error
    @unban.error
    @kick.error
    @timeout.error
    @warn.error
    @warnings.error
    @clear_warnings.error
    @purge.error
    async def moderation_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """Error handler for moderation commands."""
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "You don't have permission to use this command!",
                ephemeral=True
            )
        else:
            logger.error(f"Error in moderation command: {error}")
            await interaction.response.send_message(
                f"An error occurred: {error}",
                ephemeral=True
            )


async def setup(bot: commands.Bot):
    """Setup function for the cog."""
    await bot.add_cog(Moderation(bot))

