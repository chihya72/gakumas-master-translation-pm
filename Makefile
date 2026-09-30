SHELL := pwsh.exe
.SHELLFLAGS := -NoLogo -NoProfile -Command

update:
	[string[]]$$arguments = @('scripts\update_master_data.py'); & python @arguments; if ($$LASTEXITCODE -ne 0) { exit $$LASTEXITCODE }

backup:
	python scripts/pretranslate_process.py --backup

gen-todo:
	python scripts/pretranslate_process.py --gen_todo

merge:
	python scripts/incremental_merge.py
