/usr/local/bin/goss:
    file.managed:
      - source: https://github.com/aelsabbahy/goss/releases/download/v0.3.2/goss-linux-amd64
      - source_hash: a2bfa480663226a8a267fecef90a55112f270720ef366f3f752f84e9644b94068318d4384bfea6a7f28bf13ccab0dcd80eb925d1a50f3a15342806590fcb3e1a
      - user: root
      - mode: 755
      - makedirs: true

/usr/local/etc/goss.yaml:
    file.managed:
      - source: salt://goss/goss.yaml
      - user: root
      - mode: 644
      - makedirs: true

/usr/local/share/goss.d/ping.yaml:
    file.managed:
      - source: salt://goss/ping.yaml
      - user: root
      - mode: 644
      - makedirs: true
