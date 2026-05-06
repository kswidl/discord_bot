import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from datetime import timedelta

import time
import json

voice_start = {}
voice_total = {}

DATA_FILE = "voice_data.json"

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

@bot.event
async def on_ready():
    load_data()
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
                f"🔨 **BAN**\nModerator: {interaction.user.mention}\nUser: {member.mention}\nReason: {self.reason.value}"
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
                f"👢 **KICK**\nModerator: {interaction.user.mention}\nUser: {member}\nReason: {self.reason.value}"
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
                f"⏳ **TIMEOUT**\nModerator: {interaction.user.mention}\nUser: {member.mention}\nDuration: {duration} minutes\nReason: {self.reason.value}"
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
                f"✅ **UNBAN**\nModerator: {interaction.user.mention}\nUser: {user}"
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

    @discord.ui.button(label="Kick", style=discord.ButtonStyle.secondary)
    async def kick_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(KickModal())

    @discord.ui.button(label="Timeout", style=discord.ButtonStyle.primary)
    async def timeout_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TimeoutModal())

    @discord.ui.button(label="Unban", style=discord.ButtonStyle.success)
    async def unban_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(UnbanModal())


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

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise ValueError("DISCORD_TOKEN not found in .env")

bot.run(TOKEN)