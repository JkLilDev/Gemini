import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import google.generativeai as genai
from flask import Flask
import threading
import asyncio

# Load environment variables
load_dotenv()

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-pro')

# Initialize Discord bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

# Store conversation history per channel
chat_history = {}

# Flask app for Azure health check
app = Flask(__name__)

@app.route('/')
def health_check():
    return "Bot is running", 200

# Gemini API interaction
async def get_gemini_response(message_content, channel_id):
    try:
        # Initialize history for the channel if not exists
        if channel_id not in chat_history:
            chat_history[channel_id] = [
                {"role": "user", "parts": ["Hi!"]},
                {"role": "model", "parts": ["Hello! I am your Discord AI bot powered by Gemini."]}
            ]

        # Add user message to history
        chat_history[channel_id].append({"role": "user", "parts": [message_content]})

        # Generate response
        response = model.generate_content(
            message_content,
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,
                max_output_tokens=500
            )
        )

        # Extract response text
        response_text = response.text

        # Add bot response to history
        chat_history[channel_id].append({"role": "model", "parts": [response_text]})
        
        # Limit history to last 10 messages to manage context
        if len(chat_history[channel_id]) > 10:
            chat_history[channel_id] = chat_history[channel_id][-10:]

        return response_text
    except Exception as e:
        return f"Error: {str(e)}"

# Bot event: On ready
@bot.event
async def on_ready():
    print(f'Bot logged in as {bot.user}')

# Bot command: Summarize text
@bot.command()
async def summarize(ctx, *, text):
    response = await get_gemini_response(f"Summarize: {text}", ctx.channel.id)
    await ctx.send(response)

# Bot command: Clear conversation history
@bot.command()
async def forget(ctx):
    if ctx.channel.id in chat_history:
        del chat_history[ctx.channel.id]
    await ctx.send("Conversation history cleared!")

# Bot event: Process messages
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # Respond only if bot is mentioned or in DM
    if bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel):
        response = await get_gemini_response(message.content, message.channel.id)
        await message.channel.send(response)

    await bot.process_commands(message)

# Run Flask app in a separate thread
def run_flask():
    app.run(host='0.0.0.0', port=8000)

# Run both Flask and Discord bot
def main():
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()
    
    bot.run(os.getenv("DISCORD_TOKEN"))

if __name__ == "__main__":
    main()