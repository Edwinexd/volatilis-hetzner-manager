import json
import asyncio
import discord

import hetzner

start_stamp = int(discord.utils.utcnow().timestamp())

with open("config.json", encoding="utf-8") as f:
    config = json.load(f)
    webhook_url = config["webhook_url"]

hetzner = hetzner.Hetzner()

asyncio.run(hetzner.create())

webhook = discord.SyncWebhook.from_url(webhook_url)
webhook.send(f"Server created ☀️ Billed since <t:{start_stamp}:F> | <t:{start_stamp}:R>", username="Server On Demand")
 