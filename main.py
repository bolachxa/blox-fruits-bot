import os
from threading import Thread
import aiohttp
import discord
from discord.ext import commands, tasks
from flask import Flask

# =========================================================
# WEBSERVER KEEP-ALIVE (PARA NUVEM / RENDER / KEEPER)
# =========================================================

app = Flask("")


@app.route("/")
def home():
  return "Bot de Estoque Blox Fruits Online 24/7!"


def run_flask():
  # Porta padrão 8080 exigida por serviços PaaS como Render/Koyeb
  app.run(host="0.0.0.0", port=8080)


def keep_alive():
  t = Thread(target=run_flask)
  t.daemon = True
  t.start()


# =========================================================
# CONFIGURAÇÕES E CRÉDENCIAIS VIA VARIÁVEIS DE AMBIENTE
# =========================================================

# Buscamos as chaves do ambiente da hospedagem (fallback para string se for rodar local)
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
PARSE_API_KEY = os.getenv("PARSE_API_KEY", "")

# ID do Canal do Discord (certifique-se de que é um número inteiro)
CHANNEL_ID = int(os.getenv("CHANNEL_ID", 1553449601535582329))

API_URL = (
    "https://api.parse.bot/scraper/e534d388-6640-4c19-b9b6-b2ba12930793/get_stock"
)

# =========================================================
# DISCORD & ESTADOS
# =========================================================

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# Memória para acompanhar alterações independentes dos estoques
ultimo_normal = None
ultimo_mirage = None

# =========================================================
# CONSULTAR API
# =========================================================


async def consultar_estoque():
  headers = {"X-API-Key": PARSE_API_KEY, "Accept": "application/json"}

  try:
    async with aiohttp.ClientSession() as session:
      async with session.get(
          API_URL, headers=headers, timeout=aiohttp.ClientTimeout(total=30)
      ) as resposta:
        print(f"STATUS DA API: {resposta.status}")

        if resposta.status != 200:
          print(await resposta.text())
          return None

        dados = await resposta.json()

        if dados.get("status") != "success":
          print("❌ API não retornou success.")
          return None

        return dados.get("data")

  except Exception as erro:
    print(f"❌ Erro ao consultar API: {erro}")
    return None


# =========================================================
# EXTRAIR ASSINATURAS DOS ESTOQUES (4H vs 2H)
# =========================================================


def extrair_assinatura(lista_frutas):
  """Cria uma tupla imutável ordenada para comparação do estoque."""
  if not lista_frutas:
    return ()

  itens = [
      (
          f.get("name"),
          f.get("price_beli"),
          f.get("price_robux"),
      )
      for f in lista_frutas
  ]
  itens.sort()
  return tuple(itens)


# =========================================================
# FORMATAR FRUTAS
# =========================================================


def formatar_frutas(frutas):
  if not frutas:
    return "Nenhuma fruta disponível no momento.\n\n"

  texto = ""
  for fruta in frutas:
    nome = fruta.get("name", "Desconhecida")
    beli = fruta.get("price_beli", 0)
    robux = fruta.get("price_robux", 0)

    texto += f"🍎 **{nome}**\n💰 {beli:,} Beli\n💎 {robux} Robux\n\n"

  return texto


# =========================================================
# CRIAR MENSAGEM
# =========================================================


def criar_mensagem(estoque, mudou_normal=False, mudou_mirage=False):
  normal = estoque.get("normal", [])
  mirage = estoque.get("mirage", [])

  if mudou_normal and mudou_mirage:
    titulo = "🚨 **NOVO ESTOQUE GERAL (NORMAL + MIRAGE)!** 🚨"
  elif mudou_normal:
    titulo = "🔄 **NOVO REESTOQUE NORMAL (4H)!** 🔄"
  elif mudou_mirage:
    titulo = "🌙 **NOVO REESTOQUE MIRAGE (2H)!** 🌙"
  else:
    titulo = "🍏 **BLOX FRUITS STOCK ATUAL** 🍏"

  return (
      f"{titulo}\n\n"
      "🟢 **NORMAL STOCK (4 em 4h)**\n"
      "━━━━━━━━━━━━━━━━━━\n"
      f"{formatar_frutas(normal)}"
      "🟣 **MIRAGE STOCK (2 em 2h)**\n"
      "━━━━━━━━━━━━━━━━━━\n"
      f"{formatar_frutas(mirage)}"
  )


# =========================================================
# VERIFICAR E ENVIAR
# =========================================================


async def verificar_e_enviar():
  global ultimo_normal, ultimo_mirage

  estoque = await consultar_estoque()
  if estoque is None:
    print("❌ Não foi possível obter o estoque.")
    return

  canal = bot.get_channel(CHANNEL_ID)
  if canal is None:
    print("❌ Canal não encontrado.")
    return

  normal_atual = extrair_assinatura(estoque.get("normal", []))
  mirage_atual = extrair_assinatura(estoque.get("mirage", []))

  # 1ª Execução (Inicialização)
  if ultimo_normal is None and ultimo_mirage is None:
    ultimo_normal = normal_atual
    ultimo_mirage = mirage_atual

    mensagem = criar_mensagem(
        estoque, mudou_normal=False, mudou_mirage=False
    )
    await canal.send(mensagem)
    print("✅ Estoque inicial carregado e enviado no Discord.")
    return

  # Verificação de Mutações
  mudou_normal = normal_atual != ultimo_normal
  mudou_mirage = mirage_atual != ultimo_mirage

  if not mudou_normal and not mudou_mirage:
    print("⏳ Estoque inalterado.")
    return

  # Atualiza os estados armazenados
  ultimo_normal = normal_atual
  ultimo_mirage = mirage_atual

  # Envia o alerta customizado indicando o que mudou
  mensagem = criar_mensagem(
      estoque, mudou_normal=mudou_normal, mudou_mirage=mudou_mirage
  )
  await canal.send(mensagem)
  print(
      f"🚨 REESTOQUE DETECTADO! (Normal: {mudou_normal} | Mirage:"
      f" {mudou_mirage})"
  )


# =========================================================
# LOOP AUTOMÁTICO (Checa a API a cada 2 minutos)
# =========================================================


@tasks.loop(minutes=2)
async def verificar_estoque_loop():
  print("🔎 Verificando alteração de estoque na API...")
  await verificar_e_enviar()


# =========================================================
# COMANDOS & EVENTOS
# =========================================================


@bot.command()
async def stock(ctx):
  estoque = await consultar_estoque()
  if estoque is None:
    await ctx.send("❌ Não consegui consultar a API do estoque.")
    return

  mensagem = criar_mensagem(
      estoque, mudou_normal=False, mudou_mirage=False
  )
  await ctx.send(mensagem)


@bot.event
async def on_ready():
  print("======================================")
  print("🤖 BOT DE ESTOQUE ONLINE")
  print(f"👤 Logado como: {bot.user}")
  print("======================================")

  # Dispara a consulta inicial na entrada do Bot
  await verificar_e_enviar()

  if not verificar_estoque_loop.is_running():
    verificar_estoque_loop.start()
    print("🔄 Monitoramento automático ativado (intervalo: 2 min).")


# =========================================================
# INICIALIZAÇÃO
# =========================================================

if __name__ == "__main__":
  # Inicia o servidor HTTP para manter a instância acordada na nuvem
  keep_alive()

  # Roda o bot
  bot.run(DISCORD_TOKEN)