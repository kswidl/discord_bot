import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from collections import defaultdict
from datetime import datetime, timedelta

import time
import json

voice_start = {}
voice_total = {}

DATA_FILE = "voice_data.json"

WARNS_FILE = "warns.json"
warns = {}

user_messages = defaultdict(list)

SPAM_LIMIT = 10
SPAM_TIME = 60
TIMEOUT_MINUTES = 5

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

def load_data():
    global voice_total
    try:
        with open(DATA_FILE, "r") as f:
            voice_total = json.load(f)
    except:
        voice_total = {}

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(voice_total, f)

def load_warns():
    global warns
    try:
        with open(WARNS_FILE, "r") as f:
            warns = json.load(f)
    except:
        warns = {}


def save_warns():
    with open(WARNS_FILE, "w") as f:
        json.dump(warns, f)

def remove_expired_warns(user_id):
    if user_id not in warns:
        return

    now = datetime.now()
    valid_warns = []

    for warn in warns[user_id]:
        warn_date = datetime.strptime(warn["date"], "%Y-%m-%d %H:%M:%S")

        if now - warn_date <= timedelta(days=30):
            valid_warns.append(warn)

    warns[user_id] = valid_warns
    save_warns()

@bot.event
async def on_ready():
    load_data()
    load_warns()
    print(f"Logged in as {bot.user}")

@bot.event
async def on_member_join(member):
    role_name = "Unverify"
    role = discord.utils.get(member.guild.roles, name=role_name)

    if role:
        await member.add_roles(role)
        print(f"role issued {role_name} user {member}")
    else:
        print("role not found")

@bot.event
async def on_voice_state_update(member, before, after):
    user_id = str(member.id)

    # зашел в голос
    if before.channel is None and after.channel is not None:
        voice_start[user_id] = time.time()

    # вышел из голоса
    elif before.channel is not None and after.channel is None:
        if user_id in voice_start:
            spent = time.time() - voice_start[user_id]

            if user_id not in voice_total:
                voice_total[user_id] = 0

            voice_total[user_id] += spent
            del voice_start[user_id]

            save_data()

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    user_id = message.author.id
    now = time.time()

    user_messages[user_id].append(now)

    user_messages[user_id] = [
        msg_time for msg_time in user_messages[user_id]
        if now - msg_time <= SPAM_TIME
    ]

    if len(user_messages[user_id]) > SPAM_LIMIT:
        try:
            await message.author.timeout(
                timedelta(minutes=TIMEOUT_MINUTES),
                reason="Spam: more than 10 messages in 1 minute"
            )

            await send_mod_log(
                message.guild,
                f"🚫 **ANTI-SPAM TIMEOUT**\n"
                f"User: {message.author.mention}\n"
                f"Reason: more than {SPAM_LIMIT} messages in {SPAM_TIME} seconds\n"
                f"Duration: {TIMEOUT_MINUTES} minutes"
            )

            user_messages[user_id].clear()

        except discord.Forbidden:
            print("Bot does not have permission to timeout this user.")

    await bot.process_commands(message)

@bot.command()
async def ping(ctx):
    await ctx.send("Pong!")

@bot.command()
@commands.has_any_role("Moderator", "Admin")
async def verify (ctx, member_id: int):
    verify_role_name = "Verify"
    unverify_role_name = "Unverify"
    
    member = ctx.guild.get_member(member_id)
    if member is None:
        print("Member not found")
        return
   
    verify_role = discord.utils.get(member.guild.roles, name = verify_role_name)
    unverify_role = discord.utils.get(member.guild.roles, name = unverify_role_name)

    if verify_role is None:
        print("role {verify_role_name} not found")
        return
    
    if unverify_role is None:
        print("role {unverify_role_name} not found")
        return
    try:
        await member.add_roles(verify_role)
        if verify_role in member.roles:
            await member.remove_roles(unverify_role)
        await ctx.send(f"User {member.mention} verified")
    except discord.Forbidden:
        print("The bot can't change roles. Check the bot's permissions and role status.")
    
LOG_CHANNEL_NAME = "mod-logs"


async def send_mod_log(guild, text):
    log_channel = discord.utils.get(guild.text_channels, name=LOG_CHANNEL_NAME)

    if log_channel:
        await log_channel.send(text)


class BanModal(discord.ui.Modal, title="Ban user"):
    user_id = discord.ui.TextInput(
        label="User ID",
        placeholder="Enter user ID",
        required=True
    )

    reason = discord.ui.TextInput(
        label="Reason",
        placeholder="Enter reason",
        style=discord.TextStyle.paragraph,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            member = interaction.guild.get_member(int(self.user_id.value))

            if member is None:
                await interaction.response.send_message(
                    "User not found on this server.",
                    ephemeral=True
                )
                return

            await member.ban(reason=self.reason.value)

            await interaction.response.defer()

            await send_mod_log(
                interaction.guild,
                f"🔨 **BAN**\n"
                f"Moderator: {interaction.user.mention}\n"
                f"User: {member.mention}\n"
                f"Reason: {self.reason.value}"
            )

        except ValueError:
            await interaction.response.send_message(
                "Invalid user ID.",
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "I do not have permission to ban this user.",
                ephemeral=True
            )


class KickModal(discord.ui.Modal, title="Kick user"):
    user_id = discord.ui.TextInput(
        label="User ID",
        placeholder="Enter user ID",
        required=True
    )

    reason = discord.ui.TextInput(
        label="Reason",
        placeholder="Enter reason",
        style=discord.TextStyle.paragraph,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            member = interaction.guild.get_member(int(self.user_id.value))

            if member is None:
                await interaction.response.send_message(
                    "User not found on this server.",
                    ephemeral=True
                )
                return

            await member.kick(reason=self.reason.value)

            await interaction.response.defer()

            await send_mod_log(
                interaction.guild,
                f"👢 **KICK**\n"
                f"Moderator: {interaction.user.mention}\n"
                f"User: {member.mention}\n"
                f"Reason: {self.reason.value}"
            )

        except ValueError:
            await interaction.response.send_message(
                "Invalid user ID.",
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "I do not have permission to kick this user.",
                ephemeral=True
            )

class TimeoutModal(discord.ui.Modal, title="Timeout user"):
    user_id = discord.ui.TextInput(
        label="User ID",
        placeholder="Enter user ID",
        required=True
    )

    minutes = discord.ui.TextInput(
        label="Minutes",
        placeholder="Enter timeout duration",
        required=True
    )

    reason = discord.ui.TextInput(
        label="Reason",
        placeholder="Enter reason",
        style=discord.TextStyle.paragraph,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            member = interaction.guild.get_member(int(self.user_id.value))

            if member is None:
                await interaction.response.send_message(
                    "User not found.",
                    ephemeral=True
                )
                return

            duration = int(self.minutes.value)

            await member.timeout(
                timedelta(minutes=duration),
                reason=self.reason.value
            )

            await interaction.response.defer()

            await send_mod_log(
                interaction.guild,
                f"⏳ **TIMEOUT**\n"
                f"Moderator: {interaction.user.mention}\n"
                f"User: {member.mention}\n"
                f"Duration: {duration} minutes\n"
                f"Reason: {self.reason.value}"
            )

        except ValueError:
            await interaction.response.send_message(
                "Invalid input.",
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "I don't have permission.",
                ephemeral=True
            )

class UnbanModal(discord.ui.Modal, title="Unban user"):
    user_id = discord.ui.TextInput(
        label="User ID",
        placeholder="Enter user ID",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            user = await bot.fetch_user(int(self.user_id.value))

            await interaction.guild.unban(user)

            await interaction.response.defer()

            await send_mod_log(
                interaction.guild,
                f"✅ **UNBAN**\n"
                f"Moderator: {interaction.user.mention}\n"
                f"User: {user}"
            )

        except ValueError:
            await interaction.response.send_message(
                "Invalid user ID.",
                ephemeral=True
            )

        except discord.NotFound:
            await interaction.response.send_message(
                "User not found in ban list.",
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "I don't have permission.",
                ephemeral=True
            )

class WarnModal(discord.ui.Modal, title="Warn user"):
    user_id = discord.ui.TextInput(
        label="User ID",
        placeholder="Enter user ID",
        required=True
    )

    reason = discord.ui.TextInput(
        label="Reason",
        placeholder="Enter reason",
        style=discord.TextStyle.paragraph,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            member = interaction.guild.get_member(int(self.user_id.value))

            if member is None:
                await interaction.response.send_message("User not found.", ephemeral=True)
                return

            user_id = str(member.id)

            if user_id not in warns:
                warns[user_id] = []

            warns[user_id].append({
                "reason": self.reason.value,
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

            save_warns()

            warn_count = len(warns[user_id])

            await interaction.response.send_message(
                f"⚠️ {member.mention} has been warned.",
                ephemeral=True
            )

            await send_mod_log(
                interaction.guild,
                f"⚠️ **WARN**\n"
                f"Moderator: {interaction.user.mention}\n"
                f"User: {member.mention}\n"
                f"Reason: {self.reason.value}\n"
                f"Total warns: {warn_count}"
            )

        except ValueError:
            await interaction.response.send_message("Invalid user ID.", ephemeral=True)

class UnwarnModal(discord.ui.Modal, title="Remove warns"):
    user_id = discord.ui.TextInput(
        label="User ID",
        placeholder="Enter user ID",
        required=True
    )

    amount = discord.ui.TextInput(
        label="Amount",
        placeholder="How many warns to remove",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            member = interaction.guild.get_member(int(self.user_id.value))

            if member is None:
                await interaction.response.send_message("User not found.", ephemeral=True)
                return

            amount = int(self.amount.value)
            user_id = str(member.id)

            remove_expired_warns(user_id)

            if user_id not in warns or len(warns[user_id]) == 0:
                await interaction.response.send_message("This user has no warns.", ephemeral=True)
                return

            removed_warns = warns[user_id][-amount:]
            warns[user_id] = warns[user_id][:-amount]

            save_warns()

            warn_count = len(warns[user_id])

            removed_text = "\n".join(
                [f"- {warn['reason']}" for warn in removed_warns]
            )

            await interaction.response.send_message(
                f"✅ Removed {len(removed_warns)} warn(s) from {member.mention}.",
                ephemeral=True
            )

            await send_mod_log(
                interaction.guild,
                f"✅ **UNWARN**\n"
                f"Moderator: {interaction.user.mention}\n"
                f"User: {member.mention}\n"
                f"Removed warns:\n{removed_text}\n"
                f"Total warns: {warn_count}"
            )

        except ValueError:
            await interaction.response.send_message("Invalid input.", ephemeral=True)
class ModerationPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def interaction_check(self, interaction: discord.Interaction):
        allowed_role = "Admin"

        if discord.utils.get(interaction.user.roles, name=allowed_role):
            return True

        await interaction.response.send_message(
            "You do not have permission to use this panel.",
            ephemeral=True
        )
        return False

    @discord.ui.button(label="Ban", style=discord.ButtonStyle.danger)
    async def ban_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(BanModal())
        await interaction.message.delete()

    @discord.ui.button(label="Kick", style=discord.ButtonStyle.secondary)
    async def kick_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(KickModal())
        await interaction.message.delete()

    @discord.ui.button(label="Timeout", style=discord.ButtonStyle.primary)
    async def timeout_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TimeoutModal())
        await interaction.message.delete()

    @discord.ui.button(label="Unban", style=discord.ButtonStyle.success)
    async def unban_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(UnbanModal())
        await interaction.message.delete()
    
    @discord.ui.button(label="Warn", style=discord.ButtonStyle.primary)
    async def warn_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(WarnModal())
        await interaction.message.delete()


    @discord.ui.button(label="Unwarn", style=discord.ButtonStyle.success)
    async def unwarn_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(UnwarnModal())
        await interaction.message.delete()


@bot.command()
@commands.has_role("Admin")
async def modpanel(ctx):
    view = ModerationPanel()
    await ctx.send("Moderation panel:", view=view)

@bot.command()
async def voicetime(ctx):
    user_id = str(ctx.author.id)

    total = voice_total.get(user_id, 0)

    if user_id in voice_start:
        total += time.time() - voice_start[user_id]

    hours = int(total // 3600)
    minutes = int((total % 3600) // 60)
    seconds = int(total % 60)

    await ctx.send(
        f"⏱ {ctx.author.mention}, your total voice time is:\n"
        f"{hours} h {minutes} m {seconds} s"
    )

@bot.command()
async def voicetop(ctx):
    if not voice_total:
        await ctx.send("No voice activity data yet.")
        return

    current_totals = voice_total.copy()

    for user_id, start_time in voice_start.items():
        current_totals[user_id] = current_totals.get(user_id, 0) + (time.time() - start_time)

    sorted_users = sorted(
        current_totals.items(),
        key=lambda item: item[1],
        reverse=True
    )

    top_users = sorted_users[:10]

    embed = discord.Embed(
        title="🎙 Voice Activity Leaderboard",
        description="Top users by total time spent in voice channels",
        color=discord.Color.blue()
    )

    for index, (user_id, total) in enumerate(top_users, start=1):
        member = ctx.guild.get_member(int(user_id))

        if member:
            username = member.display_name
        else:
            username = "Unknown User"

        hours = int(total // 3600)
        minutes = int((total % 3600) // 60)
        seconds = int(total % 60)

        embed.add_field(
            name=f"{index}. {username}",
            value=f"{hours}h {minutes}m {seconds}s",
            inline=False
        )

    await ctx.send(embed=embed)

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise ValueError("DISCORD_TOKEN not found in .env")

bot.run(TOKEN)