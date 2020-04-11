all: apply

include ../../common.mk

config: $(patsubst %.template.py,%,$(wildcard *.tf.json.template.py))

package.zip: app.py
	zip package.zip app.py

init: config package.zip
	terraform init

validate: init
	terraform validate

plan: validate
	terraform plan

apply: validate
	terraform apply

auto_apply: validate
	terraform apply -auto-approve

destroy: validate
	terraform destroy

auto_destroy: validate
	@echo '!!! All resources will be deleted in 10s, hit Ctrl-C to cancel !!!'; sleep 10
	terraform destroy -auto-approve

clean:
	rm -f *.tf.json

.PHONY: all config init validate plan apply auto_apply destroy auto_destroy clean
