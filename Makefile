.PHONY: test

test:
	for v in 3.{11..15} ; do \
		printf "\n%s\n" $$v ; \
		docker run -it --rm -v ./:/app -w /app python:$$v python test.py \
			2>&1 | tee test-$$v.log ; \
	done
