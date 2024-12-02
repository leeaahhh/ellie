# Rei

> A highly customizable, fast, and efficient Discord bot with last.fm integration, minimalistic embeds, and more.

## Features

- **Highly customizable:** Tailor the bot to suit your needs.
- **Fast and efficient:** Optimized for performance.
- **Last.fm integration:** Music-related features powered by last.fm.
- **Minimalistic embeds:** Clean and aesthetic embeds.
- **Jishaku for management:** Advanced management features.
- **Moderation commands:** Useful commands to manage your server.

## Running Rei

> **Note:** You must have Docker [installed](https://docs.docker.com/engine/install/) on your machine.

### Step 1: Configure the Bot

1. Rename `config.py.example` to `config.py`. This step is **critical** for the bot to run.

    - **Linux / MacOS:**

    ```sh
    mv config.py.example config.py
    ```

    - **Windows:** Enable "Show file extensions," click the file, press F2, and remove the `.example` extension.

2. Open `config.py` in your IDE (e.g., Visual Studio Code, Notepad++) and add your Discord bot token.

    ```py
    token: str = "your bot token"
    ```

3. Add your Discord User ID in the `owners` list. You can add multiple user IDs if you'd like other users to have access to management commands.

    ```py
    owners: list[int] = [userid1, userid2]
    ```

4. Add any API keys you need (for features like RemoveBG, Weather, Spotify).

    ```py
    class Authorization:
        class Spotify:
            client_id: str = "enter client id"
            client_secret: str = "enter client secret"

        removebg: str = "get api key from remove.bg"
        weather: str = "get api key from https://www.weatherapi.com/"
    ```

**Note:** Never share your `config.py` file as it contains sensitive information.

### Step 2: Run the Bot

Run the following command to start the bot:

- **Linux / MacOS:**

    ```sh
    sudo docker compose up -d --build
    ```

- **Windows:**

    ```sh
    docker compose up -d --build
    ```

This will start the bot inside a minimal Virtual Machine for safety.

### Step 3: Restarting the Bot

If you need to restart the bot after modifying the configuration or code, use the following commands to stop it:

- **Stop the bot and database:**

    ```sh
    sudo docker compose down
    ```

## Links

- **Website Source Code:** [GitHub Repository](https://github.com/leeaahhh/rei-websitev2)
- **Discord Server:** [Join the community](https://discord.gg/3mwJgnCrZw)
