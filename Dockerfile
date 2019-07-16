# NOTE: Only use this when you want to build image locally
#       else use `docker pull entynetproject\invader:{VERSION}`
#       all image versions can be found at: https://hub.docker.com/r/entynetproject/invader/

# -----BUILD COMMANDS----
# 1) build command: `docker build -t entynetproject/invader .`
# 2) create volume storage: `docker create -v /opt/invader --name data entynetproject/invader`
# 3) run out container: `docker run -ti --volumes-from data entynetproject/invader /bin/bash`

# -----RELEASE COMMANDS----
# 1) `USERNAME=entynetproject`
# 2) `IMAGE=invader`
# 3) `git pull`
# 4) `export VERSION="$(curl -s https://raw.githubusercontent.com/entynetproject/invader/master/lib/common/invader.py | grep "VERSION =" | cut -d '"' -f2)"`
# 5) `docker tag $USERNAME/$IMAGE:latest $USERNAME/$IMAGE:$VERSION`
# 1) `docker push $USERNAME/$IMAGE:latest`
# 2) `docker push $USERNAME/$IMAGE:$VERSION`

# -----BUILD ENTRY-----

# image base
FROM ubuntu:16.04

# pull from BUILD
ARG empirversion

# extra metadata
LABEL maintainer="entynetproject"
LABEL description="Dockerfile base for invader server."
LABEL version=${empirversion}

# env setup
ENV STAGING_KEY=RANDOM
ENV DEBIAN_FRONTEND=noninteractive

# set the def shell for ENV
SHELL ["/bin/bash", "-c"]

# install basic build items
RUN apt-get update && apt-get install -qy \
    wget \
    curl \
    git \
    sudo \
    apt-utils \
    lsb-core \
    python2.7 \
    python-dev \
  && ln -sf /usr/bin/python2.7 /usr/bin/python \  
  && rm -rf /var/lib/apt/lists/*

# build invader from source
# TODO: When we merge to master set branch to master
RUN git clone --depth=1 -b dev https://github.com/entynetproject/invader.git /opt/invader && \
    cd /opt/invader/setup/ && \
    ./install.sh && \
    rm -rf /opt/invader/data/invader*
RUN python2.7 /opt/invader/setup/setup_database.py
WORKDIR "/opt/invader"
CMD ["python2.7", "invader"]
