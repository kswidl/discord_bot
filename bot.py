import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
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

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise ValueError("DISCORD_TOKEN not found in .env")

bot.run(TOKEN)