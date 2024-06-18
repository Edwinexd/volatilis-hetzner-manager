import datetime
import json
import asyncio

from hcloud import Client
from hcloud.server_types.domain import ServerType
from hcloud.servers.domain import ServerCreatePublicNetwork
from hcloud.networks.domain import Network
from hcloud.locations.client import Location
from hcloud.images.domain import Image 
from hcloud.ssh_keys.client import BoundSSHKey

class ServerNotPoweredOff(Exception):
    ...

class Hetzner():

    def __init__(self) -> None:
        with open("config.json", encoding="utf-8") as f:
            config = json.load(f)
            api_token = config["hetzner_api_token"]

        self.client = Client(token=api_token)
        self.SERVER_NAME = "volatilis-rebooted"
        self.INITIAL_SERVER_TYPE = "cpx11"
        # CPX31 = 4 vCPU, 8 GB RAM, 160 GB SSD # we usually use this one
        # CCX11 = 2 dCPU, 8 GB RAM, 80 GB SSD (intel) # BAD, depreceted
        # CCX22 = 4 dCPU, 16 GB RAM, 160 GB SSD (amd) really performant but expensive, depreceted
        # CCX13 = 2 dCPU, 8 GB RAM, 80 GB SSD (amd) # Really good for the price, cheaper than cpx31
        self.TARGET_SERVER_TYPE = "ccx13"

    async def create(self) -> int:
        # Load api token from config.json
        with open("config.json", encoding="utf-8") as f:
            config = json.load(f)
            snapshot_image_id = config["snapshot_image_id"]

        image = self.client.images.get_by_id(snapshot_image_id)
        ssh_keys = self.client.ssh_keys.get_all()
        location = Location(name="hel1")
        firewall = self.client.firewalls.get_by_name("Winrdp")
        ipv4 = self.client.primary_ips.get_by_name("volrebooted-ipv4")
        ipv6 = self.client.primary_ips.get_by_name("volrebooted-ipv6")

        response = self.client.servers.create(self.SERVER_NAME, ServerType(name=self.INITIAL_SERVER_TYPE), image, ssh_keys=ssh_keys, firewalls=[firewall], location=location, public_net=ServerCreatePublicNetwork(ipv4=ipv4, ipv6=ipv6), start_after_create=False)
        image.update(description="OLD: " + image.data_model.description)

        # Wait until the server is created
        while True:
            await asyncio.sleep(2)
            server = self.client.servers.get_by_id(response.server.id)
            if server.status == "off":
                break
        
        # Wait 10 seconds for hetzner to update their internal status
        await asyncio.sleep(10)

        self.client.servers.change_type(response.server, ServerType(name=self.TARGET_SERVER_TYPE), upgrade_disk=False)

        # Wait until the server is updated
        while True:
            await asyncio.sleep(2)
            server = self.client.servers.get_by_id(response.server.id)
            if server.status == "off":
                self.client.servers.power_on(response.server)
                break
            elif server.status == "running":
                break
        

        return response.server.id
    
    async def delete(self) -> int:
        server = self.client.servers.get_by_name(self.SERVER_NAME)

        if server.status != "off":
            raise ServerNotPoweredOff("Server must be powered off before performing this action.")

        snapshot = self.client.servers.create_image(server, description=f"{server.name};{datetime.datetime.now().isoformat()}")

        # Wait for snapshot to finish, done by checking all snapshots and as long as any is not available, wait 10 seconds and check again.
        while True:
            images = self.client.images.get_all(type="snapshot")
            if any(image.status != "available" for image in images):
                await asyncio.sleep(2)
                continue

            break

        print(f"Snapshot created: {snapshot.image.id} - {snapshot.image.data_model.description}")
        # Store snapshot image id in config.json
        with open("config.json", encoding="utf-8") as f:
            config = json.load(f)
        with open("config.json", "w", encoding="utf-8") as f:
            config["snapshot_image_id"] = snapshot.image.id
            json.dump(config, f, indent=4)

        self.client.servers.delete(server)

        return snapshot.image.id
    
    async def clean_old_snapshots(self) -> None:
        images = self.client.images.get_all(type="snapshot")
        # Sort images by creation date (by parsing the data_model.description)
        # Remove all but the 2 newest images
        images = sorted(images, key=lambda image: datetime.datetime.fromisoformat(image.data_model.description.split(";")[1]), reverse=True)
        images = images[2:]
        for image in images:
            print(image.data_model.description)
            self.client.images.delete(image)
