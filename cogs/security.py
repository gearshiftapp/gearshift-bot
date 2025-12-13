"""
Security Cog
Handles anti-raid, security, and moderation features including lockdown, quarantine, and spam filtering.
"""

import discord
from discord import app_commands
from discord.ext import commands
import logging
from datetime import datetime, timedelta
import json
import os
import asyncio
from pathlib import Path
import re

logger = logging.getLogger(__name__)


class Security(commands.Cog):
    """Security and anti-raid commands."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.lockdown_state_file = Path('lockdown_state.json')
        self.lockdown_state = self._load_lockdown_state()
        self.security_config_file = Path('security_config.json')
        self.security_config = self._load_security_config()
        
        # Anti-nuke tracking
        self.staff_actions = {}  # {staff_id: {action_type: count, last_action: timestamp}}
        self.nuke_threshold = 5  # Actions within time window
        self.nuke_time_window = 60  # seconds
        
        # Known scam/phishing domains (can be expanded)
        self.scam_domains = [
            'discord-nitro.com',
            'discordgift.com',
            'discord-app.com',
            'steamcommunlty.com',  # Common typo scam
            'steamcornmunity.com',
        ]
    
    def _is_immune(self, member: discord.Member) -> bool:
        """Check if a member has the immune role (exempt from all security measures)."""
        config = self.bot.config
        immune_role_id = config['roles'].get('immune')
        
        if not immune_role_id:
            return False
        
        immune_role = member.guild.get_role(immune_role_id)
        if not immune_role:
            return False
        
        return immune_role in member.roles
    
    def _load_lockdown_state(self) -> dict:
        """Load lockdown state from file."""
        if self.lockdown_state_file.exists():
            try:
                with open(self.lockdown_state_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load lockdown state: {e}")
        return {}
    
    def _save_lockdown_state(self):
        """Save lockdown state to file."""
        try:
            with open(self.lockdown_state_file, 'w') as f:
                json.dump(self.lockdown_state, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save lockdown state: {e}")
    
    def _load_security_config(self) -> dict:
        """Load security configuration."""
        default_config = {
            'min_account_age_days': 7,
            'quarantine_role_id': None,
            'mute_role_id': None,
            'welcome_channel_id': None,
            'verification_channel_id': None,
            'link_spam_threshold': 3,
            'mention_spam_threshold': 5,
            'auto_quarantine_enabled': True,
            'auto_age_check_enabled': True,
            'link_filter_enabled': True,
            'mention_filter_enabled': True,
            'anti_nuke_enabled': True
        }
        
        if self.security_config_file.exists():
            try:
                with open(self.security_config_file, 'r') as f:
                    config = json.load(f)
                    # Merge with defaults
                    for key, value in default_config.items():
                        if key not in config:
                            config[key] = value
                    return config
            except Exception as e:
                logger.error(f"Failed to load security config: {e}")
        
        # Save default config
        self._save_security_config(default_config)
        return default_config
    
    def _save_security_config(self, config: dict = None):
        """Save security configuration."""
        if config is None:
            config = self.security_config
        try:
            with open(self.security_config_file, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save security config: {e}")
    
    async def _log_security_action(
        self,
        action: str,
        moderator: discord.Member,
        reason: str = None,
        details: str = None
    ):
        """Log security action to moderation log."""
        config = self.bot.config
        channel_id = config['channels'].get('mod_log')
        
        if not channel_id:
            return
        
        channel = self.bot.get_channel(channel_id)
        if not channel:
            return
        
        embed = discord.Embed(
            title=f"🔒 Security Action: {action}",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(name="Moderator", value=f"{moderator.mention} ({moderator.id})", inline=True)
        if reason:
            embed.add_field(name="Reason", value=reason, inline=False)
        if details:
            embed.add_field(name="Details", value=details, inline=False)
        
        try:
            await channel.send(embed=embed)
        except Exception as e:
            logger.error(f"Failed to send security log: {e}")
    
    @app_commands.command(name="lockdown", description="Lock down all channels to prevent raids")
    @app_commands.describe(reason="Reason for the lockdown")
    @app_commands.checks.has_permissions(administrator=True)
    async def lockdown(
        self,
        interaction: discord.Interaction,
        reason: str = "Server lockdown initiated"
    ):
        """Lock down all channels by denying @everyone permissions."""
        if str(interaction.guild.id) in self.lockdown_state:
            await interaction.response.send_message(
                "⚠️ Server is already in lockdown!",
                ephemeral=True
            )
            return
        
        await interaction.response.defer(ephemeral=True)
        
        guild = interaction.guild
        everyone_role = guild.default_role
        
        locked_channels = []
        failed_channels = []
        
        # Store original permissions
        original_perms = {}
        
        for channel in guild.channels:
            try:
                # Get current permissions
                overwrite = channel.overwrites_for(everyone_role)
                original_perms[str(channel.id)] = {
                    'send_messages': overwrite.send_messages,
                    'connect': overwrite.connect,
                    'speak': overwrite.speak,
                    'view_channel': overwrite.view_channel
                }
                
                # Deny send messages for text channels
                if isinstance(channel, discord.TextChannel):
                    await channel.set_permissions(
                        everyone_role,
                        send_messages=False,
                        reason=f"Lockdown: {reason}"
                    )
                    locked_channels.append(channel.mention)
                
                # Deny connect for voice channels
                elif isinstance(channel, discord.VoiceChannel):
                    await channel.set_permissions(
                        everyone_role,
                        connect=False,
                        speak=False,
                        reason=f"Lockdown: {reason}"
                    )
                    locked_channels.append(channel.mention)
            except Exception as e:
                logger.error(f"Failed to lock channel {channel.id}: {e}")
                failed_channels.append(channel.name)
        
        # Save lockdown state
        self.lockdown_state[str(guild.id)] = {
            'moderator_id': str(interaction.user.id),
            'reason': reason,
            'timestamp': datetime.utcnow().isoformat(),
            'original_perms': original_perms
        }
        self._save_lockdown_state()
        
        await self._log_security_action("Lockdown", interaction.user, reason)
        
        embed = discord.Embed(
            title="🔒 Server Lockdown Activated",
            description=f"**Reason:** {reason}\n\n**Locked Channels:** {len(locked_channels)}\n**Failed:** {len(failed_channels)}",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )
        
        if failed_channels:
            embed.add_field(name="Failed Channels", value=", ".join(failed_channels[:10]), inline=False)
        
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="unlock", description="Unlock all channels after a lockdown")
    @app_commands.describe(reason="Reason for unlocking")
    @app_commands.checks.has_permissions(administrator=True)
    async def unlock(
        self,
        interaction: discord.Interaction,
        reason: str = "Server lockdown lifted"
    ):
        """Revert permissions to their state before lockdown."""
        guild_id = str(interaction.guild.id)
        
        if guild_id not in self.lockdown_state:
            await interaction.response.send_message(
                "⚠️ Server is not in lockdown!",
                ephemeral=True
            )
            return
        
        await interaction.response.defer(ephemeral=True)
        
        guild = interaction.guild
        everyone_role = guild.default_role
        state = self.lockdown_state[guild_id]
        original_perms = state.get('original_perms', {})
        
        unlocked_channels = []
        failed_channels = []
        
        for channel in guild.channels:
            channel_id = str(channel.id)
            if channel_id in original_perms:
                try:
                    perms = original_perms[channel_id]
                    await channel.set_permissions(
                        everyone_role,
                        send_messages=perms.get('send_messages'),
                        connect=perms.get('connect'),
                        speak=perms.get('speak'),
                        view_channel=perms.get('view_channel'),
                        reason=f"Unlock: {reason}"
                    )
                    unlocked_channels.append(channel.mention)
                except Exception as e:
                    logger.error(f"Failed to unlock channel {channel.id}: {e}")
                    failed_channels.append(channel.name)
            else:
                # If no original perms stored, just reset to default
                try:
                    await channel.set_permissions(everyone_role, overwrite=None, reason=f"Unlock: {reason}")
                    unlocked_channels.append(channel.mention)
                except Exception as e:
                    logger.error(f"Failed to unlock channel {channel.id}: {e}")
                    failed_channels.append(channel.name)
        
        # Remove lockdown state
        del self.lockdown_state[guild_id]
        self._save_lockdown_state()
        
        await self._log_security_action("Unlock", interaction.user, reason)
        
        embed = discord.Embed(
            title="🔓 Server Unlocked",
            description=f"**Reason:** {reason}\n\n**Unlocked Channels:** {len(unlocked_channels)}\n**Failed:** {len(failed_channels)}",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="silence", description="Temporarily mute all members except staff")
    @app_commands.describe(duration="Duration in minutes (default: 30)", reason="Reason for silence")
    @app_commands.checks.has_permissions(administrator=True)
    async def silence(
        self,
        interaction: discord.Interaction,
        duration: int = 30,
        reason: str = "Mass mute initiated"
    ):
        """Apply mute role to all members except staff."""
        config = self.bot.config
        staff_role_id = config['roles'].get('staff')
        staff_role = interaction.guild.get_role(staff_role_id) if staff_role_id else None
        
        mute_role_id = self.security_config.get('mute_role_id')
        if not mute_role_id:
            await interaction.response.send_message(
                "❌ Mute role not configured! Please set it in security_config.json",
                ephemeral=True
            )
            return
        
        mute_role = interaction.guild.get_role(mute_role_id)
        if not mute_role:
            await interaction.response.send_message(
                "❌ Mute role not found!",
                ephemeral=True
            )
            return
        
        await interaction.response.defer(ephemeral=True)
        
        muted_count = 0
        failed_count = 0
        
        for member in interaction.guild.members:
            if member.bot:
                continue
            
            # Skip immune members (highest priority)
            if self._is_immune(member):
                continue
            
            # Skip staff members
            if staff_role and staff_role in member.roles:
                continue
            
            # Skip if already has mute role
            if mute_role in member.roles:
                continue
            
            try:
                await member.add_roles(mute_role, reason=f"Silence: {reason}")
                muted_count += 1
            except Exception as e:
                logger.error(f"Failed to mute {member.id}: {e}")
                failed_count += 1
        
        await self._log_security_action("Silence", interaction.user, reason, f"Muted {muted_count} members for {duration} minutes")
        
        embed = discord.Embed(
            title="🔇 Server Silenced",
            description=f"**Reason:** {reason}\n**Duration:** {duration} minutes\n\n**Muted Members:** {muted_count}\n**Failed:** {failed_count}",
            color=discord.Color.orange(),
            timestamp=datetime.utcnow()
        )
        
        await interaction.followup.send(embed=embed)
        
        # Auto-remove after duration
        if duration > 0:
            await asyncio.sleep(duration * 60)
            for member in interaction.guild.members:
                # Skip immune and staff members
                if self._is_immune(member):
                    continue
                if staff_role and staff_role in member.roles:
                    continue
                if mute_role in member.roles:
                    try:
                        await member.remove_roles(mute_role, reason="Silence duration expired")
                    except:
                        pass
    
    @app_commands.command(name="pause_invites", description="Delete all invite links and prevent new ones")
    @app_commands.describe(reason="Reason for pausing invites")
    @app_commands.checks.has_permissions(administrator=True)
    async def pause_invites(
        self,
        interaction: discord.Interaction,
        reason: str = "Invite pause initiated"
    ):
        """Delete all existing invites and prevent new ones."""
        await interaction.response.defer(ephemeral=True)
        
        deleted_count = 0
        failed_count = 0
        
        try:
            invites = await interaction.guild.invites()
            for invite in invites:
                try:
                    await invite.delete(reason=f"Pause invites: {reason}")
                    deleted_count += 1
                except Exception as e:
                    logger.error(f"Failed to delete invite {invite.code}: {e}")
                    failed_count += 1
        except Exception as e:
            logger.error(f"Failed to fetch invites: {e}")
        
        # Deny create instant invite permission for @everyone
        everyone_role = interaction.guild.default_role
        try:
            await interaction.guild.default_role.edit(
                permissions=interaction.guild.default_role.permissions,
                reason=f"Pause invites: {reason}"
            )
            # Set permission override for all channels
            for channel in interaction.guild.channels:
                try:
                    await channel.set_permissions(
                        everyone_role,
                        create_instant_invite=False,
                        reason=f"Pause invites: {reason}"
                    )
                except:
                    pass
        except Exception as e:
            logger.error(f"Failed to set invite permissions: {e}")
        
        await self._log_security_action("Pause Invites", interaction.user, reason, f"Deleted {deleted_count} invites")
        
        embed = discord.Embed(
            title="⏸️ Invites Paused",
            description=f"**Reason:** {reason}\n\n**Deleted Invites:** {deleted_count}\n**Failed:** {failed_count}",
            color=discord.Color.orange(),
            timestamp=datetime.utcnow()
        )
        
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="set_min_age", description="Set minimum account age requirement in days")
    @app_commands.describe(days="Minimum account age in days")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_min_age(
        self,
        interaction: discord.Interaction,
        days: int
    ):
        """Set minimum account age requirement."""
        if days < 0 or days > 365:
            await interaction.response.send_message(
                "❌ Days must be between 0 and 365!",
                ephemeral=True
            )
            return
        
        self.security_config['min_account_age_days'] = days
        self._save_security_config()
        
        embed = discord.Embed(
            title="✅ Minimum Age Updated",
            description=f"Minimum account age set to **{days} days**",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="view_audit_log", description="View recent audit log entries")
    @app_commands.describe(limit="Number of entries to show (1-20, default: 10)")
    @app_commands.checks.has_permissions(view_audit_log=True)
    async def view_audit_log(
        self,
        interaction: discord.Interaction,
        limit: int = 10
    ):
        """View recent audit log entries."""
        if limit < 1 or limit > 20:
            limit = 10
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            entries = []
            async for entry in interaction.guild.audit_logs(limit=limit):
                entries.append(entry)
            
            if not entries:
                await interaction.followup.send("No audit log entries found.", ephemeral=True)
                return
            
            embed = discord.Embed(
                title="📋 Recent Audit Log",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            
            for entry in entries[:10]:
                action_name = str(entry.action).split('.')[-1].replace('_', ' ').title()
                user = entry.user.mention if entry.user else "Unknown"
                target = entry.target
                
                if isinstance(target, discord.Member):
                    target_str = f"{target.mention} ({target.id})"
                elif isinstance(target, discord.Role):
                    target_str = f"@{target.name}"
                elif isinstance(target, discord.abc.GuildChannel):
                    target_str = f"#{target.name}"
                else:
                    target_str = str(target) if target else "N/A"
                
                embed.add_field(
                    name=f"{action_name}",
                    value=f"**User:** {user}\n**Target:** {target_str}\n**Reason:** {entry.reason or 'No reason'}\n**Time:** <t:{int(entry.created_at.timestamp())}:R>",
                    inline=False
                )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send("❌ I don't have permission to view audit logs!", ephemeral=True)
        except Exception as e:
            logger.error(f"Error viewing audit log: {e}")
            await interaction.followup.send(f"❌ An error occurred: {e}", ephemeral=True)
    
    @app_commands.command(name="view_user_info", description="View detailed security profile for a user")
    @app_commands.describe(user="The user to check")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def view_user_info(
        self,
        interaction: discord.Interaction,
        user: discord.Member
    ):
        """View detailed user security information."""
        await interaction.response.defer(ephemeral=True)
        
        # Calculate account age
        account_age = (datetime.utcnow() - user.created_at).days
        join_age = (datetime.utcnow() - user.joined_at).days if user.joined_at else 0
        
        # Get warnings (if Supabase is configured)
        warning_count = 0
        try:
            mod_cog = self.bot.get_cog('Moderation')
            if mod_cog and hasattr(mod_cog, 'supabase') and mod_cog.supabase:
                result = mod_cog.supabase.table('warnings').select('*').eq('user_id', str(user.id)).execute()
                warning_count = len(result.data) if result.data else 0
        except Exception as e:
            logger.debug(f"Could not fetch warnings: {e}")
        
        # Check for suspicious indicators
        suspicious = []
        if account_age < self.security_config.get('min_account_age_days', 7):
            suspicious.append(f"Account age: {account_age} days (below threshold)")
        if user.avatar is None:
            suspicious.append("No avatar (default)")
        if user.discriminator == "0":
            suspicious.append("New username system")
        
        embed = discord.Embed(
            title=f"👤 User Security Profile: {user.display_name}",
            color=discord.Color.blue() if not suspicious else discord.Color.orange(),
            timestamp=datetime.utcnow()
        )
        
        embed.set_thumbnail(url=user.display_avatar.url if user.display_avatar else None)
        
        embed.add_field(name="User ID", value=str(user.id), inline=True)
        embed.add_field(name="Account Created", value=f"<t:{int(user.created_at.timestamp())}:R>", inline=True)
        embed.add_field(name="Account Age", value=f"{account_age} days", inline=True)
        embed.add_field(name="Joined Server", value=f"<t:{int(user.joined_at.timestamp())}:R>" if user.joined_at else "Unknown", inline=True)
        embed.add_field(name="Join Age", value=f"{join_age} days", inline=True)
        embed.add_field(name="Warnings", value=str(warning_count), inline=True)
        embed.add_field(name="Roles", value=f"{len(user.roles)} roles", inline=True)
        embed.add_field(name="Bot", value="Yes" if user.bot else "No", inline=True)
        
        if suspicious:
            embed.add_field(name="⚠️ Suspicious Indicators", value="\n".join(suspicious), inline=False)
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Handle new member joins - auto-quarantine and age check."""
        if member.bot:
            return
        
        # Skip immune members (highest priority - they are exempt from all security measures)
        if self._is_immune(member):
            logger.info(f"Skipping security checks for immune member {member.id}")
            return
        
        config = self.bot.config
        guild_id = str(member.guild.id)
        
        # Auto-Quarantine
        if self.security_config.get('auto_quarantine_enabled', True):
            quarantine_role_id = self.security_config.get('quarantine_role_id')
            if quarantine_role_id:
                quarantine_role = member.guild.get_role(quarantine_role_id)
                if quarantine_role:
                    try:
                        await member.add_roles(quarantine_role, reason="Auto-quarantine: New member")
                        logger.info(f"Auto-quarantined {member.id}")
                    except Exception as e:
                        logger.error(f"Failed to quarantine {member.id}: {e}")
        
        # Auto-Age Check
        if self.security_config.get('auto_age_check_enabled', True):
            account_age = (datetime.utcnow() - member.created_at).days
            min_age = self.security_config.get('min_account_age_days', 7)
            
            if account_age < min_age:
                # Kick or quarantine
                try:
                    await member.kick(reason=f"Account age {account_age} days < {min_age} days minimum")
                    logger.info(f"Auto-kicked {member.id} for account age: {account_age} days")
                    
                    # Log to mod channel
                    await self._log_security_action(
                        "Auto-Kick (Age Check)",
                        member.guild.me,
                        f"Account age: {account_age} days (minimum: {min_age} days)",
                        f"User: {member} ({member.id})"
                    )
                except Exception as e:
                    logger.error(f"Failed to kick {member.id}: {e}")
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Handle message filtering for spam."""
        if message.author.bot:
            return
        
        if not message.guild:
            return
        
        # Skip immune members (highest priority - they are exempt from all security measures)
        if isinstance(message.author, discord.Member) and self._is_immune(message.author):
            return
        
        # Link Spam Filter
        if self.security_config.get('link_filter_enabled', True):
            links = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', message.content)
            
            if links:
                # Check for scam domains
                scam_found = any(domain in link for link in links for domain in self.scam_domains)
                
                if scam_found:
                    try:
                        await message.delete()
                        await message.channel.send(
                            f"⚠️ {message.author.mention}, scam/phishing links are not allowed!",
                            delete_after=5
                        )
                        await message.author.timeout(
                            timedelta(minutes=10),
                            reason="Scam link detected"
                        )
                        logger.info(f"Deleted scam link from {message.author.id}")
                        return
                    except Exception as e:
                        logger.error(f"Failed to handle scam link: {e}")
                
                # Check for excessive links
                threshold = self.security_config.get('link_spam_threshold', 3)
                if len(links) >= threshold:
                    try:
                        await message.delete()
                        await message.author.timeout(
                            timedelta(minutes=5),
                            reason=f"Link spam detected ({len(links)} links)"
                        )
                        logger.info(f"Deleted link spam from {message.author.id}: {len(links)} links")
                    except Exception as e:
                        logger.error(f"Failed to handle link spam: {e}")
        
        # Mass Mention Filter
        if self.security_config.get('mention_filter_enabled', True):
            mentions = set(message.mentions)
            threshold = self.security_config.get('mention_spam_threshold', 5)
            
            if len(mentions) >= threshold:
                try:
                    await message.delete()
                    await message.author.timeout(
                        timedelta(minutes=10),
                        reason=f"Mass mention spam detected ({len(mentions)} mentions)"
                    )
                    logger.info(f"Deleted mention spam from {message.author.id}: {len(mentions)} mentions")
                except Exception as e:
                    logger.error(f"Failed to handle mention spam: {e}")
    
    async def _check_anti_nuke(self, guild: discord.Guild, user: discord.Member, action_type: str):
        """Check if user's actions trigger anti-nuke protection."""
        if not self.security_config.get('anti_nuke_enabled', True):
            return
        
        if not user or user.bot:
            return
        
        # Skip immune members (highest priority - they are exempt from anti-nuke)
        if self._is_immune(user):
            logger.debug(f"Skipping anti-nuke check for immune member {user.id}")
            return
        
        # Check if user is staff
        config = self.bot.config
        staff_role_id = config['roles'].get('staff')
        if not staff_role_id:
            return
        
        staff_role = guild.get_role(staff_role_id)
        if not staff_role or staff_role not in user.roles:
            return
        
        # Track staff actions
        user_id = str(user.id)
        now = datetime.utcnow()
        
        if user_id not in self.staff_actions:
            self.staff_actions[user_id] = {}
        
        # Count suspicious actions
        suspicious_actions = ['channel_delete', 'ban', 'kick', 'role_delete', 'webhook_delete']
        if any(sa in action_type for sa in suspicious_actions):
            if action_type not in self.staff_actions[user_id]:
                self.staff_actions[user_id][action_type] = {'count': 0, 'last_action': None}
            
            last_action_time = self.staff_actions[user_id][action_type]['last_action']
            if last_action_time:
                time_diff = (now - datetime.fromisoformat(last_action_time)).total_seconds()
                if time_diff < self.nuke_time_window:
                    self.staff_actions[user_id][action_type]['count'] += 1
                else:
                    self.staff_actions[user_id][action_type]['count'] = 1
            else:
                self.staff_actions[user_id][action_type]['count'] = 1
            
            self.staff_actions[user_id][action_type]['last_action'] = now.isoformat()
            
            # Check threshold
            if self.staff_actions[user_id][action_type]['count'] >= self.nuke_threshold:
                # Revoke permissions
                try:
                    member = guild.get_member(user.id)
                    if member:
                        # Remove all roles except @everyone
                        roles_to_remove = [r for r in member.roles if r != guild.default_role]
                        if roles_to_remove:
                            await member.remove_roles(*roles_to_remove, reason="Anti-nuke: Suspicious activity detected")
                        
                        await self._log_security_action(
                            "Anti-Nuke Triggered",
                            guild.me,
                            f"Suspicious activity detected: {action_type} x{self.staff_actions[user_id][action_type]['count']}",
                            f"Staff member: {member.mention} ({member.id})"
                        )
                        
                        logger.warning(f"Anti-nuke triggered for {user.id}: {action_type}")
                except Exception as e:
                    logger.error(f"Failed to handle anti-nuke: {e}")
    
    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        """Monitor bans for anti-nuke."""
        try:
            async for entry in guild.audit_logs(action=discord.AuditLogAction.ban, limit=1):
                if entry.user and entry.user.id != self.bot.user.id:
                    await self._check_anti_nuke(guild, entry.user, 'ban')
                break
        except:
            pass
    
    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """Monitor kicks for anti-nuke."""
        try:
            async for entry in member.guild.audit_logs(action=discord.AuditLogAction.kick, limit=1):
                if entry.user and entry.user.id != self.bot.user.id:
                    await self._check_anti_nuke(member.guild, entry.user, 'kick')
                break
        except:
            pass
    
    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        """Monitor channel deletions for anti-nuke."""
        try:
            async for entry in channel.guild.audit_logs(action=discord.AuditLogAction.channel_delete, limit=1):
                if entry.user and entry.user.id != self.bot.user.id:
                    await self._check_anti_nuke(channel.guild, entry.user, 'channel_delete')
                break
        except:
            pass
    
    @lockdown.error
    @unlock.error
    @silence.error
    @pause_invites.error
    @set_min_age.error
    @view_audit_log.error
    @view_user_info.error
    async def security_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """Error handler for security commands."""
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "❌ You don't have permission to use this command!",
                ephemeral=True
            )
        else:
            logger.error(f"Error in security command: {error}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    f"❌ An error occurred: {error}",
                    ephemeral=True
                )


async def setup(bot: commands.Bot):
    """Setup function for the cog."""
    await bot.add_cog(Security(bot))

