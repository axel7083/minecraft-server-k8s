# Info

This project aims to manage a Minecraft server compatible for Java and bedrock in Kubernetes. 

# Features
This project is divided in two components:

## The Minecraft java server

The Minecraft Java server is using [GeyserMC](https://github.com/GeyserMC/Geyser) as a Spigot plugin to allow Bedrock player to join the server.

## The server manager

The server manager is used to turn on or off the server. 
The server will be turned off after a certain amount of time without any player on the server.

The reason behind the server manager is that the server does not need to always be running (A Minecraft Java server requires a lot of CPU and Memory even idle.).
But I want my friends to be able to play whenever they want.

### Detecting the server is empty

Using [mcstatus](https://github.com/py-mine/mcstatus), we can ping the Minecraft server, to get the number of player currently playing.
When the server is running a ping is sent every X seconds. After a certain number of pings with 0 player, the server is shutdown.

When the server is set offline, a fake minecraft server is started, using [FakeMCServer](https://github.com/ZockerSK/FakeMCServer).
This will display a message informing any player wanted to join that the server is currently offline.
![img.png](screenshots/mc_server_list_offline.png)

### Starting the server when requested

If a player try to join the server, the FakeMCServer will handle the request then kick him. Finally, it will automatically start a new instance of a Minecraft Java Server.

# Issues

The bedrock cannot start the server. But I do not really need it since, it was just a test. It could be added in two ways:
- First remove the GeyserMC plugin from the Minecraft server, and use it as a Standalone proxy pointing to the k8s service "minecraft-server-java-service"
- Maybe GeyserMC has better performance as plugin instead of a standalone, therefore, it could be used as sidecar container of the Manager to redirect request from bedrock to the Fake instance when the real server is offline.
