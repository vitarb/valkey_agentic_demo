FROM alpine:3.19
RUN apk add --no-cache go git build-base
COPY .tools /usr/local/.tools
ENV PATH=/usr/local/.tools/bin:$PATH
RUN /usr/local/.tools/bootstrap.sh
