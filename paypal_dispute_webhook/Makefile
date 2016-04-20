BUILD_DIR=_build
OUTPUT_FILE=lambda.zip

package:
	mkdir -p $(BUILD_DIR)
	pip install -r requirements.txt -t $(BUILD_DIR) --no-compile
	cp dispute_ticket_creator.py $(BUILD_DIR)
	cd $(BUILD_DIR) && zip -r --exclude=*.pyc* --exclude=$(OUTPUT_FILE) $(OUTPUT_FILE) .
