import asyncio
import hetzner

hetzner = hetzner.Hetzner()

asyncio.run(hetzner.clean_old_snapshots())
