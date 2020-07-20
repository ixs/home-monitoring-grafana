FROM python:3.8-alpine as base
RUN apk add --no-cache libusb libusb-dev binutils

FROM base as builder
RUN apk add --no-cache git gcc g++ musl-dev linux-headers yaml-dev libusb-dev
COPY requirements.txt .
RUN pip3 install --prefix=/usr/local --no-warn-script-location -r ./requirements.txt --verbose

FROM base
LABEL maintainer="Andreas Thienemann" \
      description="PylArexx to InfluxDB Bridge"

COPY --from=builder /usr/local /usr/local

COPY . /app
WORKDIR /app

CMD ["python3", "-u", "pylarexx.py", "-f", "pylarexx.yaml", "-vv"]
