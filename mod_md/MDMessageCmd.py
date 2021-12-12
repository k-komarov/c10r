#!/usr/bin/env python3

import sys
import os.path
import mysql.connector
import logging
import toml
import dns.resolver

cwd = os.path.dirname(os.path.realpath(__file__))
config = toml.load(cwd + "/MDMessageCmd.toml")
logging.basicConfig(filename=config["logger"]["file"],
                    format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("MDMessageCMD")
logger.setLevel(config["logger"]["level"])
logger.debug("Config: %s", config)

if not len(sys.argv) == 3:
    print(f"Error: Not enough arguments!")
    print(f"Usage: {sys.argv[0]} <mod_md status> <domain>")
    print(f"Example: {sys.argv[0]} installed example.com")
    sys.exit(1)

reason = sys.argv[1]
fqdn = sys.argv[2]


def set_https_flag(domain: str, enabled: bool = True):
    try:
        # Catches any domains that incorrectly have https = 1, but no certificate exists on the fs
        cursor.execute(config["domains"]["update_https_query"] % (1 if enabled == True else 0, domain))
        cnx.commit()
        logger.debug("Setting `https` flag for [%s]: '%s' %s", domain, enabled, query)
    except mysql.connector.Error as err:
        logger.error("Mysql error: %s", err)


logger.debug("Incoming MD message for [%s]: reason '%s'", fqdn, reason)
with mysql.connector.connect(
        host=config["mysql"]["host"] or "localhost",
        port=config["mysql"]["port"] or "3306",
        db=config["mysql"]["db"] or "domains",
        user=config["mysql"]["user"] or "root",
        password=config["mysql"]["password"] or ""
) as cnx:
    with cnx.cursor(dictionary=True) as cursor:
        query = config["domains"]["select_domain_query"] % fqdn
        cursor.execute(query)
        row = cursor.fetchone()
        logger.debug("Domain [%s] %s found: %s", fqdn, "NOT" if cursor.rowcount == 0 else "", query)

        if cursor.rowcount > 0:
            result = dns.resolver.resolve(fqdn, dns.rdatatype.CNAME)
            cname_target = config["domains"]["cname_target"]
            if all(str(cname).rstrip(".") != cname_target for cname in result):
                # todo: Probably, we should be notified somehow?
                logger.warning("Domain [%s] doesn't have CNAME %s DNS record", fqdn, cname_target)

            dns.resolver.resolve(row["subdomain"])
            if reason == "renewed":
                logger.warning("Renewed: %s", fqdn)

            if reason == "installed":
                logger.debug("Certificate installed for [%s]", fqdn)
                set_https_flag(fqdn, True)

            if reason == 'expiring':
                logger.debug("Certificate expiring for [%s]", fqdn)
                # todo: Why are we disabling it? renewal?
                set_https_flag(fqdn, False)

            if reason == 'errored':
                if not os.path.isfile(f"/mnt/nfs/md/domains/{fqdn}/pubcert.pem"):
                    set_https_flag(fqdn, False)
