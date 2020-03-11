all: check_environment
	@echo "Looking good!"

check_environment:
	@if test -z "$$cxgf_home"; then echo "\nRun 'source environment' first\n"; false; fi

check_venv:
	@if test -z "$$VIRTUAL_ENV"; then echo "\nRun 'source .venv/bin/activate' first\n"; false; fi

check: check_environment check_venv

virtualenv:
	@if test -s "$$VIRTUAL_ENV"; then echo "\nRun 'deactivate' first\n"; false; fi
	if test -e .venv; then rm -rf .venv/; fi
	python3.6 -m venv .venv
	.venv/bin/pip install -U pip==10.0.1 setuptools==40.1.0 wheel==0.32.3
	@echo "\nRun 'source .venv/bin/activate' now!\n"

requirements: check
	.venv/bin/pip install -Ur requirements.txt

requirements.dev: check
	.venv/bin/pip install -Ur requirements.dev.txt

image=$(CELLXGENE_IMAGE)
tag=$(CELLXGENE_VERSION)

docker_repository: check
	aws ecr create-repository --repository-name $(image)

docker_image: check
	docker build -t $(image):$(tag) .

docker_run: check
	docker run $(image):$(tag)

docker_login: check
	python scripts/docker_login.py

docker_push: check
	export remote_image=`aws ecr describe-repositories --repository-names $(image) --output text --query repositories[0].repositoryUri` \
		&& docker tag $(image):$(tag) $$remote_image:$(tag) \
		&& docker push $$remote_image:$(tag)

.PHONY: all check_venv check_environment check \
		venv requirements requirements.dev \
		docker_repository docker_image docker_login docker_push
