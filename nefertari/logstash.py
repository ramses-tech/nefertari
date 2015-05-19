from __future__ import absolute_import
import logging
import logstash

from nefertari.utils import dictset
log = logging.getLogger(__name__)


def includeme(config):
    log.info('Including logstash')
    Settings = dictset(config.registry.settings)

    try:
        if not Settings.asbool('logstash.enable'):
            log.warning('Logstash is disabled')
            return

        if Settings.asbool('logstash.check'):
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            deftimeout = sock.gettimeout()
            sock.settimeout(3)
            try:
                sock.sendto(
                    'PING', 0,
                    (Settings['logstash.host'],
                        Settings.asint('logstash.port')))
                recv, svr = sock.recvfrom(255)
                sock.shutdown(2)
            except Exception as e:
                log.error('Looks like logstash server is not running: %s' % e)
            finally:
                sock.settimeout(deftimeout)

        logger = logging.getLogger()
        handler = logstash.LogstashHandler(
            Settings['logstash.host'],
            Settings.asint('logstash.port'),
            version=1)
        handler.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)-5.5s [%(name)s][%(threadName)s] "
            "%(module)s.%(funcName)s: %(message)s"))
        logger.addHandler(handler)

    except KeyError as e:
        log.warning('Bad settings for logstash. %s' % e)
