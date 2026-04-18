.PHONY: test

test:
	nix-shell -p "python3.withPackages(p: [p.pytest p.requests p.rich])" \
		--run "PYTHONPATH=src pytest tests/ -q"
