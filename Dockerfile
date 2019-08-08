# NOTE: Only use this when you want to build image locally
#       else use `docker pull entynetproject\Invader:{VERSION}`
#       all image versions can be found at: https://hub.docker.com/r/entynetproject/Invader/

# -----BUILD COMMANDS----
# 1) build command: `docker build -t entynetproject/Invader .`
# 2) create volume storage: `docker create -v /opt/Invader --name data entynetproject/Invader`
# 3) run out container: `docker run -ti --volumes-from data entynetproject/Invader /bin/bash`

# -----RELEASE COMMANDS----
# 1) `USERNAME=entynetproject`
# 2) `IMAGE=Invader`
# 3) `git pull`
# 4) `export VERSION="$(curl -s https://raw.githubusercontent.com/entynetproject/Invader/master/lib/common/invader.py | grep "VERSION =" | cut -d '"' -f2)"`
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
LABEL description="Dockerfile base for Invader server."
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

# build Invader from source
# TODO: When we merge to master set branch to master
RUN git clone --depth=1 -b dev https://github.com/entynetproject/Invader.git /opt/Invader && \
    cd /opt/Invader/setup/ && \
    ./install.sh && \
    rm -rf /opt/Invader/data/Invader*
RUN python2.7 /opt/Invader/setup/setup_database.py
WORKDIR "/opt/Invader"
CMD ["python2.7", "Invader"]
