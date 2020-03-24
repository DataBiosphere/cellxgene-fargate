include common.mk

all: check_environment
	@echo "Looking good!"

check_environment:
	@if test -z "$$project_root"; then echo -e "\nError: Run 'source environment' first\n"; false; fi

check_venv:
	@if test -z "$$VIRTUAL_ENV"; then echo -e "\nError: Run 'source .venv/bin/activate' first\n"; false; fi

check: check_environment check_venv

virtualenv:
	@if test -s "$$VIRTUAL_ENV"; then echo -e "\nRun 'deactivate' first\n"; false; fi
	if test -e .venv; then rm -rf .venv/; fi
	python3.6 -m venv .venv
	.venv/bin/pip install -U pip==10.0.1 setuptools==40.1.0 wheel==0.32.3
	@echo -e "\nRun 'source .venv/bin/activate' now!\n"

envhook: check_venv
	python scripts/envhook.py install

requirements: check
	.venv/bin/pip install -Ur requirements.txt

requirements.dev: check
	.venv/bin/pip install -Ur requirements.dev.txt

image=$(CELLXGENE_IMAGE)
tag=$(CELLXGENE_VERSION)

docker_repository: check
	aws ecr create-repository --repository-name $(image)

docker_image: check
	docker build -t $(image):$(tag) --build-arg CELLXGENE_VERSION=$(CELLXGENE_VERSION) .

docker_run: check
	docker run $(image):$(tag)

docker_login: check
	python scripts/docker_login.py

docker_push: check
	export remote_image=`aws ecr describe-repositories --repository-names $(image) --output text --query repositories[0].repositoryUri` \
		&& docker tag $(image):$(tag) $$remote_image:$(tag) \
		&& docker push $$remote_image:$(tag)

terraform: check
	$(MAKE) -C terraform

.PHONY: all check_venv check_environment check \
		venv envhook requirements requirements.dev \
		docker_repository docker_image docker_login docker_push
