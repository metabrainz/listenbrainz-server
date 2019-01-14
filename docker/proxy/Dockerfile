FROM ubuntu:18.04


RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    wget \
    openssh-server \
    vim \
    dnsutils

WORKDIR /root

# ssh without key
RUN mkdir .ssh && \
    chmod 700 .ssh && \
    chmod go-w ~/
RUN ssh-keygen -t rsa -f .ssh/id_rsa -P '' && \
    cat .ssh/id_rsa.pub >> .ssh/authorized_keys
RUN chmod 600 .ssh/authorized_keys
RUN echo "AllowTCPForwarding yes" >> /etc/ssh/sshd_config
RUN echo "PermitOpen any" >> /etc/ssh/sshd_config

COPY ssh_config .ssh/config
COPY keys/*.pub /tmp/ 
RUN cat /tmp/*.pub >> .ssh/authorized_keys

CMD [ "sh", "-c", "service ssh start; bash"]
