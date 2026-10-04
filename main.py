import os
import threading
import aiohttp
from flask import Flask
import discord
from discord.ext import commands, tasks

# ---------------------------------------------------------
# 1. Servidor Web Flask (para manter o Render ativo 24/7)
# ---------------------------------------------------------
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot Blox Fruits está online e operacional!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# ---------------------------------------------------------
# 2. Configurações de Variáveis e Intents
# ---------------------------------------------------------
DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")
PARSE_APP_ID = os.environ.get("PARSE_APP_ID") or os.environ.get("PARSE_API_KEY")
PARSE_REST_KEY = os.environ.get("PARSE_REST_KEY") or os.environ.get("PARSE_API_KEY")
CHANNEL_ID = os.environ.get("CHANNEL_ID")

intents = discord.Intents.default()
intents.message_content = True  # Permite ler comandos no chat

bot = commands.Bot(command_prefix="!", intents=intents)

# ---------------------------------------------------------
# 3. Consulta à Parse API / Back4App
# ---------------------------------------------------------
async def fetch_stock():
    # URL padrão da classe no Parse/Back4App
    url = "https://parseapi.back4app.com/classes/BloxFruits"
    
    headers = {
        "X-Parse-Application-Id": PARSE_APP_ID if PARSE_APP_ID else "",
        "X-Parse-REST-API-Key": PARSE_REST_KEY if PARSE_REST_KEY else "",
        "Content-Type": "application/json"
    }
    
    print(f"--> [DEBUG] Consultando Parse API... AppID configurado: {'Sim' if PARSE_APP_ID else 'Não'}")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers, timeout=10) as response:
                status = response.status
                texto = await response.text()
                print(f"--> [PARSE STATUS HTTP]: {status}")
                print(f"--> [PARSE RESPOSTA]: {texto}")
                
                if status == 200:
                    data = await response.json()
                    return data.get("results", [])
                else:
                    print(f"--> [ERRO PARSE HTTP {status}]: {texto}")
                    return None
        except Exception as e:
            print(f"--> [ERRO CONEXAO PARSE]: {e}")
            return None

# ---------------------------------------------------------
# 4. Eventos e Comandos do Bot
# ---------------------------------------------------------
@bot.event
async def on_ready():
    print(f"==========================================")
    print(f"Bot conectado com sucesso como: {bot.user.name}")
    print(f"==========================================")

@bot.command(name="estoque")
async def estoque(ctx):
    await ctx.send("🔍 *Consultando estoque no banco de dados...*")
    
    if not PARSE_APP_ID or not PARSE_REST_KEY:
        await ctx.send("⚠️ As chaves da Parse API (`PARSE_APP_ID` / `PARSE_REST_KEY`) não estão configuradas no Render.")
        return

    items = await fetch_stock()
    
    if items is not None:
        if len(items) == 0:
            await ctx.send("📦 Nenhum registro de fruta encontrado no banco de dados.")
            return

        embed = discord.Embed(
            title="🍎 Estoque Blox Fruits",
            description="Status das frutas no banco de dados:",
            color=discord.Color.green()
        )

        for item in items:
            # Tenta identificar o nome e disponibilidade em campos comuns do Parse
            nome = item.get("name") or item.get("fruit") or item.get("nome") or "Fruta Desconhecida"
            disponivel = item.get("inStock") or item.get("available") or item.get("emEstoque")
            
            if disponivel is True or str(disponivel).lower() in ["sim", "true", "1"]:
                status = "✅ Em estoque"
            else:
                status = "❌ Esgotado"

            embed.add_field(name=nome, value=status, inline=True)

        embed.set_footer(text="Atualizado via Parse API / Back4App")
        await ctx.send(embed=embed)
    else:
        await ctx.send("❌ Erro ao comunicar com a Parse API. Verifique os Logs do Render para os detalhes do status HTTP.")

# ---------------------------------------------------------
# 5. Execução do Sistema
# ---------------------------------------------------------
if __name__ == "__main__":
    # Inicia o servidor Flask numa thread separada
    threading.Thread(target=run_flask, daemon=True).start()
    
    # Inicia o bot
    if DISCORD_TOKEN:
        bot.run(DISCORD_TOKEN)
    else:
        print("ERRO CRÍTICO: DISCORD_TOKEN não encontrado nas variáveis de ambiente do Render!")
