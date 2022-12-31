FROM openjdk:18.0.2.1-jdk-bullseye

COPY build.sh /build.sh

RUN chmod +755 /build.sh

WORKDIR "/build"
CMD ["/build.sh"]
