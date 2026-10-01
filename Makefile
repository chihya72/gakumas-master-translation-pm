update:
	python scripts/update_master_data.py

backup:
	python scripts/pretranslate_process.py --backup

gen-todo:
	python scripts/pretranslate_process.py --gen_todo

merge:
	python scripts/incremental_merge.py
