{% for cert in salt['pillar.get']('certs') %}
/home/ubuntu/certs/{{ cert }}:
    file.managed:
      - source: salt://certs/{{ cert }}
      - user: root
      - mode: 644
      - makedirs: true
{% endfor %}
