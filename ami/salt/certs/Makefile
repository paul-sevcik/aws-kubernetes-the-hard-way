GENCERT=./cfssl gencert -ca=ca.pem -ca-key=ca-key.pem -config=ca-config.json -profile=kubernetes

all: ca.pem admin.pem kube-proxy.pem kubernetes.pem

cfssl:
	wget https://pkg.cfssl.org/R1.2/cfssl_darwin-amd64
	chmod +x cfssl_darwin-amd64
	mv cfssl_darwin-amd64 cfssl

cfssljson:
	wget https://pkg.cfssl.org/R1.2/cfssljson_darwin-amd64
	chmod +x cfssljson_darwin-amd64
	mv cfssljson_darwin-amd64 cfssljson

ca.pem ca-key.pem: cfssl cfssljson
	./cfssl gencert -initca ca-csr.json | ./cfssljson -bare ca
	rm admin.csr

admin.pem: ca.pem ca-key.pem
	$(GENCERT) admin-csr.json | ./cfssljson -bare admin

kube-proxy.pem: ca.pem ca-key.pem
	$(GENCERT) admin-csr.json | ./cfssljson -bare kube-proxy

kubernetes.pem: ca.pem ca-key.pem
	KUBERNETES_PUBLIC_ADDRESS=$(curl http://api.ipaddress.com/myip) $(GENCERT) kubernetes-csr.json | ./cfssljson -bare kubernetes

clean:
	rm admin.pem admin-key.pem ca.pem ca-key.pem kubernetes.pem kubernetes-key.pem kube-proxy.pem kube-proxy-key.pem
