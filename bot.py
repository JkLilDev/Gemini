import os
import discord
from discord.ext import commands
import google.generativeai as genai
# from dotenv import load_dotenv # REMOVE or COMMENT OUT this line for Azure deployment

# --- Configuration ---
# Azure App Service will provide these as environment variables
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not DISCORD_BOT_TOKEN:
    # This will now check if the environment variable is set by Azure
    # If running locally, you'll still need your .env file
    raise ValueError("DISCORD_BOT_TOKEN not found in environment variables.")
if not GEMINI_API_KEY:
    # This will now check if the environment variable is set by Azure
    raise ValueError("GEMINI_API_KEY not found in environment variables.")

# Configure the Gemini API
genai.configure(api_key=GEMINI_API_KEY)

# Initialize the Gemini model
model = genai.GenerativeModel('gemini-pro')

# --- Discord Bot Setup ---
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Dictionary to store conversation history for each user/channel
conversation_history = {}

# --- Helper function for interacting with Gemini API ---
async def generate_gemini_response(user_id, message_content):
    global conversation_history

    if user_id not in conversation_history:
        conversation_history[user_id] = model.start_chat(history=[])

    chat = conversation_history[user_id]

    try:
        response = await chat.send_message_async(message_content)
        return response.text
    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        return "An error occurred while communicating with Gemini. Please try again later."

# --- Discord Bot Events ---
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s).")
    except Exception as e:
        print(f"Error syncing commands: {e}")

@bot.command()
async def ping(ctx):
    """Responds with 'Pong!' to test bot responsiveness."""
    await ctx.send("Pong!")

@bot.tree.command(name="test", description="Tests if the bot is responding with a 'Hello!'")
async def test_command(interaction: discord.Interaction):
    """Responds with 'Hello from your bot!' as a slash command."""
    await interaction.response.send_message("Hello from your bot!", ephemeral=True)


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel):
        async with message.channel.typing():
            text_content = message.content.replace(f'<@{bot.user.id}>', '').strip()
            if not text_content:
                await message.channel.send("Hey there! How can I help you today?")
                return
            user_context_id = message.author.id
            response_text = await generate_gemini_response(user_context_id, text_content)
            await message.channel.send(response_text)

    await bot.process_commands(message)

@bot.tree.command(name="forget", description="Clears the bot's memory for your current conversation.")
async def forget(interaction: discord.Interaction):
    user_context_id = interaction.user.id
    if user_context_id in conversation_history:
        del conversation_history[user_context_id]
        await interaction.response.send_message("My memory of our conversation has been cleared!", ephemeral=True)
    else:
        await interaction.response.send_message("I don't have any memory of our conversation to clear.", ephemeral=True)

# --- Run the Bot ---
if __name__ == '__main__':
    bot.run(DISCORD_BOT_TOKEN)

