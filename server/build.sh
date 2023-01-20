#!/bin/bash

if [ ! -f "/server/$REVISION/spigot.jar" ]; then
  # Create build directory
  mkdir -p "/build/$REVISION"
  # Create server directory
  mkdir -p "/server/$REVISION"
  # Get latest BuildTools.jar
  wget -nv -O /build/BuildTools.jar https://hub.spigotmc.org/jenkins/job/BuildTools/lastSuccessfulBuild/artifact/target/BuildTools.jar
  # Building server for the targeted version
  java -jar /build/BuildTools.jar --rev "$REVISION" --output-dir "/build/$REVISION"
  # Get the spigot created
  find "/build/$REVISION" -maxdepth 1 -iname 'spigot*.jar' -exec cp {} "/server/$REVISION/spigot.jar" \;
fi

# Set current directory to our server root
cd "/server/$REVISION" || { echo "Cannot enter /server folder"; exit 1; }

mkdir "/server/$REVISION/plugins"

if [ "$BEDROCK" == "true" ]; then
  wget -nv -O "/server/$REVISION/plugins/Geyser-Spigot.jar" https://ci.opencollab.dev/job/GeyserMC/job/Geyser/job/master/lastSuccessfulBuild/artifact/bootstrap/spigot/build/libs/Geyser-Spigot.jar
  wget -nv -O "/server/$REVISION/plugins/Floodgate-Spigot.jar" https://ci.opencollab.dev/job/GeyserMC/job/Floodgate/job/master/lastSuccessfulBuild/artifact/spigot/build/libs/floodgate-spigot.jar
else

# Ensure the EULA has been accepted.
if [ "$EULA" == "true" ]; then
  echo "INFO: EULA accepted."
  echo "eula=true" > "/server/$REVISION/eula.txt"
else
  echo "You need to accept the eula by setting the env variable EULA to 'true'"
  exit 1
fi

if [ ! -f "/server/$REVISION/server.properties" ]; then
  echo "INFO: The server.properties from the configmap is copied to the server root."
  cp /tmp/properties/server.properties "/server/$REVISION/server.properties"
else
  echo "WARNING: The server.properties is already present in the server root directory, it will not be updated."
fi

java -DIReallyKnowWhatIAmDoingISwear -jar spigot.jar nogui
