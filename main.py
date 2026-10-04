import os
import threading
import aiohttp
from flask import Flask
import discord
from discord.ext import commands, tasks

# ---------------------------------------------------------
# 1. Servidor Flask (para manter o Render acordado 24/7)
# ---------------------------------------------------------
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot Blox Fruits está online e ativo!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# ---------------------------------------------------------
# 2. Configurações e Variáveis de Ambiente
# ---------------------------------------------------------
DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")
PARSE_API_KEY = os.environ.get("PARSE_API_KEY")
CHANNEL_ID = os.environ.get("CHANNEL_ID")

intents = discord.Intents.default()
intents.message_content = True  # Necessário para ler o !estoque

bot = commands.Bot(command_prefix="!", intents=intents)

# ---------------------------------------------------------
# 3. Consulta à Parse API / Back4App
# ---------------------------------------------------------
async def fetch_stock():
    # URL da classe no Parse/Back4App
    url = "https://parseapi.back4app.com/classes/BloxFruits"
    
    headers = {
        "X-Parse-Application-Id": PARSE_API_KEY,
        "X-Parse-REST-API-Key": PARSE_API_KEY,
        "Content-Type": "application/json"
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers) as response:
                print(f"[Parse API] Status HTTP: {response.status}")
                if response.status == 200:
                    data = await response.json()
                    return data.get("results", [])
                else:
                    erro = await response.text()
                    print(f"[Parse API Error]: {erro}")
                    return None
        except Exception as e:
            print(f"[Erro de Conexão Parse]: {e}")
            return None

# ---------------------------------------------------------
# 4. Comandos e Eventos do Bot
# ---------------------------------------------------------
@bot.event
async def on_ready():
    print(f"==========================================")
    print(f"Bot conectado com sucesso como: {bot.user.name}")
    print(f"==========================================")

@bot.command(name="estoque")
async def estoque(ctx):
    await ctx.send("🔍 *Buscando estoque atualizado no banco de dados...*")
    
    if not PARSE_API_KEY:
        await ctx.send("⚠️ A chave `PARSE_API_KEY` não está configurada nas Environment Variables do Render.")
        return

    items = await fetch_stock()
    
    if items is not None:
        if len(items) == 0:
            await ctx.send("📦 Nenhum registro de fruta encontrado no banco de dados.")
            return

        embed = discord.Embed(
            title="🍎 Estoque Blox Fruits",
            description="Frutas disponíveis no momento:",
            color=discord.Color.green()
        )

        for item in items:
            # Tenta pegar pelos nomes comuns de colunas no Parse
            nome = item.get("name") or item.get("fruit") or item.get("nome") or "Fruta Desconhecida"
            disponivel = item.get("inStock") or item.get("available") or item.get("emEstoque")
            
            if disponivel is True or str(disponivel).lower() in ["sim", "true", "1"]:
                status = "✅ Em estoque"
            else:
                status = "❌ Esgotado"

            embed.add_field(name=nome, value=status, inline=True)

        embed.set_footer(text="Atualizado via Parse API")
        await ctx.send(embed=embed)
    else:
        await ctx.send("❌ Não foi possível conectar ao banco de dados Parse. Verifique os logs do Render.")

# ---------------------------------------------------------
# 5. Inicialização
# ---------------------------------------------------------
if __name__ == "__main__":
    # Inicia o servidor web do Flask numa thread paralela
    threading.Thread(target=run_flask, daemon=True).start()
    
    # Inicia o bot
    if DISCORD_TOKEN:
        bot.run(DISCORD_TOKEN)
    else:
        print("ERRO CRÍTICO: DISCORD_TOKEN não encontrado nas variáveis de ambiente!")
