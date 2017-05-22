KUBE_AMIS=controller.ami worker.ami
SALT_STATES=salt/top.sls salt/goss.sls salt/certs.sls

all: build

build: $(KUBE_AMIS)

clean:
	rm -f $(KUBE_AMIS)

%.ami: kube.json $(SALT_STATES)
	rm -f $@
	packer validate -var kube_node_type=$(basename $(notdir $@)) $<
	packer build -var kube_node_type=$(basename $(notdir $@)) $<

controller.ami: kube.json

worker.ami: kube.json
