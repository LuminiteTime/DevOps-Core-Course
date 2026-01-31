FROM eclipse-temurin:25-jdk AS builder

WORKDIR /workspace

COPY gradlew build.gradle settings.gradle ./
COPY gradle/ gradle/
RUN chmod +x gradlew

RUN ./gradlew --no-daemon --version

COPY src/ src/
RUN ./gradlew --no-daemon clean bootJar

FROM eclipse-temurin:25-jre

WORKDIR /app

RUN addgroup --system app && adduser --system --ingroup app app

COPY --from=builder /workspace/build/libs/appJava-0.0.1-SNAPSHOT.jar /app/app.jar
RUN chown -R app:app /app

USER app

EXPOSE 8081

CMD ["java", "-jar", "/app/app.jar"]
