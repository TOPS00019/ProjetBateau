* ATTENTION : code pensé pour être exécuté en local, ou sur le même réseau local.

* Modules à télécharger : dotenv, numpy.

* Penser à créer un fichier .env avec ce modèle :

```
SERVER_IP="Adresse IPv4 locale de la machine"
SERVER_IP_NETMASK="Netmask de l'adresse IPv4 de la machine"
87B_CHANNEL_RECEPTION_PORT=6666
88B_CHANNEL_RECEPTION_PORT=7777
87B_CHANNEL_BROADCAST_PORT=8888
88B_CHANNEL_BROADCAST_PORT=9999
```

* D'abord exécuter server.py, puis main_boat.py (autant de fois que l'on souhaite de bateaux).
