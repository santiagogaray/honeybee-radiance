FROM python:3.6

WORKDIR /tmp/
RUN curl -L https://github.com/NREL/Radiance/releases/download/5.2/radiance-5.2.dd0f8e38a7-Linux.tar.gz | tar xz \
&& mv `ls`/usr/local/radiance/bin/* /usr/local/bin \
&& mv `ls`/usr/local/radiance/lib/* /usr/local/lib \
&& rm -rf `ls`

WORKDIR /usr/app/

COPY . .
RUN pip install .[cli]