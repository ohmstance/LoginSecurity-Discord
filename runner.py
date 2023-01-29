import logsec_discord

if __name__ == "__main__":
    username = "echotin-test"
    password = "minecraft-echotin"
    host = "munna"
    port = 25564
    database = "minecraft-test"
    import logsec_discord as ld
    ctx = ld.LogSec(username, password, host, port, database)