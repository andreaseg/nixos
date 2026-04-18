{ pkgs, ... }:

{
  home.packages = [
    (pkgs.writers.writePython3Bin "jisho"
      { libraries = with pkgs.python3Packages; [ requests rich ]; }
      (builtins.readFile ./jisho.py)
    )
  ];
}
