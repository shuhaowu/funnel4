SOURCE_FILES := $(shell find src/ -type f -print)

.PHONY: clean server

out: $(SOURCE_FILES)
	funnel4
	touch out # To make the timestamp workout

server:
	cd out && python -m http.server

clean:
	rm -r out
