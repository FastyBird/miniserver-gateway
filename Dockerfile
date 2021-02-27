FROM python:3.7-slim
ADD ./ /

RUN echo '#Main start script\n\
CONF_FOLDER="./miniserver_gateway/config"\n\
firstlaunch=${CONF_FOLDER}/.firstlaunch\n\
\n\
if [ ! -f ${firstlaunch} ]; then\n\
    cp -r /default-config/config/* /miniserver_gateway/config/\n\
    touch ${firstlaunch}\n\
    echo "#Remove this file only if you want to recreate default config files! This will overwrite exesting files" > ${firstlaunch}\n\
fi\n\
echo "nameserver 8.8.8.8" >> /etc/resolv.conf\n\
\n\
python ./miniserver_gateway/tb_gateway.py\n\
'\
>> start-gateway.sh && chmod +x start-gateway.sh

ENV PATH="/root/.local/bin:$PATH"
ENV configs /miniserver_gateway/config
ENV logs /miniserver_gateway/logs

RUN apt-get update && apt-get install gcc -y
RUN pip3 install importlib_metadata --user
RUN python /setup.py install && cp -r /miniserver_gateway/config/* /default-config/config/

VOLUME ["${configs}", "${logs}"]

CMD [ "/bin/sh", "./start-gateway.sh" ]