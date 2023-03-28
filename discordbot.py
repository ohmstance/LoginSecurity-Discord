from __future__ import annotations

import discord
from discord.ext import commands

import logging
import os
import asyncio
from dotenv import load_dotenv
from tabulate import tabulate

from logsec_discord import LogSec
from utils import BanFile, AdminFile, RegFile

load_dotenv()

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(
    intents=intents, 
    command_prefix=commands.when_mentioned_or(), 
    allowed_mentions=discord.AllowedMentions.none()
)

cog_loaded = False

class CustomCheckFailure(commands.CheckFailure):
    pass

### CHECKS AND EVENTS

@bot.event
async def on_ready():
    global cog_loaded
    if not cog_loaded:
        user_cog = UserCog()
        bot.help_command.cog = user_cog
        await bot.add_cog(user_cog)
        await bot.add_cog(AdminCog())
        await bot.add_cog(OwnerCog())
        cog_loaded = True

    print(f"Logged on as {bot.user}!")
        
# @bot.event
# async def on_message(message):
    ## print(f"Message from {message.author}: {message.content}")
    # if message.author == bot.user:
        # return
    # await bot.process_commands(message)
    
@bot.event    
async def on_command_error(ctx, error):
    if isinstance(error, CustomCheckFailure):
        await ctx.reply(error)
        return
    elif isinstance(error, commands.errors.CheckFailure):
        return
    elif isinstance(error, commands.errors.CommandNotFound):
        await ctx.reply(f"What do you mean by that? Seek /help.")
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.reply(f"You left out the `{error.param.name}` argument.")
        return
    raise error
    
@bot.check
async def globally_block_dms(ctx):
    if ctx.guild is None:
        await ctx.reply("Hey, don't DM me while I'm at work!")
    return ctx.guild is not None
    
@bot.check
async def block_banned_users(ctx):
    allowed = ctx.message.author.id not in BANNED or ctx.message.author.id == ctx.bot.application.owner.id
    if not allowed:
        await ctx.reply("Hm, who's that? It couldn't have been a BANNED user.")
    return allowed
    
def is_privileged():
    async def predicate(ctx):
        is_privileged = ctx.message.author.id in ADMINS or ctx.message.author.id == ctx.bot.application.owner.id
        if not is_privileged:
            raise CustomCheckFailure(
                f"Wha- hey! This command is off-limits! This incident will be reported."
            )
        return is_privileged
    return commands.check(predicate)
    
def registration_is_open():
    async def predicate(ctx):
        registrations_open = REG.is_open
        if not registrations_open:
            if ctx.message.author.id == ctx.bot.application.owner.id:
                raise CustomCheckFailure(
                    f"Registrations are closed. Why is it closed, <@{ctx.bot.application.owner.id}>?"
                )
            else:
                raise CustomCheckFailure("Registrations are closed. Why? I don't know. Ask my owner.")
        return registrations_open
    return commands.check(predicate)
    
def is_owner():
    async def predicate(ctx):
        is_owner = ctx.message.author.id == ctx.bot.application.owner.id
        if not is_owner:
            raise CustomCheckFailure(f"Who are you and why are you fiddling with an owner-only command!?")
        return is_owner
    return commands.check(predicate)
    
### COMMANDS

class UserCog(commands.Cog, name="User"):
    """Commands expected to be used by regular users.
    """
    
    @commands.hybrid_command(name='register')
    @registration_is_open()
    async def register(self, ctx, username = commands.param(description="Username to login to Minecraft server with")):
        """Registers Minecraft username to server
        
        Usage: register <username>
        """
    
        if not (3 <= len(username) <= 16) or ' ' in username:
            await ctx.reply("Username must be 3 to 16 characters long. Database constraints, not me.")
            return

        discord_id = str(ctx.message.author.id)
        result = LOGSEC.lookup_discord(discord_id)
        if result:
            await ctx.reply(
                f"You have already registered with username {result[0]['last_name']} on {result[0]['registration_date']}."
            )
            return

        result = LOGSEC.lookup_username(username)
        if result:
            await ctx.reply("How original -- the username is already taken. Register a different username.")
            return

        name = ctx.message.author.name
        disc = ctx.message.author.discriminator
        thread = await ctx.channel.create_thread(
            name=f"@{name}#{disc}",
            type=discord.ChannelType.private_thread,
            reason="LoginSecurity Minecraft server user registration.",
            auto_archive_duration=60,
            invitable=False
        )
        message = await ctx.reply(f"Hold on for a moment...")
        try:
            await thread.send(
                f"<@{discord_id}> \n"
                "Enter password which will be used to login to Minecraft server. \n"
                "Password must be 6 to 32 characters long, and not contain any spaces. \n"
                "Private thread will be deleted immediately after response. \n"
                "Enter 'c' to cancel registration.",
                allowed_mentions=discord.AllowedMentions.all() #Globally disabled for this bot by default
            )
            await message.edit(content=f"Head on to <#{thread.id}>. Link shows as #deleted-channel to others.")
            user_reply = await bot.wait_for(
                'message', timeout=300,
                check=lambda m: m.channel.id == thread.id and m.author.id == int(discord_id) 
            )
        except asyncio.TimeoutError:
            await message.edit(content="Shucks, timed-out waiting for your response. Cya.")
            return
        finally:
            await thread.delete()
            
        if user_reply.content == 'c':
            await message.edit(content="Changed your mind, huh? Alright.")
            return
            
        if not (6 <= len(user_reply.content) <= 32) or ' ' in user_reply.content:
            await message.edit(
                content=("Password must be 6 to 32 characters long, and not contain any spaces." 
                "I already told you that.")
            )
            return
            
        LOGSEC.register(discord_id, username, user_reply.content)
        
        await message.edit(content=f"Your username, {username}, has been registered.")

    @commands.hybrid_group(fallback='self', name='unregister', invoke_without_command=True)
    async def unregister(self, ctx):
        """Unregisters Minecraft username from server
        
        Usage: unregister [<subcommand>]
        """
    
        await self.unregister_user(ctx, str(ctx.message.author.id))

    @unregister.command(name='user')
    @is_privileged()
    async def unregister_user(self, ctx, discord_id = commands.param(description="Discord user ID or user mention")):
        """Unregisters a Discord user's Minecraft username from server
        
        Usage: unregister user <discord_id>
        """
        
        if '<@' in discord_id:
            discord_id = discord_id[2:-1]

        result = LOGSEC.lookup_discord(discord_id)
        if not result:
            await ctx.reply("User isn't registered.")
            return 
            
        user = await get_user(discord_id)
        if not user:
            await ctx.reply("Discord user not found.")
            return
        name = user.name
        disc = user.discriminator
        
        LOGSEC.unregister(discord_id)
        await ctx.reply(f"Bye-bye {result[0]['last_name']}, <@{discord_id}> unregistered.")
        
    @commands.hybrid_group(fallback='self', name='status', invoke_without_command=True)
    async def status(self, ctx):
        """Shows user status
        
        Usage: status [<subcommand>]
        """
    
        await self.status_user(ctx, str(ctx.message.author.id))
        
    @status.command(name='user')   
    @is_privileged()  
    async def status_user(self, ctx, discord_id = commands.param(description="Discord user ID or user mention")):
        """Shows information about user
        
        Usage: status user <discord_id>
        """
        
        reply = ""

        if '<@' in discord_id:
            discord_id = discord_id[2:-1]
        
        user = await get_user(discord_id)
        if not user:
            await ctx.reply("Discord user not found.")
            return
        
        reply += f"User: <@{discord_id}>\n"
        
        result = LOGSEC.lookup_discord(ctx.message.author.id)
        status = 'Banned' if discord_id in BANNED else 'Registered' if result else 'Unregistered'    
        reply += f"Status: {status}\n" 
        
        if status == 'Registered':
            reply += (
                f"Minecraft username: {result[0]['last_name']}\n" 
                f"Date registered: {result[0]['registration_date']}"
            )
        
        # Silence ping
        await ctx.reply(reply)
            
class AdminCog(commands.Cog, name="Administrative"):
    """Commands expected to be used by administrators.
    """

    @commands.hybrid_command(name='open')    
    @is_privileged()
    async def open(self, ctx):
        """Opens server for registration
        
        Usage: open
        """
    
        if REG.is_open:
            await ctx.reply("User registration is already open.")
        else:
            REG.open()
            await ctx.reply("User registration is now open.")

    @commands.hybrid_command(name='close')  
    @is_privileged()      
    async def close(self, ctx):
        """Closes server for registration
        
        Usage: close
        """
    
        if not REG.is_open:
            await ctx.reply("User registration is already closed.")
        else:
            REG.close()
            await ctx.reply("User registration is now closed.")
            
    @commands.hybrid_command(name='ban')  
    @is_privileged()   
    async def ban(self, ctx, discord_id = commands.param(description="Discord user ID or user mention")):
        """Bans a user from registration and removes their registration
        
        Usage: ban <discord_id>
        """
    
        if '<@' in discord_id:
            discord_id = discord_id[2:-1]
        
        user = await get_user(discord_id)
        if not user:
            await ctx.reply("Discord user not found.")
            return
                
        try:
            LOGSEC.unregister(discord_id)
        except KeyError:
            pass
        
        if discord_id in BANNED:
            await ctx.reply(f"<@{discord_id}> is already banned.")
        else:
            BANNED.ban(discord_id)
            await ctx.reply(f"<@{discord_id}> is banned from registering or playing.")
        
    @commands.hybrid_command(name='unban')   
    @is_privileged()  
    async def unban(self, ctx, discord_id = commands.param(description="Discord user ID or user mention")):
        """Unbans a user from registration
        
        Usage: unban <discord_id>
        """
    
        if '<@' in discord_id:
            discord_id = discord_id[2:-1]
        
        user = await get_user(discord_id)
        if not user:
            await ctx.reply("Discord user not found.")
            return
        
        if discord_id not in BANNED:
            await ctx.reply(f"<@{discord_id}> isn't banned to begin with.")
        else:
            BANNED.unban(discord_id)
            await ctx.reply(f"<@{discord_id}> is unbanned.")
            
    @commands.hybrid_command(name='banned')   
    @is_privileged()  
    async def banned(self, ctx):
        """Shows a list of banned users
        
        Usage: banned
        """
        
        banned = BANNED.banned
        
        if not banned:
            await ctx.reply("Nobody is banned.")
        else:
            banned = [f"{i}. <@{b}>" for i, b in enumerate(banned, 1)]
            await ctx.reply(f"Banned users:\n" + '\n'.join(banned))
            
    @commands.hybrid_command(name='registered')
    @is_privileged()
    async def registered(self, ctx):
        """Shows if registration is open and a list of registered users
        
        Usage: status registration
        """
    
        reply = f"User registration is {'open' if REG.is_open else 'closed'}.\n"

        registered = LOGSEC.registered
        if registered:
            registered = [list(row.values()) for row in registered]
            for i, row in enumerate(registered):
                discord_id = row[0]
                user = await get_user(discord_id)
                    
                if user:
                    name = user.name
                    disc = user.discriminator
                    registered[i][0] = f"@{name}#{disc}"
                else:
                    registered[i][0] = f"Error: <@{discord_id}>"
                    
            reply += f"```{tabulate(registered, headers=['Discord User', 'Minecraft Name', 'Date Registered'])}```\n"
        else:
            reply += "No registrations in database.\n"
            
        await ctx.reply(reply)
            
class OwnerCog(commands.Cog, name="Owner"):
    """Commands expected to be used by the owner of the bot.
    """
    
    @commands.hybrid_command(name='promote')  
    @is_owner()   
    async def promote(self, ctx, discord_id = commands.param(description="Discord user ID or user mention")):
        """Gives user privilege to bot's administrative commands
        
        Usage: promote <discord_id>
        """
    
        if '<@' in discord_id:
            discord_id = discord_id[2:-1]
        
        user = await get_user(discord_id)
        if not user:
            await ctx.reply("Discord user not found.")
            return

        if discord_id in ADMINS:
            await ctx.reply(f"<@{discord_id}> is already an admin.")
        else:
            ADMINS.promote(discord_id)
            await ctx.reply(f"<@{discord_id}> is promoted to admin.")
            
    @commands.hybrid_command(name='demote')  
    @is_owner()   
    async def demote(self, ctx, discord_id = commands.param(description="Discord user ID or user mention")):
        """Revokes user privilege to bot's administrative commands
        
        Usage: demote <discord_id>
        """
    
        if '<@' in discord_id:
            discord_id = discord_id[2:-1]
        
        user = await get_user(discord_id)
        if not user:
            await ctx.reply("Discord user not found!")
            return
 
        if discord_id not in ADMINS:
            await ctx.reply(f"<@{discord_id}> isn't an admin to begin with.")
        else:
            ADMINS.demote(discord_id)
            await ctx.reply(f"<@{discord_id}> is demoted.")
            
    @commands.hybrid_command(name='admins')   
    @is_privileged()  
    async def admins(self, ctx):
        """Shows a list of users with access to bot's administrative commands
        
        Usage: <banned>
        """
        
        admins = ADMINS.admins
        
        if not admins:
            await ctx.reply("Nobody has administrator privileges.")
        else:
            admins = [f"{i}. <@{b}>" for i, b in enumerate(admins, 1)]
            await ctx.reply(f"Administrators:\n" + '\n'.join(admins))
    
    @commands.command(name='sync') 
    @is_owner()      
    async def sync(self, ctx):
        """Syncs slash command tree to current guild
        
        Usage: sync
        """
        bot.tree.copy_global_to(guild=ctx.message.guild)
        await bot.tree.sync(guild=ctx.message.guild)
            
### UTILS

async def get_user(discord_id):
    user = bot.get_user(discord_id)
    if user is None:
        try:
            user = await bot.fetch_user(discord_id)
        except:
            pass
    return user
    
if __name__ == "__main__":
    BANNED = BanFile("./conf/banlist.txt")
    ADMINS = AdminFile("./conf/adminlist.txt")
    REG = RegFile("./conf/server.closed")

    LOGSEC = LogSec(
        os.getenv('DB_USERNAME'), 
        os.getenv('DB_PASSWORD'), 
        os.getenv('DB_HOST'), 
        os.getenv('DB_PORT'), 
        os.getenv('DB_NAME')
    )
    
    handler = logging.FileHandler(filename="./conf/discord.log", encoding="utf-8", mode="w")
    
    # Bot does not stop with default SIGTERM handling for some reason.
    # Docker will wait until timeout until sending SIGINT -- how about we do it immediately.
    import signal
    signal.signal(signal.SIGTERM, lambda x, y: signal.raise_signal(signal.SIGINT))

    bot.run(os.getenv('DISCORD_TOKEN'), log_handler=handler, log_level=logging.DEBUG)