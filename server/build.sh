#!/bin/bash

if [ ! -f "/server/spigot.jar" ]; then
  mkdir /build/
  wget -O /build/BuildTools.jar https://hub.spigotmc.org/jenkins/job/BuildTools/lastSuccessfulBuild/artifact/target/BuildTools.jar
  java -jar /build/BuildTools.jar --rev "$REVISION"
  find '/build' -maxdepth 1 -iname 'spigot*.jar' -exec cp {} /server/spigot.jar \;
fi

cd /server || { echo "Cannot enter /server folder"; exit 1; }

mkdir /server/plugins

wget -O /server/plugins/Geyser-Spigot.jar https://ci.opencollab.dev/job/GeyserMC/job/Geyser/job/master/lastSuccessfulBuild/artifact/bootstrap/spigot/build/libs/Geyser-Spigot.jar
wget -O /server/plugins/Floodgate-Spigot.jar https://ci.opencollab.dev/job/GeyserMC/job/Floodgate/job/master/lastSuccessfulBuild/artifact/spigot/build/libs/floodgate-spigot.jar

# Ensure the EULA has been accepted.
if [ "$EULA" == "true" ]; then
  echo "eula=true" > eula.txt
else
  echo "You need to accept the eula by setting the env variable EULA to 'true'"
  exit 1
fi

cp /tmp/properties/server.properties server.properties
java -jar spigot.jar nogui
