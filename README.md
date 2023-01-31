# LoginSecurity-Discord

A Discord bot that handles user registration for offline Minecraft servers that uses the LoginSecurity plugin.

## Setup
- Use MySQL as database for LoginSecurity.
- Point the bot at MySQL using the same database as LoginSecurity.
- Invite bot to Discord guild -- allow it to read and send messages, and manage threads.
- Use '@botname sync' to sync slash commands to guild.
- Block use of /register command in Minecraft server.
- See '@botname help' for available bot commands.

## Environment variables
- DB_USERNAME: 	Username of database account (string)
- DB_PASSWORD: 	Password of database account (string)
- DB_NAME:		Name of database (string)
- DB_HOST: 		IP address or hostname of MySQL server (string)
- DB_PORT:		Port number of MySQL server (integer)
- DISCORD_TOKEN:	Discord bot token (string)

## Help command output
```
Administrative:
  ban        Bans a user from registration and removes their registration
  banned     Shows a list of banned users
  close      Closes server for registration
  open       Opens server for registration
  registered Shows if registration is open and a list of registered users
  unban      Unbans a user from registration
Owner:
  admins     Shows a list of users with access to bot's administrative commands
  demote     Revokes user privilege to bot's administrative commands
  promote    Gives user privilege to bot's administrative commands
  sync       Syncs slash command tree to current guild
User:
  help       Shows this message
  register   Registers Minecraft username to server
  status     Shows user status
  unregister Unregisters Minecraft username from server

Type @Log help command for more info on a command.
You can also type @Log help category for more info on a category.
```