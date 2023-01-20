FROM openjdk:16.0.2-jdk-bullseye

COPY build.sh /build.sh

RUN chmod +755 /build.sh

WORKDIR "/build"
CMD ["/build.sh"]
