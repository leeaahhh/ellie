 # Rei Ayanami 🤖

<div align=center>
<img src="rei-pfp.png" width="200" height="200" />

![GitHub repo size](https://img.shields.io/github/repo-size/NERVCorporation/rei?style=for-the-badge)
![GitHub top language](https://img.shields.io/github/languages/top/NERVCorporation/rei?style=for-the-badge)
 ![License](https://camo.githubusercontent.com/d9b03b92063a55cc4391841c05463a86af0d39cac0536757c6602eafb1cbafaa/68747470733a2f2f696d672e736869656c64732e696f2f6769746875622f6c6963656e73652f7361746e61696e672f617374726f2d70617065723f636f6c6f723d253233324633373431267374796c653d666f722d7468652d6261646765)

 [![Discord Server](https://discordapp.com/api/guilds/1206246451840294942/widget.png?style=banner2)](https://discord.gg/3mwJgnCrZw)

[__**Join my Discord server for updates!**__](https://discord.gg/3mwJgnCrZw)
</div>

 ## 🔥Features

 - [x] highly customizable
 - [x] fast and efficient
 - [x] last.fm integration
 - [x] minimalistic embeds
 - [x] jishaku for management
 - [x] useful commands for moderation

 *You can add your own commands with minimal python knowledge if you understand the structure of Rei easily!*

 ## 👩‍💻 Running Rei Ayanami

> **_Note!_** For `Docker` commands we must have it [installed](https://docs.docker.com/engine/install/) in your machine.

<div align=center>
Start by doing your configuration file by renaming "config.py.example" to "config.py". This is a ***critical*** step as without this, the bot won't start up at all.

You must run these commands in the root of Rei.

```SH
# Linux (All Distibutions) / MacOS
mv config.py.example config.py.example

# Windows (Make sure you have the "Show file extensions" option enabled in your settings!)
Select the file by clicking on it and press F2 and remove the ".example".
```

Start editing the configuration file, "**config.py**", by opening it in a IDE of your choice (Visual Studio Code, Notepad++, etc...). Assuming you know how to get a bot token, make sure you have all the intents enabled. Change the token section to your Discord bot token.

```py
token: str = "bot token"
```

After doing so, get your Discord User ID and paste it in this section. You can put multiple User IDs if you want one of your alt accounts or friend to have access to Jishaku commands. 

__**Being on the owners list can allow the person to get your Discord bot token and to do even more potential damage to your server or personal computer depending on where you're hosting it!**__

```py
owners: list[int] = [userid1,userid2]
```

You can add if you want other API keys for certain commands like RemoveBG, Weather and Spotify.</div>

```py
class Authorization:
    class Spotify:
        client_id: str = "enter client id"
        client_secret: str = "enter client secret"

    removebg: str = "get api key from remove.bg"
    weather: str = "get api key from https://www.weatherapi.com/"
```
<div align=center>
 Now you're done with the configuration file. Make sure to never share this to anyone, no matter who it is. It is strictly confidential.

 Now you need to run the bot, it works with a simple command!

 ```sh
 # Run this in the root directory of Rei.
 # This will create a minimal Virtual Machine to run the bot safely do prevent damage on other important files or directories of your computer.

# Linux / MacOS
 sudo docker compose up -d --build

 # Windows
 docker compose up -d --build
 ```

If you ever need to restart the bot because you changed things in the source code or in the configuration file, you can run those two commands to stop the bot and the database.

```sh
# Linux / MacOS
sudo docker rm rei-bot
sudo docker rm rei-db

# Windows
docker rm rei-bot
docker rm rei-db
```

That's all you need to know for running Rei Ayanami on your personal computer or server! Enjoy!
</div>




