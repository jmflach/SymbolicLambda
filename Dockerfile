FROM nvidia/cuda:11.3.1-base-ubuntu20.04

RUN apt-get update
RUN apt-get upgrade -y



RUN apt install -y \
    git python3 ca-certificates wget sudo


RUN python3 --version

RUN apt-get -y install git

# Install pip
RUN apt-get install python3-pip -y

RUN pip3 --version

RUN pip3 install --upgrade pip

RUN pip3 --version

RUN python3 -V

#RUN pip3 --version

# set the working directory in the container
WORKDIR /code

# copy the dependencies file to the working directory
COPY requirements.txt .

# install dependencies
RUN pip install -r requirements.txt

# copy the content of the local src directory to the working directory
COPY . .

# command to run on container start
CMD [ "./evaluation.sh", "" ]
