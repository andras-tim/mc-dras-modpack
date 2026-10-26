# packwiz has no releases; pinned to a main commit
FROM golang:1.25 AS build
RUN CGO_ENABLED=0 go install github.com/packwiz/packwiz@170b22d785959dda5876b54b7f16e1b807a57fb6
FROM debian:stable-slim
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates git && rm -rf /var/lib/apt/lists/*
COPY --from=build /go/bin/packwiz /usr/local/bin/packwiz
WORKDIR /pack
ENTRYPOINT ["packwiz"]
