import json
import asyncio
import discord
import hetzner

with open("config.json", encoding="utf-8") as f:
    config = json.load(f)
    webhook_url = config["webhook_url"]

hetzner = hetzner.Hetzner()

asyncio.run(hetzner.delete())


webhook = discord.SyncWebhook.from_url(webhook_url)
webhook.send("Server destroyed 🌑", username="Server On Demand")
