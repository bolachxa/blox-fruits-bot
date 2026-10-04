import os
import threading
import aiohttp
from flask import Flask
import discord
from discord.ext import commands, tasks

# ---------------------------------------------------------
# 1. Configuração do Flask (para manter o Render acordado)
# ---------------------------------------------------------
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot Blox Fruits está online!"

def run_flask():
    # O Render atribui dinamicamente uma porta, ou usa 8080 por padrão
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# ---------------------------------------------------------
# 2. Configuração do Bot do Discord
# ---------------------------------------------------------
intents = discord.Intents.default()
intents.message_content = True  # Permite ler comandos no chat

bot = commands.Bot(command_prefix="!", intents=intents)

# Variáveis de ambiente
DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")
PARSE_API_KEY = os.environ.get("PARSE_API_KEY")
CHANNEL_ID = os.environ.get("CHANNEL_ID")

# ---------------------------------------------------------
# 3. Função para buscar o estoque na Parse API
# ---------------------------------------------------------
async def fetch_stock():
    url = "https://parseapi.back4app.com/classes/BloxFruits"  # Ajuste o endpoint se necessário
    headers = {
        "X-Parse-Application-Id": PARSE_API_KEY,
        "X-Parse-REST-API-Key": PARSE_API_KEY
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                return None
        except Exception as e:
            print(f"Erro ao buscar estoque: {e}")
            return None

# ---------------------------------------------------------
# 4. Comandos e Eventos do Bot
# ---------------------------------------------------------
@bot.event
async def on_ready():
    print(f"Bot conectado com sucesso como: {bot.user.name}")
    # Inicia a tarefa em segundo plano para monitorar estoque se necessário
    if not check_stock_loop.is_running():
        check_stock_loop.start()

@bot.command(name="estoque")
async def estoque(ctx):
    await ctx.send("🔍 Verificando o estoque atual do Blox Fruits...")
    stock_data = await fetch_stock()
    
    if stock_data:
        # Formate a resposta conforme a estrutura retornada da sua Parse API
        await ctx.send("✅ Estoque atualizado com sucesso!")
    else:
        await ctx.send("❌ Não foi possível obter o estoque no momento.")

@tasks.loop(minutes=30)
async def check_stock_loop():
    if CHANNEL_ID:
        try:
            channel = bot.get_channel(int(CHANNEL_ID))
            if channel:
                # Lógica opcional para enviar avisos automáticos de estoque
                pass
        except Exception as e:
            print(f"Erro na tarefa de estoque: {e}")

# ---------------------------------------------------------
# 5. Execução do Servidor e do Bot
# ---------------------------------------------------------
if __name__ == "__main__":
    # Inicia o Flask numa thread separada
    threading.Thread(target=run_flask, daemon=True).start()
    
    # Inicia o bot no Discord
    if DISCORD_TOKEN:
        bot.run(DISCORD_TOKEN)
    else:
        print("ERRO: A variável DISCORD_TOKEN não foi configurada!")
