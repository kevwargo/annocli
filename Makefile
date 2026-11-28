.PHONY: test

test:
	for v in 3.{10..15} ; do \
		printf "\n%s\n" $$v ; \
		docker run -it --rm -v ./:/app -w /app python:$$v python test.py \
			$(A) 2>&1 | tee test-$$v.log ; \
	done
